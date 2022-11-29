import datetime
import logging
import warnings
from collections import defaultdict
from datetime import date
from typing import TYPE_CHECKING, Union

from addrparser import AddressParser

from jkrimporter.model import Asiakas as JkrAsiakas
from jkrimporter.model import Jatelaji as JkrJatelaji
from jkrimporter.model import JkrData, Keraysvaline, KeraysvalineTyyppi
from jkrimporter.model import Keskeytys as JkrKeskeytys
from jkrimporter.model import (
    KimppaSopimus,
    Osoite,
    SopimusTyyppi,
    Tunnus,
    TyhjennysSopimus,
)
from jkrimporter.model import Tyhjennystapahtuma as JkrTyhjennystapahtuma
from jkrimporter.model import Tyhjennysvali as JkrTyhjennysvali
from jkrimporter.model import Yhteystieto
from jkrimporter.utils.intervals import Interval
from jkrimporter.utils.osoite import osoite_from_parsed_address

from .siirtotiedosto import LahtiSiirtotiedosto

if TYPE_CHECKING:
    from .siirtotiedosto import Asiakas

logger = logging.getLogger(__name__)

address_parser = AddressParser("fi")


def overlap(a: TyhjennysSopimus, b: TyhjennysSopimus) -> bool:
    a1 = a.alkupvm or datetime.date.min
    a2 = a.loppupvm or datetime.date.max
    b1 = b.alkupvm or datetime.date.min
    b2 = b.loppupvm or datetime.date.max

    return a1 <= b2 and b1 <= a2


def create_haltija(row: "Asiakas"):
    kohteen_osoite = Osoite(
        postinumero=row.kohde_postinumero,
        postitoimipaikka=row.kohde_postitoimipaikka,
    )
    if row.kohde_katuosoite:
        try:
            parsed_address = address_parser.parse(row.kohde_katuosoite)
        except ValueError:
            kohteen_osoite.erikoisosoite = row.kohde_katuosoite
        else:
            o = osoite_from_parsed_address(parsed_address)
            kohteen_osoite.katunimi = o.katunimi
            kohteen_osoite.osoitenumero = o.osoitenumero
            kohteen_osoite.huoneistotunnus = o.huoneistotunnus

    haltija = Yhteystieto(
        nimi=row.haltija_nimi,
        ytunnus=row.haltija_ytunnus,
        osoite=kohteen_osoite,
    )
    return haltija


def create_yhteyshenkilo(row: "Asiakas"):
    yhteyshenkilon_osoite = Osoite(
        postinumero=row.yhteyshenkilo_postinumero,
        postitoimipaikka=row.yhteyshenkilo_postitoimipaikka,
    )
    if row.yhteyshenkilo_katuosoite:
        try:
            parsed_address = address_parser.parse(row.kohde_katuosoite)
        except ValueError:
            yhteyshenkilon_osoite.erikoisosoite = row.yhteyshenkilo_katuosoite
        else:
            o = osoite_from_parsed_address(parsed_address)
            yhteyshenkilon_osoite.katunimi = o.katunimi
            yhteyshenkilon_osoite.osoitenumero = o.osoitenumero
            yhteyshenkilon_osoite.huoneistotunnus = o.huoneistotunnus

    yhteyshenkilo = Yhteystieto(
        nimi=row.yhteyshenkilo_nimi,
        osoite=yhteyshenkilon_osoite,
    )
    return yhteyshenkilo


class LahtiTranslator:
    def __init__(
        self, siirtotiedosto: LahtiSiirtotiedosto, tiedontuottajatunnus: str
    ):
        self._source = siirtotiedosto
        self._tiedontuottaja_tunnus = tiedontuottajatunnus
        self._asiakastunnus_to_tunnus = {}

    def as_jkr_data(self, alkupvm: Union[None, date], loppupvm: Union[None, date]):
        data = JkrData()

        data = self._add_meta(data, alkupvm, loppupvm)
        data = self._append_asiakkaat(data, alkupvm, loppupvm)
        # data = self._append_sopimukset_keraysvalineet_kuljetukset(
        #     data, alkupvm, loppupvm
        # )

        return data

    def tunnus_from_asiakasnumero(self, asiakasnro: str) -> Tunnus:
        return Tunnus(self._tiedontuottaja_tunnus, asiakasnro)

    def _add_meta(self, data: JkrData, alkupvm, loppupvm):
        data.alkupvm = alkupvm
        data.loppupvm = loppupvm

        return data

    def _append_asiakkaat(self, data: JkrData, alkupvm, loppupvm):
        print('appending asiakkaat')
        for row in self._source.asiakastiedot:
            print('got asiakastiedot')
            print(row)
            tunnus = self.tunnus_from_asiakasnumero(row.asiakasnumero)
            self._asiakastunnus_to_tunnus[row.asiakas_tunnus] = tunnus
            haltija = create_haltija(row)
            yhteyshenkilo = create_yhteyshenkilo(row)
            asiakas = JkrAsiakas(
                asiakasnumero=tunnus,
                voimassa=Interval(None, None),
                ulkoinen_asiakastieto=row,
                kiinteistot=row.kiinteistotunnukset,
                haltija=haltija,
                yhteyshenkilo=yhteyshenkilo,
            )

            data.asiakkaat[tunnus] = asiakas
        return data

    def _append_sopimukset_keraysvalineet_kuljetukset(
        self, data: JkrData, alkupvm: date, loppupvm: date
    ):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
            for row in self._source.kuljetustiedot:
                tunnus = self._asiakastunnus_to_tunnus.get(row.asiakas_tunnus, None)
                if not tunnus:
                    logger.warning(
                        "Ohitetaan kuljetustapahtuma. Ei asiakasta: "
                        f"'{row.asiakas_tunnus}'"
                    )
                    continue

                sopimus = next(
                    (
                        s
                        for s in data.asiakkaat[tunnus].sopimukset
                        if s.jatelaji == jatelaji_map[row.jatelaji]
                    ),
                    None,
                )
                if not sopimus:
                    sopimus = TyhjennysSopimus(
                        sopimustyyppi=SopimusTyyppi.tyhjennyssopimus,
                        jatelaji=jatelaji_map[row.jatelaji],
                        alkupvm=alkupvm,
                        loppupvm=loppupvm,
                    )
                    data.asiakkaat[tunnus].sopimukset.append(sopimus)

                keraysvaline = next(
                    (
                        k
                        for k in sopimus.keraysvalineet
                        if k.tyyppi == kaivotyyppi_map[row.kaivon_tyyppi]
                    ),
                    None,
                )
                if not keraysvaline:
                    keraysvaline = Keraysvaline(
                        maara=1, tyyppi=kaivotyyppi_map[row.kaivon_tyyppi]
                    )
                    sopimus.keraysvalineet.append(keraysvaline)

                data.asiakkaat[tunnus].tyhjennystapahtumat.append(
                    Tyhjennystapahtuma(
                        pvm=row.pvm,
                        jatelaji=jatelaji_map[row.jatelaji],
                        tyhjennyskerrat=1,
                        tilavuus=row.tilavuus * 1000,
                    )
                )

            return data
