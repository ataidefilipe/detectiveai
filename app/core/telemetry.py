import logging
import json

def get_telemetry_logger(name: str = "detective-telemetry") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        # We can format it as plain text or JSON
        # For simple telemetry viewing, we'll configure a basic message format
        # where the message itself is the JSON string
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

telemetry_logger = get_telemetry_logger()
