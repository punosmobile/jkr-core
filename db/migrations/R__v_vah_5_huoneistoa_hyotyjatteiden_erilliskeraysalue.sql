CREATE VIEW jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue
AS
SELECT k.id,
    k.nimi,
    k.geom,
    k.alkupvm,
    k.loppupvm,
    k.voimassaolo,
    k.kohdetyyppi_id,
    yli5.huoneistomaara
FROM jkr.kohde k
JOIN (
    SELECT k_1.id,
        SUM(COALESCE((r.huoneistomaara)::integer, 1)) AS huoneistomaara
    FROM jkr.kohde k_1
    JOIN jkr.kohteen_rakennukset kr ON k_1.id = kr.kohde_id
    JOIN jkr.rakennus r ON kr.rakennus_id = r.id
    GROUP BY k_1.id
    HAVING SUM(COALESCE((r.huoneistomaara)::integer, 1)) >= 5
) yli5 ON k.id = yli5.id
WHERE k.id NOT IN (
    SELECT kr.kohde_id
    FROM jkr.kohteen_rakennukset kr
    JOIN jkr.rakennus r ON kr.rakennus_id = r.id
    LEFT JOIN jkr.taajama t ON ST_Within(r.geom, t.geom)
    WHERE t.id IS NULL
);

ALTER VIEW jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue OWNER TO jkr_admin;