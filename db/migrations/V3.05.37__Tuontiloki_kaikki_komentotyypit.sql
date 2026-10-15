-- Tuontilokin tyyppi-sarake kattaa kaikki tuontilokiin kirjautuvat komennot.
--
-- Aiemmin tyyppi päätettiin osamerkkijonoista koko komennon alueelta, jolloin
-- tiedostopolku ratkaisi tyypin (esim. "jkr import_paatokset ../data/Liete/..."
-- näkyi Lietteenä, samoin batch_import-ajojen kaikki rivit ensimmäisen tiedoston
-- mukaan). Nyt jkr-CLI:n komennot tunnistetaan alikomennon nimestä komennon
-- alusta, ja vain muut komennot (psql, ogr2ogr, sh-skriptit) tunnistetaan sisällön
-- perusteella.
CREATE OR REPLACE VIEW jkr.v_tuontiloki_rivit
 AS
 SELECT t.id,
    (t.alkuaika AT TIME ZONE 'Europe/Helsinki')::date AS paiva,
    to_char(t.alkuaika AT TIME ZONE 'Europe/Helsinki', 'HH24:MI:SS'::text) AS kellonaika,
        CASE
            -- Velvoitefunktiot kirjaavat itse rivinsä komennolla 'SELECT jkr.<funktio>(...)'
            WHEN t.komento ~* 'jkr\.update_velvoitteet'::text THEN '🟪 Velvoiteajo'::text
            WHEN t.komento ~* 'jkr\.tallenna_velvoite_status'::text THEN '🟣 Velvoitestatus'::text
            -- jkr-CLI:n alikomennot
            WHEN k.alakomento = 'import'::text THEN '🔴 Kuljetukset'::text
            WHEN k.alakomento = 'import_liete'::text THEN '🟤 Liete'::text
            WHEN k.alakomento = 'import_liete_ilmoitukset'::text THEN '🟫 Lietteen kompostointi'::text
            WHEN k.alakomento = 'import_paatokset'::text THEN '🟡 Päätökset'::text
            WHEN k.alakomento = 'import_ilmoitukset'::text THEN '🟠 Ilmoitukset'::text
            WHEN k.alakomento = 'import_lopetusilmoitukset'::text THEN '🟧 Lopetusilmoitukset'::text
            WHEN k.alakomento = 'import_kaivotiedot'::text THEN '⚫ Kaivotiedot'::text
            WHEN k.alakomento = 'import_kaivotiedon_lopetukset'::text THEN '⬛ Kaivotiedon lopetukset'::text
            WHEN k.alakomento = 'import_viemarit'::text THEN '🔵 Viemäri'::text
            WHEN k.alakomento = 'import_lopeta_viemarit'::text THEN '🟦 Viemärin lopetus'::text
            WHEN k.alakomento = ANY (ARRAY['import_and_create_kohteet'::text, 'create_dvv_kohteet'::text]) THEN '🟢 DVV'::text
            WHEN k.alakomento = 'update_huoneistomaara'::text THEN '🟩 Huoneistomäärät'::text
            WHEN k.alakomento = 'import_hapa'::text THEN '🟨 HAPA'::text
            WHEN k.alakomento = 'import_sote'::text THEN '🟥 SOTE'::text
            WHEN k.alakomento = 'import_taajamat'::text THEN '⬜ Taajamat'::text
            WHEN k.alakomento = 'tiedontuottaja'::text THEN '🔷 Tiedontuottajat'::text
            -- Vanhat batch_import-rivit (ennen korjausta jokainen tiedosto kirjautui
            -- batch-komennolla, joten varsinaista tyyppiä ei voi päätellä komennosta)
            WHEN k.alakomento = 'batch_import'::text THEN '📦 Joukkotuonti'::text
            -- Muut kuin jkr-CLI:n komennot (API:n _run_task ja scripts/*.sh)
            WHEN t.komento ~* 'import_taajama\.sh'::text THEN '⬜ Taajamat'::text
            WHEN t.komento ~* 'import_viemari\.sh'::text THEN '🔵 Viemäriverkosto'::text
            WHEN t.komento ~* 'huoneistomaara'::text THEN '🟩 Huoneistomäärät'::text
            WHEN t.komento ~* 'import_dvv\.sql|ACTIVE_SCHEMA=jkr_dvv'::text THEN '🟢 DVV'::text
            WHEN t.komento ~* 'hapa_aineisto'::text THEN '🟨 HAPA'::text
            WHEN t.komento ~* 'sote_aineisto'::text THEN '🟥 SOTE'::text
            WHEN t.komento ~* 'jkr_koodistot\.tiedontuottaja'::text THEN '🔷 Tiedontuottajat'::text
            WHEN t.komento ~* 'jkr_posti\.sql'::text THEN '🔶 Postinumerot'::text
            WHEN t.komento ~* '\\copy'::text THEN '⚪ CSV-tuonti'::text
            WHEN t.komento ~* '^\s*ogr2ogr'::text THEN '⚪ Paikkatietotuonti'::text
            ELSE '⚪ Muu'::text
        END AS tyyppi,
    t.status,
        CASE
            WHEN t.lisatiedot ~~* '%yhteensä%'::text THEN t.lisatiedot
            ELSE split_part(t.lisatiedot, '. '::text, 1)
        END AS tulos,
    regexp_replace(t.komento, 'password=\S+'::text, 'password=***'::text, 'g'::text) AS komento
   FROM jkr.sisaanluku_tapahtuma t
     -- jkr-CLI:n alikomento komennon alusta: "jkr <alikomento> ..." tai "/polku/jkr <alikomento> ..."
     CROSS JOIN LATERAL (SELECT substring(t.komento FROM '^\s*(?:\S*/)?jkr\s+([a-z_]+)'::text) AS alakomento) k
  ORDER BY t.alkuaika DESC;

COMMENT ON COLUMN jkr.v_tuontiloki_rivit.tyyppi IS 'Aineistotyyppi värikoodilla, päätelty komennosta (jkr-alikomento tai psql/ogr2ogr/sh-skriptin sisältö)';
