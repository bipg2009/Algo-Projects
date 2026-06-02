import time
import datetime
import SafetyLogger

# A simplified mock registry to keep track of module heartbeats or last active states
_MODULE_STATUS_REGISTRY = {
    "Tradehull.py": {"status": "ONLINE", "last_seen": time.time(), "error": None},
    "Trade_Calculator.py": {"status": "ONLINE", "last_seen": time.time(), "error": None},
    "Option_strategy_core.py": {"status": "ONLINE", "last_seen": time.time(), "error": None},
    "Monitor_Engine.py": {"status": "ONLINE", "last_seen": time.time(), "error": None},
}

def update_module_status(module_name, status, error=None):
    """
    Called by modules or MainEngine to update the health status of a specific module.
    """
    try:
        if module_name in _MODULE_STATUS_REGISTRY:
            _MODULE_STATUS_REGISTRY[module_name]["status"] = str(status)
            _MODULE_STATUS_REGISTRY[module_name]["last_seen"] = time.time()
            if error:
                _MODULE_STATUS_REGISTRY[module_name]["error"] = str(error)
        else:
            _MODULE_STATUS_REGISTRY[module_name] = {
                "status": str(status),
                "last_seen": time.time(),
                "error": str(error) if error else None
            }
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Communication", "update_module_status", e,
            {"module_name": module_name, "status": status}
        )

def check_module_health(module_name):
    """
    Called by MainEngine when a module stops responding.
    Communication.py investigates the module's state.
    """
    try:
        print(f"[Communication] MainEngine requested health check for: {module_name}...", flush=True)
        
        if module_name not in _MODULE_STATUS_REGISTRY:
            return {"status": "UNKNOWN", "message": f"Module {module_name} is not registered in the system."}
            
        module_info = _MODULE_STATUS_REGISTRY[module_name]
        current_time = time.time()
        time_since_last_seen = current_time - module_info.get("last_seen", current_time)
        
        # Simulate an investigation delay
        time.sleep(0.010)
        
        if module_info.get("status") == "ERROR":
            return {
                "status": "RED_FLAG", 
                "message": f"Module {module_name} failed with error: {module_info.get('error')}. Last seen {time_since_last_seen:.2f} seconds ago."
            }
        elif time_since_last_seen > 5.0: # 5 seconds without an update is considered unresponsive
            return {
                "status": "RED_FLAG",
                "message": f"Module {module_name} is UNRESPONSIVE. Last heartbeat was {time_since_last_seen:.2f} seconds ago."
            }
        else:
            return {
                "status": "CLEAR",
                "message": f"Module {module_name} appears to be ONLINE. Last heartbeat {time_since_last_seen:.2f} seconds ago."
            }
    except Exception as e:
        SafetyLogger.log_error_with_context("Communication", "check_module_health", e, {"module_name": module_name})
        return {"status": "ERROR", "message": f"Error investigating module health: {e}"}

def diagnostic_ping_tradehull():
    """
    Specialized function to ping Tradehull (the API wrapper) to check connection.
    """
    try:
        print("[Communication] Initiating diagnostic network ping to Tradehull API...", flush=True)
        # Simulated ping delay
        time.sleep(0.050)
        
        # Normally this would be a network request or a socket check
        # For now, assuming healthy network
        update_module_status("Tradehull.py", "ONLINE")
        return True
    except Exception as e:
        SafetyLogger.log_error_with_context("Communication", "diagnostic_ping_tradehull", e)
        return False
