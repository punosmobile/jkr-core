
-- ddl-end --
COMMENT ON TABLE jkr.velvoitemalli IS E'Taulu, joka sisältää eri velvoitteet, ja niiden voimassaoloajan. Kullakin velvoitteella on näkymän ja funktion nimet, joilla velvoitteen täyttymistä voidaan seurata.';
-- ddl-end --
COMMENT ON COLUMN jkr.velvoitemalli.saanto IS E'Näkymän nimi, joka palauttaa kohteet, joita tämä velvoite koskee. Näkymän tulee sijaita "jkr"-skeemassa.';
-- ddl-end --
COMMENT ON COLUMN jkr.velvoitemalli.tayttymissaanto IS E'Funktion, joka palauttaa niiden kohteiden id:t, joilla velvoite täyttyy, nimi.\nFunktio ottaa parametrina päivämäärän, jona velvoitteen täyttymistä tutkitaan.';
-- ddl-end --
COMMENT ON COLUMN jkr.velvoitemalli.alkupvm IS E'Velvoitteen alkupäivämäärä. Velvoitetta ei muodosteta kohteille, jotka eivät ole olleet olemassa velvoitteen voimassaolon aikana.';
-- ddl-end --
COMMENT ON COLUMN jkr.velvoitemalli.loppupvm IS E'Velvoitteen loppupäivämäärä. Velvoitetta ei muodosteta kohteille, jotka eivät ole olleet olemassa velvoitteen voimassaolon aikana.';
-- ddl-end --
COMMENT ON COLUMN jkr.velvoitemalli.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä velvoitteen voimassaololle.\nHelpottaa aikavälikyselyitä. Voidaan esimerkiksi tehdä kysely\n```sql\nselect *\nfrom jkr.velvoitemalli\nwhere voimassaolo @> ''2021-1-1''::date\n```\neikä tarvitse tehdä monimutkaista\n```sql\nselect *\nfrom jkr.velvoitemalli\nwhere\n  (alkupvm is null OR alkupvm <= ''2021-1-1''::date`)\n  AND\n  (loppupvm is null OR ''2021-1-1''::date` <= loppupvm)\n```';
-- ddl-end --
COMMENT ON COLUMN jkr.osapuoli.ulkoinen_id IS E'Vierasavain, jonka avulla voidaan yksilöidä ulkoisesta lähteestä tuotavat henkilötiedot. Estää sen, ettei päivittäessä tuoda jo olemassa olevia henkilöitä uudelleen.';
-- ddl-end --
COMMENT ON TABLE jkr.jatteenkuljetusalue IS E'Jätteenkuljetusalueet sisältävä taulu.\nJätteenkuljetusalueiden ulkopuoliset kiinteistöt liittyvät aluejätekeräykseen.';
-- ddl-end --
COMMENT ON TABLE jkr.keskeytys IS E'Urakoitsijoille ilmoitetut alle vuoden keskeytykset.';
-- ddl-end --
COMMENT ON COLUMN jkr.keskeytys.alkupvm IS E'Keskeytyksen alkamispäivämäärä';
-- ddl-end --
COMMENT ON COLUMN jkr.keskeytys.loppupvm IS E'Keskeytyksen päättymispäivämäärä';
-- ddl-end --
COMMENT ON COLUMN jkr.keskeytys.selite IS E'Mahdollinen selite keskeytykselle';
-- ddl-end --
COMMENT ON COLUMN jkr.keskeytys.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä keskeytyksen voimassaololle.\nHelpottaa aikavälikyselyitä. Voidaan esimerkiksi tehdä kysely\n```sql\nselect *\nfrom jkr.keskeytys\nwhere voimassaolo @> ''2021-1-1''::date\n```\neikä tarvitse tehdä monimutkaista\n```sql\nselect *\nfrom jkr.keskeytys\nwhere\n  (alkupvm is null OR alkupvm <= ''2021-1-1''::date`)\n  AND\n  (loppupvm is null OR ''2021-1-1''::date` <= loppupvm)\n```';
-- ddl-end --
COMMENT ON TABLE jkr_koodistot.kohdetyyppi IS E'Koodistotaulu kohteen tyypille.\nKohdetyyppejä: Kiinteistö, Aluekeräyskohde, Pseudo aluekeräyskimppaisäntä';
-- ddl-end --
COMMENT ON TABLE jkr.ulkoinen_asiakastieto IS E'Kohteeseen liittyvää asiakastietoa ulkoisesta lähteestä (Facta, Dynasty, eri urakoitsijat).';
-- ddl-end --
COMMENT ON TABLE jkr_koodistot.osapuolenrooli IS E'Taulu sisältää koodiston kohteen osapuolen rooleille.\nRooleja on tällä hetkellä Asiakas ja Yhteystieto';
-- ddl-end --
COMMENT ON TABLE jkr_koodistot.sopimustyyppi IS E'Koodistotaulu sopimustyypeille.\nSopimustyyppejä: Tyhjennyssopimus, Kimppasopimus, Aluekeräyssopimus';
-- ddl-end --
COMMENT ON VIEW jkr.v_rakennusten_osoitteet IS E'Näkymä joka kokoaa kullekin rakennukselle osoitetauluista tiedot yhteen';
-- ddl-end --
COMMENT ON TABLE jkr.toimialue IS E'Viranomaisen toimialueen aluerajaus kunnittain.\nAluerajauksen avulla valitaan tutkittavaksi ainoastaan ne rakennukset/kiinteistöt, jotka sijaitseat aluerajauksen sisällä.';
-- ddl-end --
COMMENT ON FUNCTION jkr.fix_empty_point() IS E'Triggerifunktio, joka muuntaa Factan Oraclesta lähtöisin olevat POINT(infinity infinity) geometriat NULL:ksi.';
-- ddl-end --
COMMENT ON TRIGGER trg_fix_empty_rakennus_point ON jkr.rakennus IS E'Factan Oraclesta tulevien rakennusgeometrioiden siivousta varten korjataan tyhjät geometriat ennen inserttiä ja updatea.';
-- ddl-end --
COMMENT ON TABLE jkr.viemarointialue IS E'Aluerajaus, jolla on viemäröintiverkosto asennettu.\nKäytetään valitsemaan ne rakennukset, joilla tulisi olla lietteen keräys säiliöt.';
-- ddl-end --
COMMENT ON TABLE jkr.taajama IS E'Taajamien aluerajaus.\nKäytetään biojätteen keräysvelvoitteen selvittämiseen, eli rakennusten jotka sijaitsevat yli 10000 hengen taajamissa (keskustaajamat).';
-- ddl-end --
COMMENT ON COLUMN jkr.taajama.geom IS E'Taajaman aluerajaus';
-- ddl-end --
COMMENT ON VIEW jkr.v_kohteen_osapuolet IS E'Näkymä joka "purkaa" kohteen osapuolten n:n relaation kullekin kohteelle 1:n relaatioksi.';
-- ddl-end --
COMMENT ON TABLE jkr.velvoite_status IS E'Taulu sisältää tallennetut tilanteet kohteen velvollisuuksille.\nVelvoitteen tilanteet voidaan tallentaa tietylle päivämäärälle kyselyllä\n```sql\nselect tallenna_velvoite_status(''2020-3-1'');\n```';
-- ddl-end --
COMMENT ON COLUMN jkr.velvoite_status.pvm IS E'Ajanhetken päivämäärä kun velvollisuuden täyttymistä on tarkistettu.';
-- ddl-end --
COMMENT ON COLUMN jkr.velvoite_status.ok IS E'Täyttyykö velvoite kyseisenä ajanhetkenä.';
-- ddl-end --
COMMENT ON COLUMN jkr.velvoite_status.tallennuspvm IS E'Velvoitteen tilanteen tallennuspäivämäärä.';
-- ddl-end --
COMMENT ON TABLE jkr.kohteen_rakennusehdokkaat IS E'Jos kohteelle ei voida yksiselitteisesti kohdentaa rakennuksia, niin lisätään kohteelle mahdolliset rakennukset tähän tauluun.';
-- ddl-end --
