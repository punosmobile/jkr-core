-- Remove old primary_key constraint.
ALTER TABLE jkr.rakennuksen_vanhimmat
    DROP CONSTRAINT rakennuksen_vanhimmat_pk;

-- Remove old index and unique indexes.
DROP INDEX idx_rakennuksen_vanhimmat_rakennus_id;
DROP INDEX uidx_rakennuksen_vanhimmat_rakennus_id;
DROP INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain;
DROP INDEX uidx_rakennuksen_vanhimmat_huoneistonumero;
DROP INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain_huoneistonumero;
DROP INDEX uidx_rakennuksen_vanhimmat_huoneistonumero_jakokirjain;
DROP INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain_huoneistonumero_jak;

-- Add new id column, set as the new primary key.
ALTER TABLE jkr.rakennuksen_vanhimmat
    ADD COLUMN id SERIAL UNIQUE NOT NULL;

ALTER TABLE jkr.rakennuksen_vanhimmat
    ADD PRIMARY KEY (id);

-- Replace old index and unique indexes with updated ones.
CREATE INDEX idx_rakennuksen_vanhimmat ON jkr.rakennuksen_vanhimmat
USING btree
(
    rakennus_id,
    osapuoli_id,
    alkupvm
);

-- Some vanhimmat have no extra fields
CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_yksi_huoneisto
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, osapuoli_id, alkupvm)
    WHERE huoneistokirjain is null and huoneistonumero is null and jakokirjain is null;

-- Some vanhimmat have one extra field
CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, osapuoli_id, huoneistokirjain, alkupvm)
    WHERE huoneistokirjain is not null and huoneistonumero is null and jakokirjain is null;

CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistonumero
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, osapuoli_id, huoneistonumero, alkupvm)
    WHERE huoneistokirjain is null and huoneistonumero is not null and jakokirjain is null;

-- Some vanhimmat have two extra fields
CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain_huoneistonumero
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, alkupvm)
    WHERE huoneistokirjain is not null and huoneistonumero is not null and jakokirjain is null;

CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistonumero_jakokirjain
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, osapuoli_id, huoneistonumero, jakokirjain, alkupvm)
    WHERE huoneistokirjain is null and huoneistonumero is not null and jakokirjain is not null;

-- Some vanhimmat have all fields
CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain_huoneistonumero_jakokirjain
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm)
    WHERE huoneistokirjain is not null and huoneistonumero is not null and jakokirjain is not null;

-- Remove old primary key.
ALTER TABLE jkr.rakennuksen_omistajat
    DROP CONSTRAINT rakennuksen_omistajat_pk;

-- Create column id and set it as primary key.
ALTER TABLE jkr.rakennuksen_omistajat
    ADD COLUMN id SERIAL UNIQUE NOT NULL;

ALTER TABLE jkr.rakennuksen_omistajat
    ADD PRIMARY KEY (id);

-- Create Unique index for rakennuksen_omistajat, to prevent duplicate entries when updating with DVV-data.
CREATE UNIQUE INDEX uidx_rakennuksen_omistajat
    ON jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id, omistuksen_alkupvm);
