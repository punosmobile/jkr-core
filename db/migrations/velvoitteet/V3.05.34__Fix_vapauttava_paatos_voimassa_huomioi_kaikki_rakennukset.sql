-- LAH-589: Kiinteän jätteen velvoiteyhteenvetotarkastus "vapautettu" ei huomioi kaikkia rakennuksia.
--
-- Aiemmin kohteet_joilla_vapauttava_paatos_voimassa palautti kohteen jo silloin,
-- kun yhdellä kohteen rakennuksella oli voimassa oleva vapauttava päätös. Nyt
-- funktio palauttaa kohteen vasta kun kohteen kaikilla velvoiterakennuksilla
-- on voimassa oleva vapauttava päätös (AKP tai Perusmaksu, myönteinen).
--
-- Toteutus mukailee lietteen velvoitetarkistuksissa käytettyä
-- jkr.kohteet_joiden_rakennukset_vapautettu-funktiota.
--
-- Velvoiterakennus = rakennus, jolla
--   - käyttötarkoitus 011–041, tai
--   - rakennusluokka 0110–0211, tai
--   - huoneistolukumäärä > 0, tai
--   - käyttötila 01,
-- tai kohde on kohdetyypiltään hapa (id 5) tai biohapa (id 6).

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_vapauttava_paatos_voimassa(daterange)
    RETURNS TABLE(kohde_id integer)
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
SELECT DISTINCT (id) FROM (
    SELECT k.id
    FROM jkr.kohde k
    JOIN jkr.kohteen_rakennukset kr ON kr.kohde_id = k.id
    JOIN jkr.rakennus r ON r.id = kr.rakennus_id
        AND (
            r.huoneistomaara > 0
            OR (
                r.rakennuksenkayttotarkoitus_koodi::integer >= 010
                AND r.rakennuksenkayttotarkoitus_koodi::integer <= 041
            )
            OR (
                r.rakennusluokka_2018::integer >= 0110
                AND r.rakennusluokka_2018::integer <= 0211
            )
            OR r.rakennuksenolotila_koodi::integer = 1
            OR k.kohdetyyppi_id IN (5, 6)
        )
    GROUP BY k.id
    HAVING COUNT(kr.rakennus_id) <= (
        SELECT COUNT(DISTINCT kr2.rakennus_id)
        FROM jkr.kohteen_rakennukset kr2
        JOIN jkr.viranomaispaatokset vp ON vp.rakennus_id = kr2.rakennus_id
        JOIN jkr_koodistot.tapahtumalaji tl ON vp.tapahtumalaji_koodi = tl.koodi
        JOIN jkr_koodistot.paatostulos pt ON vp.paatostulos_koodi = pt.koodi
        WHERE kr2.kohde_id = k.id
          AND vp.voimassaolo && $1
          AND tl.selite IN ('AKP', 'Perusmaksu')
          AND pt.selite = 'myönteinen'
    )
) AS sub;
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_vapauttava_paatos_voimassa(daterange)
    OWNER TO jkr_admin;
