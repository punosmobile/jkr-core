-- Hae kunnan nimi viimeisimmän osoitteen tiedoista

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
			NIMI_FI,
			kr.KOHDE_ID,
			KOHDETYYPPI_ID
		FROM
			JKR_KOODISTOT.KOHDETYYPPI KT
			LEFT JOIN JKR.KOHDE K2 ON KT.ID = K2.KOHDETYYPPI_ID
			LEFT JOIN JKR.KOHTEEN_RAKENNUKSET KR ON K2.ID = KR.KOHDE_ID
			LEFT JOIN JKR.RAKENNUS R ON R.ID = KR.RAKENNUS_ID
			LEFT JOIN JKR.OSOITE O ON O.RAKENNUS_ID = R.ID
			LEFT JOIN (
				SELECT
					KUN.NIMI_FI,
					NUMERO
				FROM
					JKR_OSOITE.POSTI P
					JOIN JKR_OSOITE.KUNTA KUN ON P.KUNTA_KOODI = KUN.KOODI
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