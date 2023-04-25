-- Changes rakennuksen_vanhimmat primary key from osapuoli_id to id column.
ALTER TABLE jkr.rakennuksen_vanhimmat
    DROP CONSTRAINT rakennuksen_vanhimmat_pk;

ALTER TABLE jkr.rakennuksen_vanhimmat
    ADD COLUMN id SERIAL UNIQUE NOT NULL;

ALTER TABLE jkr.rakennuksen_vanhimmat
    ADD PRIMARY KEY (id);

-- Same but for rakennuksen_omistajat.
ALTER TABLE jkr.rakennuksen_omistajat
    DROP CONSTRAINT rakennuksen_omistajat_pk;

ALTER TABLE jkr.rakennuksen_omistajat
    ADD COLUMN id SERIAL UNIQUE NOT NULL;

ALTER TABLE jkr.rakennuksen_omistajat
    ADD PRIMARY KEY (id);