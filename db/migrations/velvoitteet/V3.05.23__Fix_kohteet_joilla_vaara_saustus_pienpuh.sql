-- upper tulee olla yhden isompi kuin tavoite kvartaali. tavoite oli 6 kvartaalia alkaen = (24 - 3)/3 = 7

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
				(LOWER($1) - INTERVAL '27 months')::date,
				(UPPER($1) - INTERVAL '24 months')::date
			) @> lietteentyhjennyspaiva
		) AND NOT EXISTS (
			SELECT 1 FROM jkr.kaivotieto 
			WHERE kohde_id = k.id AND kaivotietotyyppi_id IN (5)
		) 
		AND k.id NOT IN (SELECT * FROM jkr.kohteet_joiden_rakennukset_vapautettu($1))
);
$BODY$;