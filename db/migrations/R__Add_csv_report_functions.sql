CREATE OR REPLACE FUNCTION jkr.kohde_ids_in_taajama(
    min_vaesto_lkm INTEGER
)
RETURNS TABLE(id INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT kr.kohde_id
    FROM jkr.kohteen_rakennukset kr
    WHERE EXISTS (
        SELECT 1
        FROM jkr.rakennus r
        WHERE 
            kr.rakennus_id = r.id
            AND EXISTS (
                SELECT 1
                FROM jkr.taajama t
                WHERE
                    t.vaesto_lkm >= min_vaesto_lkm AND ST_Contains(t.geom, r.geom)
            ) 
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.filter_kohde_ids_for_report(
    tarkastelupvm DATE,
    kunta TEXT,
    huoneistomaara INTEGER, -- 4 = four or less, 5 = five or more
    is_taajama_yli_10000 BOOLEAN,
    is_taajama_yli_200 BOOLEAN,
    kohde_tyyppi_id INTEGER, -- 5 = hapa, 6 = biohapa, 7 = housing, 8 = other, null for everything
    onko_viemari BOOLEAN -- null for everything, true for viemäriliitoksessa, false for ei viemäriliitoksessa
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
        AND (kohde_tyyppi_id IS NULL OR k.kohdetyyppi_id = kohde_tyyppi_id)
        AND (onko_viemari IS NULL OR
            (
                onko_viemari = true
                AND EXISTS (
                    SELECT 1
                    FROM jkr.viemari_liitos v
                    WHERE v.kohde_id = k.id AND v.viemariverkosto_alkupvm <= tarkastelupvm AND (v.viemariverkosto_loppupvm IS NULL OR v.viemariverkosto_loppupvm >= tarkastelupvm)
                )
            )
            OR (
                onko_viemari = false
                AND NOT EXISTS (
                    SELECT 1
                    FROM jkr.viemari_liitos v
                    WHERE v.kohde_id = k.id AND v.viemariverkosto_alkupvm <= tarkastelupvm AND (v.viemariverkosto_loppupvm IS NULL OR v.viemariverkosto_loppupvm >= tarkastelupvm)
                )
            )
        );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.kohteiden_paatokset(kohde_ids INTEGER[], tarkistusjakso daterange)
RETURNS TABLE(
    Kohde_id INTEGER,
    Kompostoi DATE,
    "Perusmaksupäätös voimassa" DATE,
    "Perusmaksupäätös" TEXT,
    "Tyhjennysvälipäätös voimassa" DATE,
    "Tyhjennysvälipäätös" TEXT,
    "Akp-kohtuullistaminen voimassa" DATE,
    "Akp-kohtuullistaminen" TEXT,
    "Keskeytys voimassa" DATE,
    "Keskeytys" TEXT,
    "Erilliskeräysvelvoitteesta poikkeaminen voimassa" DATE,
    "Erilliskeräysvelvoitteesta poikkeaminen" TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH rakennukset AS (
        SELECT
            kr.kohde_id,
            kr.rakennus_id
        FROM
            unnest(kohde_ids) AS k_id(kohde_id)
        JOIN
            jkr.kohteen_rakennukset AS kr ON kr.kohde_id = k_id.kohde_id
    ),
    paatokset AS (
        SELECT
            r.kohde_id,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'PERUSMAKSU' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END) AS perusmaksupaatos_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'PERUSMAKSU' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END) AS perusmaksupaatos,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'TYHJENNYSVALI' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END) AS tyhjennysvalipaatos_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'TYHJENNYSVALI' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END) AS tyhjennysvalipaatos,
            CASE WHEN 
                COUNT(*) = SUM(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN 1 ELSE 0 END) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END)
                ELSE NULL
            END AS akp_kohtuullistaminen_voimassa,
            CASE WHEN 
                COUNT(*) = SUM(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN 1 ELSE 0 END) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END)
                ELSE NULL
            END AS akp_kohtuullistaminen,
            CASE WHEN 
                COUNT(*) = SUM(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN 1 ELSE 0 END) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END)
                ELSE NULL
            END AS keskeytys_voimassa,
            CASE WHEN 
                COUNT(*) = SUM(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN 1 ELSE 0 END) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END)
                ELSE NULL
            END AS keskeytys,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'ERILLISKERAYKSESTA_POIKKEAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END) AS erilliskerayksesta_poikkeaminen_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'ERILLISKERAYKSESTA_POIKKEAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END) AS erilliskerayksesta_poikkeaminen
        FROM
            rakennukset r
        LEFT JOIN
            jkr.viranomaispaatokset AS vp ON vp.rakennus_id = r.rakennus_id
        WHERE
            (vp.tapahtumalaji_koodi = 'PERUSMAKSU' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
            OR (vp.tapahtumalaji_koodi = 'TYHJENNYSVALI' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
            OR (vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
            OR (vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
            OR (vp.tapahtumalaji_koodi = 'ERILLISKERAYKSESTA_POIKKEAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
        GROUP BY
            r.kohde_id
    ),
    composting_status AS (
        SELECT DISTINCT ON (k_id.kohde_id)
            k_id.kohde_id,
            kom.loppupvm AS kompostoi
        FROM
            unnest(kohde_ids) AS k_id(kohde_id)
        LEFT JOIN
            jkr.kompostorin_kohteet AS k ON k.kohde_id = k_id.kohde_id
        LEFT JOIN
            jkr.kompostori AS kom ON kom.id = k.kompostori_id
        WHERE
            kom.voimassaolo && tarkistusjakso AND kom.onko_liete IS NOT TRUE
        ORDER BY
            k_id.kohde_id, kom.loppupvm DESC
    )
    SELECT
        k_id.kohde_id,
        cs.kompostoi,
        p.perusmaksupaatos_voimassa AS "Perusmaksupäätös voimassa",
        p.perusmaksupaatos AS "Perusmaksupäätös",
        p.tyhjennysvalipaatos_voimassa AS "Tyhjennysvälipäätös voimassa",
        p.tyhjennysvalipaatos AS "Tyhjennysvälipäätös",
        p.akp_kohtuullistaminen_voimassa AS "Akp-kohtuullistaminen voimassa",
        p.akp_kohtuullistaminen AS "Akp-kohtuullistaminen",
        p.keskeytys_voimassa AS "Keskeytys voimassa",
        p.keskeytys AS "Keskeytys",
        p.erilliskerayksesta_poikkeaminen_voimassa AS "Erilliskeräysvelvoitteesta poikkeaminen voimassa",
        p.erilliskerayksesta_poikkeaminen AS "Erilliskeräysvelvoitteesta poikkeaminen"
    FROM
        unnest(kohde_ids) AS k_id(kohde_id)
    LEFT JOIN
        composting_status cs ON cs.kohde_id = k_id.kohde_id
    LEFT JOIN
        paatokset p ON p.kohde_id = k_id.kohde_id
    ORDER BY
        k_id.kohde_id;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.kohteiden_kuljetukset(kohde_ids INTEGER[], tarkistusjakso DATErange)
RETURNS TABLE(
    Kohde_id INTEGER,
    Muovi DATE,
    Kartonki DATE,
    Metalli DATE,
    Lasi DATE,
    Biojäte DATE,
    Monilokero DATE,
    Sekajate DATE,
    Akp DATE
) AS $$
BEGIN
    RETURN QUERY
    WITH valid_kuljetukset AS (
        SELECT
            k.kohde_id,
            CASE WHEN jt.selite = 'Muovi' THEN k.loppupvm END AS muovi,
            CASE WHEN jt.selite = 'Kartonki' THEN k.loppupvm END AS kartonki,
            CASE WHEN jt.selite = 'Metalli' THEN k.loppupvm END AS metalli,
            CASE WHEN jt.selite = 'Lasi' THEN k.loppupvm END AS lasi,
            CASE WHEN jt.selite = 'Biojäte' THEN k.loppupvm END AS biojate,
            CASE WHEN jt.selite = 'Monilokero' THEN k.loppupvm END AS monilokero,
            CASE WHEN jt.selite = 'Sekajäte' THEN k.loppupvm END AS sekajate,
            CASE WHEN jt.selite = 'Aluekeräyspiste' THEN k.loppupvm END AS akp
        FROM
            jkr.kuljetus k
        JOIN
            jkr_koodistot.jatetyyppi jt ON k.jatetyyppi_id = jt.id
        WHERE
            k.kohde_id = ANY(kohde_ids)
            AND k.aikavali && tarkistusjakso
    ),
    aggregated_kuljetukset AS (
        SELECT
            vk.kohde_id,
            MAX(vk.muovi) AS muovi,
            MAX(vk.kartonki) AS kartonki,
            MAX(vk.metalli) AS metalli,
            MAX(vk.lasi) AS lasi,
            MAX(vk.biojate) AS biojate,
            MAX(vk.monilokero) AS monilokero,
            MAX(vk.sekajate) AS sekajate,
            MAX(vk.akp) AS akp
        FROM
            valid_kuljetukset vk
        GROUP BY
            vk.kohde_id
    )
    SELECT
        k_id.kohde_id,
        ak.muovi,
        ak.kartonki,
        ak.metalli,
        ak.lasi,
        ak.biojate,
        ak.monilokero,
        ak.sekajate,
        ak.akp
    FROM
        unnest(kohde_ids) AS k_id(kohde_id)
    LEFT JOIN
        aggregated_kuljetukset ak ON ak.kohde_id = k_id.kohde_id
    ORDER BY
        k_id.kohde_id;
END;
$$ LANGUAGE plpgsql;


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
    kohdetyyppi TEXT,
    viemarissa BOOLEAN
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
        kt.selite as kohdetyyppi,
        v.viemariverkosto_alkupvm as viemarissa
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
    LEFT JOIN jkr.viemari_liitos v ON v.kohde_id = k.id AND v.viemariverkosto_alkupvm <= tarkastelupvm AND (v.viemariverkosto_loppupvm IS NULL OR v.viemariverkosto_loppupvm >= tarkastelupvm)
    WHERE k.id = ANY(kohde_ids);
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.kohteiden_velvoitteet(kohde_ids INTEGER[], tarkistusjakso DATErange)
RETURNS TABLE(
    Kohde_id INTEGER,
    "Velvoitteen tallennuspvm" DATE,
    Velvoiteyhteenveto TEXT,
    Sekajätevelvoite TEXT,
    Biojätevelvoite TEXT,
    Muovipakkausvelvoite TEXT,
    Kartonkipakkausvelvoite TEXT,
    Lasipakkausvelvoite TEXT,
    Metallipakkausvelvoite TEXT
) AS $$
DECLARE
    selected_tallennuspvm DATE;
BEGIN
    SELECT 
        MAX(vs.tallennuspvm)
    INTO 
        selected_tallennuspvm
    FROM 
        jkr.velvoite_status vs
    WHERE 
        vs.jakso && tarkistusjakso;

    RETURN QUERY
    WITH velvoiteyhteenveto_data AS (
        SELECT
            v.kohde_id,
            vs.tallennuspvm,
            vs.jakso,
            vvm.kuvaus
        FROM
            jkr.velvoiteyhteenveto v
        JOIN
            jkr.velvoiteyhteenveto_status vs ON v.id = vs.velvoiteyhteenveto_id
        JOIN
            jkr.velvoiteyhteenvetomalli vvm ON v.velvoiteyhteenvetomalli_id = vvm.id
        WHERE
            v.kohde_id = ANY(kohde_ids)
            AND vs.ok = TRUE
            AND vs.tallennuspvm = selected_tallennuspvm
        ORDER BY
            vs.jakso DESC, v.id DESC
    ),
    velvoite_data AS (
        SELECT
            v.kohde_id,
            vs.tallennuspvm,
            vs.jakso,
            vm.kuvaus,
            vm.selite
        FROM
            jkr.velvoite v
        JOIN
            jkr.velvoite_status vs ON v.id = vs.velvoite_id
        JOIN
            jkr.velvoitemalli vm ON v.velvoitemalli_id = vm.id
        WHERE
            v.kohde_id = ANY(kohde_ids)
            AND vs.ok = TRUE
            AND vs.tallennuspvm = selected_tallennuspvm
        ORDER BY
            vs.jakso DESC, v.id DESC
    ),
    aggregated_velvoite AS (
        SELECT
            vd.kohde_id,
            MAX(CASE WHEN vd.selite = 'Sekajäte' THEN vd.kuvaus END) AS sekajatevelvoite,
            MAX(CASE WHEN vd.selite = 'Biojäte' THEN vd.kuvaus END) AS biojatevelvoite,
            MAX(CASE WHEN vd.selite = 'Muovi' THEN vd.kuvaus END) AS muovipakkausvelvoite,
            MAX(CASE WHEN vd.selite = 'Kartonki' THEN vd.kuvaus END) AS kartonkipakkausvelvoite,
            MAX(CASE WHEN vd.selite = 'Lasipakkaus' THEN vd.kuvaus END) AS lasipakkausvelvoite,
            MAX(CASE WHEN vd.selite = 'Metalli' THEN vd.kuvaus END) AS metallipakkausvelvoite
        FROM
            velvoite_data vd
        GROUP BY
            vd.kohde_id
    )
    SELECT
        k_id.kohde_id,
        selected_tallennuspvm AS "Velvoitteen tallennuspvm",
        vy.kuvaus AS velvoiteyhteenveto,
        av.sekajatevelvoite,
        av.biojatevelvoite,
        av.muovipakkausvelvoite,
        av.kartonkipakkausvelvoite,
        av.lasipakkausvelvoite,
        av.metallipakkausvelvoite
    FROM
        unnest(kohde_ids) AS k_id(kohde_id)
    LEFT JOIN
        (SELECT DISTINCT ON (kohde_id) * FROM velvoiteyhteenveto_data) vy ON vy.kohde_id = k_id.kohde_id
    LEFT JOIN
        aggregated_velvoite av ON av.kohde_id = k_id.kohde_id;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.kohteiden_rakennustiedot(kohde_ids INTEGER[])
RETURNS TABLE(
    Kohde_id INTEGER,
    "PRT 1" TEXT,
    "Käyttötarkoitus 1" TEXT,
    "Käyttötila 1" TEXT,
    "Rakennusluokka_2018 1" TEXT,
    Katuosoite TEXT,
    Postinumero TEXT,
    Postitoimipaikka TEXT,
    Sijaintikiinteistö TEXT,
    "X-koordinaatti" FLOAT,
    "Y-koordinaatti" FLOAT,
    "PRT 2" TEXT,
    "Käyttötila 2" TEXT,
    "Käyttötarkoitus 2" TEXT,
    "Rakennusluokka_2018 2" TEXT,
    "PRT 3" TEXT,
    "Käyttötila 3" TEXT,
    "Käyttötarkoitus 3" TEXT,
    "Rakennusluokka_2018 3" TEXT,
    "PRT 4" TEXT,
    "Käyttötila 4" TEXT,
    "Käyttötarkoitus 4" TEXT,
    "Rakennusluokka_2018 4" TEXT,
    "PRT 5" TEXT,
    "Käyttötila 5" TEXT,
    "Käyttötarkoitus 5" TEXT,
    "Rakennusluokka_2018 5" TEXT,
    "PRT 6" TEXT,
    "Käyttötila 6" TEXT,
    "Käyttötarkoitus 6" TEXT,
    "Rakennusluokka_2018 6" TEXT,
    "PRT 7" TEXT,
    "Käyttötila 7" TEXT,
    "Käyttötarkoitus 7" TEXT,
    "Rakennusluokka_2018 7" TEXT,
    "PRT 8" TEXT,
    "Käyttötila 8" TEXT,
    "Käyttötarkoitus 8" TEXT,
    "Rakennusluokka_2018 8" TEXT,
    "PRT 9" TEXT,
    "Käyttötila 9" TEXT,
    "Käyttötarkoitus 9" TEXT,
    "Rakennusluokka_2018 9" TEXT,
    "PRT 10" TEXT,
    "Käyttötila 10" TEXT,
    "Käyttötarkoitus 10" TEXT,
    "Rakennusluokka_2018 10" TEXT,
    "PRT 11" TEXT,
    "Käyttötila 11" TEXT,
    "Käyttötarkoitus 11" TEXT,
    "Rakennusluokka_2018 11" TEXT,
    "PRT 12" TEXT,
    "Käyttötila 12" TEXT,
    "Käyttötarkoitus 12" TEXT,
    "Rakennusluokka_2018 12" TEXT,
    "PRT 13" TEXT,
    "Käyttötila 13" TEXT,
    "Käyttötarkoitus 13" TEXT,
    "Rakennusluokka_2018 13" TEXT,
    "PRT 14" TEXT,
    "Käyttötila 14" TEXT,
    "Käyttötarkoitus 14" TEXT,
    "Rakennusluokka_2018 14" TEXT,
    "PRT 15" TEXT,
    "Käyttötila 15" TEXT,
    "Käyttötarkoitus 15" TEXT,
    "Rakennusluokka_2018 15" TEXT,
    "PRT 16" TEXT,
    "Käyttötila 16" TEXT,
    "Käyttötarkoitus 16" TEXT,
    "Rakennusluokka_2018 16" TEXT,
    "PRT 17" TEXT,
    "Käyttötila 17" TEXT,
    "Käyttötarkoitus 17" TEXT,
    "Rakennusluokka_2018 17" TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH significant_rakennukset AS (
        SELECT
            kr.kohde_id,
            r.id AS rakennus_id,
            r.prt::TEXT AS prt,
            rl.selite AS rakennusluokka_2018,
            ro.selite::TEXT AS kayttotila,
            rt.selite::TEXT AS kayttotarkoitus,
            r.kiinteistotunnus::TEXT AS sijaintikiinteisto,
            ST_X(ST_Transform(r.geom, 3067)) AS x_koordinaatti,
            ST_Y(ST_Transform(r.geom, 3067)) AS y_koordinaatti
        FROM
            jkr.kohteen_rakennukset kr
        JOIN
            jkr.rakennus r ON kr.rakennus_id = r.id
        LEFT JOIN
            jkr_koodistot.rakennuksenkayttotarkoitus rt ON r.rakennuksenkayttotarkoitus_koodi = rt.koodi
        LEFT JOIN
            jkr_koodistot.rakennuksenolotila ro ON r.rakennuksenolotila_koodi = ro.koodi
        LEFT JOIN
            jkr_koodistot.rakennusluokka_2018 rl ON r.rakennusluokka_2018 = rl.koodi
        WHERE
            kr.kohde_id = ANY(kohde_ids)
            AND (
                rt.selite = ANY(ARRAY[
                    'Yhden asunnon talot', 'Kahden asunnon talot', 'Muut erilliset pientalot', 'Rivitalot',
                    'Luhtitalot', 'Ketjutalot', 'Muut asuinkerrostalot', 'Vapaa-ajan asuinrakennukset',
                    'Muut asuntolarakennukset', 'Vanhainkodit', 'Lasten- ja koulukodit',
                    'Kehitysvammaisten hoitolaitokset', 'Muut huoltolaitosrakennukset', 'Lasten päiväkodit',
                    'Muualla luokittelemattomat sosiaalitoimen rakennukset', 'Yleissivistävien oppilaitosten rakennukset',
                    'Ammatillisten oppilaitosten rakennukset', 'Korkeakoulurakennukset', 'Tutkimuslaitosrakennukset',
                    'Järjestöjen, liittojen, työnantajien yms. opetusrakennukset', 'Muualla luokittelemattomat opetusrakennukset'
                ])
                OR (
                    r.rakennuksenkayttotarkoitus_koodi IS NULL
                    AND rl.selite = ANY(ARRAY[
                        'Omakotitalot', 'Paritalot', 'Rivitalot', 'Pienkerrostalot', 'Asuinkerrostalot',
                        'Asuntolarakennukset', 'Erityisryhmien asuinrakennukset',
                        'Ympärivuotiseen käyttöön soveltuvat vapaa-ajan asuinrakennukset',
                        'Osavuotiseen käyttöön soveltuvat vapaa-ajan asuinrakennukset',
                        'Laitospalvelujen rakennukset', 'Lasten päiväkodit',
                        'Yleissivistävien oppilaitosten rakennukset',
                        'Ammatillisten oppilaitosten rakennukset', 'Korkeakoulurakennukset'
                    ])
                )
            )
    ),
    -- Fallback: kohteille joilla ei ole yhtään significant-rakennusta
    -- haetaan kaikki rakennukset ja järjestetään "paremmuuden" mukaan
    fallback_rakennukset AS (
        SELECT
            kr.kohde_id,
            r.id AS rakennus_id,
            r.prt::TEXT AS prt,
            rl.selite AS rakennusluokka_2018,
            ro.selite::TEXT AS kayttotila,
            rt.selite::TEXT AS kayttotarkoitus,
            r.kiinteistotunnus::TEXT AS sijaintikiinteisto,
            ST_X(ST_Transform(r.geom, 3067)) AS x_koordinaatti,
            ST_Y(ST_Transform(r.geom, 3067)) AS y_koordinaatti,
            COALESCE(r.huoneistomaara, 0) AS huoneistomaara
        FROM
            jkr.kohteen_rakennukset kr
        JOIN
            jkr.rakennus r ON kr.rakennus_id = r.id
        LEFT JOIN
            jkr_koodistot.rakennuksenkayttotarkoitus rt ON r.rakennuksenkayttotarkoitus_koodi = rt.koodi
        LEFT JOIN
            jkr_koodistot.rakennuksenolotila ro ON r.rakennuksenolotila_koodi = ro.koodi
        LEFT JOIN
            jkr_koodistot.rakennusluokka_2018 rl ON r.rakennusluokka_2018 = rl.koodi
        WHERE
            kr.kohde_id = ANY(kohde_ids)
            AND NOT EXISTS (
                SELECT 1 FROM significant_rakennukset sr WHERE sr.kohde_id = kr.kohde_id
            )
    ),
    ranked_significant AS (
        SELECT DISTINCT ON (sr.kohde_id, sr.rakennus_id)
            sr.kohde_id, sr.rakennus_id, sr.prt, sr.rakennusluokka_2018,
            sr.kayttotila, sr.kayttotarkoitus, sr.sijaintikiinteisto,
            sr.x_koordinaatti, sr.y_koordinaatti,
            ROW_NUMBER() OVER (PARTITION BY sr.kohde_id ORDER BY sr.rakennus_id) AS rn
        FROM significant_rakennukset sr
    ),
    ranked_fallback AS (
        SELECT DISTINCT ON (fr.kohde_id, fr.rakennus_id)
            fr.kohde_id, fr.rakennus_id, fr.prt, fr.rakennusluokka_2018,
            fr.kayttotila, fr.kayttotarkoitus, fr.sijaintikiinteisto,
            fr.x_koordinaatti, fr.y_koordinaatti,
            ROW_NUMBER() OVER (
                PARTITION BY fr.kohde_id
                ORDER BY
                    -- 1. Käyttötilan paremmuus: aktiivinen > tuntematon/tyhjä > purettu/tuhoutunut
                    CASE fr.kayttotila
                        WHEN 'käytetään vakinaiseen asumiseen'      THEN 0
                        WHEN 'käytetään loma-asumiseen'             THEN 0
                        WHEN 'käytetään muuhun tilapäiseen asumiseen' THEN 0
                        WHEN 'toimitila- tai tuotantokäytössä'      THEN 0
                        WHEN 'tyhjillään (esim. myynnissä)'         THEN 1
                        WHEN 'käytöstä ei ole tietoa'               THEN 1
                        WHEN 'muu (sauna, liiteri, kellotapuli, ym.)' THEN 1
                        WHEN 'purettu uudisrakentamisen vuoksi'     THEN 2
                        WHEN 'purettu muusta syystä'                THEN 2
                        WHEN 'tuhoutunut'                           THEN 2
                        WHEN 'ränsistymien vuoksi hylätty'          THEN 2
                        ELSE 1  -- NULL tai tuntematon arvo
                    END ASC,
                    -- 2. Enemmän huoneistoja ensin (asuinrakennus tunnistetaan huoneistoista)
                    fr.huoneistomaara DESC,
                    -- 3. Käyttötarkoituksen mukainen paremmuusjärjestys
                    CASE fr.kayttotarkoitus
                        -- Asuminen
                        WHEN 'Asuntolat yms.'                                        THEN 0
                        WHEN 'Hotellit yms.'                                         THEN 0
                        WHEN 'Loma-, lepo- ja virkistyskodit'                        THEN 0
                        WHEN 'Vuokrattavat lomamökit ja -osakkeet'                   THEN 0
                        WHEN 'Muut majoitusliikerakennukset'                         THEN 0
                        -- Sosiaali- ja terveydenhuolto
                        WHEN 'Keskussairaalat'                                        THEN 1
                        WHEN 'Muut sairaalat'                                        THEN 1
                        WHEN 'Terveyskeskukset'                                      THEN 1
                        WHEN 'Terveydenhuollon erityislaitokset'                     THEN 1
                        WHEN 'Muut terveydenhuoltorakennukset'                       THEN 1
                        WHEN 'Vankilat'                                              THEN 1
                        -- Toimisto/kauppa/palvelu/kulttuuri (neutraali)
                        WHEN 'Myymälähallit'                                         THEN 2
                        WHEN 'Liike- ja tavaratalot, kauppakeskukset'                THEN 2
                        WHEN 'Muut myymälärakennukset'                               THEN 2
                        WHEN 'Ravintolat yms.'                                       THEN 2
                        WHEN 'Toimistorakennukset'                                   THEN 2
                        WHEN 'Rautatie- ja linja-autoasemat, lento- ja satamaterminaalit' THEN 2
                        WHEN 'Kulkuneuvojen suoja- ja huoltorakennukset'             THEN 2
                        WHEN 'Pysäköintitalot'                                       THEN 2
                        WHEN 'Tietoliikenteen rakennukset'                           THEN 2
                        WHEN 'Muut liikenteen rakennukset'                           THEN 2
                        WHEN 'Teatterit, ooppera-, konsertti- ja kongressitalot'     THEN 2
                        WHEN 'Elokuvateatterit'                                      THEN 2
                        WHEN 'Kirjastot ja arkistot'                                 THEN 2
                        WHEN 'Museot ja taidegalleriat'                              THEN 2
                        WHEN 'Näyttelyhallit'                                        THEN 2
                        WHEN 'Seura- ja kerhorakennukset yms.'                       THEN 2
                        WHEN 'Kirkot, kappelit, luostarit ja rukoushuoneet'          THEN 2
                        WHEN 'Seurakuntatalot'                                       THEN 2
                        WHEN 'Muut uskonnollisten yhteisöjen rakennukset'            THEN 2
                        WHEN 'Jäähallit'                                             THEN 2
                        WHEN 'Uimahallit'                                            THEN 2
                        WHEN 'Tennis-, squash- ja sulkapallohallit'                  THEN 2
                        WHEN 'Monitoimihallit ja muut urheiluhallit'                 THEN 2
                        WHEN 'Muut urheilu- ja kuntoilurakennukset'                  THEN 2
                        WHEN 'Muut kokoontumisrakennukset'                           THEN 2
                        -- Teollisuus/varasto/tekniikka
                        WHEN 'Voimalaitosrakennukset'                                THEN 3
                        WHEN 'Yhdyskuntatekniikan rakennukset'                       THEN 3
                        WHEN 'Teollisuushallit'                                      THEN 3
                        WHEN 'Teollisuus- ja pienteollisuustalot'                    THEN 3
                        WHEN 'Muut teollisuuden tuotantorakennukset'                 THEN 3
                        WHEN 'Teollisuusvarastot'                                    THEN 3
                        WHEN 'Kauppavarastot'                                        THEN 3
                        WHEN 'Muut varastorakennukset'                               THEN 3
                        WHEN 'Paloasemat'                                            THEN 3
                        WHEN 'Väestönsuojat'                                         THEN 3
                        WHEN 'Muut palo- ja pelastustoimen rakennukset'              THEN 3
                        -- Maatalous/piharakennukset (vähiten haluttu PRT 1:ksi)
                        WHEN 'Navetat, sikalat, kanalat yms.'                        THEN 4
                        WHEN 'Eläinsuojat, ravihevostallit, maneesit yms.'           THEN 4
                        WHEN 'Viljankuivaamot ja viljan säilytysrakennukset'         THEN 4
                        WHEN 'Kasvihuoneet'                                          THEN 4
                        WHEN 'Turkistarhat'                                          THEN 4
                        WHEN 'Muut maa-, metsä- ja kalatalouden rakennukset'         THEN 4
                        WHEN 'Saunarakennukset'                                      THEN 4
                        WHEN 'Talousrakennukset'                                     THEN 4
                        WHEN 'Muualla luokittelemattomat rakennukset'                THEN 4
                        ELSE 2  -- NULL tai tuntematon koodi → neutraali
                    END ASC,
                    -- 4. Rakennusluokan mukainen paremmuusjärjestys
                    CASE fr.rakennusluokka_2018
                        -- Asuinrakennukset ja majoitus
                        WHEN 'Omakotitalot'                                                          THEN 0
                        WHEN 'Paritalot'                                                             THEN 0
                        WHEN 'Rivitalot'                                                             THEN 0
                        WHEN 'Pienkerrostalot'                                                       THEN 0
                        WHEN 'Asuinkerrostalot'                                                      THEN 0
                        WHEN 'Asuntolarakennukset'                                                   THEN 0
                        WHEN 'Erityisryhmien asuinrakennukset'                                       THEN 0
                        WHEN 'Ympärivuotiseen käyttöön soveltuvat vapaa-ajan asuinrakennukset'       THEN 0
                        WHEN 'Osavuotiseen käyttöön soveltuvat vapaa-ajan asuinrakennukset'          THEN 0
                        WHEN 'Loma-, lepo- ja virkistyskodit'                                        THEN 0
                        WHEN 'Hotellit'                                                              THEN 0
                        WHEN 'Motellit, hostellit ja vastaavat majoitusliikerakennukset'             THEN 0
                        WHEN 'Muut majoitusliikerakennukset'                                         THEN 0
                        -- Sosiaali-, terveys- ja opetusrakennukset
                        WHEN 'Laitospalvelujen rakennukset'                                          THEN 1
                        WHEN 'Avopalvelujen rakennukset'                                             THEN 1
                        WHEN 'Terveys- ja hyvinvointikeskukset'                                      THEN 1
                        WHEN 'Keskussairaalat'                                                       THEN 1
                        WHEN 'Erikoissairaalat ja laboratoriorakennukset'                            THEN 1
                        WHEN 'Muut sairaalat'                                                        THEN 1
                        WHEN 'Kuntoutuslaitokset'                                                    THEN 1
                        WHEN 'Muut terveydenhuoltorakennukset'                                       THEN 1
                        WHEN 'Lasten päiväkodit'                                                     THEN 1
                        WHEN 'Yleissivistävien oppilaitosten rakennukset'                            THEN 1
                        WHEN 'Ammatillisten oppilaitosten rakennukset'                               THEN 1
                        WHEN 'Korkeakoulurakennukset'                                                THEN 1
                        WHEN 'Tutkimuslaitosrakennukset'                                             THEN 1
                        WHEN 'Järjestöjen, liittojen, työnantajien ja vastaavat opetusrakennukset'  THEN 1
                        -- Kauppa, toimisto, kulttuuri, urheilu (neutraali)
                        WHEN 'Tukku- ja vähittäiskaupan myymälähallit'                              THEN 2
                        WHEN 'Kauppakeskukset ja liike- ja tavaratalot'                              THEN 2
                        WHEN 'Muut myymälärakennukset'                                               THEN 2
                        WHEN 'Ravintolarakennukset ja vastaavat liikerakennukset'                    THEN 2
                        WHEN 'Toimistorakennukset'                                                   THEN 2
                        WHEN 'Asemarakennukset ja terminaalit'                                       THEN 2
                        WHEN 'Ammattiliikenteen kaluston suojarakennukset'                           THEN 2
                        WHEN 'Ammattiliikenteen kaluston huoltorakennukset'                          THEN 2
                        WHEN 'Pysäköintitalot ja -hallit'                                            THEN 2
                        WHEN 'Kulkuneuvojen katokset'                                                THEN 2
                        WHEN 'Datakeskukset ja laitetilat'                                           THEN 2
                        WHEN 'Tietoliikenteen rakennukset'                                           THEN 2
                        WHEN 'Muut liikenteen rakennukset'                                           THEN 2
                        WHEN 'Teatterit, musiikki- ja kongressitalot'                                THEN 2
                        WHEN 'Elokuvateatterit'                                                      THEN 2
                        WHEN 'Kirjastot ja arkistot'                                                 THEN 2
                        WHEN 'Museot ja taidegalleriat'                                              THEN 2
                        WHEN 'Näyttely- ja messuhallit'                                              THEN 2
                        WHEN 'Seura- ja kerhorakennukset'                                            THEN 2
                        WHEN 'Uskonnonharjoittamisrakennukset'                                       THEN 2
                        WHEN 'Seurakuntatalot'                                                       THEN 2
                        WHEN 'Muut uskonnollisten yhteisöjen rakennukset'                            THEN 2
                        WHEN 'Jäähallit'                                                             THEN 2
                        WHEN 'Uimahallit'                                                            THEN 2
                        WHEN 'Monitoimihallit'                                                       THEN 2
                        WHEN 'Urheilu- ja palloiluhallit'                                            THEN 2
                        WHEN 'Stadion- ja katsomorakennukset'                                        THEN 2
                        WHEN 'Muut urheilu- ja liikuntarakennukset'                                  THEN 2
                        WHEN 'Muut kokoontumisrakennukset'                                           THEN 2
                        -- Teollisuus, energia ja pelastustoimi
                        WHEN 'Yleiskäyttöiset teollisuushallit'                                      THEN 3
                        WHEN 'Raskaan teollisuuden tehdasrakennukset'                                THEN 3
                        WHEN 'Elintarviketeollisuuden tuotantorakennukset'                           THEN 3
                        WHEN 'Muut teollisuuden tuotantorakennukset'                                 THEN 3
                        WHEN 'Teollisuus- ja pienteollisuustalot'                                    THEN 3
                        WHEN 'Metallimalmien käsittelyrakennukset'                                   THEN 3
                        WHEN 'Sähköenergian tuotantorakennukset'                                     THEN 3
                        WHEN 'Lämpö- ja kylmäenergian tuotantorakennukset'                          THEN 3
                        WHEN 'Energiansiirtorakennukset'                                             THEN 3
                        WHEN 'Energianvarastointirakennukset'                                        THEN 3
                        WHEN 'Vedenotto-, vedenpuhdistus- ja vedenjakelurakennukset'                 THEN 3
                        WHEN 'Jätteenkeruu-, jätteenkäsittely- ja jätteenvarastointirakennukset'    THEN 3
                        WHEN 'Materiaalien kierrätysrakennukset'                                     THEN 3
                        WHEN 'Paloasemat'                                                            THEN 3
                        WHEN 'Väestönsuojat'                                                         THEN 3
                        WHEN 'Muut pelastustoimen rakennukset'                                       THEN 3
                        -- Piharakennukset (vähiten haluttu PRT 1:ksi)
                        WHEN 'Saunarakennukset'                                                      THEN 4
                        ELSE 2  -- NULL tai tuntematon → neutraali
                    END ASC,
                    -- 5. Tasatulos: pienin rakennus_id
                    fr.rakennus_id ASC
            ) AS rn
        FROM fallback_rakennukset fr
    ),
    ranked_rakennukset AS (
        SELECT * FROM ranked_significant
        UNION ALL
        SELECT * FROM ranked_fallback
    ),
    first_significant_address AS (
        SELECT DISTINCT ON (rr.kohde_id)
            rr.kohde_id,
            (k.katunimi_fi || ' ' || ao.osoitenumero)::TEXT AS katuosoite,
            ao.posti_numero::TEXT AS postinumero,
            kun.nimi_fi::TEXT AS postitoimipaikka
        FROM
            ranked_rakennukset rr
        JOIN
            jkr.osoite ao ON rr.rakennus_id = ao.rakennus_id
        LEFT JOIN
            jkr_osoite.katu k ON ao.katu_id = k.id
        LEFT JOIN
            jkr_osoite.kunta kun ON k.kunta_koodi = kun.koodi
        WHERE rr.rn = 1
    )
    SELECT
        sr.kohde_id,
        MAX(CASE WHEN rn = 1 THEN sr.prt END) AS "PRT 1",
        MAX(CASE WHEN rn = 1 THEN sr.kayttotila END) AS "Käyttötila 1",
        MAX(CASE WHEN rn = 1 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 1",
        MAX(CASE WHEN rn = 1 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 1",
        fa.katuosoite,
        fa.postinumero,
        fa.postitoimipaikka,
        MAX(CASE WHEN rn = 1 THEN sr.sijaintikiinteisto END) AS sijaintikiinteisto,
        MAX(CASE WHEN rn = 1 THEN sr.x_koordinaatti END) AS "X-koordinaatti",
        MAX(CASE WHEN rn = 1 THEN sr.y_koordinaatti END) AS "Y-koordinaatti",
        MAX(CASE WHEN rn = 2 THEN sr.prt END) AS "PRT 2",
        MAX(CASE WHEN rn = 2 THEN sr.kayttotila END) AS "Käyttötila 2",
        MAX(CASE WHEN rn = 2 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 2",
        MAX(CASE WHEN rn = 2 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 2",
        MAX(CASE WHEN rn = 3 THEN sr.prt END) AS "PRT 3",
        MAX(CASE WHEN rn = 3 THEN sr.kayttotila END) AS "Käyttötila 3",
        MAX(CASE WHEN rn = 3 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 3",
        MAX(CASE WHEN rn = 3 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 3",
        MAX(CASE WHEN rn = 4 THEN sr.prt END) AS "PRT 4",
        MAX(CASE WHEN rn = 4 THEN sr.kayttotila END) AS "Käyttötila 4",
        MAX(CASE WHEN rn = 4 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 4",
        MAX(CASE WHEN rn = 4 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 4",
        MAX(CASE WHEN rn = 5 THEN sr.prt END) AS "PRT 5",
        MAX(CASE WHEN rn = 5 THEN sr.kayttotila END) AS "Käyttötila 5",
        MAX(CASE WHEN rn = 5 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 5",
        MAX(CASE WHEN rn = 5 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 5",
        MAX(CASE WHEN rn = 6 THEN sr.prt END) AS "PRT 6",
        MAX(CASE WHEN rn = 6 THEN sr.kayttotila END) AS "Käyttötila 6",
        MAX(CASE WHEN rn = 6 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 6",
        MAX(CASE WHEN rn = 6 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 6",
        MAX(CASE WHEN rn = 7 THEN sr.prt END) AS "PRT 7",
        MAX(CASE WHEN rn = 7 THEN sr.kayttotila END) AS "Käyttötila 7",
        MAX(CASE WHEN rn = 7 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 7",
        MAX(CASE WHEN rn = 7 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 7",
        MAX(CASE WHEN rn = 8 THEN sr.prt END) AS "PRT 8",
        MAX(CASE WHEN rn = 8 THEN sr.kayttotila END) AS "Käyttötila 8",
        MAX(CASE WHEN rn = 8 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 8",
        MAX(CASE WHEN rn = 8 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 8",
        MAX(CASE WHEN rn = 9 THEN sr.prt END) AS "PRT 9",
        MAX(CASE WHEN rn = 9 THEN sr.kayttotila END) AS "Käyttötila 9",
        MAX(CASE WHEN rn = 9 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 9",
        MAX(CASE WHEN rn = 9 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 9",
        MAX(CASE WHEN rn = 10 THEN sr.prt END) AS "PRT 10",
        MAX(CASE WHEN rn = 10 THEN sr.kayttotila END) AS "Käyttötila 10",
        MAX(CASE WHEN rn = 10 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 10",
        MAX(CASE WHEN rn = 10 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 10",
        MAX(CASE WHEN rn = 11 THEN sr.prt END) AS "PRT 11",
        MAX(CASE WHEN rn = 11 THEN sr.kayttotila END) AS "Käyttötila 11",
        MAX(CASE WHEN rn = 11 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 11",
        MAX(CASE WHEN rn = 11 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 11",
        MAX(CASE WHEN rn = 12 THEN sr.prt END) AS "PRT 12",
        MAX(CASE WHEN rn = 12 THEN sr.kayttotila END) AS "Käyttötila 12",
        MAX(CASE WHEN rn = 12 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 12",
        MAX(CASE WHEN rn = 12 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 12",
        MAX(CASE WHEN rn = 13 THEN sr.prt END) AS "PRT 13",
        MAX(CASE WHEN rn = 13 THEN sr.kayttotila END) AS "Käyttötila 13",
        MAX(CASE WHEN rn = 13 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 13",
        MAX(CASE WHEN rn = 13 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 13",
        MAX(CASE WHEN rn = 14 THEN sr.prt END) AS "PRT 14",
        MAX(CASE WHEN rn = 14 THEN sr.kayttotila END) AS "Käyttötila 14",
        MAX(CASE WHEN rn = 14 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 14",
        MAX(CASE WHEN rn = 14 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 14",
        MAX(CASE WHEN rn = 15 THEN sr.prt END) AS "PRT 15",
        MAX(CASE WHEN rn = 15 THEN sr.kayttotila END) AS "Käyttötila 15",
        MAX(CASE WHEN rn = 15 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 15",
        MAX(CASE WHEN rn = 15 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 15",
        MAX(CASE WHEN rn = 16 THEN sr.prt END) AS "PRT 16",
        MAX(CASE WHEN rn = 16 THEN sr.kayttotila END) AS "Käyttötila 16",
        MAX(CASE WHEN rn = 16 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 16",
        MAX(CASE WHEN rn = 16 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 16",
        MAX(CASE WHEN rn = 17 THEN sr.prt END) AS "PRT 17",
        MAX(CASE WHEN rn = 17 THEN sr.kayttotila END) AS "Käyttötila 17",
        MAX(CASE WHEN rn = 17 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 17",
        MAX(CASE WHEN rn = 17 THEN sr.rakennusluokka_2018 END) AS "Rakennusluokka_2018 17"
    FROM ranked_rakennukset sr
    LEFT JOIN first_significant_address fa ON sr.kohde_id = fa.kohde_id
    GROUP BY sr.kohde_id, fa.katuosoite, fa.postinumero, fa.postitoimipaikka
    ORDER BY sr.kohde_id;
END;
$$ LANGUAGE plpgsql;


DROP FUNCTION IF EXISTS jkr.kohteiden_tiedot(INTEGER[]);
CREATE OR REPLACE FUNCTION jkr.kohteiden_tiedot(kohde_ids INTEGER[])
RETURNS TABLE(
    Kohde_id INTEGER,
    "Komposti-ilmoituksen tekijän nimi" TEXT,
    "Lietteen kompostointi-ilmoituksen tekijän nimi" TEXT,
    "Lietteen tilaajan nimi" TEXT,
    "Lietteen tilaajan katuosoite" TEXT,
    "Lietteen tilaajan postinumero" TEXT,
    "Lietteen tilaajan postitoimipaikka" TEXT,
    "Sekajätteen tilaajan nimi" TEXT,
    "Sekajätteen tilaajan katuosoite" TEXT,
    "Sekajätteen tilaajan postinumero" TEXT,
    "Sekajätteen tilaajan postitoimipaikka" TEXT,
    "Salpakierron tilaajan nimi" TEXT,
    "Salpakierron tilaajan katuosoite" TEXT,
    "Salpakierron postinumero" TEXT,
    "Salpakierron postitoimipaikka" TEXT,
    "Omistaja 1 nimi" TEXT,
    "Omistaja 1 katuosoite" TEXT,
    "Omistaja 1 postinumero" TEXT,
    "Omistaja 1 postitoimipaikka" TEXT,
    "Omistaja 2 nimi" TEXT,
    "Omistaja 2 katuosoite" TEXT,
    "Omistaja 2 postinumero" TEXT,
    "Omistaja 2 postitoimipaikka" TEXT,
    "Omistaja 3 nimi" TEXT,
    "Omistaja 3 katuosoite" TEXT,
    "Omistaja 3 postinumero" TEXT,
    "Omistaja 3 postitoimipaikka" TEXT,
    "Vahimman asukkaan nimi" TEXT
) AS $$
DECLARE
    sekajate_ids INTEGER[];
    salpakierto_ids INTEGER[];
    liete_tilaaja_id INTEGER;
    omistaja_id INTEGER;
    vanhin_id INTEGER;
BEGIN
    SELECT ARRAY(
        SELECT id 
        FROM jkr_koodistot.osapuolenrooli
        WHERE selite IN ('Tilaaja sekajäte', 'Kimppaisäntä sekajäte', 'Kimppaosakas sekajäte')
    ) INTO sekajate_ids;

    SELECT ARRAY(
        SELECT id 
        FROM jkr_koodistot.osapuolenrooli
        WHERE selite IN (
            'Tilaaja biojäte', 'Kimppaisäntä biojäte', 'Kimppaosakas biojäte',
            'Tilaaja muovipakkaus', 'Kimppaisäntä muovipakkaus', 'Kimppaosakas muovipakkaus',
            'Tilaaja kartonkipakkaus', 'Kimppaisäntä kartonkipakkaus', 'Kimppaosakas kartonkipakkaus',
            'Tilaaja lasipakkaus', 'Kimppaisäntä lasipakkaus', 'Kimppaosakas lasipakkaus',
            'Tilaaja metalli', 'Kimppaisäntä metalli', 'Kimppaosakas metalli'
        )
    ) INTO salpakierto_ids;

    SELECT id INTO liete_tilaaja_id
    FROM jkr_koodistot.osapuolenrooli
    WHERE selite = 'Tilaaja liete';

    SELECT id INTO omistaja_id
    FROM jkr_koodistot.osapuolenrooli
    WHERE selite = 'Omistaja';

    SELECT id INTO vanhin_id
    FROM jkr_koodistot.osapuolenrooli
    WHERE selite = 'Vanhin asukas';

    RETURN QUERY
    WITH owners AS (
        SELECT
            ko.kohde_id,
            o.nimi,
            o.katuosoite,
            o.postinumero,
            o.postitoimipaikka,
            ROW_NUMBER() OVER (PARTITION BY ko.kohde_id) AS rn
        FROM jkr.kohteen_osapuolet ko
        JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
        WHERE ko.kohde_id = ANY(kohde_ids)
        AND ko.osapuolenrooli_id = omistaja_id
    )
    SELECT
        k.kohde_id,
        (
            SELECT o.nimi
            FROM jkr.kompostorin_kohteet kk
            JOIN jkr.kompostori ko ON kk.kompostori_id = ko.id
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE kk.kohde_id = k.kohde_id AND ko.onko_liete != TRUE
            ORDER BY ko.loppupvm DESC
            LIMIT 1
        ) AS "Komposti-ilmoituksen tekijän nimi",
        (
            SELECT o.nimi
            FROM jkr.kompostorin_kohteet kk
            JOIN jkr.kompostori ko ON kk.kompostori_id = ko.id
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE kk.kohde_id = k.kohde_id AND ko.onko_liete = TRUE
            ORDER BY ko.loppupvm DESC
            LIMIT 1
        ) AS "Lietteen kompostointi-ilmoituksen tekijän nimi",
        (
            SELECT o.nimi
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = liete_tilaaja_id
            LIMIT 1
        ) AS "Lietteen tilaajan nimi",
        (
            SELECT o.katuosoite
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = liete_tilaaja_id
            LIMIT 1
        ) AS "Lietteen tilaajan katuosoite",
        (
            SELECT o.postinumero
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = liete_tilaaja_id
            LIMIT 1
        ) AS "Lietteen tilaajan postinumero",
        (
            SELECT o.postitoimipaikka
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = liete_tilaaja_id
            LIMIT 1
        ) AS "Lietteen tilaajan postitoimipaikka",
        (
            SELECT o.nimi
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = ANY(sekajate_ids)
            LIMIT 1
        ) AS "Sekajätteen tilaajan nimi",
        (
            SELECT o.katuosoite
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = ANY(sekajate_ids)
            LIMIT 1
        ) AS "Sekajätteen tilaajan katuosoite",
        (
            SELECT o.postinumero
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = ANY(sekajate_ids)
            LIMIT 1
        ) AS "Sekajätteen tilaajan postinumero",
        (
            SELECT o.postitoimipaikka
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = ANY(sekajate_ids)
            LIMIT 1
        ) AS "Sekajätteen tilaajan postitoimipaikka",
        (
            SELECT o.nimi
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = ANY(salpakierto_ids)
            LIMIT 1
        ) AS "Salpakierron tilaajan nimi",
        (
            SELECT o.katuosoite
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = ANY(salpakierto_ids)
            LIMIT 1
        ) AS "Salpakierron tilaajan katuosoite",
        (
            SELECT o.postinumero
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = ANY(salpakierto_ids)
            LIMIT 1
        ) AS "Salpakierron postinumero",
        (
            SELECT o.postitoimipaikka
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = ANY(salpakierto_ids)
            LIMIT 1
        ) AS "Salpakierron postitoimipaikka",
        MAX(CASE WHEN o.rn = 1 THEN COALESCE(o.nimi, '') ELSE NULL END) AS "Omistaja 1 nimi",
        MAX(CASE WHEN o.rn = 1 THEN COALESCE(o.katuosoite, '') ELSE NULL END) AS "Omistaja 1 katuosoite",
        MAX(CASE WHEN o.rn = 1 THEN COALESCE(o.postinumero, '') ELSE NULL END) AS "Omistaja 1 postinumero",
        MAX(CASE WHEN o.rn = 1 THEN COALESCE(o.postitoimipaikka, '') ELSE NULL END) AS "Omistaja 1 postitoimipaikka",
        MAX(CASE WHEN o.rn = 2 THEN COALESCE(o.nimi, '') ELSE NULL END) AS "Omistaja 2 nimi",
    	MAX(CASE WHEN o.rn = 2 THEN COALESCE(o.katuosoite, '') ELSE NULL END) AS "Omistaja 2 katuosoite",
        MAX(CASE WHEN o.rn = 2 THEN COALESCE(o.postinumero, '') ELSE NULL END) AS "Omistaja 2 postinumero",
        MAX(CASE WHEN o.rn = 2 THEN COALESCE(o.postitoimipaikka, '') ELSE NULL END) AS "Omistaja 2 postitoimipaikka",
        MAX(CASE WHEN o.rn = 3 THEN COALESCE(o.nimi, '') ELSE NULL END) AS "Omistaja 2 nimi",
    	MAX(CASE WHEN o.rn = 3 THEN COALESCE(o.katuosoite, '') ELSE NULL END) AS "Omistaja 2 katuosoite",
    	MAX(CASE WHEN o.rn = 3 THEN COALESCE(o.postinumero, '') ELSE NULL END) AS "Omistaja 2 postinumero",
    	MAX(CASE WHEN o.rn = 3 THEN COALESCE(o.postitoimipaikka, '') ELSE NULL END) AS "Omistaja 2 postitoimipaikka",
        (
            SELECT o.nimi
            FROM jkr.kohteen_osapuolet ko
            JOIN jkr.osapuoli o ON ko.osapuoli_id = o.id
            WHERE ko.kohde_id = k.kohde_id
            AND ko.osapuolenrooli_id = vanhin_id
            LIMIT 1
        ) AS "Vahimman asukkaan nimi"
    FROM unnest(kohde_ids) AS k(kohde_id)
    LEFT JOIN owners o ON k.kohde_id = o.kohde_id
    GROUP BY k.kohde_id;
END;
$$ LANGUAGE plpgsql;


DROP FUNCTION IF EXISTS jkr.print_report(DATE, TEXT, INTEGER, BOOLEAN, BOOLEAN, INTEGER);
CREATE OR REPLACE FUNCTION jkr.print_report(
    tarkastelupvm DATE,
    kunta TEXT,
    huoneistomaara INTEGER, -- 4 = four or less, 5 = five or more
    is_taajama_yli_10000 BOOLEAN,
    is_taajama_yli_200 BOOLEAN,
    kohde_tyyppi_id INTEGER,
    onko_viemari BOOLEAN
)
RETURNS TABLE(
    kohde_id INTEGER,
    tarkastelupvm_out DATE,
    kunta_out TEXT,
    huoneistomaara_out BIGINT,
    taajama_yli_10000 TEXT,
    taajama_yli_200 TEXT,
    "kohdetyyppi" TEXT,
    "Liitetty viemäriin" TEXT,
    "Komposti-ilmoituksen tekijän nimi" TEXT,
    "Lietteen kompostointi-ilmoituksen tekijän nimi" TEXT,
    "Lietteen tilaajan nimi" TEXT,
    "Lietteen tilaajan katuosoite" TEXT,
    "Lietteen tilaajan postinumero" TEXT,
    "Lietteen tilaajan postitoimipaikka" TEXT,
    "Sekajätteen tilaajan nimi" TEXT,
    "Sekajätteen tilaajan katuosoite" TEXT,
    "Sekajätteen tilaajan postinumero" TEXT,
    "Sekajätteen tilaajan postitoimipaikka" TEXT,
    "Salpakierron tilaajan nimi" TEXT,
    "Salpakierron tilaajan katuosoite" TEXT,
    "Salpakierron postinumero" TEXT,
    "Salpakierron postitoimipaikka" TEXT,
    "Omistaja 1 nimi" TEXT,
    "Omistaja 1 katuosoite" TEXT,
    "Omistaja 1 postinumero" TEXT,
    "Omistaja 1 postitoimipaikka" TEXT,
    "Omistaja 2 nimi" TEXT,
    "Omistaja 2 katuosoite" TEXT,
    "Omistaja 2 postinumero" TEXT,
    "Omistaja 2 postitoimipaikka" TEXT,
    "Omistaja 3 nimi" TEXT,
    "Omistaja 3 katuosoite" TEXT,
    "Omistaja 3 postinumero" TEXT,
    "Omistaja 3 postitoimipaikka" TEXT,
    "Vahimman asukkaan nimi" TEXT,
    "Viemäriverkostossa" DATE,
    "Velvoitteen tallennuspvm" DATE,
    Velvoiteyhteenveto TEXT,
    Sekajätevelvoite TEXT,
    Biojätevelvoite TEXT,
    Muovipakkausvelvoite TEXT,
    Kartonkipakkausvelvoite TEXT,
    Lasipakkausvelvoite TEXT,
    Metallipakkausvelvoite TEXT,
    Muovi DATE,
    Kartonki DATE,
    Metalli DATE,
    Lasi DATE,
    Biojäte DATE,
    Monilokero DATE,
    Sekajate DATE,
    Akp DATE,
    Kompostoi DATE,
    "Perusmaksupäätös voimassa" DATE,
    "Perusmaksupäätös" TEXT,
    "Tyhjennysvälipäätös voimassa" DATE,
    "Tyhjennysvälipäätös" TEXT,
    "Akp-kohtuullistaminen voimassa" DATE,
    "Akp-kohtuullistaminen" TEXT,
    "Keskeytys voimassa" DATE,
    "Keskeytys" TEXT,
    "Erilliskeräysvelvoitteesta poikkeaminen voimassa" DATE,
    "Erilliskeräysvelvoitteesta poikkeaminen" TEXT,
    "PRT 1" TEXT,
    "Käyttötila 1" TEXT,
    "Käyttötarkoitus 1" TEXT,
    "Rakennusluokka_2018 1" TEXT,
    Katuosoite TEXT,
    Postinumero TEXT,
    Postitoimipaikka TEXT,
    Sijaintikiinteistö TEXT,
    "X-koordinaatti" FLOAT,
    "Y-koordinaatti" FLOAT,
    "PRT 2" TEXT,
    "Käyttötila 2" TEXT,
    "Käyttötarkoitus 2" TEXT,
    "Rakennusluokka_2018 2" TEXT,
    "PRT 3" TEXT,
    "Käyttötila 3" TEXT,
    "Käyttötarkoitus 3" TEXT,
    "Rakennusluokka_2018 3" TEXT,
    "PRT 4" TEXT,
    "Käyttötila 4" TEXT,
    "Käyttötarkoitus 4" TEXT,
    "Rakennusluokka_2018 4" TEXT,
    "PRT 5" TEXT,
    "Käyttötila 5" TEXT,
    "Käyttötarkoitus 5" TEXT,
    "Rakennusluokka_2018 5" TEXT,
    "PRT 6" TEXT,
    "Käyttötila 6" TEXT,
    "Käyttötarkoitus 6" TEXT,
    "Rakennusluokka_2018 6" TEXT,
    "PRT 7" TEXT,
    "Käyttötila 7" TEXT,
    "Käyttötarkoitus 7" TEXT,
    "Rakennusluokka_2018 7" TEXT,
    "PRT 8" TEXT,
    "Käyttötila 8" TEXT,
    "Käyttötarkoitus 8" TEXT,
    "Rakennusluokka_2018 8" TEXT,
    "PRT 9" TEXT,
    "Käyttötila 9" TEXT,
    "Käyttötarkoitus 9" TEXT,
    "Rakennusluokka_2018 9" TEXT,
    "PRT 10" TEXT,
    "Käyttötila 10" TEXT,
    "Käyttötarkoitus 10" TEXT,
    "Rakennusluokka_2018 10" TEXT,
    "PRT 11" TEXT,
    "Käyttötila 11" TEXT,
    "Käyttötarkoitus 11" TEXT,
    "Rakennusluokka_2018 11" TEXT,
    "PRT 12" TEXT,
    "Käyttötila 12" TEXT,
    "Käyttötarkoitus 12" TEXT,
    "Rakennusluokka_2018 12" TEXT,
    "PRT 13" TEXT,
    "Käyttötila 13" TEXT,
    "Käyttötarkoitus 13" TEXT,
    "Rakennusluokka_2018 13" TEXT,
    "PRT 14" TEXT,
    "Käyttötila 14" TEXT,
    "Käyttötarkoitus 14" TEXT,
    "Rakennusluokka_2018 14" TEXT,
    "PRT 15" TEXT,
    "Käyttötila 15" TEXT,
    "Käyttötarkoitus 15" TEXT,
    "Rakennusluokka_2018 15" TEXT,
    "PRT 16" TEXT,
    "Käyttötila 16" TEXT,
    "Käyttötarkoitus 16" TEXT,
    "Rakennusluokka_2018 16" TEXT,
    "PRT 17" TEXT,
    "Käyttötila 17" TEXT,
    "Käyttötarkoitus 17" TEXT,
    "Rakennusluokka_2018 17" TEXT
) AS $$
DECLARE
    kohde_ids INTEGER[];
    report_start DATE := DATE_TRUNC('quarter', tarkastelupvm) - INTERVAL '6 months';
    report_end DATE := DATE_TRUNC('quarter', tarkastelupvm) + INTERVAL '3 months' - INTERVAL '1 day';
    report_period daterange := daterange(report_start, report_end);
BEGIN
    SELECT array_agg(id) INTO kohde_ids
    FROM jkr.filter_kohde_ids_for_report(
        tarkastelupvm,
        kunta,
        huoneistomaara,
        is_taajama_yli_10000,
        is_taajama_yli_200,
        kohde_tyyppi_id,
        onko_viemari
    ) AS id;

    RETURN QUERY
    SELECT
        fil.kohde_id,
        fil.tarkastelupvm_out,
        fil.kunta,
        fil.huoneistomaara,
        fil.taajama_yli_10000,
        fil.taajama_yli_200,
        fil.kohdetyyppi,
        CASE WHEN fil.viemarissa IS NOT NULL THEN 'Viemäriverkostossa' ELSE 'Ei viemäriverkostossa' END AS "Liitetty viemäriin",
        koh."Komposti-ilmoituksen tekijän nimi",
        koh."Lietteen kompostointi-ilmoituksen tekijän nimi",
        koh."Lietteen tilaajan nimi",
        koh."Lietteen tilaajan katuosoite",
        koh."Lietteen tilaajan postinumero",
        koh."Lietteen tilaajan postitoimipaikka",
        koh."Sekajätteen tilaajan nimi",
        koh."Sekajätteen tilaajan katuosoite",
        koh."Sekajätteen tilaajan postinumero",
        koh."Sekajätteen tilaajan postitoimipaikka",
        koh."Salpakierron tilaajan nimi",
        koh."Salpakierron tilaajan katuosoite",
        koh."Salpakierron postinumero",
        koh."Salpakierron postitoimipaikka",
        koh."Omistaja 1 nimi",
        koh."Omistaja 1 katuosoite",
        koh."Omistaja 1 postinumero",
        koh."Omistaja 1 postitoimipaikka",
        koh."Omistaja 2 nimi",
        koh."Omistaja 2 katuosoite",
        koh."Omistaja 2 postinumero",
        koh."Omistaja 2 postitoimipaikka",
        koh."Omistaja 3 nimi",
        koh."Omistaja 3 katuosoite",
        koh."Omistaja 3 postinumero",
        koh."Omistaja 3 postitoimipaikka",
        koh."Vahimman asukkaan nimi",
        fil.viemarissa,
        vel."Velvoitteen tallennuspvm",
        vel.Velvoiteyhteenveto,
        vel.Sekajätevelvoite,
        vel.Biojätevelvoite,
        vel.Muovipakkausvelvoite,
        vel.Kartonkipakkausvelvoite,
        vel.Lasipakkausvelvoite,
        vel.Metallipakkausvelvoite,
        kul.Muovi,
        kul.Kartonki,
        kul.Metalli,
        kul.Lasi,
        kul.Biojäte,
        kul.Monilokero,
        kul.Sekajate,
        kul.Akp,
        paa.Kompostoi,
        paa."Perusmaksupäätös voimassa",
        paa."Perusmaksupäätös",
        paa."Tyhjennysvälipäätös voimassa",
        paa."Tyhjennysvälipäätös",
        paa."Akp-kohtuullistaminen voimassa",
        paa."Akp-kohtuullistaminen",
        paa."Keskeytys voimassa",
        paa."Keskeytys",
        paa."Erilliskeräysvelvoitteesta poikkeaminen voimassa",
        paa."Erilliskeräysvelvoitteesta poikkeaminen",
        rak."PRT 1",
        rak."Käyttötila 1",
        rak."Käyttötarkoitus 1",
        rak."Rakennusluokka_2018 1",
        rak.Katuosoite,
        rak.Postinumero,
        rak.Postitoimipaikka,
        rak.Sijaintikiinteistö,
        rak."X-koordinaatti",
        rak."Y-koordinaatti",
        rak."PRT 2",
        rak."Käyttötila 2",
        rak."Käyttötarkoitus 2",
        rak."Rakennusluokka_2018 2",
        rak."PRT 3",
        rak."Käyttötila 3",
        rak."Käyttötarkoitus 3",
        rak."Rakennusluokka_2018 3",
        rak."PRT 4",
        rak."Käyttötila 4",
        rak."Käyttötarkoitus 4",
        rak."Rakennusluokka_2018 4",
        rak."PRT 5",
        rak."Käyttötila 5",
        rak."Käyttötarkoitus 5",
        rak."Rakennusluokka_2018 5",
        rak."PRT 6",
        rak."Käyttötila 6",
        rak."Käyttötarkoitus 6",
        rak."Rakennusluokka_2018 6",
        rak."PRT 7",
        rak."Käyttötila 7",
        rak."Käyttötarkoitus 7",
        rak."Rakennusluokka_2018 7",
        rak."PRT 8",
        rak."Käyttötila 8",
        rak."Käyttötarkoitus 8",
        rak."Rakennusluokka_2018 8",
        rak."PRT 9",
        rak."Käyttötila 9",
        rak."Käyttötarkoitus 9",
        rak."Rakennusluokka_2018 9",
        rak."PRT 10",
        rak."Käyttötila 10",
        rak."Käyttötarkoitus 10",
        rak."Rakennusluokka_2018 10",
        rak."PRT 11",
        rak."Käyttötila 11",
        rak."Käyttötarkoitus 11",
        rak."Rakennusluokka_2018 11",
        rak."PRT 12",
        rak."Käyttötila 12",
        rak."Käyttötarkoitus 12",
        rak."Rakennusluokka_2018 12",
        rak."PRT 13",
        rak."Käyttötila 13",
        rak."Käyttötarkoitus 13",
        rak."Rakennusluokka_2018 13",
        rak."PRT 14",
        rak."Käyttötila 14",
        rak."Käyttötarkoitus 14",
        rak."Rakennusluokka_2018 14",
        rak."PRT 15",
        rak."Käyttötila 15",
        rak."Käyttötarkoitus 15",
        rak."Rakennusluokka_2018 15",
        rak."PRT 16",
        rak."Käyttötila 16",
        rak."Käyttötarkoitus 16",
        rak."Rakennusluokka_2018 16",
        rak."PRT 17",
        rak."Käyttötila 17",
        rak."Käyttötarkoitus 17",
        rak."Rakennusluokka_2018 17"
    FROM jkr.get_report_filter(
        tarkastelupvm,
        kohde_ids
    ) fil
    LEFT JOIN jkr.kohteiden_tiedot(
        kohde_ids
    ) koh ON fil.kohde_id = koh.kohde_id
    LEFT JOIN jkr.kohteiden_velvoitteet(
        kohde_ids, report_period
    ) vel ON fil.kohde_id = vel.kohde_id
    LEFT JOIN jkr.kohteiden_kuljetukset(
        kohde_ids, report_period
    ) kul ON fil.kohde_id = kul.kohde_id
    LEFT JOIN jkr.kohteiden_paatokset(
        kohde_ids, report_period
    ) paa ON fil.kohde_id = paa.kohde_id
    LEFT JOIN jkr.kohteiden_rakennustiedot(
        kohde_ids
    ) rak ON fil.kohde_id = rak.kohde_id;
END;
$$ LANGUAGE plpgsql;
