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
						ku.koodi = r.kunta
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


-- Hae kunnan nimi vaihdetaan kunnan nimi hakeutumaan kuntakentästä

CREATE OR REPLACE FUNCTION jkr.get_report_filter(
    tarkastelupvm DATE,
    kohde_ids INTEGER[]
)
RETURNS TABLE(
    kohde_id INTEGER,
    tarkastelupvm_out DATE,
    kunta TEXT,
    huoneistomaara BIGINT,
    taajama_yli_10000 TEXT,
    taajama_yli_200 TEXT,
    kohdetyyppi TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (k.id)
        k.id,
		tarkastelupvm,
		osoitetiedot.NIMI_FI,
        (
			SELECT
				SUM(COALESCE((R.HUONEISTOMAARA)::INTEGER, 1))
			FROM
				JKR.KOHTEEN_RAKENNUKSET KR
				JOIN JKR.RAKENNUS R ON R.ID = KR.RAKENNUS_ID
			WHERE
				KR.KOHDE_ID = K.ID
		),
		(
			SELECT
				T.NIMI
			FROM
				JKR.TAAJAMA T
			WHERE
				T.vaesto_lkm >= 10000
				AND EXISTS (
					SELECT
						1
					FROM
						JKR.RAKENNUS R
					WHERE
						ST_CONTAINS (T.GEOM, R.GEOM)
						AND EXISTS (
							SELECT
								1
							FROM
								JKR.KOHTEEN_RAKENNUKSET KR
							WHERE
								KR.KOHDE_ID = K.ID
								AND KR.RAKENNUS_ID = R.ID
						)
				)
			LIMIT 1
		),
		(
			SELECT t.nimi
				FROM jkr.taajama t
				WHERE 
					t.vaesto_lkm >= 200
					AND EXISTS (
						SELECT 1
						FROM jkr.rakennus r
						WHERE
							ST_Contains(t.geom, r.geom)
		                    AND EXISTS (
		                        SELECT 1
		                        FROM jkr.kohteen_rakennukset kr
		                        WHERE
		                            kr.kohde_id = k.id AND kr.rakennus_id = r.id
		                    )
		            ) 
		        LIMIT 1
		),
        kt.selite as kohdetyyppi
    FROM jkr.kohde k
    LEFT JOIN jkr_koodistot.kohdetyyppi kt ON k.kohdetyyppi_id = kt.id
	LEFT JOIN (
		SELECT
			O.ID OSOID,
			NUMERO,
			kun.NIMI_FI,
			kr.KOHDE_ID,
			kiinteistotunnus,
			KOHDETYYPPI_ID
		FROM
			JKR_KOODISTOT.KOHDETYYPPI KT
			LEFT JOIN JKR.KOHDE K2 ON KT.ID = K2.KOHDETYYPPI_ID
			LEFT JOIN JKR.KOHTEEN_RAKENNUKSET KR ON K2.ID = KR.KOHDE_ID
			LEFT JOIN JKR.RAKENNUS R ON R.ID = KR.RAKENNUS_ID
			LEFT JOIN JKR.OSOITE O ON O.RAKENNUS_ID = R.ID
			LEFT JOIN JKR_OSOITE.KUNTA kun ON r.kunta = KUN.KOODI
			LEFT JOIN (
				SELECT
					KUN2.NIMI_FI,
					NUMERO
				FROM
					JKR_OSOITE.POSTI P
					JOIN JKR_OSOITE.KUNTA KUN2 ON P.KUNTA_KOODI = KUN2.KOODI
				ORDER BY
					NUMERO ASC
			) OT ON O.POSTI_NUMERO = OT.NUMERO
			ORDER BY
				K2.ID,
				O.ID DESC
	) osoitetiedot ON osoitetiedot.KOHDE_ID = K.ID
	AND osoitetiedot.KOHDETYYPPI_ID = K.KOHDETYYPPI_ID
    WHERE k.id = ANY(kohde_ids);
END;
$$ LANGUAGE plpgsql;