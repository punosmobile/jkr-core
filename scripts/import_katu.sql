set client_encoding = 'latin1';
begin;

create temporary table tmp_posti_baf(
    data text
) on commit drop;
\copy tmp_posti_baf FROM '../data/posti/BAF_20210821.dat' DELIMITER AS '|'

create temporary table tmp_posti_baf_formatted(
    kuntakoodi char(3),
    katunimi_fi text,
    katunimi_sv text
) on commit drop;

INSERT INTO tmp_posti_baf_formatted(kuntakoodi, katunimi_fi, katunimi_sv)
SELECT
    substring(data, 214, 3) kuntakoodi,
    nullif(trim(substring(data, 103, 30)), '') katunimi_fi,
    nullif(trim(substring(data, 133, 30)), '') katunimi_sv
FROM tmp_posti_baf
;

insert into jkr_osoite.katu(kunta_koodi, katunimi_fi, katunimi_sv)
select distinct kuntakoodi, katunimi_fi, katunimi_sv
from tmp_posti_baf_formatted
where katunimi_fi is not null or katunimi_sv is not null
on conflict do nothing
;

commit;
