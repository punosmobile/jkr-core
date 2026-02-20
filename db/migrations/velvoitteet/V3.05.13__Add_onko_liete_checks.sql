CREATE OR REPLACE FUNCTION jkr.kohteet_joilla_kompostointi_voimassa(date) RETURNS TABLE (kohde_id integer) AS
$$
SELECT DISTINCT k.id
FROM
    jkr.kohde k
WHERE
    EXISTS (
        SELECT 1
        FROM jkr.kompostorin_kohteet kk
        WHERE kk.kohde_id = k.id
        AND EXISTS (
            SELECT 1
            FROM jkr.kompostori ko
            WHERE ko.id = kk.kompostori_id
            AND ko.voimassaolo @> $1
        )
    );
$$
LANGUAGE SQL STABLE;


CREATE OR REPLACE VIEW jkr.v_kohteen_kompostorin_tiedot AS
SELECT 
    ROW_NUMBER() OVER () AS gid,
    kk.kohde_id,
    kk.kompostori_id,
    k.alkupvm,
    k.loppupvm,
    k.voimassaolo,
    k.onko_kimppa,
    k.osoite_id,
    k.osapuoli_id
FROM 
    jkr.kompostorin_kohteet kk
    INNER JOIN jkr.kompostori k ON kk.kompostori_id = k.id
WHERE k.onko_liete IS NOT TRUE;

CREATE OR REPLACE FUNCTION JKR.TESTIDATAN_TARKISTUS () RETURNS TABLE (
	RAKENNUKSET_YHDELLA_KOHTEELLA TEXT,
	KOMPOSTORIEN_KOHTEET_MUODOSTUVAT TEXT,
	KOMPOSTORIT_ILMAN_KOHTEITA TEXT,
	PAATTYNEET_KOHTEET_RAKENNUKSILLA TEXT,
	PAATTYNEET_RAKENNUKSET_KOHTEILLA TEXT,
	ASUINKIINTEISTO_KOHDETYYPPI_OIKEIN TEXT,
	MUU_KOHDETYYPPI_OIKEIN TEXT,
	KOHTEELLA_ON_VELVOITEYHTEENVETO_JOS_ON_VELVOITE TEXT,
	VELVOITESTATUKSEN_TULEE_OLLA_OK_JATELAJIN_VELVOITTEISTA TEXT
) AS $$
SELECT
	(
		SELECT
			COUNT(*)
		FROM
			JKR.RAKENNUKSET_USEALLA_KOHTEELLA ()
	) = 0 AS "Rakennukset ilman useaa kohdetta",
	(
		SELECT
			COUNT(*)
		FROM
			JKR.KOMPOSTORIN_KOHTEET
            JOIN JKR.KOMPOSTORI K ON K.ID = KOMPOSTORIN_KOHTEET.KOMPOSTORI_ID
        WHERE K.ONKO_LIETE IS NOT TRUE
	) >= 4000 AS "kk_maara",
	(
		SELECT
			COUNT(*)
		FROM
			JKR.KOMPOSTORI K
			LEFT JOIN JKR.KOMPOSTORIN_KOHTEET KK ON KK.KOMPOSTORI_ID = K.ID
		WHERE
			KK.KOHDE_ID IS NULL
	) = 0 AS "Ei orpoja kompostoreja",
	(
		SELECT
			COUNT(*)
		FROM
			JKR.RAKENNUKSET_PAATTYNEILLA_KOHTEILLA ()
	) = 0 AS "Ei Rakennusta paattyneessä kohteessa",
	(
		SELECT
			COUNT(*)
		FROM
			JKR.KOHTEET_PAATTYNEILLA_RAKENNUKSILLA ()
	) = 0 AS "Ei kohdetta päättyneellä rakennuksella",
	(
		SELECT
			COUNT(*)
		FROM
			JKR.MUU_KOHTEET_VAARILLA_OMINAISUUKSILLA ()
	) = 0 AS "Ei muita kohteita asuinkiinteistökriteerien kohteilla",
	(
		SELECT
			COUNT(*)
		FROM
			JKR.ASUINKIINTEISTO_KOHTEET_VAARILLA_OMINAISUUKSILLA ()
	) = 0 AS "EI Asuinkiinteistöä ilman oikeita kriteereitä",
	(
		SELECT
			COUNT(*)
		FROM
			JKR.Velvoitteella_ei_ole_yhteenvetoa ()
	) = 0 AS "Velvoitteilla on yhteenveto",
	( -- At least one velvoite status ok=true per kohde/jätelaji, currently 160 exceptions in test data
		SELECT
			COUNT(*)
		FROM
			JKR.velvoite_toteutumatta_jatelajeittain ()
	) <= 160 AS "Vähintään yksi toteutunut velvoite kohteella per jätelaji"
$$ LANGUAGE SQL STABLE;