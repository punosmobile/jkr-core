import os
import platform
import sys

from dotenv import dotenv_values


# Path to the .env file in the user's %APPDATA%/jkr directory
print('checking system and loading env')
if platform.system() == 'Windows':
    dotenv_path = os.path.join(os.getenv("APPDATA"), "jkr", ".env")
else:
    home_path = os.getenv("HOME")
    if home_path:
        dotenv_path = home_path + "/.config/jkr/.env"

# Read the environment variables from the .env file
env = {
    **dotenv_values(dotenv_path),
    **os.environ,
}

test_command = "pytest"

# Define database configuration using environment variables
dbconf = {
    "host": env.get("JKR_DB_HOST", None),
    "port": env.get("JKR_DB_PORT", None),
    "username": env.get("JKR_USER", None),
    "password": env.get("JKR_PASSWORD", None),
    "dbname": env.get("JKR_DB", None),
}
if (
    test_command in sys.argv[0]
):  # Running tests, set configuration for test database
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
