ALTER TABLE jkr.taajama
DROP COLUMN tilastokeskus_id,
DROP COLUMN nimi_sv,
DROP COLUMN paivitetty,
ADD COLUMN taajama_id smallint,
ADD COLUMN alkupvm date NOT NULL,
ADD COLUMN loppupvm date,
ADD COLUMN voimassaolo daterange GENERATED ALWAYS AS (daterange(coalesce(alkupvm, '-infinity'), coalesce(loppupvm, 'infinity'), '[]')) STORED;
