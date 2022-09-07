import csv

from jkrimporter.utils.osoite import parse_osoite

with ExcelFile("data/pjh/PJHn data/asiakastiedot.xlsx") as asiakastiedot, open(
    "pjh-virheelliset-osoitteet.csv", "w", newline="", encoding="cp1252"
) as csvfile:
    ok = 0
    virhe = 0
    tyhja = 0
    writer = csv.writer(csvfile, delimiter=";")
    for asiakas in asiakastiedot:
        osoite_str = asiakas["kohde_katuosoite"].strip()
        if not osoite_str:
            tyhja += 1
            continue
        try:
            osoite = parse_osoite(osoite_str)
            ok += 1
        except ValueError:
            writer.writerow([asiakas["asiakasnumero"].strip(), osoite_str])
            print(osoite_str)
            virhe += 1
    yht = ok + virhe + tyhja
    print(f"{yht=} {ok=} {virhe=} {tyhja=} virhe+tyhja%:{(virhe+tyhja)/yht*100:.2}")
