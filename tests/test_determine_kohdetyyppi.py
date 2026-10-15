"""
Yksikkötestit kohdetyypin määräytymiselle rakennuksen luokitustietojen
perusteella (LAH-226).

Testaa jkrimporter.providers.db.services.kohde.determine_kohdetyyppi-funktiota,
joka päättää onko kohde ASUINKIINTEISTO vai MUU. Tarkistusjärjestys:
    1. Rakennusluokka 2018 (110-211)
    2. Käyttötarkoitus (11-41)
    3. Huoneistomäärä > 0
    4. Rakennuksenolotila (vakinainen asuminen, koodi "01")
    5. Vähintään yksi asukas
    6. Muutoin MUU

Funktio ei käytä session-parametria, joten testit ovat puhtaita yksikkötestejä
ilman tietokantaa. HAPA/BIOHAPA-tyypit määräytyvät erikseen kannan triggerillä,
eivätkä kuulu tämän funktion vastuulle.
"""

from types import SimpleNamespace

from jkrimporter.providers.db.codes import KohdeTyyppi
from jkrimporter.providers.db.services.kohde import determine_kohdetyyppi


def make_rakennus(**overrides):
    """Luo kevyen rakennus-tuplan determine_kohdetyyppi-testejä varten.

    Oletuksena kaikki asuinkäyttöä indikoivat kentät ovat tyhjiä (None),
    jolloin tulos on MUU ellei jotain kenttää aseteta overrides-argumentilla.
    Vain *_koodi-muotoiset kentät asetetaan, joten olotilan tarkistus käyttää
    rakennuksenolotila_koodi-haaraa.
    """
    base = dict(
        prt="TEST-PRT",
        rakennusluokka_2018=None,
        rakennuksenkayttotarkoitus_koodi=None,
        huoneistomaara=None,
        rakennuksenolotila_koodi=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestDetermineKohdetyyppiRakennusluokka2018:
    """Rakennusluokka 2018 -kentän (110-211) perusteella asuinkiinteistö."""

    def test_alaraja_110_on_asuinkiinteisto(self):
        rakennus = make_rakennus(rakennusluokka_2018="0110")
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.ASUINKIINTEISTO

    def test_ylaraja_211_on_asuinkiinteisto(self):
        rakennus = make_rakennus(rakennusluokka_2018="0211")
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.ASUINKIINTEISTO

    def test_rajan_ulkopuolinen_ei_yksinaan_asuinkiinteisto(self):
        # 700 ei ole asuinrakennusluokka eikä muita asuinkäytön merkkejä ole.
        rakennus = make_rakennus(rakennusluokka_2018="0700")
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.MUU

    def test_epavalidi_arvo_kaatuu_seuraavaan_tarkistukseen(self):
        # Epävalidi rakennusluokka ei kaada funktiota vaan tarkistus jatkuu
        # käyttötarkoitukseen, joka tässä on asuinkäyttöä.
        rakennus = make_rakennus(
            rakennusluokka_2018="EI-NUMERO",
            rakennuksenkayttotarkoitus_koodi="011",
        )
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.ASUINKIINTEISTO


class TestDetermineKohdetyyppiKayttotarkoitus:
    """Käyttötarkoituskoodin (11-41) perusteella asuinkiinteistö."""

    def test_alaraja_11_on_asuinkiinteisto(self):
        rakennus = make_rakennus(rakennuksenkayttotarkoitus_koodi="011")
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.ASUINKIINTEISTO

    def test_ylaraja_41_on_asuinkiinteisto(self):
        rakennus = make_rakennus(rakennuksenkayttotarkoitus_koodi="041")
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.ASUINKIINTEISTO

    def test_rajan_ulkopuolinen_kayttotarkoitus_on_muu(self):
        rakennus = make_rakennus(rakennuksenkayttotarkoitus_koodi="511")
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.MUU


class TestDetermineKohdetyyppiMuutEhdot:
    """Huoneistomäärä, olotila ja asukkaat tekevät kohteesta asuinkiinteistön."""

    def test_huoneistomaara_yli_nollan_on_asuinkiinteisto(self):
        rakennus = make_rakennus(huoneistomaara=2)
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.ASUINKIINTEISTO

    def test_huoneistomaara_nolla_ei_riita(self):
        rakennus = make_rakennus(huoneistomaara=0)
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.MUU

    def test_vakinainen_asuminen_olotila_on_asuinkiinteisto(self):
        # RakennuksenOlotilaTyyppi.VAKINAINEN_ASUMINEN == "01"
        rakennus = make_rakennus(rakennuksenolotila_koodi="01")
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.ASUINKIINTEISTO

    def test_muu_olotila_ei_riita(self):
        rakennus = make_rakennus(rakennuksenolotila_koodi="05")  # tyhjillään
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.MUU

    def test_asukkaat_tekevat_asuinkiinteiston(self):
        rakennus = make_rakennus()
        asukkaat = {object()}
        assert (
            determine_kohdetyyppi(None, rakennus, asukkaat)
            == KohdeTyyppi.ASUINKIINTEISTO
        )


class TestDetermineKohdetyyppiMuu:
    """Kun mikään asuinkäytön ehto ei täyty, kohde on MUU."""

    def test_ei_yhtaan_asuinkayton_merkkia_on_muu(self):
        rakennus = make_rakennus()
        assert determine_kohdetyyppi(None, rakennus) == KohdeTyyppi.MUU

    def test_tyhjat_asukkaat_eivat_riita(self):
        rakennus = make_rakennus()
        assert determine_kohdetyyppi(None, rakennus, set()) == KohdeTyyppi.MUU
