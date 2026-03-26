import asyncio
import collections
import io
import json
import logging
import os
import sys
from datetime import datetime

__version__ = "0.7.6"

# ---------------------------------------------------------------------------
# Custom log level: IMPORT (between INFO=20 and WARNING=30)
# levels: DEBUG=10, INFO=20, IMPORT=25, WARNING=30, ERROR=40, CRITICAL=50
# ---------------------------------------------------------------------------
IMPORT = 25
logging.addLevelName(IMPORT, "IMPORT")


def _log_import(self, message, *args, **kwargs):
    if self.isEnabledFor(IMPORT):
        self._log(IMPORT, message, args, **kwargs)


logging.Logger.log_import = _log_import


# ---------------------------------------------------------------------------
# WebSocket log handler: kerää logiviestit ja lähettää WS-clienteille
# ---------------------------------------------------------------------------
class WebSocketLogHandler(logging.Handler):
    """Logging handler joka lähettää viestit WebSocket-clienteille."""

    MAX_BUFFER = 500

    def __init__(self, level=logging.DEBUG):
        super().__init__(level)
        self._clients: set = set()
        self._buffer: collections.deque = collections.deque(maxlen=self.MAX_BUFFER)

    def emit(self, record):
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "levelno": record.levelno,
                "logger": record.name,
                "message": self.format(record),
            }
            self._buffer.append(entry)

            # Ei serialisointia eikä lähetystä jos kukaan ei kuuntele
            if not self._clients:
                return

            msg = json.dumps(entry, ensure_ascii=False)
            stale = set()
            for ws_send in self._clients:
                try:
                    asyncio.get_event_loop().call_soon_threadsafe(
                        asyncio.ensure_future, ws_send(msg)
                    )
                except RuntimeError:
                    stale.add(ws_send)
            self._clients -= stale
        except Exception:
            self.handleError(record)

    def register(self, send_func):
        self._clients.add(send_func)

    def unregister(self, send_func):
        self._clients.discard(send_func)

    def get_buffer(self):
        return list(self._buffer)


ws_log_handler = WebSocketLogHandler()


# ---------------------------------------------------------------------------
# StreamToLogger: ohjaa stdout/stderr loggerin läpi
# ---------------------------------------------------------------------------
class StreamToLogger(io.TextIOBase):
    """Wrapperi joka ohjaa write()-kutsut (esim. print()) loggerin kautta."""

    def __init__(self, logger, level, fallback_stream):
        super().__init__()
        self._logger = logger
        self._level = level
        self._fallback = fallback_stream
        self._buffer = ""

    def write(self, message):
        if message and message.strip():
            for line in message.rstrip("\n").splitlines():
                self._logger.log(self._level, line)
        return len(message) if message else 0

    def flush(self):
        if self._fallback and hasattr(self._fallback, "flush"):
            self._fallback.flush()

    def fileno(self):
        return self._fallback.fileno()

    @property
    def encoding(self):
        return getattr(self._fallback, "encoding", "utf-8")


# ---------------------------------------------------------------------------
# Logger-konfiguraatio
# ---------------------------------------------------------------------------
_log_level_name = os.environ.get("JKR_LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, None)
if _log_level is None and _log_level_name == "IMPORT":
    _log_level = IMPORT
if _log_level is None:
    _log_level = logging.INFO

logFormatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.setLevel(_log_level)

fileHandler = logging.FileHandler("jkr.log")
fileHandler.setFormatter(logFormatter)
fileHandler.setLevel(logging.DEBUG)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(stream=sys.__stdout__)
consoleHandler.setFormatter(logFormatter)
consoleHandler.setLevel(_log_level)
rootLogger.addHandler(consoleHandler)

ws_log_handler.setFormatter(logFormatter)
ws_log_handler.setLevel(logging.DEBUG)
rootLogger.addHandler(ws_log_handler)

# ---------------------------------------------------------------------------
# Ohjaa stdout ja stderr loggerin läpi
# ---------------------------------------------------------------------------
sys.stdout = StreamToLogger(rootLogger, logging.INFO, sys.__stdout__)
sys.stderr = StreamToLogger(rootLogger, logging.ERROR, sys.__stderr__)
