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
            AND jt.selite = 'Muovipakkaus'
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
            AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                    AND jt.selite = 'Muovipakkaus'
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
            AND jt.selite = 'Muovipakkaus'
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
            AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
            AND jt.selite = 'Kartonkipakkaus'
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
            AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                    AND jt.selite = 'Kartonkipakkaus'
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
            AND jt.selite = 'Lasipakkaus'
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
            AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                    AND jt.selite = 'Lasipakkaus'
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
            AND jt.selite = 'Lasipakkaus'
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
            AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
            AND jt.selite = 'Kartonkipakkaus'
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
            AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                    AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                    AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                    AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                    AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                    AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                    AND jt.selite = 'Muovipakkaus'
                )   
            )
        )
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
            AND jt.selite = 'Kartonkipakkaus'
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
            AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
            )   
        )
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
                AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Kartonkipakkaus'
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
                    AND jt.selite = 'Kartonkipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
                    AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
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
                    AND jt.selite = 'Muovipakkaus'
                )   
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
            AND jt.selite = 'Lasipakkaus'
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
            AND jt.selite = 'Lasipakkaus'
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
                AND jt.selite = 'Lasipakkaus'
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
            AND jt.selite = 'Muovipakkaus'
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
            AND jt.selite = 'Muovipakkaus'
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
                AND jt.selite = 'Muovipakkaus'
            )   
        )
    );
$$
LANGUAGE SQL STABLE;