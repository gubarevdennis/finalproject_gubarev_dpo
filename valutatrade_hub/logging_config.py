# valutatrade_hub/logging_config.py
import logging
import logging.config
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)  # Ensure the logs directory exists


def configure_logging():
    """Configures logging for the application."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(LOGS_DIR, f"actions_{timestamp}.log")

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%dT%H:%M:%S%z'
            },
            # valutatrade_hub/logging_config.py
            'json': {
                'format': '{  "timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "log_message": "%(message)s", "action": "%(action)s", "username": "%(username)s", "currency_code": "%(currency_code)s", "amount": "%(amount)s", "rate": "%(rate)s", "base": "%(base)s",  "result": "%(result)s",  "error_type": "%(error_type)s",  "error_message": "%(error_message)s" }',
                'datefmt': '%Y-%m-%dT%H:%M:%S%z'
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',  # Default is stderr
            },
            'file': {
                'level': 'INFO',
                'formatter': 'json',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_filename,
                'maxBytes': 1024 * 1024,  # 1 MB
                'backupCount': 5,  # Rotate through 5 files
                'encoding': 'utf8',
            },
        },
        'loggers': {
            'valutatrade_hub': {  # Logger for the whole application
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': True,
            },
            'valutatrade_hub.core.usecases': {  # Logger for usecases
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,  # Do not propagate to the root logger
            },
            'valutatrade_hub.cli.interface': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'valutatrade_hub.parser_service': {
                 'handlers': ['console', 'file'],
                 'level': 'INFO',
                 'propagate': False,
            },
        },
    }
    logging.config.dictConfig(logging_config)


# Example usage:
if __name__ == "__main__":
    configure_logging()
    logger = logging.getLogger("valutatrade_hub")
    logger.info("This is a test log message.")