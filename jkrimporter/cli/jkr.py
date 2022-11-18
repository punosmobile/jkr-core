from pathlib import Path
from typing import Optional

import typer

from jkrimporter import __version__
from jkrimporter.providers.db.dbprovider import DbProvider
from jkrimporter.providers.db.services.tiedontuottaja import (
    get_tiedontuottaja,
    insert_tiedontuottaja,
    list_tiedontuottajat,
    remove_tiedontuottaja,
 )
from jkrimporter.providers.pjh.pjhprovider import PjhTranslator
from jkrimporter.providers.pjh.siirtotiedosto import PjhSiirtotiedosto


def version_callback(value: bool):
    if value:
        print(__version__)
        raise typer.Exit()


def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Kertoo lataustyökalun versionumeron.",
    ),
):
    ...


app = typer.Typer(callback=main_callback)

urakoitsija_app = typer.Typer()
app.add_typer(
    urakoitsija_app, name="urakoitsija", help="Muokkaa ja tarkastele urakoitsijoita."
)


@app.command("import", help="Import transportation data to JKR.")
def import_data(
    siirtotiedosto: Path = typer.Argument(..., help="Siirtotiedoston kansio"),
    urakoitsija: str = typer.Argument(
        ..., help="Tiedon toimittajan tunnus. Esim. 'PJH', 'HKO', 'LSJ'"
    ),
):
    tiedontuottaja = get_tiedontuottaja(urakoitsija)
    if not tiedontuottaja:
        typer.echo(
            f"Urakoitsijaa {urakoitsija} ei löydy järjestelmästä. Lisää komennolla `jkr urakoitsija add`"
        )
        raise typer.Exit()
    pjhdata = PjhSiirtotiedosto(siirtotiedosto)
    translator = PjhTranslator(pjhdata)
    jkr_data = translator.as_jkr_data()
    db = DbProvider()
    db.write(jkr_data, urakoitsija)

    print("VALMIS!")


@app.command("create_dvv_kohteet", help="Create kohteet from DVV data in database.")
def create_dvv_kohteet(
    perusmaksutiedosto: Optional[Path] = typer.Argument(
        None, help="Perusmaksurekisteritiedosto"
    ),
):
    db = DbProvider()
    db.write_dvv_kohteet(perusmaksutiedosto)

    print("VALMIS!")


@urakoitsija_app.command("add", help="Lisää uusi urakoitsija järjestelmään.")
def urakoitsija_add_new(
    tunnus: str = typer.Argument(..., help="Urakoitsijan tunnus. Esim. 'PJH'"),
    name: str = typer.Argument(..., help="Urakoitsijan nimi."),
):
    insert_tiedontuottaja(tunnus.upper(), name)


@urakoitsija_app.command("remove", help="Poista urakoitsija järjestelmästä.")
def urakoitsija_remove(
    tunnus: str = typer.Argument(..., help="Urakoitsijan tunnus. Esim. 'PJH'")
):
    remove_tiedontuottaja(tunnus.upper())


@urakoitsija_app.command("list", help="Listaa järjestelmästä löytyvät urakoitsijat.")
def urakoitsija_list():
    for tiedontuottaja in list_tiedontuottajat():
        print(f"{tiedontuottaja.tunnus}\t{tiedontuottaja.nimi}")


if __name__ == "__main__":
    app()
