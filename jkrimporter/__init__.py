import logging

__version__ = "0.2.0"

logFormatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")
rootLogger = logging.getLogger()

fileHandler = logging.FileHandler("jkr.log")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
rootLogger.addHandler(consoleHandler)
