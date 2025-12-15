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
        16
    ),
    (
        4,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_4_vk_ei_bio',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli',
        11
    ),
    (
        5,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_0_tai_yli_16_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli',
        11
    ),
    (
        6,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli',
        11
    ),
    (
        7,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte väärä tyhjennysväli',
        11
    ),
    (
        8,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_alle_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        6
    ),
    (
        9,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_enint_16_vk_bio_on',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        6
    ),
    (
        10,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_enint_16_vk_kompostointi_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        6
    ),
    (
        11,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        6
    ),
    (
        12,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Sekajäte'),
        '2022-1-1',
        'Sekajäte kunnossa',
        6
    ),
    (
        13,
        'Biojäte',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_bio_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte puuttuu',
        16
    ),
    (
        14,
        'Biojäte',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_bio_puuttuu_ei_kompostointia',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte puuttuu',
        16
    ),
    (
        15,
        'Biojäte',
        'v_erilliskeraysalueet',
        'kohteet_joilla_bio_0_tai_yli_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte väärä tyhjennysväli',
        11
    ),
    (
        16,
        'Biojäte',
        'v_erilliskeraysalueet',
        'kohteet_joilla_bio_enint_4_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte kunnossa',
        6
    ),
    (
        17,
        'Biojäte',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_kompostointi_voimassa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Biojäte'),
        '2022-1-1',
        'Biojäte kunnossa',
        6
    ),
    (
        18,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovipakkaus puuttuu',
        16
    ),
    (
        19,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_yli_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovi väärä tyhjennysväli',
        11
    ),
    (
        20,
        'Muovi',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_muovi_enintaan_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Muovi'),
        '2022-1-1',
        'Muovi kunnossa',
        6
    ),
    (
        21,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus puuttuu',
        16
    ),
    (
        22,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_yli_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus väärä tyhjennysväli',
        11
    ),
    (
        23,
        'Kartonki',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_kartonki_enintaan_12_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Kartonki'),
        '2022-1-1',
        'Kartonkipakkaus kunnossa',
        6
    ),
    (
        24,
        'Lasipakkaus',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus puuttuu',
        16
    ),
    (
        25,
        'Lasipakkaus',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_yli_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus väärä tyhjennysväli',
        11
    ),
    (
        26,
        'Lasipakkaus',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_lasi_enintaan_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Lasi'),
        '2022-1-1',
        'Lasipakkaus kunnossa',
        6
    ),
    (
        27,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_puuttuu',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli puuttuu',
        16
    ),
    (
        28,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_yli_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli väärä tyhjennysväli',
        11
    ),
    (
        29,
        'Metalli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_metalli_enintaan_26_vk',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Metalli'),
        '2022-1-1',
        'Metalli kunnossa',
        6
    ),
    (
        30,
        'Sekajäte',
        'kohde',
        'kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Aluekeräyspiste'),
        '2022-1-1',
        'Sekajäte kunnossa',
        6
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
        'kohteet_joiden_rakennukset_vapautettu_eivat_viemariverkossa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Vapautettu',
        6
    ),
    (
        33,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_kantovesi_tieto',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Kantovesi',
        6
    ),
    (
        34,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_saostusailio_tai_pienpuhdistamo_ei_harmaata_vett',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Lietteenkuljetus kunnossa saostussäiliö tai pienpuhdistamo',
        6
    ),
    (
        35,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_saostusailio_tyhja_ja_pienpuhdistamo_kompostoint',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Lietteenkuljetus kunnossa saostussäiliö tai pienpuhdistamo',
        6
    ),
    (
        36,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteella_lietekuljetus_ok_umpisailio_tai_ei_tietoa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Lietteenkuljetus kunnossa umpisäiliö tai ei tietoa',
        6
    ),
    (
        37,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_vain_harmaat_vedet',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Lietteenkuljetus kunnossa harmaat vedet',
        6
    ),
    (
        38,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_saostusai_tai_pienpuh_vaara_vali_ei_harmaata_vet',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Väärä tyhjennysväli saostussäiliö tai pienpuhdistamo',
        11
    ),
    (
        39,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteella_lietekuljetus_vaara_vali_umpisailio_tai_ei_tietoa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Väärä tyhjennysväli umpisäiliö tai ei tietoa',
        11
    ),
    (
        40,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_vaara_tyhjennysvali_vain_harmaat_vedet',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Väärä tyhjennysväli harmaat vedet',
        11
    ),
    (
        41,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_saostusai_tai_pienpuh_ei_lietekuljetus_harmaata',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Ei lietteenkuljetusta saostussäiliö tai pienpuhdistamo',
        16
    ),
    (
        42,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteella_ei_lietteenkuljetusta_umpisailio_tai_ei_tietoa',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Ei lietteenkuljetusta umpisäiliö tai ei tietoa',
        16
    ),
    (
        43,
        'Lietevelvoite',
        'v_bio_hapa_asuinkiinteisto',
        'kohteet_joilla_ei_lietteenkuljetusta_harmaat_vedet',
        (SELECT id FROM jkr_koodistot.jatetyyppi WHERE selite = 'Liete'),
        '2022-1-1',
        'Ei lietteenkuljetusta harmaat vedet',
        16
    )

ON CONFLICT DO NOTHING;
