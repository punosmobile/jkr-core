-- VM 38: Väärä tyhjennysväli saostussäiliö tai pienpuhdistamo
CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_saostusai_tai_pienpuh_vaara_vali_ei_harmaata_vet(
	daterange)
    RETURNS TABLE(kohde_id integer) 
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
SELECT 
	DISTINCT (id) 
FROM (
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1))
		AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto 
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2, 3)
			AND voimassaolo && $1
		) AND NOT EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND LOWER($1) - INTERVAL '9 months' < lietteentyhjennyspaiva
		) AND EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND daterange(
				(LOWER($1) - INTERVAL '18 months')::date,
				(LOWER($1) - INTERVAL '9 months')::date
			) @> lietteentyhjennyspaiva
		) AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto 
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (5)
			AND voimassaolo && $1
		) 
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_saostusai_tai_pienpuh_vaara_vali_ei_harmaata_vet(daterange)
    OWNER TO jkr_admin;


-- VM 39: Väärä tyhjennysväli umpisäiliö tai ei tietoa
CREATE OR REPLACE FUNCTION JKR.kohteella_lietekuljetus_vaara_vali_umpisailio_tai_ei_tietoa (DATERANGE) RETURNS TABLE (KOHDE_ID INTEGER) 
LANGUAGE 'sql' 
COST 100 
STABLE PARALLEL UNSAFE 
ROWS 1000 
AS $BODY$
SELECT 
	DISTINCT (id) 
FROM (
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1))
		AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2,3,5)
			AND voimassaolo && $1
		) AND NOT EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND LOWER($1) - INTERVAL '18 months' < lietteentyhjennyspaiva
		) AND EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND daterange(
				(LOWER($1) - INTERVAL '30 months')::date,
				(LOWER($1) - INTERVAL '18 months')::date 
			) @> lietteentyhjennyspaiva
		) 
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteella_lietekuljetus_vaara_vali_umpisailio_tai_ei_tietoa (DATERANGE) OWNER TO JKR_ADMIN;


-- VM 40: Väärä tyhjennysväli harmaat vedet
CREATE OR REPLACE FUNCTION JKR.kohteet_joilla_vaara_tyhjennysvali_vain_harmaat_vedet (DATERANGE) RETURNS TABLE (KOHDE_ID INTEGER) 
LANGUAGE 'sql' 
COST 100 
STABLE PARALLEL UNSAFE 
ROWS 1000 
AS $BODY$
SELECT 
	DISTINCT (id) 
FROM (
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1))
		AND EXISTS (
			SELECT 1
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (7)
			AND daterange(
				(LOWER($1) - INTERVAL '42 months')::date,
				(LOWER($1) - INTERVAL '30 months')::date
			) @> lietteentyhjennyspaiva
		) AND NOT EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND LOWER($1) - INTERVAL '30 months' < lietteentyhjennyspaiva
		) AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id = 5
			AND voimassaolo && $1
		)
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;