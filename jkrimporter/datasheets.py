import csv
from abc import ABC, ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Generic, Iterator, List, Set, TypeVar
from pydantic import ValidationError

from openpyxl.reader.excel import load_workbook

if TYPE_CHECKING:
    from typing import Iterable, Protocol

    from openpyxl.workbook.workbook import Workbook
    from openpyxl.worksheet.worksheet import Worksheet

    class Sheet(Iterable, Protocol):
        sheet: Any
        headers: List[str]


class CsvSheet:
    def __init__(self, file_path):
        self._file_path = file_path
        with open(self._file_path, mode="r", encoding="cp1252", newline="") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=";", quotechar='"')
            self.headers = next(csv_reader)

    def __iter__(self):
        with open(self._file_path, mode="r", encoding="cp1252", newline="") as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=";", quotechar='"')
            for row in csv_reader:
                yield row


class ExcelSheet:
    def __init__(self, sheet: "Worksheet"):
        self.sheet = sheet
        self.headers = next(
            self.sheet.iter_rows(min_row=1, max_row=1, values_only=True)
        )

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        for row in self.sheet.iter_rows(min_row=2, values_only=True):
            yield dict(zip(self.headers, row))


class SheetCollection(ABC):
    def __init__(self, path):
        self._path = path
        self._opened_error_files = set()

    def __del__(self):
        for error_sheet in self._opened_error_files:
            error_sheet.close()

    @abstractmethod
    def _open_sheet(self, name) -> "Sheet":
        raise NotImplementedError

    def _open_error_sheet(self, name: str, headers: List[str]):
        error_file = open(
            self._path / f"{name}_virheet.csv", "w", newline="", encoding="utf-8"
        )
        writer = csv.DictWriter(error_file, fieldnames=headers + ["virhe"])
        writer.writeheader()

        self._opened_error_files.add(error_file)

        return writer


class CsvSheetCollection(SheetCollection):
    def _open_sheet(self, key):
        return CsvSheet(self._path / f"{key}.csv")


class ExcelFileSheetCollection(SheetCollection):
    def __init__(self, path):
        super().__init__(path)
        self._opened_workbooks: Set["Workbook"] = set()

    def _open_sheet(self, key):
        workbook = load_workbook(
            filename=self._path / f"{key}.xlsx", data_only=True, read_only=True
        )
        self._opened_workbooks.add(workbook)

        return ExcelSheet(workbook.active)

    def __del__(self):
        for workbook in self._opened_workbooks:
            workbook.close()

        super().__del__()


class ExcelSheetCollection(SheetCollection):
    def __init__(self, path):
        super().__init__(path)
        self._workbook = load_workbook(
            filename=self._path, data_only=True, read_only=True
        )

    def __del__(self):
        self._workbook.close()

    def _open_sheet(self, key):
        return ExcelSheet(self._workbook[key])


T = TypeVar("T")


class SiirtotiedostoSheet(Generic[T], metaclass=ABCMeta):
    def __init__(self, sheet_collection: SheetCollection, sheet_name: str):
        self._sheet = sheet_collection._open_sheet(sheet_name)
        self._error_sheet = sheet_collection._open_error_sheet(
            sheet_name, self._sheet.headers
        )

    @abstractmethod
    def _obj_from_dict(data) -> T:
        raise NotImplementedError

    def __iter__(self) -> Iterator[T]:
        for row in self._sheet:
            try:
                obj = self._obj_from_dict(row)
            except ValidationError as e:
                error = "; ".join(
                    f"{''.join(error['loc'])}: {error['msg']}" for error in e.errors()
                )
                row_with_error = {**row, "virhe": error}
                self._error_sheet.writerow(row_with_error)
                continue

            yield obj
