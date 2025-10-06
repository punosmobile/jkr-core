CREATE OR REPLACE VIEW jkr.v_sopimus_tiedontuottajalla AS
SELECT 
    s.id,
    s.alkupvm,
    s.loppupvm,
    s.voimassaolo,
    s.kimppaisanta_kohde_id,
    s.kohde_id,
    s.jatetyyppi_id,
    j.selite AS jatetyyppi_selite,
    j.ewc AS jatetyyppi_ewc,
    s.sopimustyyppi_id,
    st.selite AS sopimustyyppi_selite,
    s.tiedontuottaja_tunnus,
    t.nimi AS tiedontuottaja_nimi
FROM 
    jkr.sopimus s
    INNER JOIN jkr_koodistot.tiedontuottaja t 
        ON s.tiedontuottaja_tunnus = t.tunnus
    LEFT JOIN jkr_koodistot.jatetyyppi j
        ON s.jatetyyppi_id = j.id
    INNER JOIN jkr_koodistot.sopimustyyppi st
        ON s.sopimustyyppi_id = st.id;