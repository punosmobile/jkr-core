CREATE TEMP TABLE tmp_report_result(
    kohde_id INTEGER,
    tarkastelupvm DATE,
    "Kohteen rakennuksen 1 sijaintikunta" TEXT,
    huoneistolkm BIGINT,
    "yli 10 000 taajama" TEXT,
    "200 asukkaan taajama" TEXT
);

INSERT INTO tmp_report_result
SELECT * FROM jkr.print_report(
    :'check_date',
    CASE WHEN :'municipality' = '*' THEN NULL ELSE :'municipality' END,
    :'count_apartments',
    CASE WHEN :'taajama_size' = 10000 THEN TRUE ELSE NULL END,
    CASE WHEN :'taajama_size' = 200 THEN TRUE ELSE NULL END
);

\copy tmp_report_result TO C:/tmp/raportti.csv WITH CSV HEADER 
