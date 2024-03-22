CREATE OR REPLACE VIEW jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue AS (
    SELECT DISTINCT k.*
    FROM jkr.kohde k
    JOIN jkr.kohteen_rakennukset kr ON kr.kohde_id = k.id
    JOIN jkr.rakennus r ON r.id = kr.rakennus_id
    JOIN jkr.taajama t ON ST_Contains(t.geom, r.geom)
    WHERE t.vaesto_lkm >= 10000
    AND (
        SELECT SUM(COALESCE((rak.huoneistomaara)::integer, 1))
        FROM jkr.kohteen_rakennukset kkr
        JOIN jkr.rakennus rak ON rak.id = kkr.rakennus_id
        WHERE kkr.kohde_id = k.id
    ) <= 4
);

CREATE OR REPLACE VIEW jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue AS (
    SELECT DISTINCT k.*
    FROM jkr.kohde k
    JOIN jkr.kohteen_rakennukset kr ON kr.kohde_id = k.id
    JOIN jkr.rakennus r ON r.id = kr.rakennus_id
    JOIN jkr.taajama t ON ST_Contains(t.geom, r.geom)
    AND (
        SELECT SUM(COALESCE((rak.huoneistomaara)::integer, 1))
        FROM jkr.kohteen_rakennukset kkr
        JOIN jkr.rakennus rak ON rak.id = kkr.rakennus_id
        WHERE kkr.kohde_id = k.id
    ) >= 5
);

CREATE OR REPLACE VIEW jkr.v_erilliskeraysalueet AS (
    SELECT * FROM jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue
    UNION ALL
    SELECT * FROM jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue
);
