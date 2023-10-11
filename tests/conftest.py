import os
from pathlib import Path
from shutil import copytree
import subprocess

from pytest import fixture


@fixture
def datadir(tmpdir, request):
    """
    Fixture responsible for searching a folder with the same name of test
    module and, if available, moving all contents to a temporary directory so
    tests can use them freely.
    """
    testfilepath = Path(request.module.__file__)
    testdir = testfilepath.parent
    testfilename = testfilepath.stem

    datadir = testdir / "data" / testfilename
    if os.path.isdir(datadir):
        copytree(datadir, tmpdir, dirs_exist_ok=True)
    print(datadir)
    print(tmpdir)
    print(os.listdir(tmpdir))

    return tmpdir


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.
    Creating the test database each time from scratch.
    """
    init_test_db_command = ".\\scripts\\init_database.bat"
    try:
        subprocess.check_output(init_test_db_command, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"Creating test database failed: {e.output}")
