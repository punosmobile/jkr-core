CREATE OR REPLACE FUNCTION jkr.kohteiden_paatokset(kohde_ids integer[])
RETURNS TABLE(
    Kohde_id integer,
    Kompostoi date,
    "Perusmaksupäätös voimassa" date,
    "Perusmaksupäätös" text,
    "Tyhjennysvälipäätös voimassa" date,
    "Tyhjennysvälipäätös" text,
    "Akp-kohtuullistaminen voimassa" date,
    "Akp-kohtuullistaminen" text,
    "Keskeytys voimassa" date,
    "Keskeytys" text,
    "Erilliskeräysvelvoitteesta poikkeaminen voimassa" date,
    "Erilliskeräysvelvoitteesta poikkeaminen" text
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
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'PERUSMAKSU' THEN vp.loppupvm END) AS perusmaksupaatos_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'PERUSMAKSU' THEN vp.paatosnumero END) AS perusmaksupaatos,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'TYHJENNYSVALI' THEN vp.loppupvm END) AS tyhjennysvalipaatos_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'TYHJENNYSVALI' THEN vp.paatosnumero END) AS tyhjennysvalipaatos,
            CASE WHEN 
                SUM(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' THEN 1 ELSE 0 END) = COUNT(*) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' THEN vp.loppupvm END)
                ELSE NULL
            END AS akp_kohtuullistaminen_voimassa,
            CASE WHEN 
                SUM(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' THEN 1 ELSE 0 END) = COUNT(*) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' THEN vp.paatosnumero END)
                ELSE NULL
            END AS akp_kohtuullistaminen,
            CASE WHEN 
                SUM(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' THEN 1 ELSE 0 END) = COUNT(*) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' THEN vp.loppupvm END)
                ELSE NULL
            END AS keskeytys_voimassa,
            CASE WHEN 
                SUM(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' THEN 1 ELSE 0 END) = COUNT(*) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' THEN vp.paatosnumero END)
                ELSE NULL
            END AS keskeytys,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'ERILLISKERAYKSESTA_POIKKEAMINEN' THEN vp.loppupvm END) AS erilliskerayksesta_poikkeaminen_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'ERILLISKERAYKSESTA_POIKKEAMINEN' THEN vp.paatosnumero END) AS erilliskerayksesta_poikkeaminen
        FROM
            rakennukset r
        LEFT JOIN
            jkr.viranomaispaatokset AS vp ON vp.rakennus_id = r.rakennus_id
        GROUP BY
            r.kohde_id
    ),
    composting_status AS (
        SELECT
            k_id.kohde_id,
            kom.loppupvm AS kompostoi
        FROM
            unnest(kohde_ids) AS k_id(kohde_id)
        LEFT JOIN
            jkr.kompostorin_kohteet AS k ON k.kohde_id = k_id.kohde_id
        LEFT JOIN
            jkr.kompostori AS kom ON kom.id = k.kompostori_id
    )
    SELECT
        k_id.kohde_id,
        cs.kompostoi,
        p.perusmaksupaatos_voimassa,
        p.perusmaksupaatos,
        p.tyhjennysvalipaatos_voimassa,
        p.tyhjennysvalipaatos,
        p.akp_kohtuullistaminen_voimassa,
        p.akp_kohtuullistaminen,
        p.keskeytys_voimassa,
        p.keskeytys,
        p.erilliskerayksesta_poikkeaminen_voimassa,
        p.erilliskerayksesta_poikkeaminen
    FROM
        unnest(kohde_ids) AS k_id(kohde_id)
    LEFT JOIN
        composting_status cs ON cs.kohde_id = k_id.kohde_id
    LEFT JOIN
        paatokset p ON p.kohde_id = k_id.kohde_id;
END;
$$ LANGUAGE plpgsql;