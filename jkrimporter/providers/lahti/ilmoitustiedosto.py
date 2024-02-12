import logging
from pathlib import Path

from openpyxl.reader.excel import load_workbook
from pydantic import ValidationError

from jkrimporter.providers.lahti.models import Ilmoitus

logger = logging.getLogger(__name__)


class Ilmoitustiedosto:
    def __init__(self, path):
        self._path = path

    @classmethod
    def readable_by_me(cls, path):
        file = Path(path)
        if file.is_file() and file.suffix == ".xlsx":
            try:
                workbook = load_workbook(filename=file, data_only=True, read_only=True)
                if len(workbook.sheetnames):
                    return True
            except Exception:
                pass
        return False

    @property
    def ilmoitukset(self):
        ilmoitus_list = []

        workbook = load_workbook(self._path)
        sheet = workbook[workbook.sheetnames[0]]

        # In Excel files, the row indices start from 1.
        headers = [cell.value for cell in sheet[1]]

        for row in sheet.iter_rows(min_row=2, values_only=True):
            try:
                data = dict(zip(headers, row))
                ilmoitus_obj = Ilmoitus.parse_obj(data)
                ilmoitus_list.append(ilmoitus_obj)
            except ValidationError as e:
                logger.warning(
                    f"Ilmoitus-olion luonti epäonnistui datalla: {row}. Virhe: {e}"
                )

        return ilmoitus_list
