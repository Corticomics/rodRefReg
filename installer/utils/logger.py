import logging

def setup_logging():
    logging.basicConfig(
        filename='installer.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("Installer started")

def log_info(message):
    logging.info(message)

def log_error(message):
    logging.error(message)
