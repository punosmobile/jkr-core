CREATE OR REPLACE VIEW jkr.v_bio_hapa_asuinkiinteisto
 AS
 SELECT DISTINCT id
   FROM jkr.kohde k
  WHERE kohdetyyppi_id IN (6,5,7);

ALTER TABLE jkr.v_bio_hapa_asuinkiinteisto
    OWNER TO jkr_admin;
COMMENT ON VIEW jkr.v_bio_hapa_asuinkiinteisto
    IS 'Näkymä Hapa, Biohaba ja asunkiinteistö-tyyppisten kohteiden tunnistamiseen';

GRANT ALL ON TABLE jkr.v_bio_hapa_asuinkiinteisto TO jkr_admin;
GRANT INSERT, DELETE, UPDATE ON TABLE jkr.v_bio_hapa_asuinkiinteisto TO jkr_editor;
GRANT SELECT ON TABLE jkr.v_bio_hapa_asuinkiinteisto TO jkr_viewer;


-- FUNCTION: jkr.kohteet_jotka_viemariverkossa(daterange)

-- DROP FUNCTION IF EXISTS jkr.kohteet_jotka_viemariverkossa(daterange);

CREATE OR REPLACE FUNCTION jkr.kohteet_jotka_ovat_viemariverkossa(
	daterange)
    RETURNS TABLE(kohde_id integer) 
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE EXISTS
        (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
			JOIN jkr.rakennus r ON r.id = kr.rakennus_id
            WHERE kr.kohde_id = k.id
            AND (daterange(r.kayttoonotto_pvm, r.kaytostapoisto_pvm) && $1 OR r.kaytostapoisto_pvm IS NOT NULL)
            AND r.onko_viemari IS TRUE
        )
$BODY$;

ALTER FUNCTION jkr.kohteet_jotka_ovat_viemariverkossa(daterange)
    OWNER TO jkr_admin;


ALTER TABLE jkr.velvoitemalli ADD COLUMN prioriteetti integer;

-- FUNCTION: jkr.kohteet_joiden_rakennukset_vapautettu(daterange)

-- DROP FUNCTION IF EXISTS jkr.kohteet_joiden_rakennukset_vapautettu(daterange);

CREATE OR REPLACE FUNCTION jkr.kohteet_joiden_rakennukset_vapautettu(
	daterange)
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
	GROUP BY k.id
	HAVING COUNT(kr.rakennus_id) = (
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
);
$BODY$;

ALTER FUNCTION jkr.kohteet_joiden_rakennukset_vapautettu(daterange)
    OWNER TO jkr_admin;


-- FUNCTION: jkr.kohteet_joilla_kantovesi_tieto(daterange)

-- DROP FUNCTION IF EXISTS jkr.kohteet_joilla_kantovesi_tieto(daterange);

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_kantovesi_tieto(
	daterange)
    RETURNS TABLE(kohde_id integer) 
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
SELECT k.id
FROM jkr.kohde k
JOIN jkr.kaivotieto kt ON kt.kohde_id = k.id
WHERE kt.kaivotietotyyppi_id = 1 AND kt.voimassaolo && $1
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_kantovesi_tieto(daterange)
    OWNER TO jkr_admin;