\set copy_command '\\copy tmp_report_result TO ' :'csv_path' ' WITH CSV HEADER'

CREATE TEMP TABLE tmp_report_result(
    Kohde_id INTEGER,
    Tarkastelupvm DATE,
    "Kohteen rakennuksen 1 sijaintikunta" TEXT,
    Huoneistolukumäärä BIGINT,
    "Yli 10 000 taajama" TEXT,
    "200 asukkaan taajama" TEXT,
    "kohdetyyppi" TEXT,
    "Komposti-ilmoituksen tekijan nimi" TEXT,
    "Sekajätteen tilaajan nimi" TEXT,
    "Sekajätteen tilaajan katuosoite" TEXT,
    "Sekajätteen tilaajan postinumero" TEXT,
    "Sekajätteen tilaajan postitoimipaikka" TEXT,
    "Salpakierron tilaajan nimi" TEXT,
    "Salpakierron tilaajan katuosoite" TEXT,
    "Salpakierron postinumero" TEXT,
    "Salpakierron postitoimipaikka" TEXT,
    "Omistaja 1 nimi" TEXT,
    "Omistaja 1 katuosoite" TEXT,
    "Omistaja 1 postinumero" TEXT,
    "Omistaja 1 postitoimipaikka" TEXT,
    "Omistaja 2 nimi" TEXT,
    "Omistaja 2 katuosoite" TEXT,
    "Omistaja 2 postinumero" TEXT,
    "Omistaja 2 postitoimipaikka" TEXT,
    "Omistaja 3 nimi" TEXT,
    "Omistaja 3 katuosoite" TEXT,
    "Omistaja 3 postinumero" TEXT,
    "Omistaja 3 postitoimipaikka" TEXT,
    "Vanhimman asukkaan nimi" TEXT,
    "Velvoitteen tallennuspäivämäärä" DATE,
    Velvoiteyhteenveto TEXT,
    Sekajätevelvoite TEXT,
    Biojätevelvoite TEXT,
    Muovipakkausvelvoite TEXT,
    Kartonkipakkausvelvoite TEXT,
    Lasipakkausvelvoite TEXT,
    Metallipakkausvelvoite TEXT,
    Muovi DATE,
    Kartonki DATE,
    Metalli DATE,
    Lasi DATE,
    Biojäte DATE,
    Monilokero DATE,
    Sekajäte DATE,
    Akp DATE,
    Kompostoi DATE,
    "Perusmaksupäätös voimassa" DATE,
    "Perusmaksupäätös" TEXT,
    "Tyhjennysvälipäätös voimassa" DATE,
    "Tyhjennysvalipäätös" TEXT,
    "Akp-kohtuullistaminen voimassa" DATE,
    "Akp-kohtuullistaminen" TEXT,
    "Keskeytys voimassa" DATE,
    "Keskeytys" TEXT,
    "Erilliskeraysvelvoitteesta poikkeaminen voimassa" DATE,
    "Erilliskeraysvelvoitteesta poikkeaminen" TEXT,
    "PRT 1" TEXT,
    "Käyttötila 1" TEXT,
    "Käyttötarkoitus 1" TEXT,
    Katuosoite TEXT,
    Postinumero TEXT,
    Postitoimipaikka TEXT,
    Sijaintikiinteisto TEXT,
    "X-koordinaatti" FLOAT,
    "Y-koordinaatti" FLOAT,
    "PRT 2" TEXT,
    "Käyttötila 2" TEXT,
    "Käyttötarkoitus 2" TEXT,
    "PRT 3" TEXT,
    "Käyttötila 3" TEXT,
    "Käyttötarkoitus 3" TEXT,
    "PRT 4" TEXT,
    "Käyttötila 4" TEXT,
    "Käyttötarkoitus 4" TEXT,
    "PRT 5" TEXT,
    "Käyttötila 5" TEXT,
    "Käyttötarkoitus 5" TEXT,
    "PRT 6" TEXT,
    "Käyttötila 6" TEXT,
    "Käyttötarkoitus 6" TEXT,
    "PRT 7" TEXT,
    "Käyttötila 7" TEXT,
    "Käyttötarkoitus 7" TEXT,
    "PRT 8" TEXT,
    "Käyttötila 8" TEXT,
    "Käyttötarkoitus 8" TEXT,
    "PRT 9" TEXT,
    "Käyttötila 9" TEXT,
    "Käyttötarkoitus 9" TEXT,
    "PRT 10" TEXT,
    "Käyttötila 10" TEXT,
    "Käyttötarkoitus 10" TEXT,
    "PRT 11" TEXT,
    "Käyttötila 11" TEXT,
    "Käyttötarkoitus 11" TEXT,
    "PRT 12" TEXT,
    "Käyttötila 12" TEXT,
    "Käyttötarkoitus 12" TEXT,
    "PRT 13" TEXT,
    "Käyttötila 13" TEXT,
    "Käyttötarkoitus 13" TEXT,
    "PRT 14" TEXT,
    "Käyttötila 14" TEXT,
    "Käyttötarkoitus 14" TEXT,
    "PRT 15" TEXT,
    "Käyttötila 15" TEXT,
    "Käyttötarkoitus 15" TEXT,
    "PRT 16" TEXT,
    "Käyttötila 16" TEXT,
    "Käyttötarkoitus 16" TEXT,
    "PRT 17" TEXT,
    "Käyttötila 17" TEXT,
    "Käyttötarkoitus 17" text       
);

INSERT INTO tmp_report_result
SELECT * FROM jkr.print_report(
    :'check_date',
    CASE WHEN :'municipality' = '*' THEN NULL ELSE :'municipality' END,
    :'count_apartments',
    CASE WHEN :'taajama_size' = 10000 THEN TRUE ELSE NULL END,
    CASE WHEN :'taajama_size' = 200 THEN TRUE ELSE NULL END,
    :'kohde_tyyppi_id',
);

:copy_command
