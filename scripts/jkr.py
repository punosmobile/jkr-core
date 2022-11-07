from pathlib import Path
from typing import Optional

import typer

from jkrimporter.providers.db.dbprovider import DbProvider
from jkrimporter.providers.pjh.pjhprovider import PjhTranslator
from jkrimporter.providers.pjh.siirtotiedosto import PjhSiirtotiedosto

app = typer.Typer()

urakoitsija_app = typer.Typer()
app.add_typer(
    urakoitsija_app, name="urakoitsija", help="Muokkaa ja tarkastele urakoitsijoita."
)


@app.command("import", help="Import transportation data to JKR.")
def import_data(
    siirtotiedosto: Path = typer.Argument(..., help="Siirtotiedoston kansio"),
    urakoitsija: str = typer.Argument(..., help="Urakoitsijan tunnus. Esim. 'PJH'"),
):
    pjhdata = PjhSiirtotiedosto(siirtotiedosto)
    translator = PjhTranslator(pjhdata)
    jkr_data = translator.as_jkr_data()
    db = DbProvider()
    db.write(jkr_data, urakoitsija)

    print("VALMIS!")


@app.command("import_dvv", help="Import DVV data to JKR.")
def import_dvv(
    siirtotiedosto: Path = typer.Argument(None, help="Siirtotiedoston kansio"),
    perusmaksutiedosto: Optional[Path] = typer.Argument(None, help="Perusmaksurekisteritiedosto")
):
    # TODO: call the dvv import script with the given file
    # run_script(import_dvv, siirtotiedosto)
    db = DbProvider()
    db.write_dvv_kohteet(perusmaksutiedosto)

    print("VALMIS!")


@urakoitsija_app.command("add", help="Lisää uusi urakoitsija järjestelmään.")
def urakoitsija_add_new(
    tunnus: str = typer.Argument(..., help="Urakoitsijan tunnus. Esim. 'PJH'"),
    name: str = typer.Argument(..., help="Urakoitsijan nimi."),
):
    print(f"Lisättiin uusi urakoitsija {tunnus}({name})")


@urakoitsija_app.command("list", help="Listaa järjestelmästä löytyvät urakoitsijat.")
def urakoitsija_list():
    print("PJH \t Pirkanmaan Jätehuolto Oy\n")


if __name__ == "__main__":
    app()

    # import_data(Path("data/pjh/PJHn data/2020 ja 2021/2021"), "PJH")
