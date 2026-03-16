-- LAH-510: Kohde saa useamman tarkastustuloksen
-- Korjaus: Lisätään kaivotiedon voimassaolon tarkistus (voimassaolo && $1) kaikkiin
-- lietevelvoitefunktioihin, jotka tarkistavat kaivotietotyyppiä EXISTS/NOT EXISTS -kyselyillä.
-- Ilman tätä tarkistusta päättyneet kaivotiedot (esim. poistettu saostussäiliö) osuvat
-- edelleen kyselyihin ja kohde saa useamman ristiriitaisen tuloksen.

-- VM 34: Lietteenkuljetus kunnossa saostussäiliö tai pienpuhdistamo
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
FROM (
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1))
		AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto 
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2, 3)
			AND voimassaolo && $1
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
			AND voimassaolo && $1
		) AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION jkr.kohteet_joilla_saostusailio_tai_pienpuhdistamo_ei_harmaata_vett(daterange)
    OWNER TO jkr_admin;


-- VM 35: Lietteenkuljetus kunnossa saostussäiliö tai pienpuhdistamo (kompostointi)
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
FROM (
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1)) 
		AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (3)
			AND voimassaolo && $1
		) AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (2,4)
			AND voimassaolo && $1
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


-- VM 36: Lietteenkuljetus kunnossa umpisäiliö tai ei tietoa
CREATE OR REPLACE FUNCTION JKR.kohteella_lietekuljetus_ok_umpisailio_tai_ei_tietoa (DATERANGE) RETURNS TABLE (KOHDE_ID INTEGER) 
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


-- VM 37: Lietteenkuljetus kunnossa harmaat vedet
CREATE OR REPLACE FUNCTION JKR.kohteet_joilla_vain_harmaat_vedet (DATERANGE) RETURNS TABLE (KOHDE_ID INTEGER) LANGUAGE 'sql' COST 100 STABLE PARALLEL UNSAFE ROWS 1000 AS $BODY$
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
				(LOWER($1) - INTERVAL '33 months')::date,
				UPPER($1)
			) @> lietteentyhjennyspaiva
		) AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id = 5
			AND voimassaolo && $1
		) AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteet_joilla_vain_harmaat_vedet (DATERANGE) OWNER TO JKR_ADMIN;


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
		) AND EXISTS (
			SELECT 1 
			FROM jkr.kuljetus
			WHERE kohde_id = k.id AND jatetyyppi_id IN (5, 6, 7) 
			AND daterange(
				(LOWER($1) - INTERVAL '27 months')::date,
				(UPPER($1) - INTERVAL '24 months')::date
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
				(LOWER($1) - INTERVAL '45 months')::date,
				(UPPER($1) - INTERVAL '45 months')::date
			) @> lietteentyhjennyspaiva
		) AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id = 5
			AND voimassaolo && $1
		)
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteet_joilla_vaara_tyhjennysvali_vain_harmaat_vedet (DATERANGE) OWNER TO JKR_ADMIN;


-- VM 41: Ei lietteenkuljetusta saostussäiliö tai pienpuhdistamo
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
			AND voimassaolo && $1
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
			AND voimassaolo && $1
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


-- VM 42: Ei lietteenkuljetusta umpisäiliö tai ei tietoa
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
			AND voimassaolo && $1
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


-- VM 43: Ei lietteenkuljetusta harmaat vedet
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
			AND voimassaolo && $1
		)
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
		-- LAH-453: Ei punaista jos kantovesi
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joilla_kantovesi_tieto($1))
		-- LAH-453: Ei punaista jos pienpuhdistamo + voimassa oleva lietekompostointi-ilmoitus
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint($1))
);
$BODY$;

ALTER FUNCTION JKR.kohteet_joilla_ei_lietteenkuljetusta_harmaat_vedet (DATERANGE) OWNER TO JKR_ADMIN;
