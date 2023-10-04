set client_encoding = 'latin1';
begin;
create temporary table tmp_posti_pcf(
    data text
) on commit drop;

\copy tmp_posti_pcf FROM './data/test_data_import/PCF_20230921.dat' DELIMITER AS '|'

create temporary table tmp_posti_pcf_formatted(
    postinumero char(5),
    nimi_fi text,
    nimi_sv text,
    kuntakoodi char(3),
    kuntanimi_fi text,
    kuntanimi_sv text
) on commit drop;
INSERT INTO tmp_posti_pcf_formatted(postinumero, nimi_fi, nimi_sv, kuntakoodi, kuntanimi_fi, kuntanimi_sv)
SELECT
    substring(data, 14, 5) postinumero,
    trim(substring(data, 19, 30)) nimi_fi,
    trim(substring(data, 49, 30)) nimi_sv,
    substring(data, 177, 3) kuntakoodi,
    trim(substring(data, 180, 20)) kuntanimi_fi,
    trim(substring(data, 200, 20)) kuntanimi_sv
FROM tmp_posti_pcf
;
insert into jkr_osoite.kunta(koodi, nimi_fi, nimi_sv)
select
  distinct kuntakoodi, kuntanimi_fi, kuntanimi_sv
from tmp_posti_pcf_formatted
on conflict do nothing
;

insert into jkr_osoite.posti(numero, nimi_fi, nimi_se, kunta_koodi)
select distinct postinumero, nimi_fi, nimi_sv, kuntakoodi
from tmp_posti_pcf_formatted
on conflict do nothing
;

commit;
