-- Lisää lietteentyhjennyspaiva-kenttä kuljetus-tauluun
-- LIETE-määrittelyn mukaan (17.11.2025) kuljetustietoihin tarvitaan erillinen kenttä lietteen tyhjennyspäivälle

ALTER TABLE jkr.kuljetus 
ADD COLUMN IF NOT EXISTS lietteentyhjennyspaiva date;

COMMENT ON COLUMN jkr.kuljetus.lietteentyhjennyspaiva IS 'Lietteen tyhjennyspäivämäärä (LIETE-aineisto). Käytetään lietevelvoitteiden laskennassa.';

-- HUOM: Jätetyypit ja keräysvälinetyypit hoidetaan uudelleenajettavissa migraatioissa:
-- - R__import_koodisto_jatelaji.sql
-- - R__import_koodisto_keraysvalinetyyppi.sql

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
    tv.tyhjennysvali,
    k.lietteentyhjennyspaiva
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