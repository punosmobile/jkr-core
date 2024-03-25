CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_metalli_puuttuu(date) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo @> $1
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
        AND sk.voimassaolo @> $1
        AND EXISTS (
            SELECT 1
            FROM jkr.sopimus ski
            WHERE ski.kohde_id = sk.kimppaisanta_kohde_id
            AND ski.voimassaolo @> $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE ski.jatetyyppi_id = jt.id
                AND jt.selite = 'Metalli'
            )   
        )
    )
$$
LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_metalli_yli_26_vk(date) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo @> $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Metalli'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali > 26
        )
    )
    OR EXISTS (
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
        AND sk.voimassaolo @> $1
        AND EXISTS (
            SELECT 1
            FROM jkr.sopimus ski
            WHERE ski.kohde_id = sk.kimppaisanta_kohde_id
            AND ski.voimassaolo @> $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE ski.jatetyyppi_id = jt.id
                AND jt.selite = 'Metalli'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND tv.tyhjennysvali > 26
            )
        )
    );
$$
LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_metalli_enintaan_26_vk(date) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo @> $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Metalli'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali >= 0
            AND tv.tyhjennysvali <= 26
        )
    )
    OR EXISTS (
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
        AND sk.voimassaolo @> $1
        AND EXISTS (
            SELECT 1
            FROM jkr.sopimus ski
            WHERE ski.kohde_id = sk.kimppaisanta_kohde_id
            AND ski.voimassaolo @> $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE ski.jatetyyppi_id = jt.id
                AND jt.selite = 'Metalli'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND tv.tyhjennysvali > 0
                AND tv.tyhjennysvali <= 26
            )
        )
    );
$$
LANGUAGE SQL STABLE;
