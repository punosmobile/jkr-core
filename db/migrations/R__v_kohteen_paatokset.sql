CREATE OR REPLACE VIEW jkr.v_kohteen_viranomaispaatokset
AS
SELECT vp.*, k.id AS kohde_id
FROM jkr.kohde k
JOIN jkr.kohteen_rakennukset kr ON k.id = kr.kohde_id
JOIN jkr.viranomaispaatokset vp ON kr.rakennus_id = vp.rakennus_id;

ALTER VIEW jkr.v_kohteen_viranomaispaatokset OWNER TO jkr_admin;

COMMENT ON VIEW jkr.v_kohteen_viranomaispaatokset IS E'Näkymä, joka sisältää kohteen kaikki viranomaispäätökset QGIS-tarkastelua varten.';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.id IS E'Viranomaispäätöksen yksilöivä tunniste (jkr.viranomaispaatokset.id).';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.paatosnumero IS E'Viranomaispäätöksen päätösnumero.';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.alkupvm IS E'Päätöksen voimassaolon alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.loppupvm IS E'Päätöksen voimassaolon päättymispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä päätöksen voimassaololle.';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.vastaanottaja IS E'Päätöksen vastaanottaja.';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.tyhjennysvali IS E'Päätöksen mukainen tyhjennysväli (tyhjennyskertojen lukumäärä).';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.paatostulos_koodi IS E'Viittaus päätöksen tulokseen (jkr_koodistot.paatostulos).';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.tapahtumalaji_koodi IS E'Viittaus päätöksen tapahtumalajiin (jkr_koodistot.tapahtumalaji).';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.akppoistosyy_id IS E'Viittaus aluekeräyspisteeseen liittyvään poikkeamissyyhyn (jkr_koodistot.akppoistosyy).';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.jatetyyppi_id IS E'Viittaus päätöksen jätetyyppiin (jkr_koodistot.jatetyyppi).';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.rakennus_id IS E'Viittaus rakennukseen, jota päätös koskee.';
COMMENT ON COLUMN jkr.v_kohteen_viranomaispaatokset.kohde_id IS E'Viittaus kohteeseen, jonka rakennusta päätös koskee.';
