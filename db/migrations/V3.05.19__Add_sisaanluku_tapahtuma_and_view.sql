CREATE TABLE IF NOT EXISTS jkr.sisaanluku_tapahtuma (
    id SERIAL PRIMARY KEY,
    komento TEXT NOT NULL,
    alkuaika TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    loppuaika TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'käynnissä',
    lisatiedot TEXT
);

COMMENT ON TABLE jkr.sisaanluku_tapahtuma IS 'Sisäänlukutapahtumien lokitaulu. Kirjaa kaikki aineiston sisäänlukukomennot.';
COMMENT ON COLUMN jkr.sisaanluku_tapahtuma.komento IS 'Suoritettu komento parametreineen';
COMMENT ON COLUMN jkr.sisaanluku_tapahtuma.alkuaika IS 'Sisäänluvun aloitusaika';
COMMENT ON COLUMN jkr.sisaanluku_tapahtuma.loppuaika IS 'Sisäänluvun päättymisaika. NULL jos kesken.';
COMMENT ON COLUMN jkr.sisaanluku_tapahtuma.status IS 'Tila: käynnissä, valmis, virhe';
COMMENT ON COLUMN jkr.sisaanluku_tapahtuma.lisatiedot IS 'Lisätietoja, esim. virheilmoitus';


-- View: jkr.v_tuontiloki_rivit
CREATE OR REPLACE VIEW jkr.v_tuontiloki_rivit
 AS
 SELECT id,
    alkuaika::date AS paiva,
    to_char(alkuaika, 'HH24:MI:SS'::text) AS kellonaika,
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

ALTER TABLE jkr.v_tuontiloki_rivit
    OWNER TO jkr_admin;

COMMENT ON VIEW jkr.v_tuontiloki_rivit IS 'Tuontiloki: näyttää sisäänlukutapahtumat tiivistettynä QGIS-näkymää varten.';
COMMENT ON COLUMN jkr.v_tuontiloki_rivit.id IS 'Tapahtuman yksilöivä tunniste';
COMMENT ON COLUMN jkr.v_tuontiloki_rivit.paiva IS 'Ajon päivämäärä';
COMMENT ON COLUMN jkr.v_tuontiloki_rivit.kellonaika IS 'Ajon aloituskellonaika (HH:MM:SS)';
COMMENT ON COLUMN jkr.v_tuontiloki_rivit.tyyppi IS 'Aineistotyyppi värikoodilla (Liete, DVV, Kuljetukset jne.)';
COMMENT ON COLUMN jkr.v_tuontiloki_rivit.status IS 'Tila: käynnissä, valmis, virhe';
COMMENT ON COLUMN jkr.v_tuontiloki_rivit.tulos IS 'Kooste ajon tuloksista (kohdentuneet, kohdentumattomat yms.)';
COMMENT ON COLUMN jkr.v_tuontiloki_rivit.komento IS 'Suoritettu komento';

GRANT ALL ON TABLE jkr.v_tuontiloki_rivit TO jkr_admin;
GRANT INSERT, UPDATE, DELETE ON TABLE jkr.v_tuontiloki_rivit TO jkr_editor;
GRANT SELECT ON TABLE jkr.v_tuontiloki_rivit TO jkr_viewer;