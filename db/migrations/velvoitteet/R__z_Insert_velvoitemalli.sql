INSERT INTO jkr.velvoitemalli(id, selite, saanto, tayttymissaanto, jatetyyppi_id, alkupvm, kuvaus, prioriteetti)
VALUES
    (
        3,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte puuttuu',
        11
    ),
    (
        4,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_4_vk_ei_bio',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli',
        6
    ),
    (
        5,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_0_tai_yli_16_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli',
        6
    ),
    (
        6,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli',
        6
    ),
    (
        7,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli',
        6
    ),
    (
        8,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_alle_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        1
    ),
    (
        9,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_enint_16_vk_bio_on',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        1
    ),
    (
        10,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_enint_16_vk_kompostointi_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        1
    ),
    (
        11,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        1
    ),
    (
        12,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        1
    ),
    (
        13,
        'Biojäte',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_bio_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte puuttuu',
        11
    ),
    (
        14,
        'Biojäte',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_bio_puuttuu_ei_kompostointia',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte puuttuu',
        11
    ),
    (
        15,
        'Biojäte',
        'v_erilliskeraysalueet',
        'kohteet_joilla_bio_0_tai_yli_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte väärä tyhjennysväli',
        6
    ),
    (
        16,
        'Biojäte',
        'v_erilliskeraysalueet',
        'kohteet_joilla_bio_enint_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte kunnossa',
        1
    ),
    (
        17,
        'Biojäte',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_kompostointi_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte kunnossa',
        1
    ),
    (
        18,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovipakkaus puuttuu',
        11
    ),
    (
        19,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_yli_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovi väärä tyhjennysväli',
        6
    ),
    (
        20,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_enintaan_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovi kunnossa',
        1
    ),
    (
        21,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus puuttuu',
        11
    ),
    (
        22,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_yli_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus väärä tyhjennysväli',
        6
    ),
    (
        23,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_enintaan_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus kunnossa',
        1
    ),
    (
        24,
        'Lasipakkaus',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus puuttuu',
        11
    ),
    (
        25,
        'Lasipakkaus',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_yli_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus väärä tyhjennysväli',
        6
    ),
    (
        26,
        'Lasipakkaus',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_enintaan_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus kunnossa',
        1
    ),
    (
        27,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli puuttuu',
        11
    ),
    (
        28,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_yli_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli väärä tyhjennysväli',
        6
    ),
    (
        29,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_enintaan_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli kunnossa',
        1
    ),
    (
        30,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Aluekeräyspiste'),
        '2022-1-1',
        'Sekajäte kunnossa',
        1
    ),
    (
        31,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_jotka_ovat_viemariverkossa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Viemäriverkostossa',
        1
    ),
    (
        32,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joiden_rakennukset_vapautettu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Vapautettu',
        1
    ),
    (
        33,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_kantovesi_tieto',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Kantovesi',
        1
    ),
    (
        34,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_saostusailio_tai_pienpuhdistamo_ei_harmaata_vett',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Lietteenkuljetus kunnossa saostussäiliö tai pienpuhdistamo',
        1
    ),
    (
        35,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Lietteenkuljetus kunnossa saostussäiliö tai pienpuhdistamo',
        1
    ),
    (
        36,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteella_lietekuljetus_ok_umpisailio_tai_ei_tietoa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Lietteenkuljetus kunnossa umpisäiliö tai ei tietoa',
        1
    ),
    (
        37,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_vain_harmaat_vedet',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Lietteenkuljetus kunnossa harmaat vedet',
        1
    )
ON CONFLICT DO NOTHING;
