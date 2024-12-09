-- V2.43.0__Add_rakennusluokka_2018.sql
ALTER TABLE jkr.rakennus 
ADD COLUMN rakennusluokka_2018 VARCHAR(4);

COMMENT ON COLUMN jkr.rakennus.rakennusluokka_2018 
IS 'Rakennusluokka 2018 -luokituksen mukainen rakennuksen käyttötarkoitus';

CREATE INDEX idx_rakennus_rakennusluokka_2018 
ON jkr.rakennus(rakennusluokka_2018);