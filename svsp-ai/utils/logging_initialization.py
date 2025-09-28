import logging


def initialize_logging():
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                        filename="log.log",
                        level=logging.DEBUG)
    logging.debug("Logging started.")
