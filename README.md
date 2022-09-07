# Jätteenkuljetusrekisteri Core

This repository contains core parts of Jätteenkuljetusrekisteri including the data model and the importer tool.

This project is intended to be extended by customer specific modifications etc. import format plugins etc.


## Installing

You probably want install this to a virtual environment so your system python don't get cluttered of dependencies.
```bash
$ python -m venv jkr-venv
$ jkr-venv\scripts\activate
```

Download the whl file etc. `jkr-0.1.0-py3-none-any.whl`
```bash
(jkr-venv) $ pip install jkr-0.1.0-py3-none-any.whl
```

Now import script can be started
```bash
(jkr-venv) $ jkr import SIIRTOTIEDOSTO TIEDONTUOTTAJA
```

## Setting up a dev environment

The development environment uses [Poetry](https://python-poetry.org/). Install it before anything.

```bash
$ git clone https://github.com/GispoCoding/jkr-core.git
$ cd jkr-core

$ poetry install
```

### Db env

Install docker and docker-compose (version >= 1.28.0)

Copy .env.template to .env and change parameters
```bash
$ cp .env.template .env

# Edit the .env file
$ nano .env
```

```bash
docker-compose up db -d
docker-compose up flyway
```

## Handling database model changes
The diff operation in pgModeler is quite fragile and not recommended used directly.

We use Flyway (for now) to generate database migrations. Flyway is a SQL file based migration system.
PgModeler is used to generate diff SQL files and then Flyway is used to apply the migrations.

### Create the initial migration
```bash
pgmodeler-cli.exe --export-to-file --input jkr.dbm --output migrations/V1__initial.sql --pgsql-ver 12.0
```

### Creating incremental migrations
```bash
# 1. Verify db is up to date (all current migrations applied) by running 
docker-compose up flyway

# 2. Modify the pgmodeler model

# 3. Create a diff file. Change the conn-alias and output file.
pgmodeler-cli.exe --diff --save --input jkr.dbm --compare-to jkr --conn-alias local-db --output migrations/V2__add_sailio_table.sql --pgsql-ver 12.0

# 4. Validate and modify the migration file

# 5. Migrate by running 
docker-compose up flyway

# 6. Verify all changes in model are apllied to the database by executing step 3 again and checking that no diff is generated.
```

**Repairing migrations**
```bash
docker-compose run --rm flyway repair
```

### Running migrations against different platform
```bash
docker-compose run --rm flyway migrate -user=jkr_admin -password=<password> -url=jdbc:postgresql://trepx-paikka1.tre.t.verkko:5432/ymparisto_test_db
```

## QGIS project

1. Create a PostgreSQL service file to some folder for example in `~/jkrconfig/pg_service.conf` 
```
[jkr-dev]
host=localhost
port=5435
dbname=ymparisto_db

[jkr-test]
host=jkr_test_server
port=5432
dbname=ymparisto_db

[jkr-prod]
host=jkr_test_server
port=5432
dbname=ymparisto_db
```

2. Add a `PGSERVICEFILE` environment variable to your account to point to that file.

3. (Optional) Create a new QGIS profile for this project
4. Add three QGIS authentication configs for each environment. Set the id to `jkrdeve`, `jkrtest` and `jkrprod`.
5. Open the QGIS-project
