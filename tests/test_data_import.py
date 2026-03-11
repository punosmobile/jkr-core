import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import (
    Osapuolenrooli,
)


@pytest.fixture(scope="module", autouse=True)
def engine():
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
            **conf.dbconf
        ),
        future=True,
        json_serializer=json_dumps,
    )
    return engine


def test_osapuolenrooli(engine):
    osapuolenroolit = [
        (1, "Omistaja"),
        (2, "Vanhin asukas"),
        (11, "Tilaaja sekajäte"),
        (12, "Tilaaja biojäte"),
        (13, "Tilaaja muovipakkaus"),
        (14, "Tilaaja kartonkipakkaus"),
        (15, "Tilaaja lasipakkaus"),
        (16, "Tilaaja metalli"),
        (17, "Tilaaja monilokero"),
        (18, "Tilaaja liete"),
        (19, "Tilaaja aluekeräyspiste"),
        (111, "Kimppaisäntä sekajäte"),
        (112, "Kimppaisäntä biojäte"),
        (113, "Kimppaisäntä muovipakkaus"),
        (114, "Kimppaisäntä kartonkipakkaus"),
        (115, "Kimppaisäntä lasipakkaus"),
        (116, "Kimppaisäntä metalli"),
        (117, "Kimppaisäntä monilokero"),
        (211, "Kimppaosakas sekajäte"),
        (212, "Kimppaosakas biojäte"),
        (213, "Kimppaosakas muovipakkaus"),
        (214, "Kimppaosakas kartonkipakkaus"),
        (215, "Kimppaosakas lasipakkaus"),
        (216, "Kimppaosakas metalli"),
        (217, "Kimppaosakas monilokero"),
        (311, "Yhteyshenkilö kompostointi"),
    ]
    session = Session(engine)
    result = session.execute(select([Osapuolenrooli.id, Osapuolenrooli.selite]))
    assert [tuple(row) for row in result] == osapuolenroolit
