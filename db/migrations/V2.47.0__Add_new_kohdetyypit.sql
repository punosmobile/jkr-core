-- V2.47.0__Add_new_kohdetyypit.sql

-- Lisätään kaikki puuttuvat kohdetyypit
INSERT INTO jkr_koodistot.kohdetyyppi (id, selite) VALUES
    (5, 'hapa'),
    (6, 'biohapa'),
    (7, 'asuinkiinteistö'),  
    (8, 'muu')
ON CONFLICT (id) DO NOTHING;

-- Päivitetään indeksi alkamaan seuraavasta vapaasta id:stä
SELECT setval('jkr_koodistot.kohdetyyppi_id_seq', 
             (SELECT MAX(id) FROM jkr_koodistot.kohdetyyppi));

COMMENT ON TABLE jkr_koodistot.kohdetyyppi IS 'Kohteen tyypit';