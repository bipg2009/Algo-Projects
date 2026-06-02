import pandas as pd
import time
import talib

# Keep track of previous snapshot to calculate delta changes per minute
_prev_chain_snapshot = None
_last_chain_analysis_time = 0

def process_and_analyze_chain(current_chain_df, nifty_spot, core_engine, alert_logger, throttle_sec=60):
    """
    Processes the live option chain DataFrame every minute.
    Calculates macro changes, validates chain context for the strategy core,
    and passes alerts to the logger.
    
    Parameters:
    -----------
    current_chain_df : pd.DataFrame
        Expects columns: ['strike', 'option_type', 'volume', 'oi', 'oi_change', 'symbol']
    nifty_spot : float
        Current spot price of Nifty
    core_engine : module
        The imported Option_strategy_core module
    alert_logger : module
        The imported Alert_logger module
    """
    global _prev_chain_snapshot, _last_chain_analysis_time
    
    if current_chain_df is None or current_chain_df.empty:
        return current_chain_df

    now = time.time()
    # Ensure this runs roughly on your designated minute heartbeat
    if now - _last_chain_analysis_time < throttle_sec:
        return current_chain_df
        
    _last_chain_analysis_time = now

    # 1. Total Volume & OI Buildup Tracking
    total_ce_vol = current_chain_df[current_chain_df['option_type'] == 'CE']['volume'].sum()
    total_pe_vol = current_chain_df[current_chain_df['option_type'] == 'PE']['volume'].sum()
    total_ce_oi = current_chain_df[current_chain_df['option_type'] == 'CE']['oi'].sum()
    total_pe_oi = current_chain_df[current_chain_df['option_type'] == 'PE']['oi'].sum()

    # 2. Check for significant shifts if we have a previous baseline
    if _prev_chain_snapshot is not None:
        prev_ce_vol = _prev_chain_snapshot[_prev_chain_snapshot['option_type'] == 'CE']['volume'].sum()
        prev_pe_vol = _prev_chain_snapshot[_prev_chain_snapshot['option_type'] == 'PE']['volume'].sum()
        
        ce_vol_growth = total_ce_vol - prev_ce_vol
        pe_vol_growth = total_pe_vol - prev_pe_vol
        
        # Report heavy volume surges directly to the logger if they exceed parameters
        if ce_vol_growth > 0 or pe_vol_growth > 0:
            # We construct a summary message for the master log
            msg = f"Chain Activity Check - New CE Vol: +{ce_vol_growth:,} | New PE Vol: +{pe_vol_growth:,}"
            
            # Use a generic call to alert_logger for overall chain tracking
            try:
                from scanner_excel import oi_volume_log
                print(f"[chain_macro] {msg}", flush=True)
                oi_volume_log.append("CHAIN_MACRO", "NIFTY", msg, ce_vol_delta=ce_vol_growth, pe_vol_delta=pe_vol_growth)
            except Exception as e:
                print(f"[!] Chain macro logging failed: {e}", flush=True)

    # 3. Perform the Chain Context Validations via Core Engine rules
    # Validate CE Runway (Call Resistance)
    ce_pass, ce_barrier = core_engine.validate_oi_barrier_distance(nifty_spot, "CE", current_chain_df)
    # Validate PE Runway (Put Support)
    pe_pass, pe_barrier = core_engine.validate_oi_barrier_distance(nifty_spot, "PE", current_chain_df)
    
    # Validate Directional Volume Bias
    ce_vol_supported = core_engine.validate_volume_support("CE", current_chain_df)
    pe_vol_supported = core_engine.validate_volume_support("PE", current_chain_df)

    # 4. Save state for next minute's delta tracking
    _prev_chain_snapshot = current_chain_df.copy()

    return current_chain_df