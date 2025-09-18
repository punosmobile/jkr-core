CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia(
	daterange)
    RETURNS TABLE(kohde_id integer) 
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
    ROWS 1000
AS $BODY$
SELECT DISTINCT k.id
FROM
	JKR.KOHDE K
	JOIN JKR.KULJETUS KU ON KU.KOHDE_ID = K.ID
	JOIN jkr.sopimus s ON s.kohde_id = k.id
	JOIN jkr_koodistot.jatetyyppi j ON j.id = KU.jatetyyppi_id OR s.jatetyyppi_id = ku.jatetyyppi_id
WHERE
	j.selite = 'Aluekeräys' AND (s.voimassaolo && $1 OR ku.aikavali && $1)
$BODY$;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_ok(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (
        k.id IN (
            SELECT kohteet_joilla_seka_alle_4_vk
            FROM jkr.kohteet_joilla_seka_alle_4_vk($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_enint_16_vk_bio_on
            FROM jkr.kohteet_joilla_seka_enint_16_vk_bio_on($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_enint_16_vk_kompostointi_ok
            FROM jkr.kohteet_joilla_seka_enint_16_vk_kompostointi_ok($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia
            FROM jkr.kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia($1)
        )
    );
$$
LANGUAGE SQL STABLE;


CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Sekajäte'
        )
    )
    AND NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus sk
        WHERE sk.kohde_id = k.id
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.sopimustyyppi st
            WHERE sk.sopimustyyppi_id = st.id
            AND st.selite = 'Kimppasopimus'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE sk.jatetyyppi_id = jt.id
            AND jt.selite = 'Sekajäte'
        )
        AND sk.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr.sopimus ski
            WHERE ski.kohde_id = sk.kimppaisanta_kohde_id
            AND ski.voimassaolo && $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE ski.jatetyyppi_id = jt.id
                AND jt.selite = 'Sekajäte'
            )   
        )
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_vapauttava_paatos_voimassa
        FROM jkr.kohteet_joilla_vapauttava_paatos_voimassa($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_keskeyttava_paatos_voimassa
        FROM jkr.kohteet_joilla_keskeyttava_paatos_voimassa($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_pidentava_voimassa
        FROM jkr.kohteet_joilla_pidentava_voimassa($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_yli_4_vk_ei_bio
        FROM jkr.kohteet_joilla_seka_yli_4_vk_ei_bio($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_0_tai_yli_16_vk
        FROM jkr.kohteet_joilla_seka_0_tai_yli_16_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok
        FROM jkr.kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok
        FROM jkr.kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_alle_4_vk
        FROM jkr.kohteet_joilla_seka_alle_4_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_enint_16_vk_bio_on
        FROM jkr.kohteet_joilla_seka_enint_16_vk_bio_on($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_enint_16_vk_kompostointi_ok
        FROM jkr.kohteet_joilla_seka_enint_16_vk_kompostointi_ok($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok
        FROM jkr.kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok
        FROM jkr.kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia
        FROM jkr.kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia($1)
    );
$$
LANGUAGE SQL STABLE;