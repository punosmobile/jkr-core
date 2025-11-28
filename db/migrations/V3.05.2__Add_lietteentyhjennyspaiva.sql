-- Lisää lietteentyhjennyspaiva-kenttä kuljetus-tauluun
-- LIETE-määrittelyn mukaan (17.11.2025) kuljetustietoihin tarvitaan erillinen kenttä lietteen tyhjennyspäivälle

ALTER TABLE jkr.kuljetus 
ADD COLUMN IF NOT EXISTS lietteentyhjennyspaiva date;

COMMENT ON COLUMN jkr.kuljetus.lietteentyhjennyspaiva IS 'Lietteen tyhjennyspäivämäärä (LIETE-aineisto). Käytetään lietevelvoitteiden laskennassa.';

-- Päivitä LIETE-jätetyypit koodistoon määrittelyjen mukaan (17.11.2025)
-- Lietteen tyyppi (jätelaji): Musta, Harmaa, Ei tietoa
-- Huom: "Jätteen kuvaus" (Umpisäiliö, Saostussäiliö, Pienpuhdistamo) on keräysvälinetyyppi, ei jätetyyppi

-- Varmista että jätetyypit ovat olemassa OIKEASSA JÄRJESTYKSESSÄ (ID = lisäysjärjestys)
-- Järjestys määrittää QGIS-värit, joten tämä on kriittistä!

-- 1. Biojäte
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Biojäte', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte');

-- 2. Sekajäte
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Sekajäte', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte');

-- 3. Kartonki
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Kartonki', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki');

-- 4. Lasi
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Lasi', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi');

-- 5. Liete
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Liete', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete');

-- 6. Musta liete
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Musta liete', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Musta liete');

-- 7. Harmaa liete
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Harmaa liete', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Harmaa liete');

-- 8. Metalli
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Metalli', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli');

-- 9. Muovi
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Muovi', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi');

-- 10. Pahvi
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Pahvi', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Pahvi');

-- 11. Paperi
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Paperi', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Paperi');

-- 12. Perusmaksu
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Perusmaksu', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Perusmaksu');

-- 13. Energia
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Energia', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Energia');

-- 14. Aluekeräyspiste
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Aluekeräyspiste', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Aluekeräyspiste');

-- 15. Monilokero
INSERT INTO jkr_koodistot.jatetyyppi (selite, ewc)
SELECT 'Monilokero', NULL
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.jatetyyppi WHERE selite = 'Monilokero');

-- Päivitä vanhat nimitykset jos ne ovat käytössä
UPDATE jkr_koodistot.jatetyyppi SET selite = 'Musta liete' WHERE selite = 'Mustaliete';
UPDATE jkr_koodistot.jatetyyppi SET selite = 'Harmaa liete' WHERE selite = 'Harmaaliete';

-- Lisää keräysvälinetyypit OIKEASSA JÄRJESTYKSESSÄ (ID = lisäysjärjestys)
-- Järjestys määrittää QGIS-värit!

-- 1. PINTA
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'PINTA'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'PINTA');

-- 2. SYVÄ
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'SYVÄ'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'SYVÄ');

-- 3. SAKO
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'SAKO'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'SAKO');

-- 4. UMPI
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'UMPI'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'UMPI');

-- 5. RULLAKKO
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'RULLAKKO'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'RULLAKKO');

-- 6. SÄILIÖ
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'SÄILIÖ'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'SÄILIÖ');

-- 7. PIENPUHDISTAMO
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'PIENPUHDISTAMO'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'PIENPUHDISTAMO');

-- 8. PIKAKONTTI
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'PIKAKONTTI'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'PIKAKONTTI');

-- 9. NOSTOKONTTI
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'NOSTOKONTTI'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'NOSTOKONTTI');

-- 10. VAIHTOLAVA
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'VAIHTOLAVA'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'VAIHTOLAVA');

-- 11. JÄTESÄKKI
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'JÄTESÄKKI'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'JÄTESÄKKI');

-- 12. PURISTINSÄILIÖ
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'PURISTINSÄILIÖ'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'PURISTINSÄILIÖ');

-- 13. PURISTIN
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'PURISTIN'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'PURISTIN');

-- 14. VAIHTOLAVASÄILIÖ
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'VAIHTOLAVASÄILIÖ'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'VAIHTOLAVASÄILIÖ');

-- 15. PAALI
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'PAALI'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'PAALI');

-- 16. MONILOKERO
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'MONILOKERO'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'MONILOKERO');

-- 17. Umpisäiliö (LIETE-määrittelyn mukainen)
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'Umpisäiliö'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'Umpisäiliö');

-- 18. Saostussäiliö (LIETE-määrittelyn mukainen)
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'Saostussäiliö'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'Saostussäiliö');

-- 19. Pienpuhdistamo (LIETE-määrittelyn mukainen)
INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite)
SELECT 'Pienpuhdistamo'
WHERE NOT EXISTS (SELECT 1 FROM jkr_koodistot.keraysvalinetyyppi WHERE selite = 'Pienpuhdistamo');

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