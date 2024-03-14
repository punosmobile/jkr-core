import os

from dotenv import dotenv_values

from tests.conftest import TEST_ENV


# Path to the .env file in the user's %APPDATA%/jkr directory
dotenv_path = os.path.join(os.getenv('APPDATA'), 'jkr', '.env')

# Read the environment variables from the .env file
env = {
    **dotenv_values(dotenv_path),
    **os.environ,
}

# Define database configuration using environment variables
dbconf = {
    "host": env.get("JKR_DB_HOST", None),
    "port": env.get("JKR_DB_PORT", None),
    "username": env.get("JKR_USER", None),
    "password": env.get("JKR_PASSWORD", None),
    "dbname": env.get("JKR_DB", None),
}
if TEST_ENV:
    dbconf["port"] = env.get("JKR_TEST_DB_PORT", None)
    dbconf["password"] = env.get("JKR_TEST_PASSWORD", None)
    dbconf["dbname"] = env.get("JKR_TEST_DB", None)

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
