-- LAH-590: Velvoiteyhteenvedon tulos, kun biojäte puuttuu ja sekajätteen
-- tyhjennysväli on väärä.
--
-- Biojätteen erilliskeräysalueella (enintään 4 huoneistoa) voimassa oleva
-- kompostointi-ilmoitus täyttää biojätevelvoitteen. Aiemmin
-- velvoiteyhteenvetomalli id 46 (saanto v_erilliskeraysalueet) palautti
-- tuloksen "Velvoiteyhteenveto biojäte puuttuu" myös biojätealueen
-- kohteille, joilla oli voimassa oleva kompostointi-ilmoitus. Koska id 46:n
-- luokitus oli 1 (sama kuin id 42:n "sekajäte väärä tyhjennysväli"), kohde
-- sai virheellisesti molemmat tulokset rinnakkain.
--
-- Korjaus:
--   * Lisätään täyttymissääntö, joka huomioi kompostoinnin biojätealueella:
--     sekajätteen tyhjennysväli on väärä, voimassa oleva biojätesopimus
--     puuttuu eikä kohteella ole voimassa olevaa kompostointi-ilmoitusta.
--   * Rajataan id 46 koskemaan vain hyötyjätteen erilliskeräysaluetta
--     (vähintään 5 huoneistoa), jolla kompostointi ei täytä
--     biojätevelvoitetta, ja yhtenäistetään sen luokitus muiden
--     "biojäte puuttuu" -mallien kanssa (luokitus 2).
--   * Biojätteen erilliskeräysalueen tapaus mallinnetaan uudella
--     velvoiteyhteenvetomalli-rivillä id 47, joka käyttää alla luotavaa
--     täyttymissääntöä (ks. R__z_Insert_velvoiteyhteenvetomalli.sql).

CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_seka_vaara_tvali_bio_puuttuu_ei_kompostointia(daterange) RETURNS TABLE (kohde_id integer) AS
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
            SELECT kohteet_joilla_bio_puuttuu
            FROM jkr.kohteet_joilla_bio_puuttuu($1)
        )
        AND k.id NOT IN (
            SELECT kohteet_joilla_kompostointi_voimassa
            FROM jkr.kohteet_joilla_kompostointi_voimassa($1)
        )
    );
$$
LANGUAGE SQL STABLE;

-- Rajataan id 46 hyötyjätteen erilliskeräysalueelle ja yhtenäistetään
-- luokitus. Olemassa olevissa kannoissa R__z_Insert_velvoiteyhteenvetomalli.sql
-- ei päivitä riviä (ON CONFLICT DO NOTHING), joten päivitys tehdään tässä.
UPDATE jkr.velvoiteyhteenvetomalli
SET saanto = 'v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue',
    luokitus = 2
WHERE id = 46;
