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

## Using the QGIS project

The QGIS project reads data from a PostgreSQL service named `jkr` with a QGIS authentication which id is `jkruser`.

1. Create a PostgreSQL service file for each environment (Development, Testing, Production) to some folder for example in `<your home folder>/jkrconfig/`. Name the files for example `pg_service_jkr_dev.conf`, `pg_service_jkr_test.conf`, `pg_service_jkr_prod.conf`. Add the following with correct values for each environment:
```ini
[jkr]
host=localhost
port=5435
dbname=ymparisto_db
```
2. Create a QGIS-profile for each environment (Development, Testing, Production). Name the profiles for example `jkr-dev`, `jkr-test`, `jkr-prod`. A new QGIS window will open. Use that   
![schreenshot of new profile menu](docs/img/qgis-new-profile.png)
3. In QGIS settings add a `PGSERVICEFILE` environment variable and fill the file path of corresponding service file as a value.  
![screenshot of menu location](docs/img/qgis-settings.png)  
![screenshot of the setting dialog](docs/img/qgis-pgservicefile-environment-variable.png)
4. Restart QGIS to make the environment variable to take effect.
5. Create a authentication key to QGIS which ID is `jkruser`.  
![screenshot of the authentication dialog](docs/img/qgis-authentication.png)
6. Create a new PostgreSQL connection  
![screenshot of the new connection menu](docs/img/qgis-new-connection.png)  
![screenshot of the new connection dialog](docs/img/qgis-create-connection.png)
7. Open the QGIS project from the jkr-qgis-projektit -schema.  
![screenshot of the qgis projects schema](docs/img/qgis-open-project.png)


> **Development**  
> For development use the [QGIS-project](qgis/jkr.qgs) can be used.
