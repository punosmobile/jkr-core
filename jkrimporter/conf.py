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

kohdentumattomat_filename = "kohdentumattomat"
siirtotiedosto_fileext = ".csv"
paatostiedosto_fileext, ilmoitustiedosto_fileext = ".xlsx"


def get_kohdentumattomat_siirtotiedosto_filename():
    return kohdentumattomat_filename + siirtotiedosto_fileext


def get_kohdentumattomat_paatos_filename():
    return kohdentumattomat_filename + paatostiedosto_fileext


def get_kohdentumattomat_ilmoitus_filename():
    return kohdentumattomat_filename + ilmoitustiedosto_fileext
