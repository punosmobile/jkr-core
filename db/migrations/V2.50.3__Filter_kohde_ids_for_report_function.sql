CREATE OR REPLACE FUNCTION jkr.filter_kohde_ids_for_report(
    tarkastelupvm DATE,
    kunta TEXT,
    huoneistomaara INTEGER, -- 4 = four or less, 5 = five or more
    is_taajama_yli_10000 BOOLEAN,
    is_taajama_yli_200 BOOLEAN,
    kohde_tyyppi_id INTEGER -- 5 = hapa, 6 = biohapa, 7 = housing, 8 = other, null for everything
)
RETURNS TABLE(id INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT k.id
    FROM jkr.kohde k
    WHERE
        (tarkastelupvm IS NULL OR k.voimassaolo @> tarkastelupvm)
        AND (kunta IS NULL OR EXISTS (
            SELECT 1
            FROM jkr_osoite.kunta ku
            WHERE
                ku.nimi_fi LIKE kunta
                AND EXISTS (
					SELECT 1
					FROM jkr.rakennus r
					WHERE
						ku.koodi = LEFT(r.kiinteistotunnus,3)
						AND EXISTS (
							SELECT 1
							FROM jkr.kohteen_rakennukset kr
							WHERE
								k.id = kr.kohde_id AND r.id = kr.rakennus_id
								LIMIT 1
						
						)
                )
        ))
        AND (huoneistomaara IS NULL OR huoneistomaara = 0
            OR (
                huoneistomaara = 4 AND
                (SELECT SUM(COALESCE((r.huoneistomaara)::INTEGER, 1))
                FROM jkr.kohteen_rakennukset kr
                JOIN jkr.rakennus r ON r.id = kr.rakennus_id
                WHERE kr.kohde_id = k.id) <= 4
            )
            OR (
                huoneistomaara = 5 AND
                (SELECT SUM(COALESCE((r.huoneistomaara)::INTEGER, 1))
                FROM jkr.kohteen_rakennukset kr
                JOIN jkr.rakennus r ON r.id = kr.rakennus_id
                WHERE kr.kohde_id = k.id) >= 5
            )
        )
        AND (is_taajama_yli_10000 IS NULL OR
            (
                is_taajama_yli_10000 = true
                AND k.id IN (SELECT kohde_ids_in_taajama FROM jkr.kohde_ids_in_taajama(10000))
            )
            OR (
                is_taajama_yli_10000 = false
                AND k.id NOT IN (SELECT kohde_ids_in_taajama FROM jkr.kohde_ids_in_taajama(10000))
            )
        )
        AND (is_taajama_yli_200 IS NULL OR
            (
                is_taajama_yli_200 = true
                AND k.id IN (SELECT kohde_ids_in_taajama FROM jkr.kohde_ids_in_taajama(200))
            )
            OR (
                is_taajama_yli_200 = false
                AND k.id NOT IN (SELECT kohde_ids_in_taajama FROM jkr.kohde_ids_in_taajama(200))
            )
        ) 
        AND (kohde_tyyppi_id IS NULL OR k.kohdetyyppi_id = kohde_tyyppi_id);
END;
$$ LANGUAGE plpgsql;