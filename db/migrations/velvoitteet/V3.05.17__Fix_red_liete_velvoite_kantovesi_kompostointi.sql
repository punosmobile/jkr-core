-- LAH-453: Lietevelvoitteet eivät toimi määrittelyn mukaan
-- Korjaus velvoitematriisin mukaisesti:
-- 
-- PUNAISET (ei lietteenkuljetusta): Kantovesi=EI, Kompostointi-ilmoitus=EI
-- KELTAISET (väärä tyhjennysväli): Kantovesi=ei merkitystä, Kompostointi=ei merkitystä

-- FUNCTION: jkr.kohteet_joilla_saostusai_tai_pienpuh_ei_lietekuljetus_harmaata(daterange)
-- Velvoitemalli 41: Ei lietteenkuljetusta saostussäiliö/pienpuhdistamo (punainen)
CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_saostusai_tai_pienpuh_ei_lietekuljetus_harmaata(
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
		) AND NOT EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND daterange(
				(LOWER($1) - INTERVAL '18 months')::date,
				UPPER($1)
			) @> lietteentyhjennyspaiva
		) AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto 
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (5)
		) 
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
		-- LAH-453: Ei punaista jos kantovesi
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joilla_kantovesi_tieto($1))
		-- LAH-453: Ei punaista jos pienpuhdistamo + voimassa oleva lietekompostointi-ilmoitus
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint($1))
);
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_saostusai_tai_pienpuh_ei_lietekuljetus_harmaata(daterange)
    OWNER TO jkr_admin;


-- FUNCTION: jkr.kohteella_ei_lietteenkuljetusta_umpisailio_tai_ei_tietoa(daterange)
-- Velvoitemalli 42: Ei lietteenkuljetusta umpisäiliö/ei tietoa (punainen)
CREATE OR REPLACE FUNCTION JKR.kohteella_ei_lietteenkuljetusta_umpisailio_tai_ei_tietoa (DATERANGE) RETURNS TABLE (KOHDE_ID INTEGER) 
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
		) AND NOT EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND daterange(
				(LOWER($1) - INTERVAL '30 months')::date,
				UPPER($1) 
			) @> lietteentyhjennyspaiva
		) 
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
		-- LAH-453: Ei punaista jos kantovesi
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joilla_kantovesi_tieto($1))
		-- LAH-453: Ei punaista jos pienpuhdistamo + voimassa oleva lietekompostointi-ilmoitus
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteella_ei_lietteenkuljetusta_umpisailio_tai_ei_tietoa (DATERANGE) OWNER TO JKR_ADMIN;


-- FUNCTION: jkr.kohteet_joilla_ei_lietteenkuljetusta_harmaat_vedet(daterange)
-- Velvoitemalli 43: Ei lietteenkuljetusta harmaat vedet (punainen)
CREATE OR REPLACE FUNCTION JKR.kohteet_joilla_ei_lietteenkuljetusta_harmaat_vedet (DATERANGE) RETURNS TABLE (KOHDE_ID INTEGER) 
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
			SELECT 1
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (7)
			AND daterange(
				(LOWER($1) - INTERVAL '45 months')::date,
				UPPER($1)
			) @> lietteentyhjennyspaiva
		) AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id = 5
		)
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
		-- LAH-453: Ei punaista jos kantovesi
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joilla_kantovesi_tieto($1))
		-- LAH-453: Ei punaista jos pienpuhdistamo + voimassa oleva lietekompostointi-ilmoitus
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteet_joilla_ei_lietteenkuljetusta_harmaat_vedet (DATERANGE) OWNER TO JKR_ADMIN;


-- KELTAISET VELVOITTEET (väärä tyhjennysväli)

-- FUNCTION: jkr.kohteet_joilla_saostusai_tai_pienpuh_vaara_vali_ei_harmaata_vet(daterange)
-- Velvoitemalli 38: Väärä tyhjennysväli saostussäiliö/pienpuhdistamo (keltainen)
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
		) AND EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND daterange(
				(LOWER($1) - INTERVAL '18 months')::date,
				(UPPER($1) - INTERVAL '18 months')::date
			) @> lietteentyhjennyspaiva
		) AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto 
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (5)
		) 
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_saostusai_tai_pienpuh_vaara_vali_ei_harmaata_vet(daterange)
    OWNER TO jkr_admin;


-- FUNCTION: jkr.kohteella_lietekuljetus_vaara_vali_umpisailio_tai_ei_tietoa(daterange)
-- Velvoitemalli 39: Väärä tyhjennysväli umpisäiliö/ei tietoa (keltainen)
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
		) AND EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND daterange(
				(LOWER($1) - INTERVAL '30 months')::date,
				(UPPER($1) - INTERVAL '30 months')::date 
			) @> lietteentyhjennyspaiva
		) 
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteella_lietekuljetus_vaara_vali_umpisailio_tai_ei_tietoa (DATERANGE) OWNER TO JKR_ADMIN;


-- FUNCTION: jkr.kohteet_joilla_vaara_tyhjennysvali_vain_harmaat_vedet(daterange)
-- Velvoitemalli 40: Väärä tyhjennysväli harmaat vedet (keltainen)
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
				(LOWER($1) - INTERVAL '45 months')::date,
				(UPPER($1) - INTERVAL '45 months')::date
			) @> lietteentyhjennyspaiva
		) AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id = 5
		)
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteet_joilla_vaara_tyhjennysvali_vain_harmaat_vedet (DATERANGE) OWNER TO JKR_ADMIN;
