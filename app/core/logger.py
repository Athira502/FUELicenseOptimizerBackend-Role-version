
import logging
import sys
import os
import datetime


def configure_logging(client_name=None, system_id=None):
    """Configures logging for the application with optional client/system-based filename."""
    logger = logging.getLogger(__name__)
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.ERROR)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if client_name and system_id:
        filename = f"{client_name}-{system_id}-{timestamp}.log"
    elif client_name:
        filename = f"{client_name}-{timestamp}.log"
    else:
        filename = f"app-{timestamp}.log"

    file_handler = logging.FileHandler(os.path.join(log_dir, filename))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# 🔧 Add this line
logger = configure_logging()
