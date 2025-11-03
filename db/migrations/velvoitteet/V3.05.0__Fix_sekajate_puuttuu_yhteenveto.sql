-- V3.05.0__Fix_sekajate_puuttuu_yhteenveto.sql
-- LAH-383: Korjaa "sekajäte puuttuu" yhteenveto biohapa-kohteille
--
-- Ongelma: Yhteenvetomalli 34 käyttää saanto='kohde' mikä on TAULU, ei näkymä.
-- update_velvoitteet() funktio vaatii että saanto on näkymä.
--
-- Ratkaisu: Luodaan näkymä v_kohde joka palauttaa kaikki kohteet.
-- Varsinainen suodatus (keillä sekajäte puuttuu) tapahtuu tayttymissaanto-funktiossa
-- joka ottaa daterange parametrin, joten historiallisten yhteenvetojen luominen toimii.

-- Luodaan näkymä joka palauttaa kaikki kohteet
CREATE OR REPLACE VIEW jkr.v_kohde AS
SELECT * FROM jkr.kohde;

-- Päivitetään yhteenvetomalli 34 käyttämään näkymää taulun sijaan
UPDATE jkr.velvoiteyhteenvetomalli
SET saanto = 'v_kohde'
WHERE id = 34;