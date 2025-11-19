CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_vaara_tvali_bio_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (
        k.id IN (
            SELECT kohteet_joilla_seka_vaara_tvali
            FROM jkr.kohteet_joilla_seka_vaara_tvali($1)
        )
        AND k.id IN (
            SELECT kohteet_joilla_seka_ok_bio_puuttuu 
            FROM jkr.kohteet_joilla_seka_ok_bio_puuttuu($1)
        )
    );
$$
LANGUAGE SQL STABLE;


CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_aluekeräys_tai_perusmaksu_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (
        k.id IN (
            SELECT kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia
            FROM jkr.kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia($1)
        )
        AND k.id IN (
            SELECT kohteet_joilla_vapauttava_paatos_voimassa 
            FROM jkr.kohteet_joilla_vapauttava_paatos_voimassa($1)
        )
    );
$$
LANGUAGE SQL STABLE;