import time

# =========================================================
# STATE DICTIONARIES FOR THROTTLING
# =========================================================
_last_log_vol = {}
_oi_alert_last = {}

def log_volume_ema_cross(symbol, discrete, ema, cross_direction, throttle_sec=45):
    """Handles screen display and Excel logging for Volume EMA crosses."""
    now = time.time()
    
    # Throttle check
    if now - _last_log_vol.get(symbol, 0) < throttle_sec:
        return
        
    _last_log_vol[symbol] = now
    direction = str(cross_direction or "").strip().upper()
    if direction not in ("ABOVE", "BELOW"):
        direction = "ABOVE"
    msg = f"1m volume {discrete:.0f} crossed {direction} 20 EMA ({ema:.0f})"
    
    # Screen Display
    print(f"[vol] {symbol}: {msg}", flush=True)
    
    # Excel Output
    try:
        from scanner_excel import oi_volume_log
        oi_volume_log.append(
            direction, symbol, msg,
            volume_1m=round(discrete, 0),
            volume_ema_20=round(ema, 0),
        )
    except Exception as log_exc:
        print(f"[!] OI/Volume Excel log failed: {log_exc}", flush=True)

def log_oi_change(sym, oi, prev_oi, pct, delta, throttle_sec=60):
    """Handles screen display and Excel logging for OI changes."""
    now = time.time()
    
    # Throttle check
    if now - _oi_alert_last.get(sym, 0) < throttle_sec:
        return
        
    _oi_alert_last[sym] = now
    direction = "ABOVE" if delta >= 0 else "BELOW"
    msg = f"{pct:.1f}% (oi={oi:,}, prev={prev_oi:,}, delta={delta:+,})"
    
    # Screen Display
    print(f"[oi] {sym}: {msg}", flush=True)
    
    # Excel Output
    try:
        from scanner_excel import oi_volume_log
        oi_volume_log.append(
            direction, sym, msg, oi=oi, prev_oi=prev_oi,
            oi_change_pct=round(pct, 1), oi_delta=delta,
        )
    except Exception as log_exc:
        print(f"[!] OI/Volume Excel log failed: {log_exc}", flush=True)