import logging


def setup_logging():
    loglevel = logging.INFO
    logformat = '%(asctime)s %(levelname)s - %(filename)s: %(message)s'

    logging.basicConfig(filename='linuxff12rnghelper.log',
                        level=loglevel,
                        format=logformat)

    logging.debug("Login setup complete")
