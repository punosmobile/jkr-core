from .viemaritiedosto import ViemariIlmoitustiedosto, ViemariLopetustiedosto
from jkrimporter.model import (
    ViemariIlmoitus,
    ViemariLopetusIlmoitus
)

class ViemariLopetusIlmoitusTranslator:

    def __init__(self, lopetusilmoitukset: ViemariLopetustiedosto):
        self._source = lopetusilmoitukset

    def as_jkr_data(self):
        data = []

        for row in self._source.lopetusilmoitukset:
            data.append(
                ViemariLopetusIlmoitus(
                    viemariverkosto_loppupvm=row.viemariverkosto_loppupvm,
                    prt=row.prt,
                    rawdata=row.rawdata,
                )
            )

        return data


class ViemariIlmoitusTranslator:

    def __init__(self, viemariilmoitukset: ViemariIlmoitustiedosto):
        self._source = viemariilmoitukset

    def as_jkr_data(self):
        data = []

        for row in self._source.viemariilmoitukset:
            data.append(
                ViemariIlmoitus(
                    viemariverkosto_alkupvm=row.viemariverkosto_alkupvm,
                    prt=row.prt,
                    rawdata=row.rawdata,
                )
            )

        return data