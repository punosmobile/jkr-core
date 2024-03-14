INSERT INTO jkr.velvoitemalli(id,selite, saanto, tayttymissaanto, jatetyyppi_id, alkupvm, kuvaus)
VALUES
    (
        1,
        'Velvoiteyhteenveto',
        'kohde',
        'kohteet_joilla_vapauttava_paatos_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto ei tarvitse jätteenkuljetusta'
    ),
    (
        2,
        'Velvoiteyhteenveto',
        'kohde',
        'kohteet_joilla_keskeyttava_paatos_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto ei tarvitse jätteenkuljetusta'
    ),
    (
        3,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte puuttuu'
    ),
    (
        4,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_4_vk_ei_bio',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli'
    ),
    (
        5,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_0_tai_yli_16_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli'
    ),
    (
        6,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli'
    ),
    (
        7,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli'
    ),
    (
        8,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_alle_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa'
    ),
    (
        9,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_enint_16_vk_bio_on',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa'
    ),
    (
        10,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_enint_16_vk_kompostointi_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa'
    ),
    (
        11,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa'
    ),
    (
        12,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa'
    )
ON CONFLICT DO NOTHING;
