-- All osoite fields are nullable. Most addresses have all fields.
CREATE UNIQUE INDEX idx_osoite_osoitenumero_katu_id_rakennus_id_posti_numero
    ON jkr.osoite
    (osoitenumero, katu_id, rakennus_id, posti_numero)
    WHERE osoitenumero is not null;

-- Some addresses are missing osoitenumero.
CREATE UNIQUE INDEX idx_osoite_katu_id_rakennus_id_posti_numero
    ON jkr.osoite
    (katu_id, rakennus_id, posti_numero)
    WHERE osoitenumero is null and katu_id is not null;

-- Some addresses are missing katu_id too. All addresses have postinumero.
CREATE UNIQUE INDEX idx_osoite_rakennus_id_posti_numero
    ON jkr.osoite
    (rakennus_id, posti_numero)
    WHERE osoitenumero is null and katu_id is null;

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
