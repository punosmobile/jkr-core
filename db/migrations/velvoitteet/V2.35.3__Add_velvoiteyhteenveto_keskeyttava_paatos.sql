CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_keskeyttava_paatos_voimassa(date) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.kohteen_rakennukset kr
        WHERE kr.kohde_id = k.id
        AND EXISTS (
            SELECT 1
            FROM jkr.viranomaispaatokset vp
            WHERE vp.rakennus_id = kr.rakennus_id
            AND vp.voimassaolo @> $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.tapahtumalaji tl
                WHERE vp.tapahtumalaji_koodi = tl.koodi
                AND tl.selite = 'Keskeyttäminen'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.paatostulos pt
                WHERE vp.paatostulos_koodi = pt.koodi
                AND pt.selite = 'myönteinen'
            )
        )
    );
$$
LANGUAGE SQL STABLE;
