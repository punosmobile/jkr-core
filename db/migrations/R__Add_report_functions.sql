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
    is_taajama_yli_200 BOOLEAN
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
                    FROM jkr_osoite.posti p
                    WHERE
                        ku.koodi = p.kunta_koodi
                        AND EXISTS (
                            SELECT 1
                            FROM jkr.osoite o
                            WHERE
                                p.numero = o.posti_numero
                                AND EXISTS (
                                    SELECT 1
                                    FROM jkr.rakennus r
                                    WHERE
                                        o.rakennus_id = r.id
                                        AND EXISTS (
                                            SELECT 1
                                            FROM jkr.kohteen_rakennukset kr
                                            WHERE
                                                k.id = kr.kohde_id AND r.id = kr.rakennus_id
                                                LIMIT 1
                                        )
                                )
                        )
                )
        ))
        AND (huoneistomaara IS NULL
            OR (
                huoneistomaara = 4 AND
                (SELECT SUM(COALESCE((r.huoneistomaara)::integer, 1))
                FROM jkr.kohteen_rakennukset kr
                JOIN jkr.rakennus r ON r.id = kr.rakennus_id
                WHERE kr.kohde_id = k.id) <= 4
            )
            OR (
                huoneistomaara = 5 AND
                (SELECT SUM(COALESCE((r.huoneistomaara)::integer, 1))
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
        );
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
    taajama_yli_200 TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        k.id, 
        tarkastelupvm,
        (SELECT ku.nimi_fi
        FROM jkr_osoite.kunta ku
        WHERE EXISTS (
            SELECT 1
            FROM jkr_osoite.posti p
            WHERE
                ku.koodi = p.kunta_koodi
                AND EXISTS (
                    SELECT 1
                    FROM jkr.osoite o
                    WHERE
                        p.numero = o.posti_numero
                        AND EXISTS (
                            SELECT 1
                            FROM jkr.rakennus r
                            WHERE
                                o.rakennus_id = r.id
                                AND EXISTS (
                                    SELECT 1
                                    FROM jkr.kohteen_rakennukset kr
                                    WHERE
                                        k.id = kr.kohde_id AND r.id = kr.rakennus_id
                                        LIMIT 1
                                )
                        )
                )
        )
        LIMIT 1),
        (SELECT SUM(COALESCE((r.huoneistomaara)::integer, 1))
        FROM jkr.kohteen_rakennukset kr
        JOIN jkr.rakennus r ON r.id = kr.rakennus_id
        WHERE kr.kohde_id = k.id),
        (SELECT t.nimi
        FROM jkr.taajama t
        WHERE 
            t.vaesto_lkm >= 10000
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
        LIMIT 1),
        (SELECT t.nimi
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
        LIMIT 1)
    FROM jkr.kohde k
    WHERE k.id = ANY(kohde_ids);
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.print_report(
    tarkastelupvm DATE,
    kunta TEXT,
    huoneistomaara INTEGER, -- 4 = four or less, 5 = five or more
    is_taajama_yli_10000 BOOLEAN,
    is_taajama_yli_200 BOOLEAN
)
RETURNS TABLE(
    kohde_id INTEGER,
    tarkastelupvm_out DATE,
    kunta_out TEXT,
    huoneistomaara_out BIGINT,
    taajama_yli_10000 TEXT,
    taajama_yli_200 TEXT
) AS $$
DECLARE
    kohde_ids INTEGER[];
    report_start date := DATE_TRUNC('quarter', tarkastelupvm) - INTERVAL '6 months';
    report_end date := DATE_TRUNC('quarter', tarkastelupvm) + INTERVAL '3 months' - INTERVAL '1 day';
    report_period daterange := daterange(report_start, report_end);
BEGIN
    SELECT array_agg(id) INTO kohde_ids
    FROM jkr.filter_kohde_ids_for_report(
        tarkastelupvm,
        kunta,
        huoneistomaara,
        is_taajama_yli_10000,
        is_taajama_yli_200
    ) AS id;

    RETURN QUERY
    SELECT *
    FROM jkr.get_report_filter(
        tarkastelupvm,
        kohde_ids
    );
END;
$$ LANGUAGE plpgsql;
