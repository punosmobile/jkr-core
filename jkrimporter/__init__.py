import logging

__version__ = "0.7.4"

logFormatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")
rootLogger = logging.getLogger()

fileHandler = logging.FileHandler("jkr.log")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
rootLogger.addHandler(consoleHandler)
