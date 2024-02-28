CREATE OR REPLACE VIEW jkr.v_kohteen_viranomaispaatokset
AS
SELECT vp.*, k.id AS kohde_id
FROM jkr.kohde k
JOIN jkr.kohteen_rakennukset kr ON k.id = kr.kohde_id
JOIN jkr.viranomaispaatokset vp ON kr.rakennus_id = vp.rakennus_id;

ALTER VIEW jkr.v_kohteen_viranomaispaatokset OWNER TO jkr_admin;

COMMENT ON VIEW jkr.v_kohteen_viranomaispaatokset IS E'Näkymä, joka sisältää kohteen kaikki viranomaispäätökset QGIS-tarkastelua varten.'
