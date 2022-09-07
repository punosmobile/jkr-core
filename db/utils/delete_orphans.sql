DELETE FROM jkr.osapuoli op
WHERE NOT EXISTS (
        SELECT
            1
        FROM
            jkr.kohteen_osapuolet ko
        WHERE
            op.id = ko.osapuoli_id)
    AND NOT EXISTS (
        SELECT
            1
        FROM
            jkr.rakennuksen_omistajat ro
        WHERE
            op.id = ro.osapuoli_id)
    AND NOT EXISTS (
        SELECT
            1
        FROM
            jkr.kiinteiston_omistajat ko
        WHERE
            op.id = ko.osapuoli_id)
    AND NOT EXISTS (
        SELECT
            1
        FROM
            jkr.sopimus s
        WHERE
            op.id = s.urakoitsija_osapuoli_id)
    AND NOT EXISTS (
        SELECT
            1
        FROM
            jkr.kuljetus k
        WHERE
            op.id = k.urakoitsija_osapuoli_id);

