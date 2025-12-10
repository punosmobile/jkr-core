-- FUNCTION: jkr.kohteet_joilla_vain_harmaat_vedet(daterange)
-- DROP FUNCTION IF EXISTS jkr.kohteet_joilla_vain_harmaat_vedet(daterange);
CREATE OR REPLACE FUNCTION JKR.kohteet_joilla_vain_harmaat_vedet (DATERANGE) RETURNS TABLE (KOHDE_ID INTEGER) LANGUAGE 'sql' COST 100 STABLE PARALLEL UNSAFE ROWS 1000 AS $BODY$
SELECT 
	DISTINCT (id) 
FROM ( -- Ei ole viemäriliitosta, on harmaavesikaivo ja kuljetus 13 kvartaalin ajalta, ei vapauttavia päätöksiä
	SELECT k.id
	FROM jkr.kohde k
	WHERE k.id NOT IN (SELECT jkr.kohteet_jotka_ovat_viemariverkossa($1))
		AND EXISTS (
			SELECT 1
			FROM jkr.kuljetus
			WHERE jatetyyppi_id IN (7)
			AND daterange(
				(LOWER($1) - INTERVAL '30 months')::date,
				UPPER($1)
			) @> lietteentyhjennyspaiva
		) AND EXISTS (
			SELECT 1 FROM jkr.kaivotieto
			WHERE kohde_id = k.id AND kaivotietotyyppi_id = 5
		)AND NOT EXISTS (
			SELECT 1
			FROM jkr.kohteen_rakennukset kr
			WHERE kr.kohde_id = k.id
			AND EXISTS (
				SELECT 1
				FROM jkr.viranomaispaatokset vp
				WHERE vp.rakennus_id = kr.rakennus_id
				AND vp.voimassaolo && $1
				AND EXISTS (
					SELECT 1
					FROM jkr_koodistot.tapahtumalaji tl
					WHERE vp.tapahtumalaji_koodi = tl.koodi
					AND tl.selite IN ('AKP', 'Perusmaksu')
				)
				AND EXISTS (
					SELECT 1
					FROM jkr_koodistot.paatostulos pt
					WHERE vp.paatostulos_koodi = pt.koodi
					AND pt.selite = 'myönteinen'
				)
			)
		)
);
$BODY$;

ALTER FUNCTION JKR.kohteet_joilla_vain_harmaat_vedet (DATERANGE) OWNER TO JKR_ADMIN;
