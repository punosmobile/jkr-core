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
        'Velvoiteyhteenveto kartonkipakkaus puutteellinen',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_kartonki_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto kartonkipakkaus puutteellinen',
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
        'Velvoiteyhteenveto Lasipakkaus puutteellinen',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_ok_bio_enint_4_lasi_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto Lasipakkaus puutteellinen',
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
        2
    ),
    (
        45,
        'Velvoiteyhteenveto biojäte puuttuu',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_bio_vaara_tvali_muut_voimassa',
        '2022-1-1',
        'Velvoiteyhteenveto biojäte puuttuu',
        2
    ),
    (
        46,
        'Velvoiteyhteenveto biojäte puuttuu',
        'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
        'kohteet_joilla_seka_vaara_tvali_bio_puuttuu',
        '2022-1-1',
        'Velvoiteyhteenveto biojäte puuttuu',
        2
    ),
    (
        47,
        'Velvoiteyhteenveto biojäte puuttuu',
        'v_enint_4_huoneistoa_biojatteen_erilliskeraysalue',
        'kohteet_joilla_seka_vaara_tvali_bio_puuttuu_ei_kompostointia',
        '2022-1-1',
        'Velvoiteyhteenveto biojäte puuttuu',
        2
    )
ON CONFLICT DO NOTHING;

-- LAH-591: Päivitetään saannon_selite ja tayttymissaannon_selite kaikille olemassa
-- oleville velvoiteyhteenvetomalleille.
UPDATE jkr.velvoiteyhteenvetomalli vym
SET saannon_selite = v.saannon_selite,
    tayttymissaannon_selite = v.tayttymissaannon_selite
FROM (VALUES
    -- Saannon_selite avaa saanto-kentän näkymän tai erikoisarvon 'kohde' kohderyhmän:
    --   'kohde'                                              = sääntöä ei rajata, sovelletaan kaikkiin kohteisiin
    --   v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue    = >=5 huoneiston kohteet taajamassa
    --   v_enint_4_huoneistoa_biojatteen_erilliskeraysalue    = <=4 huoneiston kohteet >=10 000 as. taajamassa
    --   v_erilliskeraysalueet                                = molempien erilliskeräysalueiden yhdistelmä
    --   v_ei_erilliskeraysalueet                             = erilliskeräysalueen ulkopuoliset kohteet
    (1,  'Sääntöä ei rajata näkymällä - sääntöä sovelletaan kaikkiin kohteisiin riippumatta kohdetyypistä, sijainnista tai huoneistomäärästä.',
         'Kohteen kaikilla velvoiterakennuksilla on voimassa oleva myönteinen AKP- tai Perusmaksu-päätös.'),
    (2,  'Sääntöä ei rajata näkymällä - sääntöä sovelletaan kaikkiin kohteisiin.',
         'Kohteella on voimassa oleva myönteinen Keskeyttämispäätös.'),
    (30, 'Erilliskeräysalueen ulkopuoliset kohteet: <=4 huoneiston kohteet jotka eivät ole biojätteen erilliskeräysalueella, sekä >=5 huoneiston kohteet jotka eivät ole hyötyjätteen erilliskeräysalueella.',
         'Kohteen sekajätekeräys on kunnossa (jokin sekajäte-kunnossa-tila täyttyy tai voimassa oleva aluekeräys).'),
    (31, 'Biojätteen erilliskeräysalueen kohteet: kohteella on rakennus vähintään 10 000 asukkaan taajamassa ja kohteen rakennusten huoneistomäärä on yhteensä enintään 4.',
         'Kohteen sekajätekeräys on kunnossa ja voimassa oleva kompostointi-ilmoitus.'),
    (32, 'Biojätteen erilliskeräysalueen kohteet: kohteella on rakennus vähintään 10 000 asukkaan taajamassa ja kohteen rakennusten huoneistomäärä on yhteensä enintään 4.',
         'Kohteen sekajätekeräys on kunnossa ja biojätteen tyhjennysväli enintään 4 viikkoa.'),
    (33, 'Hyötyjätteen erilliskeräysalueen kohteet: kohteella on rakennus taajaman aluerajauksen sisällä ja kohteen rakennusten huoneistomäärä on yhteensä vähintään 5.',
         'Kohteen sekajätekeräys on kunnossa, biojätteen tyhjennysväli enintään 4 viikkoa ja kartonki-, metalli-, lasi- sekä muovipakkaussopimukset voimassa.'),
    (34, 'Sääntöä ei rajata näkymällä - sääntöä sovelletaan kaikkiin kohteisiin.',
         'Kohteelta puuttuu voimassa oleva sekajätesopimus eikä sillä ole voimassa olevaa vapauttavaa, keskeyttävää tai pidentävää päätöstä.'),
    (35, 'Erilliskeräysalueen kohteet: yhdistelmä biojätteen (enintään 4 huoneistoa, taajaman väestö >=10 000) ja hyötyjätteen (vähintään 5 huoneistoa, mikä tahansa taajama) erilliskeräysalueiden kohteista.',
         'Kohteen sekajätekeräys on kunnossa, mutta voimassa oleva biojätesopimus puuttuu.'),
    (36, 'Hyötyjätteen erilliskeräysalueen kohteet: kohteella on rakennus taajaman aluerajauksen sisällä ja kohteen rakennusten huoneistomäärä on yhteensä vähintään 5.',
         'Kohteen sekajätekeräys on kunnossa ja biojätteen tyhjennysväli enintään 4 viikkoa, mutta kartonkipakkaussopimus puuttuu.'),
    (37, 'Hyötyjätteen erilliskeräysalueen kohteet: kohteella on rakennus taajaman aluerajauksen sisällä ja kohteen rakennusten huoneistomäärä on yhteensä vähintään 5.',
         'Kohteen sekajätekeräys on kunnossa ja biojätteen tyhjennysväli enintään 4 viikkoa, mutta metallisopimus puuttuu.'),
    (38, 'Hyötyjätteen erilliskeräysalueen kohteet: kohteella on rakennus taajaman aluerajauksen sisällä ja kohteen rakennusten huoneistomäärä on yhteensä vähintään 5.',
         'Kohteen sekajätekeräys on kunnossa ja biojätteen tyhjennysväli enintään 4 viikkoa, mutta lasipakkaussopimus puuttuu.'),
    (39, 'Hyötyjätteen erilliskeräysalueen kohteet: kohteella on rakennus taajaman aluerajauksen sisällä ja kohteen rakennusten huoneistomäärä on yhteensä vähintään 5.',
         'Kohteen sekajätekeräys on kunnossa ja biojätteen tyhjennysväli enintään 4 viikkoa, mutta muovipakkaussopimus puuttuu.'),
    (40, 'Hyötyjätteen erilliskeräysalueen kohteet: kohteella on rakennus taajaman aluerajauksen sisällä ja kohteen rakennusten huoneistomäärä on yhteensä vähintään 5.',
         'Sekajätteen tyhjennysväli on väärä, mutta biojäte-, kartonki-, metalli-, lasi- ja muovipakkaussopimukset voimassa.'),
    (41, 'Biojätteen erilliskeräysalueen kohteet: kohteella on rakennus vähintään 10 000 asukkaan taajamassa ja kohteen rakennusten huoneistomäärä on yhteensä enintään 4.',
         'Sekajätteen tyhjennysväli on väärä, mutta biojätesopimus voimassa.'),
    (42, 'Biojätteen erilliskeräysalueen kohteet: kohteella on rakennus vähintään 10 000 asukkaan taajamassa ja kohteen rakennusten huoneistomäärä on yhteensä enintään 4.',
         'Sekajätteen tyhjennysväli on väärä, mutta kompostointi-ilmoitus voimassa.'),
    (43, 'Erilliskeräysalueen ulkopuoliset kohteet: <=4 huoneiston kohteet jotka eivät ole biojätteen erilliskeräysalueella, sekä >=5 huoneiston kohteet jotka eivät ole hyötyjätteen erilliskeräysalueella.',
         'Sekajätteen tyhjennysväli on väärä (jokin sekajäte-väärä-väli-tila täyttyy).'),
    (44, 'Biojätteen erilliskeräysalueen kohteet: kohteella on rakennus vähintään 10 000 asukkaan taajamassa ja kohteen rakennusten huoneistomäärä on yhteensä enintään 4.',
         'Biojätteen tyhjennysväli on väärä ja sekajätesopimus voimassa.'),
    (45, 'Hyötyjätteen erilliskeräysalueen kohteet: kohteella on rakennus taajaman aluerajauksen sisällä ja kohteen rakennusten huoneistomäärä on yhteensä vähintään 5.',
         'Biojätteen tyhjennysväli on väärä ja sekajäte-, kartonki-, metalli-, lasi- ja muovipakkaussopimukset voimassa.'),
    (46, 'Hyötyjätteen erilliskeräysalueen kohteet: kohteella on rakennus taajaman aluerajauksen sisällä ja kohteen rakennusten huoneistomäärä on yhteensä vähintään 5.',
         'Sekajätteen tyhjennysväli on väärä ja voimassa oleva biojätesopimus puuttuu.'),
    (47, 'Biojätteen erilliskeräysalueen kohteet: kohteella on rakennus vähintään 10 000 asukkaan taajamassa ja kohteen rakennusten huoneistomäärä on yhteensä enintään 4.',
         'Sekajätteen tyhjennysväli on väärä, voimassa oleva biojätesopimus puuttuu eikä kohteella ole voimassa olevaa kompostointi-ilmoitusta.')
) AS v(id, saannon_selite, tayttymissaannon_selite)
WHERE vym.id = v.id;
