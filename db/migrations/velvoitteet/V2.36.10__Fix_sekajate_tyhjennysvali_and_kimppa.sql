CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_puuttuu(date) RETURNS TABLE (kohde_id integer) AS
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
    );
$$
LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_yli_4_vk_ei_bio(date) RETURNS TABLE (kohde_id integer) AS
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
            AND jt.selite = 'Sekajäte'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali > 4
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
            AND jt.selite = 'Sekajäte'
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
                AND jt.selite = 'Sekajäte'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND tv.tyhjennysvali > 4
            )
        )
    )
    AND NOT EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo @> $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Biojäte'
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
            AND jt.selite = 'Biojäte'
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
                AND jt.selite = 'Biojäte'
            )   
        )
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
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
    );
$$
LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_0_tai_yli_16_vk(date) RETURNS TABLE (kohde_id integer) AS
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
            AND jt.selite = 'Sekajäte'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND (tv.tyhjennysvali = 0 OR tv.tyhjennysvali > 16)
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
            AND jt.selite = 'Sekajäte'
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
                AND jt.selite = 'Sekajäte'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND (tv.tyhjennysvali = 0 OR tv.tyhjennysvali > 16)
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
    );
$$
LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_alle_4_vk(date) RETURNS TABLE (kohde_id integer) AS
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
            AND jt.selite = 'Sekajäte'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali < 4
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
            AND jt.selite = 'Sekajäte'
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
                AND jt.selite = 'Sekajäte'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali < 4
            )
        )
    );
$$
LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_enint_16_vk_bio_on(date) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (EXISTS
        (
            SELECT 1
            FROM jkr.sopimus s
            WHERE s.kohde_id = k.id
            AND s.voimassaolo @> $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE s.jatetyyppi_id = jt.id
                AND jt.selite = 'Sekajäte'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = s.id
                AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali <= 16
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
                AND jt.selite = 'Sekajäte'
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
                    AND jt.selite = 'Sekajäte'
                )
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = ski.id
                    AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali <= 16
                )
            )
        )
    )
    AND (
        EXISTS (
            SELECT 1
            FROM jkr.sopimus s
            WHERE s.kohde_id = k.id
            AND s.voimassaolo @> $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE s.jatetyyppi_id = jt.id
                AND jt.selite = 'Biojäte'
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
                AND jt.selite = 'Biojäte'
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
                    AND jt.selite = 'Biojäte'
                )   
            )
        )
    );
$$
LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_enint_16_vk_kompostointi_ok(date) RETURNS TABLE (kohde_id integer) AS
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
            AND jt.selite = 'Sekajäte'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali <= 16
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
            AND jt.selite = 'Sekajäte'
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
                AND jt.selite = 'Sekajäte'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali <= 16
            )
        )
    )
    AND k.id IN (
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
    );
$$
LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok(date) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (EXISTS      
        (
            SELECT 1
            FROM jkr.sopimus s
            WHERE s.kohde_id = k.id
            AND s.voimassaolo @> $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE s.jatetyyppi_id = jt.id
                AND jt.selite = 'Biojäte'
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
                AND jt.selite = 'Biojäte'
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
                    AND jt.selite = 'Biojäte'
                )   
            )
        )
    )
    AND EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo @> $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Sekajäte'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
            WHERE kr.kohde_id = k.id
            AND EXISTS (
                SELECT 1
                FROM jkr.viranomaispaatokset vp
                WHERE vp.rakennus_id = kr.rakennus_id
                AND vp.voimassaolo @> $1
                AND EXISTS (
                    SELECT 1
                    FROM jkr_koodistot.tapahtumalaji tl
                    WHERE vp.tapahtumalaji_koodi = tl.koodi
                    AND tl.selite = 'Tyhjennysväli'
                )
                AND EXISTS (
                    SELECT 1
                    FROM jkr_koodistot.paatostulos pt
                    WHERE vp.paatostulos_koodi = pt.koodi
                    AND pt.selite = 'myönteinen'
                )
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = s.id
                    AND tv.tyhjennysvali <= vp.tyhjennysvali AND tv.tyhjennysvali > 16
                )
            )
        )
    );
$$
LANGUAGE SQL STABLE;
