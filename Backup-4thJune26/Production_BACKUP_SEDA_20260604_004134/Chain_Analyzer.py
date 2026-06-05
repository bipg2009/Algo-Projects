import pandas as pd
import time
import json
import os
import SafetyLogger
from pathlib import Path

# Per-underlying snapshots (NIFTY, SENSEX, …) for CHAIN_MACRO volume deltas
_prev_chain_snapshots = {}
_last_chain_analysis_times = {}


def _vol_sign_label(delta):
    n = int(delta or 0)
    return f"+{n:,}" if n >= 0 else f"{n:,}"


def process_and_analyze_chain(
    current_chain_df, spot, core_engine, underlying="NIFTY", throttle_sec=60
):
    """
    Processes the live option chain DataFrame every minute.
    Calculates macro changes, validates chain context for the strategy core,
    and passes alerts to the logger.
    
    Parameters:
    -----------
    current_chain_df : pd.DataFrame
    spot : float
    core_engine : module
    underlying : str
        Index name for CSV symbol column (NIFTY, SENSEX, …).
    """
    global _prev_chain_snapshots, _last_chain_analysis_times

    underlying = str(underlying or "NIFTY").upper()

    try:
        if current_chain_df is None or current_chain_df.empty:
            return current_chain_df

        now = time.time()
        last_run = _last_chain_analysis_times.get(underlying, 0.0)
        if now - last_run < throttle_sec:
            return current_chain_df

        _last_chain_analysis_times[underlying] = now

        # Convert option_type/volume/oi safely in case of weird formats
        current_chain_df['option_type'] = current_chain_df['option_type'].astype(str).str.upper()
        current_chain_df['volume'] = pd.to_numeric(current_chain_df['volume'], errors='coerce').fillna(0)
        current_chain_df['oi'] = pd.to_numeric(current_chain_df['oi'], errors='coerce').fillna(0)

        # 1. Total Volume & OI Buildup Tracking
        import numpy as np
        opt_types = current_chain_df['option_type'].to_numpy(dtype=object)
        vols = current_chain_df['volume'].values
        ois = current_chain_df['oi'].values
        
        ce_mask = opt_types == 'CE'
        pe_mask = opt_types == 'PE'
        
        total_ce_vol = np.sum(vols[ce_mask])
        total_pe_vol = np.sum(vols[pe_mask])
        total_ce_oi = np.sum(ois[ce_mask])
        total_pe_oi = np.sum(ois[pe_mask])

        ce_vol_growth = 0
        pe_vol_growth = 0
        prev_snapshot = _prev_chain_snapshots.get(underlying)
        # 2. Check for significant shifts if we have a previous baseline
        if prev_snapshot is not None:
            try:
                prev_opt_types = prev_snapshot['option_type'].to_numpy(dtype=object)
                prev_vols = prev_snapshot['volume'].values
                prev_ce_vol = np.sum(prev_vols[prev_opt_types == 'CE'])
                prev_pe_vol = np.sum(prev_vols[prev_opt_types == 'PE'])

                ce_vol_growth = total_ce_vol - prev_ce_vol
                pe_vol_growth = total_pe_vol - prev_pe_vol

                if ce_vol_growth != 0 or pe_vol_growth != 0:
                    msg = (
                        f"Chain Activity Check - New CE Vol: {_vol_sign_label(ce_vol_growth)} "
                        f"| New PE Vol: {_vol_sign_label(pe_vol_growth)}"
                    )
                    try:
                        from scanner_excel import oi_volume_log

                        print(f"[chain_macro] {underlying}: {msg}", flush=True)
                        oi_volume_log.append(
                            "CHAIN_MACRO",
                            underlying,
                            msg,
                            ce_vol_delta=ce_vol_growth,
                            pe_vol_delta=pe_vol_growth,
                        )
                    except Exception as e:
                        SafetyLogger.log_error_with_context(
                            "Chain_Analyzer", "log_volume_growth_to_excel_ignored", e
                        )
            except Exception as e:
                SafetyLogger.log_error_with_context("Chain_Analyzer", "calculate_delta_growth", e)

        # 3. Perform the Chain Context Validations via Core Engine rules Safely
        ce_pass, ce_barrier = True, 0
        pe_pass, pe_barrier = True, 0
        ce_vol_supported = True
        pe_vol_supported = True

        try:
            ce_pass, ce_barrier = core_engine.validate_oi_barrier_distance(spot, "CE", current_chain_df)
        except Exception as e:
            SafetyLogger.log_error_with_context("Chain_Analyzer", "core_validate_oi_barrier_ce", e)

        try:
            pe_pass, pe_barrier = core_engine.validate_oi_barrier_distance(spot, "PE", current_chain_df)
        except Exception as e:
            SafetyLogger.log_error_with_context("Chain_Analyzer", "core_validate_oi_barrier_pe", e)
            
        try:
            ce_vol_supported = core_engine.validate_volume_support("CE", current_chain_df)
        except Exception as e:
            SafetyLogger.log_error_with_context("Chain_Analyzer", "core_validate_volume_support_ce", e)

        try:
            pe_vol_supported = core_engine.validate_volume_support("PE", current_chain_df)
        except Exception as e:
            SafetyLogger.log_error_with_context("Chain_Analyzer", "core_validate_volume_support_pe", e)

        findings = {
            "timestamp": now,
            "underlying": underlying,
            "index_spot": float(spot),
            "nifty_spot": float(spot),
            "total_ce_vol": float(total_ce_vol),
            "total_pe_vol": float(total_pe_vol),
            "ce_vol_growth": float(ce_vol_growth),
            "pe_vol_growth": float(pe_vol_growth),
            "ce_pass": bool(ce_pass),
            "pe_pass": bool(pe_pass),
            "ce_barrier": float(ce_barrier),
            "pe_barrier": float(pe_barrier),
            "ce_vol_supported": bool(ce_vol_supported),
            "pe_vol_supported": bool(pe_vol_supported),
            "roadblock_ce": not (ce_pass and ce_vol_supported),
            "roadblock_pe": not (pe_pass and pe_vol_supported)
        }

        # Write the state to a json file so independent processes (MainEngine) can read it
        try:
            SCANNER_ROOT = Path(__file__).resolve().parent
            state_file = SCANNER_ROOT / "chain_state.json"
            with open(state_file, "w") as f:
                json.dump(findings, f)
        except Exception as e:
            SafetyLogger.log_error_with_context("Chain_Analyzer", "write_chain_state_json", e)

        # 4. Save state for next minute's delta tracking
        _prev_chain_snapshots[underlying] = current_chain_df.copy()

    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Chain_Analyzer", "process_and_analyze_chain_master", e,
            {"underlying": underlying, "spot": spot},
        )
    return current_chain_df

def get_latest_chain_findings():
    """
    Reads the latest chain analysis state to provide security check roadblocks to MainEngine or Option_strategy_core.
    """
    try:
        state_file = Path(__file__).resolve().parent / "chain_state.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                return json.load(f)
    except Exception as e:
        SafetyLogger.log_error_with_context("Chain_Analyzer", "get_latest_chain_findings", e)
    return None

def is_safe_to_trade(option_type):
    """
    Returns True if no roadblocks are present for the given option type direction.
    CE needs clear upward runway (ce_pass) and volume support (ce_vol_supported).
    PE needs clear downward runway (pe_pass) and volume support (pe_vol_supported).
    """
    try:
        findings = get_latest_chain_findings()
        if not findings:
            return True # Default to True if chain_analyzer hasn't written anything yet
            
        if option_type == "CE":
            return not findings.get("roadblock_ce", False)
        elif option_type == "PE":
            return not findings.get("roadblock_pe", False)
    except Exception as e:
        SafetyLogger.log_error_with_context("Chain_Analyzer", "is_safe_to_trade", e, {"option_type": option_type})
    return True
