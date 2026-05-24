# utils/logging_config.py - Enhanced Logging Configuration for Crisis Simulation

import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logging(log_level="INFO", log_dir="logs"):
    """
    Set up comprehensive logging for the crisis simulation.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
    """
    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(exist_ok=True)
    
    # Generate timestamp for log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Configure logging format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for general logs
    file_handler = logging.FileHandler(
        f"{log_dir}/crisis_sim_{timestamp}.log"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Specialized loggers for different components
    setup_component_loggers(log_dir, timestamp, formatter)
    
    return logger

def setup_component_loggers(log_dir, timestamp, formatter):
    """Set up specialized loggers for different system components."""
    
    # Agent performance logger
    agent_logger = logging.getLogger("agents")
    agent_handler = logging.FileHandler(
        f"{log_dir}/agents_{timestamp}.log"
    )
    agent_handler.setFormatter(formatter)
    agent_logger.addHandler(agent_handler)
    
    # LLM/reasoning logger
    llm_logger = logging.getLogger("reasoning")
    llm_handler = logging.FileHandler(
        f"{log_dir}/reasoning_{timestamp}.log"
    )
    llm_handler.setFormatter(formatter)
    llm_logger.addHandler(llm_handler)
    
    # Decision quality logger
    decision_logger = logging.getLogger("decisions")
    decision_handler = logging.FileHandler(
        f"{log_dir}/decisions_{timestamp}.log"
    )
    decision_handler.setFormatter(formatter)
    decision_logger.addHandler(decision_handler)
    
    # Tool calling logger
    tools_logger = logging.getLogger("tools")
    tools_handler = logging.FileHandler(
        f"{log_dir}/tools_{timestamp}.log"
    )
    tools_handler.setFormatter(formatter)
    tools_logger.addHandler(tools_handler)

def get_logger(name):
    """Get a named logger for a specific component."""
    return logging.getLogger(name)
