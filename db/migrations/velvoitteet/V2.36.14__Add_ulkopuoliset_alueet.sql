CREATE OR REPLACE VIEW jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue AS (
    SELECT DISTINCT k.*
    FROM jkr.kohde k
    JOIN jkr.kohteen_rakennukset kr ON kr.kohde_id = k.id
    JOIN jkr.rakennus r ON r.id = kr.rakennus_id
    WHERE
        k.id NOT IN (
            SELECT ke.id FROM jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue ke
        ) 
        AND (
            SELECT SUM(COALESCE((rak.huoneistomaara)::integer, 1))
            FROM jkr.kohteen_rakennukset kkr
            JOIN jkr.rakennus rak ON rak.id = kkr.rakennus_id
            WHERE kkr.kohde_id = k.id
        ) <= 4
);

CREATE OR REPLACE VIEW jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue AS (
    SELECT DISTINCT k.*
    FROM jkr.kohde k
    JOIN jkr.kohteen_rakennukset kr ON kr.kohde_id = k.id
    JOIN jkr.rakennus r ON r.id = kr.rakennus_id
    WHERE
        k.id NOT IN (
            SELECT ke.id FROM jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue ke
        ) 
        AND (
            SELECT SUM(COALESCE((rak.huoneistomaara)::integer, 1))
            FROM jkr.kohteen_rakennukset kkr
            JOIN jkr.rakennus rak ON rak.id = kkr.rakennus_id
            WHERE kkr.kohde_id = k.id
        ) >= 5
);

CREATE OR REPLACE VIEW jkr.v_ei_erilliskeraysalueet AS (
    SELECT * FROM jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue
    UNION ALL
    SELECT * FROM jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue
);
