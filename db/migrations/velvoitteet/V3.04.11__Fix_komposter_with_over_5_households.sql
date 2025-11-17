DROP FUNCTION jkr.kohteet_joilla_bio_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_bio_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Biojäte'
        )
    )
    AND NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus sk
        WHERE sk.kohde_id = k.id
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.sopimustyyppi st
            WHERE sk.sopimustyyppi_id = st.id
            AND st.selite = 'Kimppasopimus'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE sk.jatetyyppi_id = jt.id
            AND jt.selite = 'Biojäte'
        )
        AND sk.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr.sopimus ski
            WHERE ski.kohde_id = sk.kimppaisanta_kohde_id
            AND ski.voimassaolo && $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE ski.jatetyyppi_id = jt.id
                AND jt.selite = 'Biojäte'
            )   
        )        
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_bio_0_tai_yli_4_vk
        FROM jkr.kohteet_joilla_bio_0_tai_yli_4_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_bio_enint_4_vk
        FROM jkr.kohteet_joilla_bio_enint_4_vk($1)
    )
    AND (
		k.id NOT IN (
	        SELECT kohteet_joilla_kompostointi_voimassa
	        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
	    ) OR (
			SELECT
				SUM(COALESCE(RAK.HUONEISTOMAARA::INTEGER, 1)) AS SUM
			FROM
				JKR.KOHTEEN_RAKENNUKSET KKR
				JOIN JKR.RAKENNUS RAK ON RAK.ID = KKR.RAKENNUS_ID
			WHERE
				KKR.KOHDE_ID = K.ID
		) >= 5
	);
$$
LANGUAGE SQL STABLE;