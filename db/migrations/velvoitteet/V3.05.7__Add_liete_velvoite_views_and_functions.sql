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
WHERE EXISTS(
		SELECT 1
		FROM jkr.viemari_liitos vl
		WHERE k.id = vl.kohde_id 
			AND (
				vl.voimassaolo && $1 
				OR vl.viemariverkosto_loppupvm IS NULL
			)
	) AND NOT EXISTS (
		SELECT 1 FROM jkr.kaivotieto
		WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2,3,4,5)
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
	JOIN jkr.rakennus r ON r.id = kr.rakennus_id 
		AND (
			R.HUONEISTOMAARA > 0
			OR (
				R.RAKENNUKSENKAYTTOTARKOITUS_KOODI::INTEGER >= 010
				AND R.RAKENNUKSENKAYTTOTARKOITUS_KOODI::INTEGER <= 041
			)
			OR (
				R.RAKENNUSLUOKKA_2018::INTEGER >= 0110
				AND R.RAKENNUSLUOKKA_2018::INTEGER <= 0211
			)
			OR R.RAKENNUKSENOLOTILA_KOODI::INTEGER = 1
		)
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1))
	GROUP BY k.id
	HAVING COUNT(kr.rakennus_id) <= (
	    SELECT COUNT(DISTINCT kr2.rakennus_id)
	    FROM jkr.kohteen_rakennukset kr2
	    JOIN jkr.viranomaispaatokset vp ON vp.rakennus_id = kr2.rakennus_id
	    JOIN jkr_koodistot.tapahtumalaji tl ON vp.tapahtumalaji_koodi = tl.koodi
	    JOIN jkr_koodistot.paatostulos pt ON vp.paatostulos_koodi = pt.koodi
	    WHERE kr2.kohde_id = k.id
	      AND vp.voimassaolo && $1
	      AND tl.selite IN ('Keskeyttäminen', 'Perusmaksu')
	      AND pt.selite = 'myönteinen' 
	)
);
$BODY$;

-- FUNCTION: jkr.kohteet_joiden_rakennukset_vapautettu(daterange)

-- DROP FUNCTION IF EXISTS jkr.kohteet_joiden_rakennukset_vapautettu(daterange);

CREATE OR REPLACE FUNCTION jkr.kohteet_joiden_rakennukset_vapautettu_eivat_viemariverkossa(
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
	WHERE k.id NOT IN (
		SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1)
	)
	AND k.id IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
	GROUP BY k.id
	
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
WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1)) 
	AND kt.kaivotietotyyppi_id = 1 
	AND kt.voimassaolo && $1 
	AND NOT EXISTS (
		SELECT 1 FROM jkr.kaivotieto
		WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2,3,4,5)
	)
	AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_kantovesi_tieto(daterange)
    OWNER TO jkr_admin;

-- FUNCTION: jkr.kohteet_joilla_saostusailio_tai_pienpuhdistamo_ei_harmaata_vett(daterange)

-- DROP FUNCTION IF EXISTS jkr.kohteet_joilla_saostusailio_tai_pienpuhdistamo_ei_harmaata_vett(daterange);

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_saostusailio_tai_pienpuhdistamo_ei_harmaata_vett(
	daterange)
    RETURNS TABLE(kohde_id integer) 
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
    ROWS 1000
	
AS $BODY$
SELECT 
	DISTINCT (id) 
FROM ( -- Saostussäiliö tai pienpuhdistamo, tyhjennys edellisen viiden kvartaalin aikana ei harmaita vesiä
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1))
		AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto 
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2, 3)
		) AND EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7)
			AND daterange(
				(LOWER($1) - INTERVAL '6 months')::date,
				UPPER($1) 
			) @> lietteentyhjennyspaiva
		) AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto 
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (5)
		) AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_saostusailio_tai_pienpuhdistamo_ei_harmaata_vett(daterange)
    OWNER TO jkr_admin;


-- FUNCTION: jkr.kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint(daterange)

-- DROP FUNCTION IF EXISTS jkr.kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint(daterange);

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint(
	daterange)
    RETURNS TABLE(kohde_id integer) 
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
SELECT 
	DISTINCT (id) 
FROM ( -- Pienpuhdistamo muttei saostussäiliötä tai umpisäiliötä ja voimassaoleva kompostointi-ilmoitus
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1)) 
		AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (3)
		) AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2,4)
		) AND EXISTS (
			SELECT 1
			FROM jkr.kompostori ko
			JOIN jkr.kompostorin_kohteet kk ON ko.id = kk.kompostori_id
			WHERE ko.voimassaolo && $1 AND ko.onko_liete IS true AND kk.kohde_id = k.id
		) AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint(daterange)
    OWNER TO jkr_admin;


-- FUNCTION: jkr.kohteella_lietekuljetus_ok_umpisailio_tai_ei_tietoa(daterange)
-- DROP FUNCTION IF EXISTS jkr.kohteella_lietekuljetus_ok_umpisailio_tai_ei_tietoa(daterange);
CREATE OR REPLACE FUNCTION JKR.kohteella_lietekuljetus_ok_umpisailio_tai_ei_tietoa (DATERANGE) RETURNS TABLE (KOHDE_ID INTEGER) 
LANGUAGE 'sql' 
COST 100 
STABLE PARALLEL UNSAFE 
ROWS 1000 
AS $BODY$
SELECT 
	DISTINCT (id) 
FROM ( -- Lietteenkuljetus kunnossa
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1))
		AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2,3,5)
		) AND EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7)
			AND daterange(
				(LOWER($1) - INTERVAL '18 months')::date,
				UPPER($1) 
			) @> lietteentyhjennyspaiva
		) AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteella_lietekuljetus_ok_umpisailio_tai_ei_tietoa (DATERANGE) OWNER TO JKR_ADMIN;
