import pandas as pd
import numpy as np
import datetime

import Risk_Engine as risk_engine
import RiseFall_sub as rise_fall
import indicator_engine as Indicators
import SafetyLogger
from System_Config import *


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
        # OI BUILDUP
        # -----------------------------------------
        if oi_change > 5:
            score += 15
        elif oi_change < -2:
            score -= 15

        # -----------------------------------------
        # VWAP + EMA ALIGNMENT
        # -----------------------------------------
        row = df_1m.iloc[-2]
        close_price = row["close"]
        vwap_price = row["VWAP"]
        ema9 = row["EMA9"]
        ema20 = row["EMA20"]

        if option_type == "CE":
            if close_price > vwap_price and ema9 > ema20:
                score += 10
            else:
                score -= 15

        if option_type == "PE":
            if close_price < vwap_price and ema9 < ema20:
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
        
        BASE_RSI_POINTS = 10 
        
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
# MAIN TRIGGER
# =========================================================

def detect_trigger_1m(
    df_1m, option_type, opt_row, nifty_spot, previous_close, today_open, pcr_value=1.0, option_chain_df=None
):
    try:
        if df_1m is None or df_1m.empty or len(df_1m) < 30:
            return False
        if not isinstance(opt_row, dict):
            return False

        df_1m = Indicators.add_vwap(df_1m)
        df_1m = Indicators.add_ema(df_1m)

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
        allowed = risk_engine.allow_trade(df_1m, rsi_series, option_type, previous_close, today_open)
        if not allowed:
            return False

        score = build_score(opt_row, option_type, df_1m, pcr_value, gap_mode)
        required_score = 92 if gap_mode else STRONG_BUY_THRESHOLD
        if score < required_score:
            return False

        current_rsi = Indicators.calculate_rsi(df_1m)
        row = df_1m.iloc[-2]
        
        if "st_color" in row:
            st_color = str(row["st_color"]).upper()
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
                  return True

        if option_type == "PE":
             if rise_fall.evaluate_pe_trigger(current_rsi, tactical_slice, pe_exhaustion_slice, st_color):
                  return True

        return False
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Option_strategy_core", "detect_trigger_1m", e,
            {"nifty_spot": nifty_spot, "option_type": option_type}
        )
        return False

def explain_trigger_failure(
    df_1m, option_type, opt_row, nifty_spot, previous_close, today_open, pcr_value=1.0, option_chain_df=None
):
    details = {}
    try:
        if df_1m is None or df_1m.empty or len(df_1m) < 30:
            return False, "insufficient_1m_bars", details
        if not isinstance(opt_row, dict):
            return False, "invalid_contract_row", details

        work = Indicators.add_vwap(df_1m)
        work = Indicators.add_ema(work)
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
        if not risk_engine.allow_trade(work, rsi_series, option_type, previous_close, today_open):
            reason = risk_engine.explain_allow_trade_block(work, rsi_series, option_type, previous_close, today_open)
            return False, reason or "risk_engine_blocked", details

        score = build_score(opt_row, option_type, work, pcr_value, gap_mode)
        required = 92 if gap_mode else STRONG_BUY_THRESHOLD
        details["score"] = score
        details["required_score"] = required
        
        if score < required:
            return False, f"score_{score}_below_{required}", details

        current_rsi = Indicators.calculate_rsi(work)
        details["rsi"] = round(current_rsi, 2)
        row = work.iloc[-2]
        
        if "st_color" in row:
            st_color = str(row["st_color"]).upper()
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
            "Option_strategy_core", "explain_trigger_failure", e,
            {"nifty_spot": nifty_spot, "option_type": option_type}
        )
        return False, f"exception_in_explain_trigger: {e}", details


def verify_trade_calculations(ltp, option_symbol, calc_package, margin_requirement_pc):
    """
    Crucial verification step: independently recalculates math for Qty, SL, Target, Margin.
    Matches calculated numbers against the calc_package exactly to prevent catastrophic errors.
    """
    try:
        print(f"[Core Verification] Independently recalculating math for {option_symbol} at LTP {ltp}...")
        
        # Independent Constants
        TRADING_LOTS = 1
        
        expected_lot_size = 75
        sym_upper = str(option_symbol).upper()
        if "SENSEX" in sym_upper:
            expected_lot_size = 20
        elif "RELIANCE" in sym_upper:
            expected_lot_size = 500
        elif "FINNIFTY" in sym_upper:
            expected_lot_size = 60
        elif "BANKNIFTY" in sym_upper:
            expected_lot_size = 30
        elif "NIFTY" in sym_upper:
            expected_lot_size = 65
        
        parsed_ltp = float(ltp) if ltp else 0.1
        DEPLOYED_CAPITAL = 300000.0
        lots = int(DEPLOYED_CAPITAL // (parsed_ltp * expected_lot_size))
        if lots < 1:
            lots = 1
            
        expected_qty = expected_lot_size * lots
        expected_target = round(float(ltp) + TARGET_POINTS, 2)
        expected_sl = round(float(ltp) - INITIAL_SL_POINTS, 2)
        
        pct_val = margin_requirement_pc if margin_requirement_pc < 1.0 else (margin_requirement_pc / 100.0)
        expected_margin = round(float(expected_qty * ltp * pct_val), 2)
        
        is_valid = True
        if calc_package["qty"] != expected_qty:
            print(f"[-] QTY Verification Failed! expected {expected_qty}, got {calc_package['qty']}")
            is_valid = False
        if calc_package["target_price"] != expected_target:
            print(f"[-] Target Verification Failed! expected {expected_target}, got {calc_package['target_price']}")
            is_valid = False
        if calc_package["sl_price"] != expected_sl:
            print(f"[-] SL Verification Failed! expected {expected_sl}, got {calc_package['sl_price']}")
            is_valid = False
        if float(calc_package["estimated_margin"]) != expected_margin:
            print(f"[-] Margin Verification Failed! expected {expected_margin}, got {calc_package['estimated_margin']}")
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
