CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_on_aluekerays_kuljetuksia_tai_sopimuksia(
	daterange)
    RETURNS TABLE(kohde_id integer) 
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
    ROWS 1000
AS $BODY$
SELECT DISTINCT k.id
FROM
	JKR.KOHDE K
	JOIN JKR.KULJETUS KU ON KU.KOHDE_ID = K.ID
	JOIN jkr.sopimus s ON s.kohde_id = k.id
	JOIN jkr_koodistot.jatetyyppi j ON j.id = KU.jatetyyppi_id OR s.jatetyyppi_id = ku.jatetyyppi_id
WHERE
	j.selite = 'Aluekeräyspiste' AND (s.voimassaolo && $1 OR ku.aikavali && $1)
$BODY$;