FROM postgres:12-bullseye

ENV POSTGIS_MAJOR 3

RUN apt-get update \
     && apt-cache showpkg postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR \
     && apt-get install -y --no-install-recommends \
     postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR \
     postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR-scripts \
     && rm -rf /var/lib/apt/lists/*
