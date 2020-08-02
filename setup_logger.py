import logging
# logging.basicConfig(level=logging.DEBUG)
def get_logger():
    # Create a custom logger
    logger = logging.getLogger('e2e_output.log')
    # Create handlers
    f_handler = logging.FileHandler('e2e_output.log')
    f_handler.setLevel(logging.WARNING)

    # Create formatters and add it to handlers
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(f_handler)
    return logger
