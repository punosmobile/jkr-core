INSERT INTO jkr.velvoiteyhteenvetomalli(id, selite, saanto, tayttymissaanto, alkupvm, kuvaus, luokitus)
VALUES
    (
        1,
        'Velvoiteyhteenveto vapautettu',
        'kohde',
        'kohteet_joilla_vapauttava_paatos_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto ei tarvitse jätteenkuljetusta',
        1
    ),
    (
        2,
        'Velvoiteyhteenveto keskeytetty',
        'kohde',
        'kohteet_joilla_keskeyttava_paatos_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto ei tarvitse jätteenkuljetusta',
        1
    ),
    (
        30,
        'Velvoiteyhteenveto jätteenkuljetus kunnossa',
        'v_ei_erilliskeraysalueet',
        'kohteet_joilla_seka_ok',
        '2022-1-1',
        'Velvoiteyhteenveto jätteenkuljetus kunnossa',
        1
    ),
    (
        31,
        'Velvoiteyhteenveto jätteenkuljetus kunnossa',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_kompostointi_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto jätteenkuljetus kunnossa',
        1
    ),
    (
        32,
        'Velvoiteyhteenveto jätteenkuljetus kunnossa',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4',
        '2022-1-1',
        'Velvoiteyhteenveto jätteenkuljetus kunnossa',
        1
    ),
    (
        33,
        'Velvoiteyhteenveto jätteenkuljetus kunnossa',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_muut_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto jätteenkuljetus kunnossa',
        1
    ),
    (
        34,
        'Velvoiteyhteenveto ei jätehuoltoa',
        'kohde',
        'kohteet_joilla_seka_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto ei jätehuoltoa',
        3
    ),
    (
        35,
        'Velvoiteyhteenveto biojäte puuttuu',
        'v_erilliskeraysalueet',
        'kohteet_joilla_seka_ok_bio_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto biojäte puuttuu',
        2
    ),
    (
        36,
        'Velvoiteyhteenveto kartonki puutteellinen',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_kartonki_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto kartonki puutteellinen',
        2
    ),
    (
        37,
        'Velvoiteyhteenveto metalli puutteellinen',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_metalli_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto metalli puutteellinen',
        2
    ),
    (
        38,
        'Velvoiteyhteenveto lasi puutteellinen',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_lasi_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto lasi puutteellinen',
        2
    ),
    (
        39,
        'Velvoiteyhteenveto muovipakkaus puutteellinen',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_muovi_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto muovipakkaus puutteellinen',
        2
    ),
    (
        40,
        'Velvoiteyhteenveto sekajäte väärä tyhjennysväli',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_vaara_tvali_muut_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli sekajäte',
        1
    ),
    (
        41,
        'Velvoiteyhteenveto sekajäte väärä tyhjennysväli',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_vaara_tvali_bio_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli sekajäte',
        1
    ),
    (
        42,
        'Velvoiteyhteenveto sekajäte väärä tyhjennysväli',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_vaara_tvali_kompostointi_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli sekajäte',
        1
    ),
    (
        43,
        'Velvoiteyhteenveto sekajäte väärä tyhjennysväli',
        'v_ei_erilliskeraysalueet',
        'kohteet_joilla_seka_vaara_tvali',
        '2022-1-1',
        'Velvoiteyhteenveto väärä tyhjennysväli sekajäte',
        1
    ),
    (
        44,
        'Velvoiteyhteenveto biojäte puuttuu',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_bio_vaara_tvali_seka_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto biojäte puuttuu',
        1
    ),
    (
        45,
        'Velvoiteyhteenveto biojäte puuttuu',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_bio_vaara_tvali_muut_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto biojäte puuttuu',
        1
    )
ON CONFLICT DO NOTHING;
