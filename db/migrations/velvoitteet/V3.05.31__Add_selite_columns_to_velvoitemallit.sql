-- LAH-591: Velvoitemalli- ja velvoiteyhteenvetomalli-taulujen kuvauskenttien tarkennukset.
--
-- Tietokantafunktioiden nimien pituudet ovat rajallisia, joten ne eivät yksin
-- kykene sisältämään kaikkia tarvittavia yksityiskohtia. Lisätään tauluihin
-- kentät saannon_selite ja tayttymissaannon_selite, joihin avataan saanto- ja
-- tayttymissaanto-kenttien funktioiden/näkymien toiminta luettavampaan muotoon.
--
-- Itse selitetekstit asetetaan R__z_Insert_velvoitemalli.sql ja
-- R__z_Insert_velvoiteyhteenvetomalli.sql -tiedostoissa, jotta selitteet
-- pysyvät synkassa rivien muiden tietojen kanssa.

ALTER TABLE jkr.velvoitemalli
    ADD COLUMN IF NOT EXISTS saannon_selite text,
    ADD COLUMN IF NOT EXISTS tayttymissaannon_selite text;

COMMENT ON COLUMN jkr.velvoitemalli.saannon_selite
    IS 'Luettava selite saanto-kentän näkymän/funktion toiminnasta. Avaa funktionimen lyhennetyn merkityksen.';
COMMENT ON COLUMN jkr.velvoitemalli.tayttymissaannon_selite
    IS 'Luettava selite tayttymissaanto-kentän funktion toiminnasta. Avaa funktionimen lyhennetyn merkityksen.';

ALTER TABLE jkr.velvoiteyhteenvetomalli
    ADD COLUMN IF NOT EXISTS saannon_selite text,
    ADD COLUMN IF NOT EXISTS tayttymissaannon_selite text;

COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.saannon_selite
    IS 'Luettava selite saanto-kentän näkymän/funktion toiminnasta. Avaa funktionimen lyhennetyn merkityksen.';
COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.tayttymissaannon_selite
    IS 'Luettava selite tayttymissaanto-kentän funktion toiminnasta. Avaa funktionimen lyhennetyn merkityksen.';
