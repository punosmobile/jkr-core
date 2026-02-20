-- V3.05.15__Add_biohapa_velvoitteet.sql
-- LAH-460: Biohapa tarvitsee omat velvoitetarkastukset
--
-- Päätetään vanhat biojätevelvoitteet (ID 13-17) päättymispäivämäärällä 31.12.2023
-- Uudet Biohapa-velvoitteet (ID 44-48) lisätään R__z_Insert_velvoitemalli.sql:ssä

-- Päätetään vanhat biojätevelvoitteet (ID 13-17)
UPDATE jkr.velvoitemalli SET loppupvm = '2023-12-31' WHERE id = 13;
UPDATE jkr.velvoitemalli SET loppupvm = '2023-12-31' WHERE id = 14;
UPDATE jkr.velvoitemalli SET loppupvm = '2023-12-31' WHERE id = 15;
UPDATE jkr.velvoitemalli SET loppupvm = '2023-12-31' WHERE id = 16;
UPDATE jkr.velvoitemalli SET loppupvm = '2023-12-31' WHERE id = 17;
