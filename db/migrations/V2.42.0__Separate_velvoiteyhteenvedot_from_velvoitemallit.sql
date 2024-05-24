CREATE TABLE jkr.velvoiteyhteenvetomalli (
    id integer UNIQUE,
    selite text,
    saanto text,
    tayttymissaanto text,
    alkupvm date,
    loppupvm date,
    voimassaolo daterange GENERATED ALWAYS AS (daterange(alkupvm, loppupvm, '[]'::text)) STORED,
    kuvaus text NOT NULL,
    luokitus integer NOT NULL,
    CONSTRAINT velvoiteyhteenvetomalli_pk PRIMARY KEY (id)
);

COMMENT ON TABLE jkr.velvoiteyhteenvetomalli
    IS 'Taulu, joka sisältää eri velvoiteyhteenvedot, ja niiden voimassaoloajan. Kullakin yhteenvedolla on näkymän ja funktion nimet, joilla velvoitteen täyttymistä voidaan seurata.';

COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.selite
    IS 'Kuvaus tietyn tunnisteen omaavasta velvoiteyhteenvedosta';
COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.saanto
    IS 'Näkymän nimi, joka palauttaa kohteet, joita tämä yhteenveto koskee. Näkymän tulee sijaita "jkr"-skeemassa.';
COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.tayttymissaanto
    IS 'Funktion, joka palauttaa niiden kohteiden id:t, joilla yhteenveto täyttyy, nimi. Funktio ottaa parametrina päivämäärän, jona yhteenvedon täyttymistä tutkitaan.';
COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.alkupvm
    IS 'Yhteenvedon alkupäivämäärä. Yhteenvetoa ei muodosteta kohteille, jotka eivät ole olleet olemassa yhteenvedon voimassaolon aikana.';
COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.loppupvm
    IS 'Yhteenvedon loppupäivämäärä. Yhteenvetoa ei muodosteta kohteille, jotka eivät ole olleet olemassa yhteenvedon voimassaolon aikana.';
COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.voimassaolo
    IS 'Automaattisesti luotu aikaväli-kenttä yhteenvedon voimassaololle.';
COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.kuvaus
    IS 'Velvoiteyhteenvedon selitettä pidempi kuvaus.';
COMMENT ON COLUMN jkr.velvoiteyhteenvetomalli.luokitus
    IS 'Velvoiteyhteenvedon luokitus. Mitä pienempi arvo, sitä korkeamman luokituksen yhteenveto saa. Kohde vain sen yhteenvedon tai ne yhteenvedot, joilla on korkein luokitus.';

CREATE INDEX idx_velvoiteyhteenvetomalli_luokitus ON jkr.velvoiteyhteenvetomalli
USING btree (luokitus);

CREATE UNIQUE INDEX uidx_velvoiteyhteenvetomalli_saanto_tayttymissaanto ON jkr.velvoiteyhteenvetomalli
USING btree
(
    saanto,
    tayttymissaanto
);

DELETE FROM jkr.velvoitemalli;

CREATE TABLE jkr.velvoiteyhteenveto (
    id serial NOT NULL,
    kohde_id integer NOT NULL,
    velvoiteyhteenvetomalli_id integer NOT NULL,
    CONSTRAINT velvoiteyhteenveto_pk PRIMARY KEY (id),
    CONSTRAINT kohde_fk FOREIGN KEY (kohde_id)
        REFERENCES jkr.kohde (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT velvoiteyhteenvetomalli_fk FOREIGN KEY (velvoiteyhteenvetomalli_id)
        REFERENCES jkr.velvoiteyhteenvetomalli (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

COMMENT ON TABLE jkr.velvoiteyhteenveto
    IS 'Taulu, joka sisältää kohteeseen liittyvät velvoiteyhteenvedot';

CREATE INDEX idx_velvoiteyhteenveto_velvoiteyhteenvetomalli_id ON jkr.velvoiteyhteenveto
USING btree (velvoiteyhteenvetomalli_id);

CREATE UNIQUE INDEX uidx_velvoiteyhteenveto_kohde_id_velvoiteyhteenvetomalli_id ON jkr.velvoiteyhteenveto
USING btree
(
    kohde_id,
    velvoiteyhteenvetomalli_id
);

CREATE TABLE jkr.velvoiteyhteenveto_status (
    id serial NOT NULL,
    ok boolean NOT NULL,
    velvoiteyhteenveto_id integer NOT NULL,
    tallennuspvm date NOT NULL,
    jakso daterange NOT NULL,
    CONSTRAINT velvoiteyhteenveto_status_pk PRIMARY KEY (id),
    CONSTRAINT velvoiteyhteenveto_fk FOREIGN KEY (velvoiteyhteenveto_id)
        REFERENCES jkr.velvoiteyhteenveto (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

COMMENT ON TABLE jkr.velvoiteyhteenveto_status
    IS 'Taulu sisältää tallennetut tilanteet kohteen velvoiteyhteenvedoille.';
COMMENT ON COLUMN jkr.velvoiteyhteenveto_status.ok
    IS 'Täyttyykö velvoiteyhteenveto kyseisellä ajanjaksolla.';
COMMENT ON COLUMN jkr.velvoiteyhteenveto_status.tallennuspvm
    IS 'Velvoiteyhteenvedon tilanteen tallennuspäivämäärä.';
COMMENT ON COLUMN jkr.velvoiteyhteenveto_status.jakso
    IS 'Ajanjakso, jolla velvoiteyhteenvedon täyttyminen on tarkistettu.';

CREATE INDEX idx_velvoiteyhteenveto_status_velvoiteyhteenveto_id ON jkr.velvoiteyhteenveto_status
USING btree(velvoiteyhteenveto_id);

CREATE UNIQUE INDEX uidx_velvoiteyhteenveto_status_velvoiteyhteenveto_id_jakso ON jkr.velvoiteyhteenveto_status
USING btree
(
    velvoiteyhteenveto_id, jakso
);

CREATE OR REPLACE VIEW jkr.v_velvoiteyhteenveto_status AS
SELECT id,
    lower(jakso) || ' - ' || upper(jakso) AS jakso,
    ok,
    velvoiteyhteenveto_id,
    tallennuspvm
FROM jkr.velvoiteyhteenveto_status;
