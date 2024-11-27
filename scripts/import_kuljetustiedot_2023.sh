#!/bin/bash
export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD


    # Tarkista että tiedontuottaja on olemassa
jkr tiedontuottaja list | grep -q "LSJ" || \
jkr tiedontuottaja add LSJ "Lahden Seudun Jätehuolto"


# Q1 2023
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2023/Q1 LSJ 1.1.2023 31.3.2023

# Q2 2023 
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2023/Q2 LSJ 1.4.2023 30.6.2023

# Q3 2023
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2023/Q3 LSJ 1.7.2023 30.9.2023

# Q4 2023
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2023/Q4 LSJ 1.10.2023 31.12.2023