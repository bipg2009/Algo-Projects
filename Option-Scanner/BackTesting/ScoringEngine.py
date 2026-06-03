"""
Option Scanner Unified Scoring Engine
Implements the 165-Point SEDA-Compliant Market Microstructure Matrix.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional


class OptionScoringEngine:
    @staticmethod
    def evaluate_contract(
        row_1m: pd.Series,  # Current 1-minute index underlying data row
        prev_row_1m: pd.Series,  # Previous 1-minute index underlying data row
        opt_snapshot: Dict[str, Any],  # Real-time option contract premium details
        option_type: str,  # "CE" or "PE"
        system_config: Any,  # System_Config module instance reference
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Executes a rigorous multi-factor scoring sequence.
        Returns: Tuple (Action_String, Final_Score, Score_Breakdown_Dict)
        """
        # Read constants safely from centralized configuration
        min_premium = getattr(system_config, "MIN_PREMIUM_THRESHOLD", 10.0)
        pcr_bullish = getattr(system_config, "PCR_BULLISH", 1.15)
        pcr_bearish = getattr(system_config, "PCR_BEARISH", 0.85)
        gap_mode = getattr(system_config, "GAP_MODE_ACTIVE", False)

        ce_rsi_trigger = getattr(system_config, "CE_RSI_TRIGGER", 65.0)
        pe_rsi_trigger = getattr(system_config, "PE_RSI_TRIGGER", 41.0)

        # Extract Option Contract Data
        opt_ltp = float(opt_snapshot.get("ltp", 0.0))
        opt_vwap = float(opt_snapshot.get("option_vwap", 0.0))
        opt_vol = float(opt_snapshot.get("volume", 0.0))
        opt_vol_ema = float(opt_snapshot.get("volume_ema", 1.0))
        opt_oi_pct = float(opt_snapshot.get("oi_change_pct", 0.0))
        opt_premium_pct = float(opt_snapshot.get("premium_change_pct", 0.0))
        bid_ask_spread = float(opt_snapshot.get("bid_ask_spread_pct", 0.0))

        # Extract Underlying Index Microstructure Data
        idx_close = float(row_1m.get("close", 0.0))
        idx_vwap = float(row_1m.get("VWAP", 0.0))
        idx_ema9 = float(row_1m.get("EMA9", 0.0))
        idx_ema20 = float(row_1m.get("EMA20", 0.0))

        adx_now = float(row_1m.get("ADX", 0.0))
        adx_prev = (
            float(prev_row_1m.get("ADX", 0.0)) if prev_row_1m is not None else adx_now
        )
        rsi_now = float(row_1m.get("RSI", 50.0))
        pcr_now = float(row_1m.get("PCR", 1.0))

        # Higher Timeframe Alignment (15-Minute Resampled Equivalents)
        htf_ema20 = float(row_1m.get("EMA_15m_20", 0.0))
        htf_ema50 = float(row_1m.get("EMA_15m_50", 0.0))

        # Initialize breakdown logs
        breakdown = {}

        # =====================================================================
        # LEVEL 0: LIQUIDITY FILTER (HARD REJECTS)
        # =====================================================================
        if bid_ask_spread > 2.0:
            return (
                "IGNORE (REJECTED: Spread > 2%)",
                0.0,
                {"Hard Reject": "Bid-Ask Spread > 2%"},
            )
        if opt_vol == 0:
            return (
                "IGNORE (REJECTED: Zero Volume)",
                0.0,
                {"Hard Reject": "Option Volume = 0"},
            )
        if opt_ltp < min_premium:
            return (
                f"IGNORE (REJECTED: Premium < {min_premium})",
                0.0,
                {"Hard Reject": f"LTP < Minimum Premium"},
            )

        # Hard Kill constraints via ADX
        if adx_now < 15.0:
            return (
                "IGNORE (REJECTED: Dead Market ADX < 15)",
                0.0,
                {"Hard Reject": "ADX < 15"},
            )

        # Hard Kill constraints via RSI
        if option_type == "CE":
            if rsi_now < 40.0:
                return (
                    "IGNORE (REJECTED: RSI < 40 on CE)",
                    0.0,
                    {"Hard Reject": "CE RSI < 40"},
                )
        elif option_type == "PE":
            if rsi_now > 60.0:
                return (
                    "IGNORE (REJECTED: RSI > 60 on PE)",
                    0.0,
                    {"Hard Reject": "PE RSI > 60"},
                )

        # Base Score initialization
        score = 60.0
        breakdown["Base Score"] = 60.0

        # =====================================================================
        # LEVEL 1: OPTION VOLUME EXPANSION (MAX +15 / MIN -15)
        # =====================================================================
        vol_score = 0.0
        if not gap_mode:
            if opt_vol > opt_vol_ema:
                vol_score = 15.0
            else:
                vol_score = -10.0
        else:
            if opt_vol > (opt_vol_ema * 1.5):
                vol_score = 15.0
            else:
                vol_score = -15.0
        score += vol_score
        breakdown["Volume Expansion"] = vol_score

        # =====================================================================
        # LEVEL 2: OPEN INTEREST (OI) STRUCTURE (MAX +20 / MIN -20)
        # =====================================================================
        oi_score = 0.0
        # A. Short Covering
        if opt_premium_pct > 0.0 and opt_oi_pct < 0.0:
            oi_score = 20.0
        # B. Long Build-Up
        elif opt_premium_pct > 0.0 and opt_oi_pct > 0.0:
            is_vol_confirmed = opt_vol > opt_vol_ema
            base_lb = 15.0 if is_vol_confirmed else 5.0

            # Apply dynamic structural multipliers
            abs_oi = abs(opt_oi_pct)
            if abs_oi < 2.0:
                oi_score = base_lb * 0.5
            elif 2.0 <= abs_oi <= 5.0:
                oi_score = base_lb * 1.0
            else:
                oi_score = base_lb * 1.5
            oi_score = min(20.0, oi_score)
        # C. Long Unwinding
        elif opt_premium_pct < 0.0 and opt_oi_pct < 0.0:
            oi_score = -10.0
        # D. Fresh Writing
        elif opt_premium_pct < 0.0 and opt_oi_pct > 0.0:
            oi_score = -20.0

        score += oi_score
        breakdown["OI Structure"] = oi_score

        # =====================================================================
        # LEVEL 3: UNDERLYING INDEX ALIGNMENT (MAX +15 / MIN -15)
        # =====================================================================
        align_score = -15.0  # Default to misaligned penalty
        if option_type == "CE":
            if idx_close >= idx_vwap and idx_ema9 > idx_ema20:
                align_score = 15.0
        elif option_type == "PE":
            if idx_close <= idx_vwap and idx_ema9 < idx_ema20:
                align_score = 15.0
        score += align_score
        breakdown["Index Alignment"] = align_score

        # =====================================================================
        # LEVEL 4: PREMIUM STRENGTH / OPTION VWAP (MAX +10 / MIN -10)
        # =====================================================================
        premium_score = 10.0 if opt_ltp > opt_vwap else -10.0
        score += premium_score
        breakdown["Premium Strength"] = premium_score

        # =====================================================================
        # LEVEL 5: ADX REGIME (MAX +15 / MIN -15)
        # =====================================================================
        adx_score = 0.0
        if adx_now > 22.0 and adx_now > adx_prev:
            adx_score = 15.0
        elif adx_now >= 25.0:
            adx_score = 10.0
        elif 22.0 <= adx_now < 25.0:
            adx_score = 5.0
        elif 18.0 <= adx_now < 22.0:
            adx_score = -5.0
        elif adx_now < 18.0:
            adx_score = -15.0
        score += adx_score
        breakdown["ADX Regime"] = adx_score

        # =====================================================================
        # LEVEL 6: 15-MINUTE TREND FILTER (MAX +15 / MIN -20)
        # =====================================================================
        htf_score = -20.0
        if option_type == "CE":
            if htf_ema20 > htf_ema50:
                htf_score = 15.0
        elif option_type == "PE":
            if htf_ema20 < htf_ema50:
                htf_score = 15.0
        score += htf_score
        breakdown["15m HTF Filter"] = htf_score

        # =====================================================================
        # LEVEL 7: TIME-WEIGHTED RSI MOMENTUM (MAX +10 / MIN -30)
        # =====================================================================
        rsi_score = 0.0
        if option_type == "CE":
            if rsi_now >= ce_rsi_trigger:
                rsi_score = 10.0
            elif rsi_now < 50.0:
                rsi_score = -20.0
        elif option_type == "PE":
            if rsi_now <= pe_rsi_trigger:
                rsi_score = 10.0
            elif rsi_now > 50.0:
                rsi_score = -30.0
        score += rsi_score
        breakdown["RSI Momentum"] = rsi_score

        # =====================================================================
        # LEVEL 8: PUT-CALL RATIO (MAX +5 / MIN 0)
        # =====================================================================
        pcr_score = 0.0
        if option_type == "CE" and pcr_now > pcr_bullish:
            pcr_score = 5.0
        elif option_type == "PE" and pcr_now < pcr_bearish:
            pcr_score = 5.0
        score += pcr_score
        breakdown["PCR Sentiment"] = pcr_score

        # Bound constraints safely to protect your structural database records
        score = max(0.0, min(165.0, score))
        breakdown["Total Computed Score"] = score

        # =====================================================================
        # CATEGORIZATION ENGINE
        # =====================================================================
        if score >= 100.0:
            action = "STRONG BUY"
        elif 85.0 <= score <= 99.0:
            action = "BUY"
        elif 70.0 <= score <= 84.0:
            action = "WATCHLIST"
        else:
            action = "IGNORE"

        return action, score, breakdown
