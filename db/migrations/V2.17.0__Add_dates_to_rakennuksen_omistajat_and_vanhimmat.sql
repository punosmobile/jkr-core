ALTER TABLE jkr.rakennuksen_vanhimmat 
ADD COLUMN alkupvm date;

ALTER TABLE jkr.rakennuksen_vanhimmat
ADD COLUMN loppupvm date;

ALTER TABLE jkr.rakennuksen_omistajat
ADD COLUMN omistuksen_alkupvm date;

ALTER TABLE jkr.rakennuksen_omistajat
ADD COLUMN omistuksen_loppupvm date;
