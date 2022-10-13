ALTER TABLE jkr.osapuoli
    ADD COLUMN henkilotunnus text;

CREATE INDEX idx_osapuoli_henkilotunnus ON jkr.osapuoli USING btree (henkilotunnus);
CREATE INDEX idx_osapuoli_nimi ON jkr.osapuoli USING btree (nimi);
CREATE INDEX idx_osapuoli_katuosoite ON jkr.osapuoli USING btree (katuosoite);
CREATE INDEX idx_osapuoli_postitoimipaikka ON jkr.osapuoli USING btree (postitoimipaikka);
CREATE INDEX idx_osapuoli_postinumero ON jkr.osapuoli USING btree (postinumero);
CREATE INDEX idx_osapuoli_erikoisosoite ON jkr.osapuoli USING btree (erikoisosoite);
