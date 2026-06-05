import pandas as pd
import numpy as np
import datetime

import Risk_Engine as risk_engine
import RiseFall_sub as rise_fall
import indicator_engine as Indicators
import SafetyLogger
from System_Config import (
    STRONG_BUY_THRESHOLD, BUY_THRESHOLD, WATCHLIST_THRESHOLD, MIN_PREMIUM_THRESHOLD, TACTICAL_LOOKBACK, EXHAUSTION_WINDOW,
    PE_EXHAUSTION_WINDOW, MAX_NIFTY_DROP, NIFTY_DROP_WINDOW,
    PCR_BULLISH, PCR_BEARISH, NORMAL_ITM_DISTANCE, GAP_ITM_DISTANCE,
    OI_CHANGE_ALERT_PCT, TARGET_POINTS, INITIAL_SL_POINTS,
    DEPLOYED_CAPITAL, LOT_SIZES, DEFAULT_LOT_SIZE, BASE_RSI_POINTS,
    GAP_RISK_THRESHOLD, MARGIN_REQUIREMENT_PCT
)


def get_time_slot_and_multiplier(now=None):
    try:
        if now is None:
            now = datetime.datetime.now()
        t = now.time()
        if t < datetime.time(10, 0):
            return "Opening (9:15-10:00)", 1.2
        if t < datetime.time(11, 30):
            return "Morning (10:00-11:30)", 1.0
        if t < datetime.time(14, 0):
            return "Midday (11:30-14:00)", 0.9
        if t <= datetime.time(15, 30):
            return "Afternoon (14:00-15:30)", 1.0
        return "Post-market", 0.0
    except Exception as e:
        SafetyLogger.log_error_with_context("Option_strategy_core", "get_time_slot_and_multiplier", e)
        return "Unknown", 1.0

# 4

def validate_itm_distance(nifty_spot, strike, option_type, gap_mode=False):
    try:
        if strike is None or nifty_spot is None:
            return False
        strike = float(strike)
        nifty_spot = float(nifty_spot)
        required_distance = GAP_ITM_DISTANCE if gap_mode else NORMAL_ITM_DISTANCE

        if option_type == "CE":
            return strike <= (nifty_spot - required_distance)
        if option_type == "PE":
            return strike >= (nifty_spot + required_distance)
        return False
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "validate_itm_distance", e,
            {"nifty_spot": nifty_spot, "strike": strike, "option_type": option_type, "gap_mode": gap_mode}
        )
        return False

# 5

def validate_oi_barrier_distance(nifty_spot, option_type, option_chain_df, min_distance=60):
    try:
        if option_chain_df is None or option_chain_df.empty:
            return True, 0
            
        opt_types = option_chain_df['option_type'].to_numpy(dtype=object)
        strikes = option_chain_df['strike'].values
        ois = option_chain_df['oi'].values if 'oi' in option_chain_df.columns else np.zeros(len(option_chain_df))
            
        if option_type == "CE":
            mask = (opt_types == 'CE') & (strikes > nifty_spot)
            if not np.any(mask):
                return True, 0
                
            max_oi_idx = np.argmax(ois[mask])
            highest_oi_strike = strikes[mask][max_oi_idx]
            
            distance = highest_oi_strike - nifty_spot
            return (distance >= min_distance), highest_oi_strike

        if option_type == "PE":
            mask = (opt_types == 'PE') & (strikes < nifty_spot)
            if not np.any(mask):
                return True, 0
                
            max_oi_idx = np.argmax(ois[mask])
            highest_oi_strike = strikes[mask][max_oi_idx]
            
            distance = nifty_spot - highest_oi_strike
            return (distance >= min_distance), highest_oi_strike

        return False, 0
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "validate_oi_barrier_distance", e,
            {"nifty_spot": nifty_spot, "option_type": option_type, "df_len": len(option_chain_df) if option_chain_df is not None else 0}
        )
        return True, 0 # Return benign state as fallback so we do not block trades unnecessarily

def validate_volume_support(option_type, option_chain_df, min_ratio=1.2):
    try:
        if option_chain_df is None or option_chain_df.empty:
            return True
            
        opt_types = option_chain_df['option_type'].to_numpy(dtype=object)
        if 'volume' in option_chain_df.columns:
            vols = option_chain_df['volume'].values
        else:
            vols = np.zeros(len(option_chain_df))
            
        total_ce_vol = np.sum(vols[opt_types == 'CE'])
        total_pe_vol = np.sum(vols[opt_types == 'PE'])
        
        if total_ce_vol == 0 or total_pe_vol == 0:
            return False
            
        if option_type == "CE":
            return total_ce_vol > (total_pe_vol * min_ratio)
            
        if option_type == "PE":
            return total_pe_vol > (total_ce_vol * min_ratio)
            
        return False
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "validate_volume_support", e,
            {"option_type": option_type, "df_len": len(option_chain_df) if option_chain_df is not None else 0}
        )
        return True # Fallback to True

# =========================================================
# SUPPORT FOR VOL & OI MONITOR (called by scanner_excel.py)
# =========================================================

def check_volume_ema_cross(symbol, current_volume):
    try:
        discrete_volume, volume_ema = Indicators.parse_discrete_1m_volume(symbol, current_volume)
        return discrete_volume > volume_ema
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "check_volume_ema_cross", e,
            {"symbol": symbol, "current_volume": current_volume}
        )
        return False

def check_oi_change_alert(opt_row):
    try:
        if not isinstance(opt_row, dict):
            return False
        oi_change = opt_row.get("oi_change", 0)
        return oi_change >= OI_CHANGE_ALERT_PCT
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "check_oi_change_alert", e,
            {"opt_row_keys": list(opt_row.keys()) if isinstance(opt_row, dict) else type(opt_row)}
        )
        return False

# =========================================================
# BUILD SCORE
# =========================================================

def build_score(opt_row, option_type, df_1m, pcr_value=1.0, gap_mode=False):
    try:
        score = 60
        symbol = opt_row["symbol"]
        cumulative_volume = opt_row.get("volume", 0)
        oi_change = opt_row.get("oi_change", 0)

        discrete_volume, volume_ema = Indicators.parse_discrete_1m_volume(symbol, cumulative_volume)

        # -----------------------------------------
        # VOLUME EXPANSION
        # -----------------------------------------
        if gap_mode:
            if discrete_volume > (volume_ema * 1.5):
                score += 15
            else:
                score -= 15
        else:
            if discrete_volume > volume_ema:
                score += 15
            else:
                score -= 10

        # -----------------------------------------
        # ADX PENALTY
        # -----------------------------------------
        if "ADX" in df_1m.columns:
            adx_val = df_1m["ADX"].iloc[-1]
            if not pd.isna(adx_val):
                if adx_val < 18:
                    score -= 15
                elif 18 <= adx_val < 22:
                    score -= 5

        # -----------------------------------------
        # 15-MINUTE TREND FILTER
        # -----------------------------------------
        if "EMA_15m_20" in df_1m.columns and "EMA_15m_50" in df_1m.columns:
            ema_15m_20 = df_1m["EMA_15m_20"].iloc[-1]
            ema_15m_50 = df_1m["EMA_15m_50"].iloc[-1]
            if not pd.isna(ema_15m_20) and not pd.isna(ema_15m_50):
                if option_type == "CE":
                    if ema_15m_20 > ema_15m_50:
                        score += 15
                    else:
                        score -= 20
                elif option_type == "PE":
                    if ema_15m_20 < ema_15m_50:
                        score += 15
                    else:
                        score -= 20

        # -----------------------------------------
        # OI BUILDUP & PREMIUM
        # -----------------------------------------
        prev_oi = opt_row.get("previous_oi") or 1
        oi_change_pct = (oi_change / prev_oi * 100) if prev_oi > 0 else 0
        
        prev_close = float(opt_row.get("previous_close") or opt_row.get("close") or 0.0)
        option_ltp = float(opt_row.get("ltp") or 0.0)
        premium_change_pct = ((option_ltp - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
        
        if oi_change > 5:
            if premium_change_pct > 0 and oi_change_pct > 0 and discrete_volume > volume_ema:
                base_buildup_score = 15
            else:
                base_buildup_score = 5
                
            if oi_change_pct < 2.0:
                calc_score = int(base_buildup_score * 0.5)
            elif oi_change_pct <= 5.0:
                calc_score = int(base_buildup_score * 1.0)
            else:
                calc_score = int(base_buildup_score * 1.5)
            score += min(20, calc_score)
        elif oi_change < -2:
            score -= 15

        # -----------------------------------------
        # PREMIUM STRENGTH
        # -----------------------------------------
        option_vwap = float(opt_row.get("option_vwap") or 0.0)
        if option_type in ["CE", "PE"]:
            if option_ltp > option_vwap:
                score += 10
            else:
                score -= 10

        # -----------------------------------------
        # VWAP + EMA ALIGNMENT
        # -----------------------------------------
        row = df_1m.iloc[-2]
        close_price = row["close"]
        vwap_price = row["VWAP"]
        ema9 = row["EMA9"]
        ema20 = row["EMA20"]

        if option_type == "CE":
            if close_price >= vwap_price and ema9 > ema20:
                score += 10
            else:
                score -= 15

        if option_type == "PE":
            if close_price <= vwap_price and ema9 < ema20:
                score += 10
            else:
                score -= 15

        # -----------------------------------------
        # PCR
        # -----------------------------------------
        if option_type == "CE":
            if pcr_value > PCR_BULLISH:
                score += 10

        if option_type == "PE":
            if pcr_value < PCR_BEARISH:
                score += 10

        # -----------------------------------------
        # TIME-WEIGHTED RSI BREAKOUT SCORE
        # -----------------------------------------
        current_rsi = Indicators.calculate_rsi(df_1m)
        
        if "datetime" in row.index:
            tick_time = row["datetime"]
        elif hasattr(row, "name") and isinstance(row.name, pd.Timestamp):
            tick_time = row.name
        else:
            tick_time = datetime.datetime.now()
            
        _, time_multiplier = get_time_slot_and_multiplier(tick_time)
        
        # BASE_RSI_POINTS imported from System_Config
        
        if option_type == "CE":
             if current_rsi >= rise_fall.CE_RSI_TRIGGER:
                  score += (BASE_RSI_POINTS * time_multiplier)
             elif current_rsi < 50.0:
                  score -= 20
             if current_rsi < 40.0:
                  score -= 40
                
        if option_type == "PE":
             if current_rsi <= rise_fall.PE_RSI_TRIGGER:
                  score += (BASE_RSI_POINTS * time_multiplier)
             elif current_rsi < 40.0:
                  score += (5 * time_multiplier) 
             elif current_rsi > 50.0:
                  score -= 20
             if current_rsi > 55.0:
                  score -= 40

        score = max(0, min(score, 100))

        # --- ISOLATED DASHBOARD STATE EXPORT ---
        try:
            import json, os
            import datetime as dt_dash
            last_bar = df_1m.iloc[-1] if not df_1m.empty else {}
            
            ltp = float(last_bar.get("close", 0))
            vwap = float(last_bar.get("VWAP", 0))
            ema20 = float(last_bar.get("EMA20", 0))
            ema50 = float(last_bar.get("EMA50", 0))
            adx = float(last_bar.get("ADX", 0))
            ema9 = float(last_bar.get("EMA9", 0))
            
            state = {
                "timestamp": dt_dash.datetime.now().strftime("%H:%M:%S"),
                "symbol": symbol,
                "nifty_ltp": ltp,
                "vwap": vwap,
                "ema20": ema20,
                "ema50": ema50,
                "adx": adx,
                "trend_direction": "UP" if ema9 > ema20 else "DOWN",
                "pcr": float(pcr_value),
                "oi_change_pct": float(opt_row.get("oi_change_pct", 0)),
                "premium_change_pct": float(opt_row.get("premium_change_pct", 0)),
                "atm_iv": float(opt_row.get("iv", 0)),
                "bull_score": score,
                "score_breakdown": {
                    "trend": 15 if (ema9 > ema20) else -15,
                    "oi": 15 if opt_row.get("oi_change_pct", 0) < -2 else (-15 if opt_row.get("oi_change_pct", 0) > 5 else 5),
                    "vwap": 15 if ltp >= vwap else -15,
                    "volume": 15
                }
            }
            out_path = os.path.join(os.path.dirname(__file__), "..", "StreamLit Dashboard", "live_dashboard_state.json")
            with open(out_path, "w") as f:
                json.dump(state, f)
        except Exception:
            pass
        # ---------------------------------------

        return score
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "build_score", e,
            {"symbol": opt_row.get("symbol") if isinstance(opt_row, dict) else "Unknown", "option_type": option_type}
        )
        return 0

def build_and_score_contract(opt_row, option_type, df_1m, pcr_value=1.0):
    try:
        if not isinstance(opt_row, dict):
            return 0, {}
        if df_1m is None or df_1m.empty:
            return 0, {}
        work = Indicators.add_vwap(df_1m)
        work = Indicators.add_ema(work)
        work = Indicators.add_adx(work)
        score = build_score(opt_row, option_type, work, pcr_value=pcr_value, gap_mode=False)
        return score, {"score": score}
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "build_and_score_contract", e,
            {"option_type": option_type}
        )
        return 0, {}

def calculate_rsi_series(df, period=14):
    try:
        return Indicators.calculate_rsi_series(df, period)
    except Exception as e:
        SafetyLogger.log_error_with_context("Option_strategy_core", "calculate_rsi_series", e)
        return pd.Series(50.0, index=df.index if df is not None else [0])

def calculate_rsi(df, period=14):
    try:
        return Indicators.calculate_rsi(df, period)
    except Exception as e:
        SafetyLogger.log_error_with_context("Option_strategy_core", "calculate_rsi", e)
        return 50.0

# =========================================================
# SYSTEM STABILITY & NORMALIZATION UTILITIES
# =========================================================

# get_live_client extracted to broker_client.py — single source of truth
from broker_client import get_live_client

def is_atr_expanding(df_1m, period=14):
    try:
        if df_1m is None or df_1m.empty or len(df_1m) < period + 5:
            return True
        high = pd.to_numeric(df_1m['high'], errors='coerce')
        low = pd.to_numeric(df_1m['low'], errors='coerce')
        close = pd.to_numeric(df_1m['close'], errors='coerce')
        
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        atr_now = atr.iloc[-2]
        atr_prev = atr.iloc[-3]
        if len(atr) >= 20:
            atr_ma = atr.rolling(window=20).mean().iloc[-2]
            return (atr_now > atr_prev) or (atr_now > atr_ma)
        return (atr_now > atr_prev)
    except Exception:
        return True

def _normalize_args(args, kwargs):
    """
    Robust normalizer to handle keyword format vs incorrect positional order.
    """
    df_1m = kwargs.get("df_1m")
    option_type = kwargs.get("option_type")
    opt_row = kwargs.get("opt_row")
    nifty_spot = kwargs.get("nifty_spot")
    previous_close = kwargs.get("previous_close")
    today_open = kwargs.get("today_open")
    pcr_value = kwargs.get("pcr_value", 1.0)
    option_chain_df = kwargs.get("option_chain_df")

    if len(args) > 0:
        if len(args) == 9:
            df_1m = args[0]
            option_type = args[2]  # target_type is at index 2
            opt_row = args[3]     # candidate is at index 3
            nifty_spot = args[4]
            previous_close = args[5]
            today_open = args[6]
            pcr_value = args[7]
            option_chain_df = args[8]
        else:
            if len(args) >= 1: df_1m = args[0]
            if len(args) >= 2: option_type = args[1]
            if len(args) >= 3: opt_row = args[2]
            if len(args) >= 4: nifty_spot = args[3]
            if len(args) >= 5: previous_close = args[4]
            if len(args) >= 6: today_open = args[5]
            if len(args) >= 7: pcr_value = args[6]
            if len(args) >= 8: option_chain_df = args[7]

    return df_1m, option_type, opt_row, nifty_spot, previous_close, today_open, pcr_value, option_chain_df

# =========================================================
# MAIN TRIGGER
# =========================================================

def detect_trigger_1m(*args, **kwargs):
    try:
        df_1m, option_type, opt_row, nifty_spot, previous_close, today_open, pcr_value, option_chain_df = _normalize_args(args, kwargs)

        if df_1m is None or df_1m.empty or len(df_1m) < 30:
            return False
        if not isinstance(opt_row, dict):
            return False

        df_1m = Indicators.add_vwap(df_1m)
        df_1m = Indicators.add_ema(df_1m)
        df_1m = Indicators.add_adx(df_1m)

        gap_mode = risk_engine.detect_gap_risk(previous_close, today_open)

        strike = opt_row.get("strike")
        if not validate_itm_distance(nifty_spot, strike, option_type, gap_mode):
            return False

        # Runway Check
        is_far_enough, _ = validate_oi_barrier_distance(nifty_spot, option_type, option_chain_df, min_distance=60)
        if not is_far_enough:
            return False

        # Volume Support Check
        has_volume_support = validate_volume_support(option_type, option_chain_df, min_ratio=1.2)
        if not has_volume_support:
            return False

        rsi_series = Indicators.calculate_rsi_series(df_1m)
        
        # ---------------------------------------------------------
        # HARD KILL CONDITIONS (LIQUIDITY & RISK)
        # ---------------------------------------------------------
        if opt_row.get("volume", 0) <= 0:
            return False
            
        ltp_val = float(opt_row.get("ltp") or 0.0)
        if ltp_val < MIN_PREMIUM_THRESHOLD:
            return False

        ask_val = float(opt_row.get("ask") or 0.0)
        bid_val = float(opt_row.get("bid") or 0.0)
        if ask_val > 0:
            spread_pct = ((ask_val - bid_val) / ask_val) * 100
            if spread_pct > 2.0:
                return False

        if "ADX" in df_1m.columns:
            adx_val = df_1m["ADX"].iloc[-1]
            if not pd.isna(adx_val) and adx_val < 15:
                return False

        if len(rsi_series) > 0:
            rsi_val = rsi_series.iloc[-1]
            if option_type == "CE" and rsi_val < 40:
                return False
            if option_type == "PE" and rsi_val > 60:
                return False

        allowed = risk_engine.allow_trade(df_1m, rsi_series, option_type, previous_close, today_open)
        if not allowed:
            return False

        score = build_score(opt_row, option_type, df_1m, pcr_value, gap_mode)
        required_score = 92 if gap_mode else BUY_THRESHOLD
        if score < required_score:
            return False

        # =========================================================
        # DUAL NIFTY SPOT + OPTION PREMIUM RUNTIME EXECUTION GATE
        # =========================================================
        nifty_rsi = Indicators.calculate_rsi(df_1m)
        row = df_1m.iloc[-2]
        close_price = row["close"]
        vwap_price = row["VWAP"]
        ema20 = row["EMA20"]
        
        atr_expanding = is_atr_expanding(df_1m)
        
        symbol = opt_row.get("symbol")
        opt_rsi = 75.0
        opt_volume_spike = True
        
        if symbol:
            import os
            is_backtest = os.environ.get("IS_BACKTEST") == "1"
            tsl = None if is_backtest else get_live_client()
            if tsl:
                try:
                    should_fetch = True
                    if hasattr(tsl, "instrument_df") and tsl.instrument_df is not None:
                        try:
                            exch_db = 'BSE' if symbol.startswith(('SENSEX', 'BANKEX')) else 'NSE'
                            exists = not tsl.instrument_df[
                                ((tsl.instrument_df['SEM_TRADING_SYMBOL'] == symbol) | 
                                 (tsl.instrument_df['SEM_CUSTOM_SYMBOL'] == symbol)) &
                                (tsl.instrument_df['SEM_EXM_EXCH_ID'] == exch_db)
                            ].empty
                            if not exists:
                                should_fetch = False
                        except Exception:
                            pass
                    
                    if should_fetch:
                        exch_req = 'BFO' if symbol.startswith(('SENSEX', 'BANKEX')) else 'NFO'
                        opt_df = tsl.get_intraday_data(symbol, exch_req, 1)
                        if opt_df is not None and not opt_df.empty and len(opt_df) >= 15:
                            opt_rsi_series = Indicators.calculate_rsi_series(opt_df)
                            if len(opt_rsi_series) >= 2:
                                opt_rsi = opt_rsi_series.iloc[-2]
                                
                            opt_vol = pd.to_numeric(opt_df["volume"], errors="coerce").fillna(0.0)
                            discrete_v = opt_vol.iloc[-2]
                            vol_ema = opt_vol.rolling(window=20).mean().iloc[-2]
                            if vol_ema > 0:
                                opt_volume_spike = (discrete_v > (vol_ema * 1.5))
                except Exception as e:
                    print(f"[Core] Option premium analysis bypassed for {symbol}: {e}", flush=True)

        if option_type == "CE":
            import System_Config
            nifty_dir_pass = (System_Config.CE_RSI_TRIGGER <= nifty_rsi <= 90) and (close_price > ema20) and (close_price >= vwap_price)
            opt_exec_pass = opt_volume_spike
            
            # Check if Uptrend Pullback fallback strategy triggers
            import Uptrend_Buy
            fallback_signal = Uptrend_Buy.detect_uptrend_pullback_signal(df_1m)
            is_fallback = fallback_signal is not None and fallback_signal.get("signal") == "BUY"
            
            if is_fallback:
                # Bypass rigid CE RSI gate
                nifty_dir_pass = True
                
            if not (nifty_dir_pass and atr_expanding and opt_exec_pass):
                return False
                
        elif option_type == "PE":
            nifty_dir_pass = (nifty_rsi <= 40) and (close_price < ema20) and (close_price <= vwap_price)
            opt_exec_pass = opt_volume_spike
            
            # Check if Downtrend Rejection fallback strategy triggers (which allows RSI up to 55)
            import Downtrend_Sell
            fallback_signal = Downtrend_Sell.detect_downtrend_rejection_signal(df_1m)
            is_fallback = fallback_signal is not None and fallback_signal.get("signal") == "BUY"
            
            if is_fallback:
                # Bypass the rigid RSI <= 40 gate, since Downtrend_Sell checks its own dynamic filters
                nifty_dir_pass = True
                
            if not (nifty_dir_pass and atr_expanding and opt_exec_pass):
                return False

        current_rsi = Indicators.calculate_rsi(df_1m)
        row = df_1m.iloc[-2]
        
        if "ST_COLOR" in row:
            st_color = str(row["ST_COLOR"]).upper()
        elif "st_color" in row:
            st_color = str(row["st_color"]).upper()
        elif "ST" in row:
            st_color = "GREEN" if row["close"] >= row["ST"] else "RED"
        elif "supertrend" in row:
            st_color = "GREEN" if row["close"] >= row["supertrend"] else "RED"
        else:
            return False

        # Macro Exhaustion Check
        if option_type == "PE":
            index_30m_ago = df_1m["close"].iloc[-(NIFTY_DROP_WINDOW + 1)] if len(df_1m) > NIFTY_DROP_WINDOW else df_1m["close"].iloc[0]
            nifty_points_fallen = index_30m_ago - nifty_spot
            if nifty_points_fallen > MAX_NIFTY_DROP:
                return False

        tactical_slice = rsi_series.iloc[-(2 + TACTICAL_LOOKBACK):-1]
        ce_exhaustion_slice = rsi_series.iloc[-(2 + EXHAUSTION_WINDOW):-1]
        pe_exhaustion_slice = rsi_series.iloc[-(2 + PE_EXHAUSTION_WINDOW):-1]
        if option_type == "CE":
             if rise_fall.evaluate_ce_trigger(current_rsi, tactical_slice, ce_exhaustion_slice, st_color):
                  if isinstance(opt_row, dict):
                      opt_row["strategy_suffix"] = ""
                  return True
                          # Secondary fallback strategy for CE
             import Uptrend_Buy
             fallback_signal = Uptrend_Buy.detect_uptrend_pullback_signal(df_1m)
             if fallback_signal is not None and fallback_signal.get("signal") == "BUY":
                  SafetyLogger.log_info(f"Option_strategy_core | Uptrend strategy fallback triggered: {fallback_signal.get('reason')}")
                  if isinstance(opt_row, dict):
                      opt_row["strategy_suffix"] = "(U)"
                  return True

        if option_type == "PE":
             if rise_fall.evaluate_pe_trigger(current_rsi, tactical_slice, pe_exhaustion_slice, st_color):
                  if isinstance(opt_row, dict):
                      opt_row["strategy_suffix"] = ""
                  return True
              
             # Secondary fallback strategy
             import Downtrend_Sell
             fallback_signal = Downtrend_Sell.detect_downtrend_rejection_signal(df_1m)
             if fallback_signal is not None and fallback_signal.get("signal") == "BUY":
                  SafetyLogger.log_info(f"Option_strategy_core | Downtrend strategy fallback triggered: {fallback_signal.get('reason')}")
                  if isinstance(opt_row, dict):
                      opt_row["strategy_suffix"] = "(D)"
                  return True

        return False
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "detect_trigger_1m", e
        )
        return False

def explain_trigger_failure(*args, **kwargs):
    details = {}
    try:
        df_1m, option_type, opt_row, nifty_spot, previous_close, today_open, pcr_value, option_chain_df = _normalize_args(args, kwargs)

        if df_1m is None or df_1m.empty or len(df_1m) < 30:
            return False, "insufficient_1m_bars", details
        if not isinstance(opt_row, dict):
            return False, "invalid_contract_row", details

        work = Indicators.add_vwap(df_1m)
        work = Indicators.add_ema(work)
        work = Indicators.add_adx(work)
        gap_mode = risk_engine.detect_gap_risk(previous_close, today_open)
        details["gap_mode"] = gap_mode

        strike = opt_row.get("strike")
        if not validate_itm_distance(nifty_spot, strike, option_type, gap_mode):
            dist = NORMAL_ITM_DISTANCE if not gap_mode else GAP_ITM_DISTANCE
            details["required_itm_pts"] = dist
            return False, f"not_deep_itm_need_{dist}pt", details

        # Barrier check
        is_far_enough, major_barrier = validate_oi_barrier_distance(nifty_spot, option_type, option_chain_df, min_distance=60)
        details["major_barrier_strike"] = major_barrier
        if not is_far_enough:
            distance = abs(major_barrier - nifty_spot)
            return False, f"oi_barrier_too_close_{distance:.1f}pts", details
                
        # Volume checking
        has_volume_support = validate_volume_support(option_type, option_chain_df, min_ratio=1.2)
        details["volume_support_passed"] = has_volume_support
        if not has_volume_support:
            return False, "insufficient_directional_volume_ratio", details

        rsi_series = Indicators.calculate_rsi_series(work)
        
        # ---------------------------------------------------------
        # HARD KILL CONDITIONS (LIQUIDITY & RISK)
        # ---------------------------------------------------------
        if opt_row.get("volume", 0) <= 0:
            return False, "zero_volume_hard_kill", details
            
        ltp_val = float(opt_row.get("ltp") or 0.0)
        if ltp_val < MIN_PREMIUM_THRESHOLD:
            return False, f"ltp_{ltp_val:.1f}_below_min_premium_hard_kill", details
            
        ask_val = float(opt_row.get("ask") or 0.0)
        bid_val = float(opt_row.get("bid") or 0.0)
        if ask_val > 0:
            spread_pct = ((ask_val - bid_val) / ask_val) * 100
            if spread_pct > 2.0:
                return False, f"spread_{spread_pct:.1f}%_too_high_hard_kill", details

        if "ADX" in work.columns:
            adx_val = work["ADX"].iloc[-1]
            if not pd.isna(adx_val) and adx_val < 15:
                return False, f"adx_{adx_val:.1f}_below_15_hard_kill", details

        if len(rsi_series) > 0:
            rsi_val = rsi_series.iloc[-1]
            if option_type == "CE" and rsi_val < 40:
                return False, f"rsi_{rsi_val:.1f}_below_40_hard_kill", details
            if option_type == "PE" and rsi_val > 60:
                return False, f"rsi_{rsi_val:.1f}_above_60_hard_kill", details

        if not risk_engine.allow_trade(work, rsi_series, option_type, previous_close, today_open):
            reason = risk_engine.explain_allow_trade_block(work, rsi_series, option_type, previous_close, today_open)
            return False, reason or "risk_engine_blocked", details

        score = build_score(opt_row, option_type, work, pcr_value, gap_mode)
        required = 92 if gap_mode else BUY_THRESHOLD
        details["score"] = score
        details["required_score"] = required
        
        if score < required:
            return False, f"score_{score}_below_{required}", details

        # =========================================================
        # DUAL NIFTY SPOT + OPTION PREMIUM RUNTIME EXECUTION GATE
        # =========================================================
        nifty_rsi = Indicators.calculate_rsi(work)
        row = work.iloc[-2]
        close_price = row["close"]
        vwap_price = row["VWAP"]
        ema20 = row["EMA20"]
        
        atr_expanding = is_atr_expanding(work)
        
        symbol = opt_row.get("symbol")
        opt_rsi = 75.0
        opt_volume_spike = True
        
        if symbol:
            import os
            is_backtest = os.environ.get("IS_BACKTEST") == "1"
            tsl = None if is_backtest else get_live_client()
            if tsl:
                try:
                    should_fetch = True
                    if hasattr(tsl, "instrument_df") and tsl.instrument_df is not None:
                        try:
                            exch_db = 'BSE' if symbol.startswith(('SENSEX', 'BANKEX')) else 'NSE'
                            exists = not tsl.instrument_df[
                                ((tsl.instrument_df['SEM_TRADING_SYMBOL'] == symbol) | 
                                 (tsl.instrument_df['SEM_CUSTOM_SYMBOL'] == symbol)) &
                                (tsl.instrument_df['SEM_EXM_EXCH_ID'] == exch_db)
                            ].empty
                            if not exists:
                                should_fetch = False
                        except Exception:
                            pass
                    
                    if should_fetch:
                        exch_req = 'BFO' if symbol.startswith(('SENSEX', 'BANKEX')) else 'NFO'
                        opt_df = tsl.get_intraday_data(symbol, exch_req, 1)
                        if opt_df is not None and not opt_df.empty and len(opt_df) >= 15:
                            opt_rsi_series = Indicators.calculate_rsi_series(opt_df)
                            if len(opt_rsi_series) >= 2:
                                opt_rsi = opt_rsi_series.iloc[-2]
                                
                            opt_vol = pd.to_numeric(opt_df["volume"], errors="coerce").fillna(0.0)
                            discrete_v = opt_vol.iloc[-2]
                            vol_ema = opt_vol.rolling(window=20).mean().iloc[-2]
                            if vol_ema > 0:
                                opt_volume_spike = (discrete_v > (vol_ema * 1.5))
                except Exception as e:
                    pass

        details["nifty_rsi"] = round(nifty_rsi, 2)
        details["opt_rsi"] = round(opt_rsi, 2)
        details["opt_volume_spike"] = opt_volume_spike
        details["atr_expanding"] = atr_expanding
        
        if option_type == "CE":
            import Uptrend_Buy
            fallback_signal = Uptrend_Buy.detect_uptrend_pullback_signal(df_1m)
            is_fallback = fallback_signal is not None and fallback_signal.get("signal") == "BUY"
            
            if not is_fallback:
                import System_Config
                if not (System_Config.CE_RSI_TRIGGER <= nifty_rsi <= 90):
                    return False, f"nifty_rsi_{nifty_rsi:.1f}_not_between_{System_Config.CE_RSI_TRIGGER}_and_90", details
                if close_price <= ema20:
                    return False, f"nifty_close_{close_price:.1f}_not_above_ema20_{ema20:.1f}", details
                if close_price <= vwap_price:
                    return False, f"nifty_close_{close_price:.1f}_not_above_vwap_{vwap_price:.1f}", details
            
            if not atr_expanding:
                return False, "atr_volatility_not_expanding", details
            if not opt_volume_spike:
                return False, "option_volume_spike_not_active", details
        elif option_type == "PE":
            import Downtrend_Sell
            fallback_signal = Downtrend_Sell.detect_downtrend_rejection_signal(df_1m)
            is_fallback = fallback_signal is not None and fallback_signal.get("signal") == "BUY"
            
            if not is_fallback:
                if nifty_rsi > 40:
                    return False, f"nifty_rsi_{nifty_rsi:.1f}_not_below_or_equal_to_40", details
                if close_price >= ema20:
                    return False, f"nifty_close_{close_price:.1f}_not_below_ema20_{ema20:.1f}", details
                if close_price >= vwap_price:
                    return False, f"nifty_close_{close_price:.1f}_not_below_vwap_{vwap_price:.1f}", details
            
            if not atr_expanding:
                return False, "atr_volatility_not_expanding", details
            if not opt_volume_spike:
                return False, "option_volume_spike_not_active", details

        current_rsi = Indicators.calculate_rsi(work)
        details["rsi"] = round(current_rsi, 2)
        row = work.iloc[-2]
        
        if "ST_COLOR" in row:
            st_color = str(row["ST_COLOR"]).upper()
        elif "st_color" in row:
            st_color = str(row["st_color"]).upper()
        elif "ST" in row:
            st_color = "GREEN" if row["close"] >= row["ST"] else "RED"
        elif "supertrend" in row:
            st_color = "GREEN" if row["close"] >= row["supertrend"] else "RED"
        else:
            return False, "supertrend_missing", details
        details["trend"] = st_color

        tactical_slice = rsi_series.iloc[-(2 + TACTICAL_LOOKBACK):-1]
        ce_exhaustion_slice = rsi_series.iloc[-(2 + EXHAUSTION_WINDOW):-1]
        pe_exhaustion_slice = rsi_series.iloc[-(2 + PE_EXHAUSTION_WINDOW):-1]

        if option_type == "CE":
             reason = rise_fall.explain_ce_failure(current_rsi, tactical_slice, ce_exhaustion_slice, st_color, TACTICAL_LOOKBACK)
             if reason != "":
                  return False, reason, details
             return True, "", details

        if option_type == "PE":
             nifty_points_fallen = 0.0
             index_30m_ago = df_1m["close"].iloc[-(NIFTY_DROP_WINDOW + 1)] if len(df_1m) > NIFTY_DROP_WINDOW else df_1m["close"].iloc[0]
             nifty_points_fallen = index_30m_ago - nifty_spot

             if nifty_points_fallen > MAX_NIFTY_DROP:
                  return False, f"nifty_crashed_{nifty_points_fallen:.1f}_pts_in_{NIFTY_DROP_WINDOW}m", details
                
             reason = rise_fall.explain_pe_failure(current_rsi, tactical_slice, pe_exhaustion_slice, st_color, TACTICAL_LOOKBACK)
             if reason != "":
                  return False, reason, details
             return True, "", details

        return False, "unknown_option_type", details
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "explain_trigger_failure", e
        )
        return False, f"exception_in_explain_trigger: {e}", details


from models import TradeParameters

def verify_trade_calculations(ltp: float, option_symbol: str, calc_package: TradeParameters, margin_requirement_pc: float) -> bool:
    """
    Crucial verification step: independently recalculates math for Qty, SL, Target, Margin.
    Matches calculated numbers against the calc_package exactly to prevent catastrophic errors.
    """
    try:
        print(f"[Core Verification] Independently recalculating math for {option_symbol} at LTP {ltp}...")
        
        # Use centralized lot sizes and capital from System_Config
        import Trade_Calculator
        expected_lot_size = Trade_Calculator.get_lot_size(option_symbol)
        
        parsed_ltp = float(ltp) if ltp else 0.1
        lots = int(DEPLOYED_CAPITAL // (parsed_ltp * expected_lot_size))
        if lots < 1:
            lots = 1
            
        expected_qty = expected_lot_size * lots
        expected_target = round(float(ltp) + TARGET_POINTS, 2)
        expected_sl = round(float(ltp) - INITIAL_SL_POINTS, 2)
        
        pct_val = margin_requirement_pc if margin_requirement_pc < 1.0 else (margin_requirement_pc / 100.0)
        expected_margin = round(float(expected_qty * ltp * pct_val), 2)
        
        is_valid = True
        if calc_package.qty != expected_qty:
            print(f"[-] QTY Verification Failed! expected {expected_qty}, got {calc_package.qty}")
            is_valid = False
        if calc_package.target_price != expected_target:
            print(f"[-] Target Verification Failed! expected {expected_target}, got {calc_package.target_price}")
            is_valid = False
        if calc_package.sl_price != expected_sl:
            print(f"[-] SL Verification Failed! expected {expected_sl}, got {calc_package.sl_price}")
            is_valid = False
        if float(calc_package.estimated_margin) != expected_margin:
            print(f"[-] Margin Verification Failed! expected {expected_margin}, got {calc_package.estimated_margin}")
            is_valid = False
            
        if is_valid:
            print("[+] MainEngine Verification SUCCESS. Green Light for execution!")
            
        return is_valid
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "MainEngine_Verification", "verify_trade_calculations", e,
            {"ltp": ltp, "symbol": option_symbol, "calc_package": calc_package}
        )
        return False
