#!/bin/bash

# Check if env file parameter is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path-to-env-file>"
    exit 1
fi

# Check if env file exists
if [ ! -f "$1" ]; then
    echo "Error: $1 file not found"
    exit 1
fi

# Load environment variables
set -a
source $1
set +a

# Set PostgreSQL client encoding
export PGCLIENTENCODING=UTF8

# Check required variables
required_vars=("JKR_DB_HOST" "JKR_DB_PORT" "JKR_DB" "JKR_USER" "QGIS_BIN_PATH")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var variable not set in $1"
        exit 1
    fi
done

echo "Converting to jkr format..."
psql -h "$JKR_DB_HOST" -p "$JKR_DB_PORT" -d "$JKR_DB" -U "$JKR_USER" -f "drop_schemas.sql"