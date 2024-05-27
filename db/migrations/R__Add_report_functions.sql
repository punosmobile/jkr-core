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
    huoneistomaara INTEGER,
    velvoite_status_tallennuspvm DATE,
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
                                        )
                                )
                        )
                )
        ))
        AND (huoneistomaara IS NULL OR (
            SELECT SUM(COALESCE((r.huoneistomaara)::integer, 1))
            FROM jkr.kohteen_rakennukset kr
            JOIN jkr.rakennus r ON r.id = kr.rakennus_id
            WHERE kr.kohde_id = k.id
        ) = huoneistomaara)
        AND (velvoite_status_tallennuspvm IS NULL OR EXISTS (
            SELECT 1
            FROM jkr.velvoite v
            WHERE
                v.kohde_id = k.id
                AND EXISTS (
                    SELECT 1
                    FROM jkr.velvoite_status vs
                    WHERE vs.velvoite_id = v.id AND vs.tallennuspvm = velvoite_status_tallennuspvm
                )
        ))
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
