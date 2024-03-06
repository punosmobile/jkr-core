DROP INDEX uidx_velvoitemalli_selite;

CREATE UNIQUE INDEX uidx_velvoitemalli_saanto_tayttymissaanto_jatetyyppi_id ON jkr.velvoitemalli
USING btree
(
    saanto,
    tayttymissaanto,
    jatetyyppi_id
);
