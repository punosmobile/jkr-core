# Kevyt testiajuri-image CI-porttia varten (LAH-629).
#
# Sisältää vain sen minkä testit oikeasti tarvitsevat:
#   - Python 3.11 (sama pohja kuin tuotanto-image)
#   - poetry (riippuvuudet asennetaan ajossa: `poetry install`, koska /app
#     mountataan volyymina)
#   - ogr2ogr (gdal-bin) ja psql (postgresql-client) DVV-testidatan tuontiin
#     (conftest.pytest_sessionstart -> tests/scripts/init_database_container.sh)
#
# EI QGIS:ää eikä GDAL-Python-bindingsejä — niitä ei importoida missään
# (koko koodikannassa vain shapely + geoalchemy2, jotka asentuvat wheelinä).
# Riippuvuudet eivät vaadi build-toolseja, joten build-essential/libgdal-dev
# jätetään pois. Tämä pudottaa image-buildin ~20-30 min -> ~1-3 min vs.
# tuotannon QGIS-image.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.5.1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends \
        gdal-bin \
        postgresql-client \
        locales \
        bash \
    && sed -i '/fi_FI.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Sama locale kuin tuotannossa (numero-/päivämäärämuotoilun yhdenmukaisuus).
ENV LANG=fi_FI.UTF-8 \
    LANGUAGE=fi_FI:fi \
    LC_ALL=fi_FI.UTF-8

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app
