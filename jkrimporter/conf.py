import os

from dotenv import dotenv_values

env = {
    **dotenv_values(".env"),
    **os.environ,
}

dbconf = {
    "host": env.get("JKR_DB_HOST", None),
    "port": env.get("JKR_DB_PORT", None),
    "username": env.get("JKR_USER", None),
    "password": env.get("JKR_PASSWORD", None),
    "dbname": env.get("JKR_DB", None),
}

__all__ = ["dbconf"]
