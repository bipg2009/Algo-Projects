import pandas as pd
import datetime

from System_Config import CE_RSI_TRIGGER, PE_RSI_TRIGGER

def evaluate_ce_trigger(current_rsi, tactical_slice, ce_exhaustion_slice, st_color):
    """
    Evaluates CE conditions using RSI and SuperTrend.
    tactical_slice: The RSI values from -(2+lookback) to -2
    ce_exhaustion_slice: The RSI values from -(2+exhaustion_window) to -2.
    """
    if current_rsi < CE_RSI_TRIGGER:
        return False
        
    if st_color != "GREEN":
        return False

    return True

def explain_ce_failure(current_rsi, tactical_slice, ce_exhaustion_slice, st_color, tactical_lookback):
    if st_color != "GREEN":
         return "supertrend_not_green"
    if current_rsi < CE_RSI_TRIGGER:
         return f"current_rsi_{current_rsi:.1f}_below_{CE_RSI_TRIGGER}"
    return ""


def evaluate_pe_trigger(current_rsi, tactical_slice, pe_exhaustion_slice, st_color):
    """
    Evaluates PE conditions.
    """
    if current_rsi > PE_RSI_TRIGGER:
        return False

    if st_color != "RED":
         return False

    return True

def explain_pe_failure(current_rsi, tactical_slice, pe_exhaustion_slice, st_color, tactical_lookback):
    if st_color != "RED":
         return "supertrend_not_red"
    if current_rsi > PE_RSI_TRIGGER:
         return f"current_rsi_{current_rsi:.1f}_above_{PE_RSI_TRIGGER}"
    return ""
