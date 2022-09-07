import csv

jatetyyppi = set()
astiatyyppi = set()
with open(
    "data/pjh/PJHn data/2020 ja 2021/2021/Keräysvälineet.csv",
    mode="r",
    encoding="cp1252",
    newline="",
) as csv_file:
    csv_reader = csv.DictReader(csv_file, delimiter=";", quotechar='"')
    for row in csv_reader:
        jatetyyppi.add(row["jätelaji"])
        astiatyyppi.add(row["tyyppi"])


print(sorted(list(jatetyyppi)))
print(sorted(list(astiatyyppi)))
