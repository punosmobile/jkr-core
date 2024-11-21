#!/bin/bash
export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD


    # Tarkista että tiedontuottaja on olemassa
jkr tiedontuottaja list | grep -q "LSJ" || \
jkr tiedontuottaja add LSJ "Lahden Seudun Jätehuolto"


# Q1 2022
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2022/Q1 LSJ 1.1.2022 31.3.2022

# Q2 2022 
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2022/Q2 LSJ 1.4.2022 30.6.2022

# Q3 2022
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2022/Q3 LSJ 1.7.2022 30.9.2022

# Q4 2022
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2022/Q4 LSJ 1.10.2022 31.12.2022