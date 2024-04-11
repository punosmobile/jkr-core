DROP FUNCTION jkr.kohteet_joilla_vapauttava_paatos_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_vapauttava_paatos_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.kohteen_rakennukset kr
        WHERE kr.kohde_id = k.id
        AND EXISTS (
            SELECT 1
            FROM jkr.viranomaispaatokset vp
            WHERE vp.rakennus_id = kr.rakennus_id
            AND vp.voimassaolo && $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.tapahtumalaji tl
                WHERE vp.tapahtumalaji_koodi = tl.koodi
                AND tl.selite IN ('AKP', 'Perusmaksu')
            )
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.paatostulos pt
                WHERE vp.paatostulos_koodi = pt.koodi
                AND pt.selite = 'myönteinen'
            )
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_keskeyttava_paatos_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_keskeyttava_paatos_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.kohteen_rakennukset kr
        WHERE kr.kohde_id = k.id
        AND EXISTS (
            SELECT 1
            FROM jkr.viranomaispaatokset vp
            WHERE vp.rakennus_id = kr.rakennus_id
            AND vp.voimassaolo && $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.tapahtumalaji tl
                WHERE vp.tapahtumalaji_koodi = tl.koodi
                AND tl.selite = 'Keskeyttäminen'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.paatostulos pt
                WHERE vp.paatostulos_koodi = pt.koodi
                AND pt.selite = 'myönteinen'
            )
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_pidentava_voimassa;
CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_pidentava_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.kohteen_rakennukset kr
        WHERE kr.kohde_id = k.id
        AND EXISTS (
            SELECT 1
            FROM jkr.viranomaispaatokset vp
            WHERE vp.rakennus_id = kr.rakennus_id
            AND vp.voimassaolo && $1
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
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_seka_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_yli_4_vk_ei_bio;
CREATE FUNCTION jkr.kohteet_joilla_seka_yli_4_vk_ei_bio(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
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
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = ski.id
                    AND tv.tyhjennysvali > 4
                )
            )
        )
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
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_0_tai_yli_16_vk;
CREATE FUNCTION jkr.kohteet_joilla_seka_0_tai_yli_16_vk(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
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
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = ski.id
                    AND (tv.tyhjennysvali = 0 OR tv.tyhjennysvali > 16)
                )
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
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok;
CREATE FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    k.id NOT IN (
        SELECT kohteet_joilla_vapauttava_paatos_voimassa
        FROM jkr.kohteet_joilla_vapauttava_paatos_voimassa($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_keskeyttava_paatos_voimassa
        FROM jkr.kohteet_joilla_keskeyttava_paatos_voimassa($1)
    )
    AND k.id IN (
        SELECT kohteet_joilla_pidentava_voimassa
        FROM jkr.kohteet_joilla_pidentava_voimassa($1)
    )
    AND EXISTS (
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
        AND EXISTS (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
            WHERE kr.kohde_id = k.id
            AND EXISTS (
                SELECT 1
                FROM jkr.viranomaispaatokset vp
                WHERE vp.rakennus_id = kr.rakennus_id
                AND vp.voimassaolo && $1
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
                    AND tv.tyhjennysvali > vp.tyhjennysvali AND tv.tyhjennysvali > 16
                )
            )
        )
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
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok;
CREATE FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok(daterange) RETURNS TABLE (kohde_id integer) AS 
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
                AND jt.selite = 'Biojäte'
            )   
        )
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
    )   
    AND EXISTS (
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
        AND EXISTS (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
            WHERE kr.kohde_id = k.id
            AND EXISTS (
                SELECT 1
                FROM jkr.viranomaispaatokset vp
                WHERE vp.rakennus_id = kr.rakennus_id
                AND vp.voimassaolo && $1
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
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_alle_4_vk;
CREATE FUNCTION jkr.kohteet_joilla_seka_alle_4_vk(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
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


DROP FUNCTION jkr.kohteet_joilla_seka_enint_16_vk_bio_on;
CREATE FUNCTION jkr.kohteet_joilla_seka_enint_16_vk_bio_on(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
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
            AND s.voimassaolo && $1
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
                    AND jt.selite = 'Biojäte'
                )   
            )
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_enint_16_vk_kompostointi_ok;
CREATE FUNCTION jkr.kohteet_joilla_seka_enint_16_vk_kompostointi_ok(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
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


DROP FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok;
CREATE FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_kompostointi_ok_pidentava_ok(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    k.id IN (
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
    )   
    AND EXISTS (
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
        AND EXISTS (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
            WHERE kr.kohde_id = k.id
            AND EXISTS (
                SELECT 1
                FROM jkr.viranomaispaatokset vp
                WHERE vp.rakennus_id = kr.rakennus_id
                AND vp.voimassaolo && $1
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


DROP FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok;
CREATE FUNCTION jkr.kohteet_joilla_seka_yli_16_vk_bio_on_pidentava_ok(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
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
                    AND jt.selite = 'Biojäte'
                )   
            )
        )
    )
    AND EXISTS (
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
        AND EXISTS (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
            WHERE kr.kohde_id = k.id
            AND EXISTS (
                SELECT 1
                FROM jkr.viranomaispaatokset vp
                WHERE vp.rakennus_id = kr.rakennus_id
                AND vp.voimassaolo && $1
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


DROP FUNCTION jkr.kohteet_joilla_bio_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_bio_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
                AND jt.selite = 'Biojäte'
            )   
        )        
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_bio_0_tai_yli_4_vk
        FROM jkr.kohteet_joilla_bio_0_tai_yli_4_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_bio_enint_4_vk
        FROM jkr.kohteet_joilla_bio_enint_4_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_bio_puuttuu_ei_kompostointia;
CREATE FUNCTION jkr.kohteet_joilla_bio_puuttuu_ei_kompostointia(daterange) RETURNS TABLE (kohde_id integer) AS
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
                AND jt.selite = 'Biojäte'
            )   
        )        
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_bio_0_tai_yli_4_vk
        FROM jkr.kohteet_joilla_bio_0_tai_yli_4_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_bio_enint_4_vk
        FROM jkr.kohteet_joilla_bio_enint_4_vk($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_bio_0_tai_yli_4_vk;
CREATE FUNCTION jkr.kohteet_joilla_bio_0_tai_yli_4_vk(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE s.jatetyyppi_id = jt.id
                AND jt.selite = 'Biojäte'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = s.id
                AND (tv.tyhjennysvali = 0 OR tv.tyhjennysvali > 4)
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
                    AND jt.selite = 'Biojäte'
                )
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = ski.id
                    AND (tv.tyhjennysvali = 0 OR tv.tyhjennysvali > 4)
                )
            )
        )
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_bio_enint_4_vk
        FROM jkr.kohteet_joilla_bio_enint_4_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_bio_enint_4_vk;
CREATE FUNCTION jkr.kohteet_joilla_bio_enint_4_vk(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.sopimus s
        WHERE s.kohde_id = k.id
        AND s.voimassaolo && $1
        AND EXISTS (
            SELECT 1
            FROM jkr_koodistot.jatetyyppi jt
            WHERE s.jatetyyppi_id = jt.id
            AND jt.selite = 'Biojäte'
        )
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali <= 4
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
                AND jt.selite = 'Biojäte'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali <= 4
            )
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_kompostointi_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_kompostointi_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.kompostorin_kohteet kk
        WHERE kk.kohde_id = k.id
        AND EXISTS (
            SELECT 1
            FROM jkr.kompostori ko
            WHERE ko.id = kk.kompostori_id
            AND ko.voimassaolo && $1
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_muovi_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_muovi_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_muovi_yli_12_vk
        FROM jkr.kohteet_joilla_muovi_yli_12_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_muovi_enintaan_12_vk
        FROM jkr.kohteet_joilla_muovi_enintaan_12_vk($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_muovi_yli_12_vk;
CREATE FUNCTION jkr.kohteet_joilla_muovi_yli_12_vk(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE s.jatetyyppi_id = jt.id
                AND jt.selite = 'Muovi'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = s.id
                AND tv.tyhjennysvali > 12
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
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = ski.id
                    AND tv.tyhjennysvali > 12
                )
            )
        )
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_muovi_enintaan_12_vk
        FROM jkr.kohteet_joilla_muovi_enintaan_12_vk($1)
    );    
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_muovi_enintaan_12_vk;
CREATE FUNCTION jkr.kohteet_joilla_muovi_enintaan_12_vk(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
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
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali >= 0
            AND tv.tyhjennysvali <= 12
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
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND tv.tyhjennysvali > 0
                AND tv.tyhjennysvali <= 12
            )
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_kartonki_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_kartonki_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_kartonki_yli_12_vk
        FROM jkr.kohteet_joilla_kartonki_yli_12_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_kartonki_enintaan_12_vk
        FROM jkr.kohteet_joilla_kartonki_enintaan_12_vk($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_kartonki_yli_12_vk;
CREATE FUNCTION jkr.kohteet_joilla_kartonki_yli_12_vk(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE s.jatetyyppi_id = jt.id
                AND jt.selite = 'Kartonki'
            )
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = s.id
                AND tv.tyhjennysvali > 12
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
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = ski.id
                    AND tv.tyhjennysvali > 12
                )
            )
        )
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_kartonki_enintaan_12_vk
        FROM jkr.kohteet_joilla_kartonki_enintaan_12_vk($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_kartonki_enintaan_12_vk;
CREATE FUNCTION jkr.kohteet_joilla_kartonki_enintaan_12_vk(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
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
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali <= 12
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
            AND EXISTS (
                SELECT 1
                FROM jkr.tyhjennysvali tv
                WHERE tv.sopimus_id = ski.id
                AND tv.tyhjennysvali > 0 AND tv.tyhjennysvali <= 12
            )
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_lasi_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_lasi_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_lasi_yli_26_vk
        FROM jkr.kohteet_joilla_lasi_yli_26_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_lasi_enintaan_26_vk
        FROM jkr.kohteet_joilla_lasi_enintaan_26_vk($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_lasi_yli_26_vk;
CREATE FUNCTION jkr.kohteet_joilla_lasi_yli_26_vk(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
            AND EXISTS (
                SELECT 1
                FROM jkr_koodistot.jatetyyppi jt
                WHERE s.jatetyyppi_id = jt.id
                AND jt.selite = 'Lasi'
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
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = ski.id
                    AND tv.tyhjennysvali > 26
                )
            )
        )
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_lasi_enintaan_26_vk
        FROM jkr.kohteet_joilla_lasi_enintaan_26_vk($1)
    );    
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_lasi_enintaan_26_vk;
CREATE FUNCTION jkr.kohteet_joilla_lasi_enintaan_26_vk(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
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


DROP FUNCTION jkr.kohteet_joilla_metalli_puuttuu;
CREATE FUNCTION jkr.kohteet_joilla_metalli_puuttuu(daterange) RETURNS TABLE (kohde_id integer) AS
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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_metalli_yli_26_vk
        FROM jkr.kohteet_joilla_metalli_yli_26_vk($1)
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_metalli_enintaan_26_vk
        FROM jkr.kohteet_joilla_metalli_enintaan_26_vk($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_metalli_yli_26_vk;
CREATE FUNCTION jkr.kohteet_joilla_metalli_yli_26_vk(daterange) RETURNS TABLE (kohde_id integer) AS
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
            AND s.voimassaolo && $1
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
                AND EXISTS (
                    SELECT 1
                    FROM jkr.tyhjennysvali tv
                    WHERE tv.sopimus_id = ski.id
                    AND tv.tyhjennysvali > 26
                )
            )
        )
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_metalli_enintaan_26_vk
        FROM jkr.kohteet_joilla_metalli_enintaan_26_vk($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_metalli_enintaan_26_vk;
CREATE FUNCTION jkr.kohteet_joilla_metalli_enintaan_26_vk(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
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
        AND EXISTS (
            SELECT 1
            FROM jkr.tyhjennysvali tv
            WHERE tv.sopimus_id = s.id
            AND tv.tyhjennysvali > 0
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


DROP FUNCTION jkr.kohteet_joilla_seka_ok;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok(daterange) RETURNS TABLE (kohde_id integer) AS
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
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_ok_kompostointi_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok_kompostointi_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
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
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4(daterange) RETURNS TABLE (kohde_id integer) AS
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
    );
$$
LANGUAGE SQL STABLE;

DROP FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_muut_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_seka_ok_bio_enint_4_muut_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
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
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_vaara_tvali_muut_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_seka_vaara_tvali_muut_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (
        k.id IN (
            SELECT kohteet_joilla_seka_yli_4_vk_ei_bio
            FROM jkr.kohteet_joilla_seka_yli_4_vk_ei_bio($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_0_tai_yli_16_vk
            FROM jkr.kohteet_joilla_seka_0_tai_yli_16_vk($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok($1)
        )
    )
    AND (
        EXISTS (
            SELECT 1
            FROM jkr.sopimus s
            WHERE s.kohde_id = k.id
            AND s.voimassaolo && $1
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
                    AND jt.selite = 'Biojäte'
                )   
            )
        )
    )
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    );   
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_vaara_tvali_bio_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_seka_vaara_tvali_bio_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (
        k.id IN (
            SELECT kohteet_joilla_seka_yli_4_vk_ei_bio
            FROM jkr.kohteet_joilla_seka_yli_4_vk_ei_bio($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_0_tai_yli_16_vk
            FROM jkr.kohteet_joilla_seka_0_tai_yli_16_vk($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok($1)
        )
    )
    AND (
        EXISTS (
            SELECT 1
            FROM jkr.sopimus s
            WHERE s.kohde_id = k.id
            AND s.voimassaolo && $1
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
                    AND jt.selite = 'Biojäte'
                )   
            )
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_vaara_tvali_kompostointi_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_seka_vaara_tvali_kompostointi_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (
        k.id IN (
            SELECT kohteet_joilla_seka_yli_4_vk_ei_bio
            FROM jkr.kohteet_joilla_seka_yli_4_vk_ei_bio($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_0_tai_yli_16_vk
            FROM jkr.kohteet_joilla_seka_0_tai_yli_16_vk($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok($1)
        )
    )
    AND k.id IN (
        SELECT kohteet_joilla_kompostointi_voimassa
        FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_seka_vaara_tvali;
CREATE FUNCTION jkr.kohteet_joilla_seka_vaara_tvali(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (
        k.id IN (
            SELECT kohteet_joilla_seka_yli_4_vk_ei_bio
            FROM jkr.kohteet_joilla_seka_yli_4_vk_ei_bio($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_0_tai_yli_16_vk
            FROM jkr.kohteet_joilla_seka_0_tai_yli_16_vk($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_pidentava_ei_ok($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok
            FROM jkr.kohteet_joilla_seka_yli_16_vk_ei_bio_pidentava_ok($1)
        )
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_bio_vaara_tvali_seka_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_bio_vaara_tvali_seka_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    k.id IN (
        SELECT kohteet_joilla_bio_0_tai_yli_4_vk
        FROM jkr.kohteet_joilla_bio_0_tai_yli_4_vk($1)
    )
    AND (
        EXISTS (
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
    );
$$
LANGUAGE SQL STABLE;


DROP FUNCTION jkr.kohteet_joilla_bio_vaara_tvali_muut_voimassa;
CREATE FUNCTION jkr.kohteet_joilla_bio_vaara_tvali_muut_voimassa(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    k.id IN (
        SELECT kohteet_joilla_bio_0_tai_yli_4_vk
        FROM jkr.kohteet_joilla_bio_0_tai_yli_4_vk($1)
    )
    AND (
        EXISTS (
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
    )
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    )
    AND (
        EXISTS (
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
        )
    );
$$
LANGUAGE SQL STABLE;


CREATE FUNCTION jkr.kohteet_joilla_velvoiteyhteenveto_vihrea(daterange) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    (
        k.id IN (
            SELECT kohteet_joilla_vapauttava_paatos_voimassa
            FROM jkr.kohteet_joilla_vapauttava_paatos_voimassa($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_keskeyttava_paatos_voimassa
            FROM jkr.kohteet_joilla_keskeyttava_paatos_voimassa($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_ok
            FROM jkr.kohteet_joilla_seka_ok($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_ok_kompostointi_voimassa
            FROM jkr.kohteet_joilla_seka_ok_kompostointi_voimassa($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_ok_bio_enint_4
            FROM jkr.kohteet_joilla_seka_ok_bio_enint_4($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_ok_bio_enint_4_muut_voimassa
            FROM jkr.kohteet_joilla_seka_ok_bio_enint_4_muut_voimassa($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_vaara_tvali_muut_voimassa
            FROM jkr.kohteet_joilla_seka_vaara_tvali_muut_voimassa($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_vaara_tvali_bio_voimassa
            FROM jkr.kohteet_joilla_seka_vaara_tvali_bio_voimassa($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_vaara_tvali_kompostointi_voimassa
            FROM jkr.kohteet_joilla_seka_vaara_tvali_kompostointi_voimassa($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_seka_vaara_tvali
            FROM jkr.kohteet_joilla_seka_vaara_tvali($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_bio_vaara_tvali_seka_voimassa
            FROM jkr.kohteet_joilla_bio_vaara_tvali_seka_voimassa($1)
        ) OR
        k.id IN (
            SELECT kohteet_joilla_bio_vaara_tvali_muut_voimassa
            FROM jkr.kohteet_joilla_bio_vaara_tvali_muut_voimassa($1)
        )
    );
$$
LANGUAGE SQL STABLE;


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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_velvoiteyhteenveto_vihrea
        FROM jkr.kohteet_joilla_velvoiteyhteenveto_vihrea($1)
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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_velvoiteyhteenveto_vihrea
        FROM jkr.kohteet_joilla_velvoiteyhteenveto_vihrea($1)
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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_velvoiteyhteenveto_vihrea
        FROM jkr.kohteet_joilla_velvoiteyhteenveto_vihrea($1)
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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_velvoiteyhteenveto_vihrea
        FROM jkr.kohteet_joilla_velvoiteyhteenveto_vihrea($1)
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
    )
    AND k.id NOT IN (
        SELECT kohteet_joilla_velvoiteyhteenveto_vihrea
        FROM jkr.kohteet_joilla_velvoiteyhteenveto_vihrea($1)
    );
$$
LANGUAGE SQL STABLE;
