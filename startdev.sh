# Pysäytetään nykyinen Docker-compose stack
docker compose -f dev.docker-compose.yml --env-file ".env.local" down

# Poistetaan volume
docker volume rm jkr-core_postgis-data

# Käynnistetään tietokanta
docker compose -f dev.docker-compose.yml --env-file ".env.local" up db -d

# Suoritetaan Flyway-migraatiot
docker compose -f dev.docker-compose.yml --env-file ".env.local" up flyway

echo "Docker stack on nyt resetoitu ja käynnistetty uudelleen."