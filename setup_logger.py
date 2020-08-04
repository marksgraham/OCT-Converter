import logging
# logging.basicConfig(level=logging.DEBUG)
def get_logger():
    # Create a custom logger
    logger = logging.getLogger('e2e_output.log')

    # logger = logging.basicConfig(filename='e2e_output.log', filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Create handlers
    f_handler = logging.FileHandler('e2e_output.log')
    # f_handler = logging.FileHandler(__name__)
    f_handler.setLevel(logging.WARNING)

    # Create formatters and add it to handlers
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(f_handler)
    return logger

def default_logger(name=__name__):
    logging.basicConfig(filename=name, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    return logging
