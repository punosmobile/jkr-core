-- Do not allow multiple unknown streets per kunta
DELETE from jkr_osoite.katu duplicate
    WHERE exists (
        select 1 from jkr_osoite.katu where
            katu.katunimi_fi is null and duplicate.katunimi_fi is null and
            katu.katunimi_sv is null and duplicate.katunimi_sv is null and
            katu.kunta_koodi = duplicate.kunta_koodi
            and katu.id < duplicate.id
    );
CREATE UNIQUE INDEX idx_katu_kunta
    ON jkr_osoite.katu
    (kunta_koodi)
    WHERE katu.katunimi_fi is null and katu.katunimi_sv is null;

-- Delete all duplicates before adding constraints.
DELETE FROM jkr.osoite
WHERE id IN (
  SELECT id FROM (
    SELECT id, row_number() over (partition by rakennus_id, katu_id, osoitenumero, posti_numero order by id) from jkr.osoite
  ) duplikaatit
  WHERE duplikaatit.row_number > 1
);

-- All osoite fields are nullable. Most addresses have all fields.
CREATE UNIQUE INDEX idx_osoite_osoitenumero_katu_id_rakennus_id_posti_numero
    ON jkr.osoite
    (osoitenumero, katu_id, rakennus_id, posti_numero)
    WHERE osoitenumero is not null;

-- Some addresses are missing osoitenumero.
CREATE UNIQUE INDEX idx_osoite_katu_id_rakennus_id_posti_numero
    ON jkr.osoite
    (katu_id, rakennus_id, posti_numero)
    WHERE osoitenumero is null and katu_id is not null and posti_numero is not null;

-- Some addresses are missing katu_id and only have postinumero.
CREATE UNIQUE INDEX idx_osoite_rakennus_id_posti_numero
    ON jkr.osoite
    (rakennus_id, posti_numero)
    WHERE osoitenumero is null and katu_id is null and posti_numero is not null;

-- Some addresses might only have kunta_id. In this case, only katu_id will exist,
-- pointing to an empty street.
CREATE UNIQUE INDEX idx_osoite_katu_id_rakennus_id
    ON jkr.osoite
    (katu_id, rakennus_id)
    WHERE osoitenumero is null and katu_id is not null and posti_numero is null;

DROP INDEX jkr.idx_osapuoli_henkilotunnus;
CREATE UNIQUE INDEX idx_osapuoli_henkilotunnus ON jkr.osapuoli USING btree (henkilotunnus);

DROP INDEX jkr.idx_osapuoli_ytunnus;
CREATE UNIQUE INDEX idx_osapuoli_ytunnus ON jkr.osapuoli USING btree (henkilotunnus);
