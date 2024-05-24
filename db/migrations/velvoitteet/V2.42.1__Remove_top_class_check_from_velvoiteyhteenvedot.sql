DROP FUNCTION jkr.kohteet_joilla_seka_ok_bio_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok_bio_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
        )
    )
    AND k.id IN (
        SELECT kohteet_joilla_bio_puuttuu
        FROM jkr.kohteet_joilla_bio_puuttuu($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_kartonki_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_kartonki_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
        )
    )
    AND k.id IN (
        SELECT kohteet_joilla_bio_enint_4_vk
        FROM jkr.kohteet_joilla_bio_enint_4_vk($1)
    )
    AND NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Kartonki'
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
            AND jt.selite = 'Kartonki'
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
                AND jt.selite = 'Kartonki'
            )   
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_metalli_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_metalli_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
        )
    )
    AND k.id IN (
        SELECT kohteet_joilla_bio_enint_4_vk
        FROM jkr.kohteet_joilla_bio_enint_4_vk($1)
    )
    AND NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Metalli'
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
            AND jt.selite = 'Metalli'
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
                AND jt.selite = 'Metalli'
            )   
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_lasi_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_lasi_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
        )
    )
    AND k.id IN (
        SELECT kohteet_joilla_bio_enint_4_vk
        FROM jkr.kohteet_joilla_bio_enint_4_vk($1)
    )
    AND NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Lasi'
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
            AND jt.selite = 'Lasi'
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
                AND jt.selite = 'Lasi'
            )   
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_muovi_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_muovi_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
        )
    )
    AND k.id IN (
        SELECT kohteet_joilla_bio_enint_4_vk
        FROM jkr.kohteet_joilla_bio_enint_4_vk($1)
    )
    AND NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Muovi'
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
            AND jt.selite = 'Muovi'
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
                AND jt.selite = 'Muovi'
            )   
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_velvoiteyhteenveto_vihrea;
