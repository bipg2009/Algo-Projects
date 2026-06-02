import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler

# Global setup
_LOGGER_INITIALIZED = False
_logger = None

def setup_logger():
    global _LOGGER_INITIALIZED, _logger
    if _LOGGER_INITIALIZED:
        return _logger
        
    try:
        log_dir = "Dependencies/log_files"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        logger = logging.getLogger("SystemSafetyLogger")
        logger.setLevel(logging.DEBUG)
        
        # Rotating file handler (5MB max per file, 5 backups max)
        handler = RotatingFileHandler(os.path.join(log_dir, "system_errors.log"), maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        # Store in global 
        _logger = logger
        _LOGGER_INITIALIZED = True
        return _logger
    except Exception as e:
        print(f"Failed to initialize logger: {e}")
        return logging.getLogger("Fallback")


def log_error(module_name, func_name, exception):
    """Basic error logging"""
    logger = setup_logger()
    error_msg = f"{module_name}.{func_name} | {type(exception).__name__}: {str(exception)}"
    logger.error(error_msg)
    logger.debug(traceback.format_exc())
    print(f"[-] ERROR: {error_msg}")

def log_error_with_context(module_name, func_name, exception, context_dict=None):
    """Error logging with context details to make debugging easier"""
    logger = setup_logger()
    error_msg = f"{module_name}.{func_name} | {type(exception).__name__}: {str(exception)}"
    logger.error(error_msg)
    
    if context_dict:
        context_str = " | Context: " + ", ".join([f"{k}={v}" for k, v in context_dict.items()])
        logger.error(context_str)
        
    logger.debug(traceback.format_exc())
    print(f"[-] ERROR: {error_msg}")

def log_warning(module_name, message):
    logger = setup_logger()
    logger.warning(f"{module_name} | {message}")
    print(f"[!] WARNING: {module_name} | {message}")

def log_info(message):
    logger = setup_logger()
    logger.info(message)
    print(f"[i] INFO: {message}")
