\echo :csv_path

CREATE TEMP TABLE tmp_report_result(
    kohde_id INTEGER,
    tarkastelupvm_out DATE,
    kunta_out TEXT,
    huoneistomaara_out BIGINT,
    taajama_yli_10000 TEXT,
    taajama_yli_200 TEXT
);

INSERT INTO tmp_report_result
SELECT * FROM jkr.print_report(
    :'check_date',
    :'municipality',
    :'count_apartments',
    :'taajama_size'=10000,
    :'taajama_size'=200
);

\copy tmp_report_result TO C:/tmp/raportti.csv WITH CSV HEADER 
