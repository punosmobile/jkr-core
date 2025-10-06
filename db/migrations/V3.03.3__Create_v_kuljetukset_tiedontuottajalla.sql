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
    t.nimi AS tiedontuottaja_nimi
FROM 
    jkr.kuljetus k
    INNER JOIN jkr_koodistot.tiedontuottaja t 
        ON k.tiedontuottaja_tunnus = t.tunnus
    INNER JOIN jkr_koodistot.jatetyyppi j
        ON k.jatetyyppi_id = j.id;