import os
import datetime

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
csv_fileext = ".csv"
excel_fileext = ".xlsx"


def get_kohdentumattomat_siirtotiedosto_filename():
    return f"{kohdentumattomat_filename}_kuljetukset{csv_fileext}"


def get_kohdentumattomat_paatos_filename():
    return f"{kohdentumattomat_filename}_paatokset{excel_fileext}"


def get_kohdentumattomat_ilmoitus_filename():
    return f"{kohdentumattomat_filename}_ilmoitukset{excel_fileext}"


def get_kohdentumattomat_lopetusilmoitus_filename():
    return f"{kohdentumattomat_filename}_lopetusilmoitukset{excel_fileext}"
