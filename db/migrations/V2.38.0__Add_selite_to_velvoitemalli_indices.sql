DROP INDEX uidx_velvoitemalli_saanto_tayttymissaanto_jatetyyppi_id;

CREATE UNIQUE INDEX uidx_velvoitemalli_saanto_tayttymissaanto_jatetyyppi_id_selite ON jkr.velvoitemalli
USING btree
(
    saanto,
    tayttymissaanto,
    jatetyyppi_id,
    selite
);