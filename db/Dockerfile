# Migration image: Flyway with this repo's migrations. Runs in the migration job
# before the backend is updated (deploy/deploy-backend.sh) and locally against any
# database with the same settings as the backend, e.g.
#   docker run --rm -e JKR_DB_HOST -e JKR_DB_PORT -e JKR_DB -e JKR_USER -e JKR_PASSWORD jkr-core-migrations [info|repair]
FROM flyway/flyway:13.11.1@sha256:fd082457bd0a470f567e236e16ec886c5fd1bd579b1bd1431e65d0e05fde88e2

COPY flyway.conf /flyway/conf/flyway.conf
COPY migrations /flyway/sql
COPY migrate.sh /flyway/migrate.sh

ENTRYPOINT ["/flyway/migrate.sh"]
