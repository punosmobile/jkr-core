import logging
import csv
from pathlib import Path
from typing import List

from jkrimporter.datasheets import SiirtotiedostoSheet
from jkrimporter.providers.lahti.models import Asiakas
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class AsiakastiedotSheet(SiirtotiedostoSheet[Asiakas]):
    @staticmethod
    def _obj_from_dict(data):
        return Asiakas.parse_obj(data)


class LahtiSiirtotiedosto:
    def __init__(self, path):
        self._path = path

    @classmethod
    def readable_by_me(cls, path):
        directory = Path(path)
        for file in directory.iterdir():
            if file.is_file() and file.suffix == ".csv":
                return True
        return False

    @property
    def asiakastiedot(self):
        all_data = []

        # Iterate through all CSV files in the directory
        for csv_file_path in Path(self._path).glob("*.csv"):
            with open(csv_file_path, mode="r", encoding="cp1252", newline="") as csv_file:
                csv_reader = csv.DictReader(csv_file, delimiter=";", quotechar='"')
                data_list = [row for row in csv_reader]
                all_data.extend(data_list)

        # Convert to a list of Asiakas objects
        asiakas_list = []
        for data in all_data:
            # Validate Asiakas, if validation fails skip.
            try:
                asiakas_obj = Asiakas.parse_obj(data)
                asiakas_list.append(asiakas_obj)
            except ValidationError as e:
                logger.error(f"Validation failed for data: {data}. Error: {e}")

        return asiakas_list
