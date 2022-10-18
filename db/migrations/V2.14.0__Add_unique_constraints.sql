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

-- All osoite fields are nullable. Most addresses have all fields.
-- Is not distinct from is too slow, better delete null and non-null
-- duplicates using separate queries.
DELETE from jkr.osoite duplicate
    WHERE exists (
        select 1 from jkr.osoite where
            osoite.osoitenumero = duplicate.osoitenumero and
            osoite.katu_id = duplicate.katu_id and
            osoite.rakennus_id = duplicate.rakennus_id and
            osoite.posti_numero = duplicate.posti_numero
            and osoite.id < duplicate.id
    );
CREATE UNIQUE INDEX idx_osoite_osoitenumero_katu_id_rakennus_id_posti_numero
    ON jkr.osoite
    (osoitenumero, katu_id, rakennus_id, posti_numero)
    WHERE osoitenumero is not null;

-- Some addresses are missing osoitenumero.
DELETE from jkr.osoite duplicate
    WHERE exists (
        select 1 from jkr.osoite where
            osoite.osoitenumero is null and duplicate.osoitenumero is null and
            osoite.katu_id = duplicate.katu_id and
            osoite.rakennus_id = duplicate.rakennus_id and
            osoite.posti_numero = duplicate.posti_numero
            and osoite.id < duplicate.id
    );
CREATE UNIQUE INDEX idx_osoite_katu_id_rakennus_id_posti_numero
    ON jkr.osoite
    (katu_id, rakennus_id, posti_numero)
    WHERE osoitenumero is null and katu_id is not null and posti_numero is not null;

-- Some addresses are missing katu_id and only have postinumero.
DELETE from jkr.osoite duplicate
    WHERE exists (
        select 1 from jkr.osoite where
            osoite.osoitenumero is null and duplicate.osoitenumero is null and
            osoite.katu_id is null and duplicate.katu_id is null and
            osoite.rakennus_id = duplicate.rakennus_id and
            osoite.posti_numero = duplicate.posti_numero
            and osoite.id < duplicate.id
    );
CREATE UNIQUE INDEX idx_osoite_rakennus_id_posti_numero
    ON jkr.osoite
    (rakennus_id, posti_numero)
    WHERE osoitenumero is null and katu_id is null and posti_numero is not null;

-- Some addresses might only have kunta_id. In this case, only katu_id will exist,
-- pointing to an empty street.
DELETE from jkr.osoite duplicate
    WHERE exists (
        select 1 from jkr.osoite where
            osoite.osoitenumero is null and duplicate.osoitenumero is null and
            osoite.katu_id = duplicate.katu_id and
            osoite.rakennus_id = duplicate.rakennus_id and
            osoite.posti_numero is null and duplicate.posti_numero is null
            and osoite.id < duplicate.id
    );
CREATE UNIQUE INDEX idx_osoite_katu_id_rakennus_id
    ON jkr.osoite
    (katu_id, rakennus_id)
    WHERE osoitenumero is null and katu_id is not null and posti_numero is null;

ALTER TABLE jkr.osapuoli
    ADD UNIQUE (henkilotunnus);

ALTER TABLE jkr.osapuoli
    ADD UNIQUE (ytunnus);

-- People/companies with identical names and addresses must be considered the
-- same if other identification is missing. This is because we are matching
-- incoming incomplete data with name and address alone. However, all osoite
-- fields are again nullable here.
CREATE UNIQUE INDEX idx_osapuoli_nimi_katuosoite_postitoimipaikka_postinumero
    ON jkr.osapuoli
    (nimi, katuosoite, postitoimipaikka, postinumero)
    WHERE
        henkilotunnus is null and
        ytunnus is null and
        katuosoite is not null and
        postitoimipaikka is not null and
        postinumero is not null;

-- Some addresses are missing katuosoite.
CREATE UNIQUE INDEX idx_osapuoli_nimi_postitoimipaikka_postinumero
    ON jkr.osapuoli
    (nimi, postitoimipaikka, postinumero)
    WHERE
        henkilotunnus is null and
        ytunnus is null and
        katuosoite is null and
        postitoimipaikka is not null and
        postinumero is not null;

-- Some addresses are missing katuosoite and postitoimipaikka.
CREATE UNIQUE INDEX idx_osapuoli_nimi_postinumero
    ON jkr.osapuoli
    (nimi, postinumero)
    WHERE
        henkilotunnus is null and
        ytunnus is null and
        katuosoite is null and
        postitoimipaikka is null and
        postinumero is not null;

-- No addresses are currently missing katuosoite and postinumero.
-- This is probably accidental, so better enforce it anyway.
CREATE UNIQUE INDEX idx_osapuoli_nimi_postitoimipaikka
    ON jkr.osapuoli
    (nimi, postinumero)
    WHERE
        henkilotunnus is null and
        ytunnus is null and
        katuosoite is null and
        postitoimipaikka is not null and
        postinumero is null;

-- Some addresses are missing postitoimipaikka.
CREATE UNIQUE INDEX idx_osapuoli_nimi_katuosoite_postinumero
    ON jkr.osapuoli
    (nimi, katuosoite, postinumero)
    WHERE
        henkilotunnus is null and
        ytunnus is null and
        katuosoite is not null and
        postitoimipaikka is null and
        postinumero is not null;

-- Some addresses are missing postinumero and postitoimipaikka.
CREATE UNIQUE INDEX idx_osapuoli_nimi_katuosoite
    ON jkr.osapuoli
    (nimi, katuosoite)
    WHERE
        henkilotunnus is null and
        ytunnus is null and
        katuosoite is not null and
        postitoimipaikka is null and
        postinumero is null;

-- Some addresses are just missing.
CREATE UNIQUE INDEX idx_osapuoli_nimi_unique
    ON jkr.osapuoli
    (nimi)
    WHERE
        henkilotunnus is null and
        ytunnus is null and
        katuosoite is null and
        postitoimipaikka is null and
        postinumero is null;
