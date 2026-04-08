# Pysäytetään nykyinen Docker-compose stack
docker compose -f dev.docker-compose.yml --env-file ".env.local" down

# Poistetaan volume
docker volume rm jkr-core_postgis-data

# Poistetaan flyway
docker rm jkr-core-flyway-1

# Käynnistetään tietokanta
docker compose -f dev.docker-compose.yml --env-file ".env.local" up db -d

# Suoritetaan Flyway-migraatiot
docker compose -f dev.docker-compose.yml --env-file ".env.local" up flyway

# Käynnistetään jkr-core-runner (API portti 8000)
docker compose -f dev.docker-compose.yml --env-file ".env.local" up jkr-core-runner -d

echo "Docker stack on nyt resetoitu ja käynnistetty uudelleen."
echo "API on saatavilla osoitteessa http://localhost:8000"