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
    ),
    (
        13,
        'Biojäte',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_bio_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte puuttuu'
    ),
    (
        14,
        'Biojäte',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_bio_puuttuu_ei_kompostointia',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte puuttuu'
    ),
    (
        15,
        'Biojäte',
        'v_erilliskeraysalueet',
        'kohteet_joilla_bio_0_tai_yli_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte väärä tyhjennysväli'
    ),
    (
        16,
        'Biojäte',
        'v_erilliskeraysalueet',
        'kohteet_joilla_bio_enint_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte kunnossa'
    ),
    (
        17,
        'Biojäte',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_kompostointi_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte kunnossa'
    ),
    (
        18,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovipakkaus puuttuu'
    ),
    (
        19,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_yli_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovi väärä tyhjennysväli'
    ),
    (
        20,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_enintaan_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovi kunnossa'
    ),
    (
        21,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus puuttuu'
    ),
    (
        22,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_yli_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus väärä tyhjennysväli'
    ),
    (
        23,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_enintaan_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus kunnossa'
    ),
    (
        24,
        'Lasi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus puuttuu'
    ),
    (
        25,
        'Lasi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_yli_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus väärä tyhjennysväli'
    ),
    (
        26,
        'Lasi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_enintaan_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus kunnossa'
    ),
    (
        27,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli puuttuu'
    ),
    (
        28,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_yli_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli väärä tyhjennysväli'
    ),
    (
        29,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_enintaan_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli kunnossa'
    ),
    (
        30,
        'Velvoiteyhteenveto',
        'v_ei_erilliskeraysalueet',
        'kohteet_joilla_seka_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto jätteenkuljetus kunnossa'
    ),
    (
        31,
        'Velvoiteyhteenveto',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_kompostointi_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto jätteenkuljetus kunnossa'
    ),
    (
        32,
        'Velvoiteyhteenveto',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto jätteenkuljetus kunnossa'
    ),
    (
        33,
        'Velvoiteyhteenveto',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_muut_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto jätteenkuljetus kunnossa'
    ),
    (
        34,
        'Velvoiteyhteenveto',
        'kohde',
        'kohteet_joilla_seka_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto ei jätehuoltoa'
    ),
    (
        35,
        'Velvoiteyhteenveto',
        'v_erilliskeraysalueet',
        'kohteet_joilla_seka_ok_bio_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto biojäte puuttuu'
    ),
    (
        36,
        'Velvoiteyhteenveto',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_enintaan_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto pakkausjäte puutteellinen'
    ),
    (
        37,
        'Velvoiteyhteenveto',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_metalli_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto pakkausjäte puutteellinen'
    ),
    (
        38,
        'Velvoiteyhteenveto',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_lasi_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto pakkausjäte puutteellinen'
    ),
    (
        39,
        'Velvoiteyhteenveto',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_muovi_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto pakkausjäte puutteellinen'
    ),
    (
        40,
        'Velvoiteyhteenveto',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_vaara_tvali_muut_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli sekajäte'
    ),
    (
        41,
        'Velvoiteyhteenveto',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_vaara_tvali_bio_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli sekajäte'
    ),
    (
        42,
        'Velvoiteyhteenveto',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_vaara_tvali_kompostointi_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli sekajäte'
    ),
    (
        43,
        'Velvoiteyhteenveto',
        'v_ei_erilliskeraysalueet',
        'kohteet_joilla_seka_vaara_tvali',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli sekajäte'
    ),
    (
        44,
        'Velvoiteyhteenveto',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_bio_vaara_tvali_seka_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli biojäte'
    ),
    (
        45,
        'Velvoiteyhteenveto',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_bio_vaara_tvali_muut_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli biojäte'
    )
ON CONFLICT DO NOTHING;
