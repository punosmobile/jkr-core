INSERT INTO jkr.velvoitemalli(selite, saanto, tayttymissaanto, jatetyyppi_id, alkupvm, kuvaus)
VALUES
    (
        'Velvoiteyhteenveto',
        'kohde',
        'kohteet_joilla_vapauttava_paatos_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto ei tarvitse jätteenkuljetusta'
    );
