-- LAH-511: Karttanäkymä näyttää väärän velvoitteen
-- Korjaus: "Väärä tyhjennysväli" -funktioiden aikaikkunat olivat väärin sekä
-- harmaille vesille (VM 40) että umpisäiliölle (VM 39).
--
-- Vanha kaava käytti (LOWER-Xkk, UPPER-Xkk) joka luo kapean, väärässä kohdassa
-- olevan ikkunan. Oikea kaava on (LOWER-max_kv*3kk, UPPER-ok_max_kv*3kk-9kk)
-- eli "väärä väli" -ikkuna alkaa siitä mihin OK-ikkuna päättyy.
--
-- Umpisäiliö/Ei tietoa (VM 39): OK=1-9kv, Väärä=10-13kv
--   Vanha: (LOWER-30kk, UPPER-30kk)
--   Uusi:  (LOWER-39kk, UPPER-27kk)  eli (LOWER-13kv, LOWER-6kv) = väärä väli 10-13kv
--
-- Harmaat vedet (VM 40): OK=1-13kv, Väärä=14-17kv
--   Vanha: (LOWER-45kk, UPPER-45kk)
--   Uusi:  (LOWER-51kk, UPPER-42kk)  eli (LOWER-17kv, LOWER-11kv) = väärä väli 14-17kv

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
				(LOWER($1) - INTERVAL '39 months')::date,
				(UPPER($1) - INTERVAL '27 months')::date 
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
				(LOWER($1) - INTERVAL '51 months')::date,
				(UPPER($1) - INTERVAL '42 months')::date
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
