# RiseFall_sub.py

"""
Sub-module for handling Call (CE) and Put (PE) entry logic.
Decoupled from the main strategy core for cleaner execution and easier threshold tuning.
"""

import SafetyLogger

# --- CE & PE RSI CONFIGURATIONS ---
CE_RSI_TRIGGER = 73.0
CE_RSI_LOWER_BAND = 60.0

PE_RSI_TRIGGER = 39.0
PE_RSI_UPPER_BAND = 45.0

def evaluate_ce_trigger(current_rsi, tactical_slice, exhaustion_slice, st_color):
    """Evaluates if the CE conditions have been met for execution."""
    try:
        if tactical_slice is None or list(tactical_slice) == [] or len(tactical_slice) == 0:
            return False
        if exhaustion_slice is None or list(exhaustion_slice) == [] or len(exhaustion_slice) == 0:
            return False
            
        rsi_is_strong = current_rsi >= CE_RSI_TRIGGER
        came_from_lower_band = (tactical_slice <= CE_RSI_LOWER_BAND).any()
        is_exhausted = (exhaustion_slice > 70.0).all()
        
        # Classic Bull Run Override:
        if current_rsi >= 75.0 and st_color == "GREEN" and not is_exhausted:
            return True
        
        if rsi_is_strong and came_from_lower_band and not is_exhausted and st_color == "GREEN":
            return True
        return False
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "RiseFall_sub", "evaluate_ce_trigger", e,
            {"current_rsi": current_rsi, "st_color": st_color, "tactical_len": len(tactical_slice) if tactical_slice is not None else 0}
        )
        return False

def evaluate_pe_trigger(current_rsi, tactical_slice, exhaustion_slice, st_color):
    """Evaluates if the PE conditions have been met for execution."""
    try:
        if tactical_slice is None or list(tactical_slice) == [] or len(tactical_slice) == 0:
            return False
        if exhaustion_slice is None or list(exhaustion_slice) == [] or len(exhaustion_slice) == 0:
            return False

        rsi_is_strong = current_rsi <= PE_RSI_TRIGGER
        came_from_upper_band = (tactical_slice >= PE_RSI_UPPER_BAND).any()
        is_exhausted = (exhaustion_slice <= PE_RSI_TRIGGER).all()
        
        # Classic Market Fall Override: Allow if RSI drops deeply but not yet exhausted
        if current_rsi <= 35.0 and st_color == "RED" and not is_exhausted:
            return True
        
        if rsi_is_strong and came_from_upper_band and not is_exhausted and st_color == "RED":
            return True
        return False
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "RiseFall_sub", "evaluate_pe_trigger", e,
            {"current_rsi": current_rsi, "st_color": st_color, "tactical_len": len(tactical_slice) if tactical_slice is not None else 0}
        )
        return False

def explain_ce_failure(current_rsi, tactical_slice, exhaustion_slice, st_color, tactical_lookback):
    """Returns the exact reason a CE trade was rejected for logging."""
    try:
        if tactical_slice is None or len(tactical_slice) == 0:
            return "empty_tactical_slice"
        if exhaustion_slice is None or len(exhaustion_slice) == 0:
            return "empty_exhaustion_slice"

        came_from_lower_band = (tactical_slice <= CE_RSI_LOWER_BAND).any()
        is_exhausted = (exhaustion_slice > 70.0).all()
        mins_above_70 = (exhaustion_slice > 70.0).sum()

        if is_exhausted:
            return f"exhaustion_blocked_rsi_above_70_for_{mins_above_70}_mins_straight"
        if current_rsi < CE_RSI_TRIGGER:
            return f"rsi_{current_rsi:.1f}_below_trigger_{CE_RSI_TRIGGER}"    
        if not came_from_lower_band and current_rsi < 75.0:
            return f"no_lower_band_origin_in_past_{tactical_lookback}_candles"
        if st_color != "GREEN":
            return f"trend_{st_color}_need_GREEN_for_CE"
        return ""
    except Exception as e:
        SafetyLogger.log_error_with_context("RiseFall_sub", "explain_ce_failure", e)
        return f"exception_in_explain_ce: {e}"

def explain_pe_failure(current_rsi, tactical_slice, exhaustion_slice, st_color, tactical_lookback):
    """Returns the exact reason a PE trade was rejected for logging."""
    try:
        if tactical_slice is None or len(tactical_slice) == 0:
            return "empty_tactical_slice"
        if exhaustion_slice is None or len(exhaustion_slice) == 0:
            return "empty_exhaustion_slice"

        came_from_upper_band = (tactical_slice >= PE_RSI_UPPER_BAND).any()
        is_exhausted = (exhaustion_slice <= PE_RSI_TRIGGER).all()
        mins_below_trigger = (exhaustion_slice <= PE_RSI_TRIGGER).sum()

        if is_exhausted:
            return f"exhaustion_blocked_rsi_below_{PE_RSI_TRIGGER}_for_{mins_below_trigger}_mins_straight"
        if current_rsi > PE_RSI_TRIGGER:
            return f"rsi_{current_rsi:.1f}_above_trigger_{PE_RSI_TRIGGER}"
        if not came_from_upper_band and current_rsi > 35.0:
            return f"no_upper_band_origin_in_past_{tactical_lookback}_candles"
        if st_color != "RED":
            return f"trend_{st_color}_need_RED_for_PE"
        return ""
    except Exception as e:
        SafetyLogger.log_error_with_context("RiseFall_sub", "explain_pe_failure", e)
        return f"exception_in_explain_pe: {e}"
