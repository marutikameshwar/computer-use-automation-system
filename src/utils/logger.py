import logging
import os
import sys
from datetime import datetime
from functools import wraps

def setup_logger(run_type: str) -> None:
    """
    Configure the root logger for the application.
    run_type: e.g., 'discovery' or 'replay' to name the log file.
    """
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    
    # Ensure logs directory exists
    log_dir = os.path.join("src", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{run_type}_run_{timestamp}.log")
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO, # Default to INFO for production
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    logging.info("Initialized root logger. File output: %s", log_file)


def log_execution(func):
    """
    Decorator to automatically log function entry and exit.
    Instantiates a logger specific to the module where the function lives.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Dynamically get the logger for the module where the function lives
        logger = logging.getLogger(func.__module__)
        logger.debug(">>> Entering function: %s", func.__name__)
        try:
            result = func(*args, **kwargs)
            logger.debug("<<< Exiting function: %s", func.__name__)
            return result
        except Exception as e:
            logger.error("!!! Exception in function: %s - %s", func.__name__, str(e))
            raise
    return wrapper
