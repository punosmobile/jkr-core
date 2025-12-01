-- Kaivotietotyyppien koodisto
-- LAH-415: Kaivotiedot ja kaivotiedon lopetus

INSERT INTO jkr_koodistot.kaivotietotyyppi(id, selite) VALUES
    (1, 'Kantovesi'),
    (2, 'Saostussäiliö'),
    (3, 'Pienpuhdistamo'),
    (4, 'Umpisäiliö'),
    (5, 'Vain harmaat vedet')
ON CONFLICT (id) DO UPDATE SET selite = EXCLUDED.selite;
