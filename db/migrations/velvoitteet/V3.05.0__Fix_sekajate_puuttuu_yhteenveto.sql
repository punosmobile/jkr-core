
-- Luodaan näkymä joka käyttää kohteet_joilla_seka_puuttuu() funktiota
-- Käytetään viimeisintä kvartaalia (nykyhetki) parametrina
CREATE OR REPLACE VIEW jkr.v_kohteet_joilla_seka_puuttuu AS
SELECT kohde_id AS id
FROM jkr.kohteet_joilla_seka_puuttuu(
    daterange(
        (DATE_TRUNC('quarter', CURRENT_DATE) - INTERVAL '6 months')::date,
        (DATE_TRUNC('quarter', CURRENT_DATE) + INTERVAL '3 months' - INTERVAL '1 day')::date
    )
);

-- Päivitetään yhteenvetomalli 34 käyttämään uutta näkymää
UPDATE jkr.velvoiteyhteenvetomalli
SET saanto = 'v_kohteet_joilla_seka_puuttuu'
WHERE id = 34;