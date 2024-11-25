#!/bin/bash
export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD


    # Tarkista että tiedontuottaja on olemassa
jkr tiedontuottaja list | grep -q "LSJ" || \
jkr tiedontuottaja add LSJ "Lahden Seudun Jätehuolto"


# Q1 2024
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2024/Q1 LSJ 1.1.2024 31.3.2024

# Q2 2024 
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2024/Q2 LSJ 1.4.2024 30.6.2024

# Q3 2024
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2024/Q3 LSJ 1.7.2024 30.9.2024

# Q4 2024
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2024/Q4 LSJ 1.10.2024 31.12.2024