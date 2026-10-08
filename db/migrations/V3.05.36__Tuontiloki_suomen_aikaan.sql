-- Tuontilokin päivä ja kellonaika Suomen aikaan session aikavyöhykkeestä riippumatta
-- (Azure/docker-kannan oletus on UTC).
CREATE OR REPLACE VIEW jkr.v_tuontiloki_rivit
 AS
 SELECT id,
    (alkuaika AT TIME ZONE 'Europe/Helsinki')::date AS paiva,
    to_char(alkuaika AT TIME ZONE 'Europe/Helsinki', 'HH24:MI:SS'::text) AS kellonaika,
        CASE
            WHEN komento ~~* '%import_liete%'::text OR komento ~~* '%Liete%'::text THEN '🟤 Liete'::text
            WHEN komento ~~* '%import_viemari%'::text OR komento ~~* '%viemari%'::text THEN '🔵 Viemäri'::text
            WHEN komento ~~* '%DVV%'::text OR komento ~~* '%dvv%'::text THEN '🟢 DVV'::text
            WHEN komento ~~* '%import_paatokset%'::text THEN '🟡 Päätökset'::text
            WHEN komento ~~* '%ilmoitus%'::text THEN '🟠 Ilmoitukset'::text
            WHEN komento ~~* '%Kuljetustiedot%'::text THEN '🔴 Kuljetukset'::text
            WHEN komento ~~* '%kaivotied%'::text THEN '⚫ Kaivotiedot'::text
            WHEN komento ~~* '%tallenna_velvoite_status%'::text THEN '🟣 Velvoitestatus'::text
            WHEN komento ~~* '%update_velvoitteet%'::text THEN '🟪 Velvoiteajo'::text
            ELSE '⚪ Muu'::text
        END AS tyyppi,
    status,
        CASE
            WHEN lisatiedot ~~* '%yhteensä%'::text THEN lisatiedot
            ELSE split_part(lisatiedot, '. '::text, 1)
        END AS tulos,
    regexp_replace(komento, 'password=\S+'::text, 'password=***'::text, 'g'::text) AS komento
   FROM jkr.sisaanluku_tapahtuma
  ORDER BY alkuaika DESC;
