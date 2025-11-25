CREATE OR REPLACE VIEW jkr.v_kuljetukset_tiedontuottajalla AS
SELECT 
    k.id,
    k.alkupvm,
    k.loppupvm,
    k.tyhjennyskerrat,
    k.massa,
    k.tilavuus,
    k.aikavali,
    k.kohde_id,
    k.jatetyyppi_id,
    j.selite AS jatetyyppi_selite,
    k.tiedontuottaja_tunnus,
    t.nimi AS tiedontuottaja_nimi,
    tv.tyhjennysvali
FROM 
    jkr.kuljetus k
    INNER JOIN jkr_koodistot.tiedontuottaja t 
        ON k.tiedontuottaja_tunnus = t.tunnus
    INNER JOIN jkr_koodistot.jatetyyppi j
        ON k.jatetyyppi_id = j.id
    LEFT JOIN jkr.sopimus s
        ON s.kohde_id = k.kohde_id
        AND s.jatetyyppi_id = k.jatetyyppi_id
        AND s.voimassaolo && k.aikavali
    LEFT JOIN jkr.tyhjennysvali tv
        ON tv.sopimus_id = s.id;