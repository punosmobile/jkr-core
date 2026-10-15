-- =====================================================================
-- Tietokantadokumentaation täydentäminen (LAH-622)
--
-- Lisätään puuttuvat taulu-, näkymä- ja kenttäkommentit jkr-skeemoihin,
-- jotta /db/documentation -rajapinnan tuottama dokumentaatio on riittävän
-- kattava. Kommentit noudattavat aiempien kommenttien tarkkuutta ja tyyliä.
--
-- Itsestäänselvät surrogaattiavaimet (taulujen oma id-sarake) on jätetty
-- kommentoimatta. Koodisto- ja referenssitaulujen avaimet on kommentoitu
-- siskotaulujen vakiintuneen käytännön mukaisesti.
-- =====================================================================


-- =====================================================================
-- 1. Puuttuvat taulukommentit (skeema jkr)
-- =====================================================================

COMMENT ON TABLE jkr.kompostori IS E'Kohteiden ilmoittamat kompostointitiedot. Yksi kompostori voi palvella useaa kohdetta (kimppakompostointi).';

COMMENT ON TABLE jkr.kompostorin_kohteet IS E'Liitostaulu, joka yhdistää kompostorit niitä käyttäviin kohteisiin. Mahdollistaa saman kompostorin liittämisen useaan kohteeseen.';

COMMENT ON TABLE jkr.rakennuksen_vanhimmat IS E'Rakennuksen vanhimmat asukkaat huoneistoittain (DVV:n väestötietojärjestelmästä). Käytetään kohteiden muodostamiseen ja asukastietojen liittämiseen rakennukseen.';

COMMENT ON TABLE jkr.viemari_liitos IS E'Kohteiden liittymät viemäriverkostoon. Käytetään lietteen jätehuoltovelvoitteiden tarkastelussa.';

COMMENT ON TABLE jkr.viranomaispaatokset IS E'Kohteita ja rakennuksia koskevat viranomaispäätökset, esim. jätehuollon keskeytykset ja erilliskeräysvelvoitteesta poikkeamiset. Yksi rivi vastaa yhtä päätöstä.';


-- =====================================================================
-- 2. Puuttuvat taulukommentit (skeema jkr_koodistot)
-- =====================================================================

COMMENT ON TABLE jkr_koodistot.akppoistosyy IS E'Koodistotaulu aluekeräyspisteeseen (AKP) liittyville poikkeamissyille (esim. pihapiiri, pitkä matka).';

COMMENT ON TABLE jkr_koodistot.paatostulos IS E'Koodistotaulu viranomaispäätösten tuloksille (myönteinen / kielteinen).';

COMMENT ON TABLE jkr_koodistot.rakennusluokka_2018 IS E'Koodistotaulu Tilastokeskuksen Rakennusluokitus 2018 -luokille.';

COMMENT ON TABLE jkr_koodistot.tapahtumalaji IS E'Koodistotaulu viranomaispäätösten tapahtumalajeille (esim. tyhjennysväli, keskeyttäminen, erilliskeräyksestä poikkeaminen).';


-- =====================================================================
-- 3. Puuttuvat taulukommentit (skeema jkr_qgis_projektit)
-- =====================================================================

COMMENT ON TABLE jkr_qgis_projektit.qgis_api_credentials IS E'QGIS-rajapinnan käyttämät tunnistautumistiedot ulkoisiin palveluihin.';


-- =====================================================================
-- 4. Kenttäkommentit: skeema jkr
-- =====================================================================

-- jkr.dvv_poimintapvm
COMMENT ON COLUMN jkr.dvv_poimintapvm.poimintapvm IS E'Päivämäärä, jolloin DVV-aineisto on poimittu (rakennus- ja henkilötietojen ajantasaisuus).';

-- jkr.jatteenkuljetusalue
COMMENT ON COLUMN jkr.jatteenkuljetusalue.nimi IS E'Jätteenkuljetusalueen nimi';

-- jkr.kaivotieto
COMMENT ON COLUMN jkr.kaivotieto.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä kaivotiedon voimassaololle.';
COMMENT ON COLUMN jkr.kaivotieto.luotu IS E'Rivin luontiajankohta';
COMMENT ON COLUMN jkr.kaivotieto.muokattu IS E'Rivin viimeisin muokkausajankohta';

-- jkr.keraysvaline
COMMENT ON COLUMN jkr.keraysvaline.sopimus_id IS E'Viittaus sopimukseen, johon keräysväline liittyy';
COMMENT ON COLUMN jkr.keraysvaline.keraysvalinetyyppi_id IS E'Viittaus keräysvälineen tyyppiin (jkr_koodistot.keraysvalinetyyppi)';
COMMENT ON COLUMN jkr.keraysvaline.kohde_id IS E'Viittaus kohteeseen, jolla keräysväline on käytössä';

-- jkr.keskeytys
COMMENT ON COLUMN jkr.keskeytys.sopimus_id IS E'Viittaus sopimukseen, jota keskeytys koskee';

-- jkr.kohde
COMMENT ON COLUMN jkr.kohde.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi): kiinteistö, aluekeräyskohde tai pseudo aluekeräyskimppaisäntä.';
COMMENT ON COLUMN jkr.kohde.loppumisen_syy IS E'Selite sille, miksi kohteen jätehuoltovelvollisuus on päättynyt';

-- jkr.kohteen_osapuolet
COMMENT ON COLUMN jkr.kohteen_osapuolet.kohde_id IS E'Viittaus kohteeseen';
COMMENT ON COLUMN jkr.kohteen_osapuolet.osapuoli_id IS E'Viittaus osapuoleen';
COMMENT ON COLUMN jkr.kohteen_osapuolet.osapuolenrooli_id IS E'Viittaus osapuolen rooliin kohteessa (jkr_koodistot.osapuolenrooli), esim. asiakas tai yhteystieto.';

-- jkr.kohteen_rakennukset
COMMENT ON COLUMN jkr.kohteen_rakennukset.rakennus_id IS E'Viittaus rakennukseen, joka kuuluu kohteeseen';
COMMENT ON COLUMN jkr.kohteen_rakennukset.kohde_id IS E'Viittaus kohteeseen, johon rakennus kuuluu';

-- jkr.kohteen_rakennusehdokkaat
COMMENT ON COLUMN jkr.kohteen_rakennusehdokkaat.kohde_id IS E'Viittaus kohteeseen';
COMMENT ON COLUMN jkr.kohteen_rakennusehdokkaat.rakennus_id IS E'Viittaus rakennukseen, joka on ehdolla kohteeseen liitettäväksi';

-- jkr.kompostori
COMMENT ON COLUMN jkr.kompostori.alkupvm IS E'Kompostoinnin alkamispäivämäärä';
COMMENT ON COLUMN jkr.kompostori.loppupvm IS E'Kompostoinnin päättymispäivämäärä';
COMMENT ON COLUMN jkr.kompostori.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä kompostoinnin voimassaololle.';
COMMENT ON COLUMN jkr.kompostori.onko_kimppa IS E'Tieto siitä, onko kyseessä usean kohteen yhteinen kimppakompostori';
COMMENT ON COLUMN jkr.kompostori.osoite_id IS E'Viittaus osoitteeseen, jossa kompostori sijaitsee';
COMMENT ON COLUMN jkr.kompostori.osapuoli_id IS E'Viittaus osapuoleen, joka vastaa kompostorista (kompostoinnista ilmoittanut)';
COMMENT ON COLUMN jkr.kompostori.onko_liete IS E'Tieto siitä, kompostoidaanko kompostorissa lietettä (sako- ja umpikaivoliete)';

-- jkr.kompostorin_kohteet
COMMENT ON COLUMN jkr.kompostorin_kohteet.kompostori_id IS E'Viittaus kompostoriin';
COMMENT ON COLUMN jkr.kompostorin_kohteet.kohde_id IS E'Viittaus kohteeseen, joka käyttää kompostoria';

-- jkr.kuljetus
COMMENT ON COLUMN jkr.kuljetus.kohde_id IS E'Viittaus kohteeseen, jota kuljetustapahtuma koskee';
COMMENT ON COLUMN jkr.kuljetus.jatetyyppi_id IS E'Viittaus kuljetetun jätteen tyyppiin (jkr_koodistot.jatetyyppi)';
COMMENT ON COLUMN jkr.kuljetus.tiedontuottaja_tunnus IS E'Kuljetustiedon toimittaneen tiedontuottajan tunnus (jkr_koodistot.tiedontuottaja)';

-- jkr.osapuoli
COMMENT ON COLUMN jkr.osapuoli.osapuolenlaji_koodi IS E'Viittaus osapuolen lajiin (jkr_koodistot.osapuolenlaji), esim. henkilö tai yritys.';
COMMENT ON COLUMN jkr.osapuoli.kunta IS E'Osapuolen kotikunta';
COMMENT ON COLUMN jkr.osapuoli.henkilotunnus IS E'Osapuolen henkilötunnus (vain henkilöasiakkailla)';
COMMENT ON COLUMN jkr.osapuoli.tiedontuottaja_tunnus IS E'Osapuolitiedon toimittaneen tiedontuottajan tunnus';

-- jkr.osoite
COMMENT ON COLUMN jkr.osoite.katu_id IS E'Viittaus kadun nimitietoon (jkr_osoite.katu)';
COMMENT ON COLUMN jkr.osoite.rakennus_id IS E'Viittaus rakennukseen, jolle osoite kuuluu';
COMMENT ON COLUMN jkr.osoite.posti_numero IS E'Osoitteen postinumero (viittaus jkr_osoite.posti)';

-- jkr.rakennuksen_omistajat
COMMENT ON COLUMN jkr.rakennuksen_omistajat.omistuksen_alkupvm IS E'Rakennuksen omistuksen alkamispäivämäärä';
COMMENT ON COLUMN jkr.rakennuksen_omistajat.omistuksen_loppupvm IS E'Rakennuksen omistuksen päättymispäivämäärä';

-- jkr.rakennuksen_vanhimmat
COMMENT ON COLUMN jkr.rakennuksen_vanhimmat.rakennus_id IS E'Viittaus rakennukseen';
COMMENT ON COLUMN jkr.rakennuksen_vanhimmat.osapuoli_id IS E'Viittaus osapuoleen (huoneiston vanhin asukas)';
COMMENT ON COLUMN jkr.rakennuksen_vanhimmat.huoneistokirjain IS E'Huoneiston kirjainosa rakennuksen sisällä (esim. A, B)';
COMMENT ON COLUMN jkr.rakennuksen_vanhimmat.huoneistonumero IS E'Huoneiston numero rakennuksen sisällä';
COMMENT ON COLUMN jkr.rakennuksen_vanhimmat.jakokirjain IS E'Huoneiston jakokirjain, joka tarkentaa huoneiston yksilöinnin';
COMMENT ON COLUMN jkr.rakennuksen_vanhimmat.alkupvm IS E'Asukkuuden alkamispäivämäärä';
COMMENT ON COLUMN jkr.rakennuksen_vanhimmat.loppupvm IS E'Asukkuuden päättymispäivämäärä';

-- jkr.rakennus
COMMENT ON COLUMN jkr.rakennus.rakennuksenkayttotarkoitus_koodi IS E'Viittaus rakennuksen käyttötarkoitukseen (jkr_koodistot.rakennuksenkayttotarkoitus)';
COMMENT ON COLUMN jkr.rakennus.rakennuksenolotila_koodi IS E'Viittaus rakennuksen olotilaan (jkr_koodistot.rakennuksenolotila), esim. käytössä tai käytöstä poistettu.';
COMMENT ON COLUMN jkr.rakennus.kaytossaolotilanteenmuutos_pvm IS E'Päivämäärä, jolloin rakennuksen käytössäolotilanne on viimeksi muuttunut';

-- jkr.sopimus
COMMENT ON COLUMN jkr.sopimus.kimppaisanta_kohde_id IS E'Kimppasopimuksessa viittaus kimppaisäntänä toimivaan kohteeseen';
COMMENT ON COLUMN jkr.sopimus.kohde_id IS E'Viittaus kohteeseen, jota sopimus koskee';
COMMENT ON COLUMN jkr.sopimus.jatetyyppi_id IS E'Viittaus sopimuksen jätetyyppiin (jkr_koodistot.jatetyyppi)';
COMMENT ON COLUMN jkr.sopimus.sopimustyyppi_id IS E'Viittaus sopimustyyppiin (jkr_koodistot.sopimustyyppi), esim. tyhjennys-, kimppa- tai aluekeräyssopimus.';
COMMENT ON COLUMN jkr.sopimus.tiedontuottaja_tunnus IS E'Sopimustiedon toimittaneen tiedontuottajan tunnus';

-- jkr.taajama
COMMENT ON COLUMN jkr.taajama.nimi IS E'Taajaman nimi';
COMMENT ON COLUMN jkr.taajama.vaesto_lkm IS E'Taajaman väkiluku. Käytetään mm. erilliskeräysvelvoitteiden määrittelyssä (10000 asukkaan raja).';
COMMENT ON COLUMN jkr.taajama.taajama_id IS E'Taajaman ulkoinen tunniste lähdeaineistossa (Tilastokeskus)';
COMMENT ON COLUMN jkr.taajama.alkupvm IS E'Taajamarajauksen voimassaolon alkamispäivämäärä';
COMMENT ON COLUMN jkr.taajama.loppupvm IS E'Taajamarajauksen voimassaolon päättymispäivämäärä';
COMMENT ON COLUMN jkr.taajama.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä taajamarajauksen voimassaololle.';

-- jkr.toimialue
COMMENT ON COLUMN jkr.toimialue.nimi IS E'Toimialueen nimi (kunta)';
COMMENT ON COLUMN jkr.toimialue.geom IS E'Toimialueen aluerajauksen geometria';

-- jkr.tyhjennysvali
COMMENT ON COLUMN jkr.tyhjennysvali.sopimus_id IS E'Viittaus sopimukseen, jota tyhjennysväli koskee';
COMMENT ON COLUMN jkr.tyhjennysvali.kertaaviikossa IS E'Tyhjennyskertojen lukumäärä viikossa';

-- jkr.ulkoinen_asiakastieto
COMMENT ON COLUMN jkr.ulkoinen_asiakastieto.tiedontuottaja_tunnus IS E'Asiakastiedon toimittaneen tiedontuottajan tunnus';
COMMENT ON COLUMN jkr.ulkoinen_asiakastieto.kohde_id IS E'Viittaus kohteeseen, johon asiakastieto liittyy';

-- jkr.velvoite
COMMENT ON COLUMN jkr.velvoite.kohde_id IS E'Viittaus kohteeseen, jota velvoite koskee';
COMMENT ON COLUMN jkr.velvoite.velvoitemalli_id IS E'Viittaus velvoitemalliin, jonka perusteella velvoite on muodostettu';
COMMENT ON COLUMN jkr.velvoite.loppupvm IS E'Velvoitteen päättymispäivämäärä';

-- jkr.velvoite_status
COMMENT ON COLUMN jkr.velvoite_status.velvoite_id IS E'Viittaus velvoitteeseen, jonka tilaa rivi kuvaa';

-- jkr.velvoitemalli
COMMENT ON COLUMN jkr.velvoitemalli.jatetyyppi_id IS E'Viittaus velvoitteen jätetyyppiin (jkr_koodistot.jatetyyppi)';
COMMENT ON COLUMN jkr.velvoitemalli.kuvaus IS E'Velvoitemallin käyttäjälle näytettävä kuvaus';
COMMENT ON COLUMN jkr.velvoitemalli.prioriteetti IS E'Velvoitemallin järjestysprioriteetti yhteenvedoissa ja esityksessä';

-- jkr.velvoiteyhteenveto
COMMENT ON COLUMN jkr.velvoiteyhteenveto.kohde_id IS E'Viittaus kohteeseen, jota velvoiteyhteenveto koskee';
COMMENT ON COLUMN jkr.velvoiteyhteenveto.velvoiteyhteenvetomalli_id IS E'Viittaus velvoiteyhteenvetomalliin, jonka perusteella yhteenveto on muodostettu';
COMMENT ON COLUMN jkr.velvoiteyhteenveto.loppupvm IS E'Velvoiteyhteenvedon päättymispäivämäärä';

-- jkr.velvoiteyhteenveto_status
COMMENT ON COLUMN jkr.velvoiteyhteenveto_status.velvoiteyhteenveto_id IS E'Viittaus velvoiteyhteenvetoon, jonka tilaa rivi kuvaa';

-- jkr.viemari_liitos
COMMENT ON COLUMN jkr.viemari_liitos.kohde_id IS E'Viittaus kohteeseen, jota viemäriliitos koskee';
COMMENT ON COLUMN jkr.viemari_liitos.viemariverkosto_alkupvm IS E'Viemäriverkostoon liittymisen alkamispäivämäärä';
COMMENT ON COLUMN jkr.viemari_liitos.viemariverkosto_loppupvm IS E'Viemäriverkostoon liittymisen päättymispäivämäärä';
COMMENT ON COLUMN jkr.viemari_liitos.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä viemäriliitoksen voimassaololle.';
COMMENT ON COLUMN jkr.viemari_liitos.rakennus_prt IS E'Liitokseen liittyvän rakennuksen pysyvä rakennustunnus (PRT)';

-- jkr.viemariverkosto
COMMENT ON COLUMN jkr.viemariverkosto.nimi IS E'Viemäriverkoston nimi';
COMMENT ON COLUMN jkr.viemariverkosto.viemariverkosto_id IS E'Viemäriverkoston ulkoinen tunniste lähdeaineistossa';
COMMENT ON COLUMN jkr.viemariverkosto.alkupvm IS E'Viemäriverkoston voimassaolon alkamispäivämäärä';
COMMENT ON COLUMN jkr.viemariverkosto.loppupvm IS E'Viemäriverkoston voimassaolon päättymispäivämäärä';
COMMENT ON COLUMN jkr.viemariverkosto.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä viemäriverkoston voimassaololle.';

-- jkr.viemarointialue
COMMENT ON COLUMN jkr.viemarointialue.nimi IS E'Viemäröintialueen nimi';
COMMENT ON COLUMN jkr.viemarointialue.geom IS E'Viemäröintialueen aluerajauksen geometria';

-- jkr.viranomaispaatokset
COMMENT ON COLUMN jkr.viranomaispaatokset.paatosnumero IS E'Viranomaispäätöksen päätösnumero';
COMMENT ON COLUMN jkr.viranomaispaatokset.alkupvm IS E'Päätöksen voimassaolon alkamispäivämäärä';
COMMENT ON COLUMN jkr.viranomaispaatokset.loppupvm IS E'Päätöksen voimassaolon päättymispäivämäärä';
COMMENT ON COLUMN jkr.viranomaispaatokset.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä päätöksen voimassaololle.';
COMMENT ON COLUMN jkr.viranomaispaatokset.vastaanottaja IS E'Päätöksen vastaanottaja';
COMMENT ON COLUMN jkr.viranomaispaatokset.tyhjennysvali IS E'Päätöksen mukainen tyhjennysväli (tyhjennyskertojen lukumäärä)';
COMMENT ON COLUMN jkr.viranomaispaatokset.paatostulos_koodi IS E'Viittaus päätöksen tulokseen (jkr_koodistot.paatostulos)';
COMMENT ON COLUMN jkr.viranomaispaatokset.tapahtumalaji_koodi IS E'Viittaus päätöksen tapahtumalajiin (jkr_koodistot.tapahtumalaji)';
COMMENT ON COLUMN jkr.viranomaispaatokset.akppoistosyy_id IS E'Viittaus aluekeräyspisteeseen liittyvään poikkeamissyyhyn (jkr_koodistot.akppoistosyy)';
COMMENT ON COLUMN jkr.viranomaispaatokset.jatetyyppi_id IS E'Viittaus päätöksen jätetyyppiin (jkr_koodistot.jatetyyppi)';
COMMENT ON COLUMN jkr.viranomaispaatokset.rakennus_id IS E'Viittaus rakennukseen, jota päätös koskee';


-- =====================================================================
-- 5. Kenttäkommentit: skeema jkr_koodistot
-- =====================================================================

-- jkr_koodistot.akppoistosyy
COMMENT ON COLUMN jkr_koodistot.akppoistosyy.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';
COMMENT ON COLUMN jkr_koodistot.akppoistosyy.selite IS E'Kuvaus tietyn tunnisteen omaavasta aluekeräyspisteeseen liittyvästä poikkeamissyystä';

-- jkr_koodistot.jatetyyppi
COMMENT ON COLUMN jkr_koodistot.jatetyyppi.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';

-- jkr_koodistot.kaivotietotyyppi
COMMENT ON COLUMN jkr_koodistot.kaivotietotyyppi.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';
COMMENT ON COLUMN jkr_koodistot.kaivotietotyyppi.selite IS E'Kuvaus tietyn tunnisteen omaavasta kaivotietotyypistä';

-- jkr_koodistot.kohdetyyppi
COMMENT ON COLUMN jkr_koodistot.kohdetyyppi.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';

-- jkr_koodistot.paatostulos
COMMENT ON COLUMN jkr_koodistot.paatostulos.koodi IS E'Taulun avaimena toimiva uniikki tekstimuotoinen tunniste';
COMMENT ON COLUMN jkr_koodistot.paatostulos.selite IS E'Kuvaus tietyn tunnisteen omaavasta päätöstuloksesta';

-- jkr_koodistot.rakennusluokka_2018
COMMENT ON COLUMN jkr_koodistot.rakennusluokka_2018.koodi IS E'Taulun avaimena toimiva uniikki tekstimuotoinen tunniste (Rakennusluokitus 2018 -koodi)';
COMMENT ON COLUMN jkr_koodistot.rakennusluokka_2018.selite IS E'Kuvaus tietyn tunnisteen omaavasta rakennusluokasta (Rakennusluokitus 2018)';

-- jkr_koodistot.tapahtumalaji
COMMENT ON COLUMN jkr_koodistot.tapahtumalaji.koodi IS E'Taulun avaimena toimiva uniikki tekstimuotoinen tunniste';
COMMENT ON COLUMN jkr_koodistot.tapahtumalaji.selite IS E'Kuvaus tietyn tunnisteen omaavasta tapahtumalajista';


-- =====================================================================
-- 6. Kenttäkommentit: skeema jkr_osoite
-- =====================================================================

-- jkr_osoite.katu
COMMENT ON COLUMN jkr_osoite.katu.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';
COMMENT ON COLUMN jkr_osoite.katu.kunta_koodi IS E'Viittaus kuntaan (jkr_osoite.kunta), jossa katu sijaitsee';

-- jkr_osoite.posti
COMMENT ON COLUMN jkr_osoite.posti.kunta_koodi IS E'Viittaus kuntaan (jkr_osoite.kunta), johon postinumero kuuluu';


-- =====================================================================
-- 7. Kenttäkommentit: skeema jkr_qgis_projektit
-- =====================================================================

-- jkr_qgis_projektit.qgis_api_credentials
COMMENT ON COLUMN jkr_qgis_projektit.qgis_api_credentials.auth_id IS E'QGIS:n autentikaatiokonfiguraation tunniste (authcfg)';
COMMENT ON COLUMN jkr_qgis_projektit.qgis_api_credentials.service_name IS E'Palvelun nimi, jolle tunnistautumistiedot kuuluvat';
COMMENT ON COLUMN jkr_qgis_projektit.qgis_api_credentials.auth_type IS E'Tunnistautumistavan tyyppi (esim. Basic, OAuth2)';
COMMENT ON COLUMN jkr_qgis_projektit.qgis_api_credentials.auth_config IS E'Tunnistautumisen konfiguraatio ja salaisuudet JSON-muodossa';
COMMENT ON COLUMN jkr_qgis_projektit.qgis_api_credentials.description IS E'Vapaamuotoinen kuvaus tunnistautumistiedosta';
COMMENT ON COLUMN jkr_qgis_projektit.qgis_api_credentials.created_at IS E'Rivin luontiajankohta';
COMMENT ON COLUMN jkr_qgis_projektit.qgis_api_credentials.updated_at IS E'Rivin viimeisin muokkausajankohta';


-- =====================================================================
-- 8. Näkymäkommentit (skeema jkr)
-- =====================================================================

COMMENT ON MATERIALIZED VIEW jkr.nearby_buildings IS E'Esilaskettu pareittainen etäisyystaulu rakennuksista, jotka sijaitsevat enintään 300 metrin päässä toisistaan. Käytetään lähekkäisten rakennusten tunnistamiseen mm. kohteiden muodostuksessa.';
-- HUOM: Materialisoidut näkymät v_kompostorien_kohteet_kolmeviimeista,
-- v_kuljetustietojen_kohteet_kolmeviimeista, v_velvoiteyhteenvetojen_kohteet ja
-- v_velvoitteiden_kohteet luodaan R__-migraatioissa, jotka ajetaan vasta tämän
-- jälkeen. Niiden kommentit on annettu kyseisissä migraatioissa (LAH-622).

COMMENT ON VIEW jkr.v_ei_erilliskeraysalueet IS E'Kohteet, jotka eivät kuulu biojätteen tai hyötyjätteen erilliskeräysvelvoitteen piiriin. Yhdistää enintään 4 huoneiston ei-biojätekohteet ja vähintään 5 huoneiston ei-hyötyjätekohteet.';
COMMENT ON VIEW jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue IS E'Enintään 4 huoneiston kohteet, jotka kuuluvat biojätteen erilliskeräysvelvoitteen piiriin (sijaitsevat vähintään 10000 asukkaan taajamassa). Käytetään jätelain erilliskeräysvelvoitteiden määrittelyyn.';
COMMENT ON VIEW jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue IS E'Enintään 4 huoneiston kohteet, jotka eivät kuulu biojätteen erilliskeräysvelvoitteen piiriin (eivät vähintään 10000 asukkaan taajamassa). Käytetään jätelain erilliskeräysvelvoitteiden määrittelyyn.';
COMMENT ON VIEW jkr.v_erilliskeraysalueet IS E'Kohteet, jotka kuuluvat erilliskeräysvelvoitteen piiriin. Yhdistää enintään 4 huoneiston biojätekohteet ja vähintään 5 huoneiston hyötyjätekohteet.';
COMMENT ON VIEW jkr.v_kohdehaku IS E'Kohteiden hakunäkymä, joka kokoaa kohteen osapuolet, ulkoiset asiakastiedot sekä rakennusten osoite- ja kiinteistötiedot yhteen. Käytetään kohteiden hakuun ja tunnistamiseen.';
COMMENT ON VIEW jkr.v_kohdevelvoitteet_distinct IS E'Kohteen velvoitteet statustietoineen koottuna ja järjestettynä esitystä varten. Sisältää velvoitemallin kuvauksen päättymispäivineen sekä luettavan jaksomerkinnän.';
COMMENT ON VIEW jkr.v_kohdevelvoitteet_status IS E'Apunäkymä kohteen velvoitteille: liittää jokaiseen velvoitteeseen sen tuoreimman statuksen ja velvoitemallin selitteen, kuvauksen sekä voimassaolotiedon. Mukana vain ok-tilaiset velvoitteet.';
COMMENT ON VIEW jkr.v_kohteen_kompostorin_tiedot IS E'Kohteiden ja niihin liittyvien (ei-liete) kompostorien tiedot QGIS-karttatasoa varten. Sisältää kompostorin voimassaolon, kimppatiedon, osoitteen ja osapuolen.';
COMMENT ON VIEW jkr.v_kohteen_osapuolet IS E'Kohteen osapuolet rooleineen yhdistettynä osapuolen tietoihin (nimi, osoite, tunnukset). Apunäkymä kohteen osapuolien hakuun.';
COMMENT ON VIEW jkr.v_kohteen_osapuolet_roolilla IS E'Kohteen osapuolet osapuolenroolin selitteellä täydennettynä. Käytetään osapuolien esittämiseen roolin nimellä QGIS-karttatasolla.';
COMMENT ON VIEW jkr.v_kohteet_ilman_rakennuksia IS E'Kohteet, joihin ei ole liitetty yhtään rakennusta. Käytetään puutteellisten kohteiden tunnistamiseen.';
COMMENT ON VIEW jkr.v_kuljetukset_tiedontuottajalla IS E'Kuljetustapahtumat tiedontuottajan nimellä, jätetyypin selitteellä ja sopimuksen tyhjennysvälillä täydennettynä. Apunäkymä kuljetustietojen tarkasteluun.';
COMMENT ON VIEW jkr.v_sopimus_tiedontuottajalla IS E'Sopimukset tiedontuottajan nimellä sekä jätetyypin ja sopimustyypin selitteillä täydennettynä. Apunäkymä sopimustietojen tarkasteluun.';
COMMENT ON VIEW jkr.v_ulkoinen_asiakastieto_tiedontuottajalla IS E'Ulkoiset asiakastiedot tiedontuottajan nimellä täydennettynä ja JSON-kentästä eritellyt sarakkeet (haltija-, kiinteistö-, kimppa- ja astiatiedot). Käytetään ulkoisesta järjestelmästä tuotujen asiakastietojen tarkasteluun.';
COMMENT ON VIEW jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue IS E'Vähintään 5 huoneiston kohteet, jotka eivät kuulu hyötyjätteen erilliskeräysvelvoitteen piiriin (eivät vähintään 10000 asukkaan taajamassa). Käytetään jätelain erilliskeräysvelvoitteiden määrittelyyn.';
COMMENT ON VIEW jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue IS E'Vähintään 5 huoneiston kohteet, jotka kuuluvat hyötyjätteen erilliskeräysvelvoitteen piiriin (sijaitsevat vähintään 10000 asukkaan taajamassa). Käytetään jätelain erilliskeräysvelvoitteiden määrittelyyn.';
COMMENT ON VIEW jkr.v_velvoite_status IS E'Velvoitteiden statushistoria luettavalla jaksomerkinnällä (alku - loppu), uusin jakso ensin. Apunäkymä velvoitteen tilan tarkasteluun.';
COMMENT ON VIEW jkr.v_velvoiteyhteenveto_status IS E'Velvoiteyhteenvetojen statushistoria luettavalla jaksomerkinnällä (alku - loppu), uusin jakso ensin. Apunäkymä velvoiteyhteenvedon tilan tarkasteluun.';


-- =====================================================================
-- 9. Näkymäsarakkeiden kommentit (skeema jkr)
--
-- Näkymien sarakkeet eivät peri kommentteja lähdetauluista, joten ne
-- kommentoidaan erikseen /db/documentation -kattavuuden vuoksi.
-- Läpivientisarakkeet noudattavat lähdetaulun sanamuotoa; johdetut ja
-- liitetyt sarakkeet on kuvattu lähdeviittauksella.
-- =====================================================================

-- v_bio_hapa_asuinkiinteisto
COMMENT ON COLUMN jkr.v_bio_hapa_asuinkiinteisto.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id; bio-, hapa- tai biohapa-kohdetyypit).';
-- v_biohapa_kohde
COMMENT ON COLUMN jkr.v_biohapa_kohde.id IS E'Biohapa-kohteen yksilöivä tunniste (jkr.kohde.id, kohdetyyppi 6).';
-- v_ei_erilliskeraysalueet
COMMENT ON COLUMN jkr.v_ei_erilliskeraysalueet.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id).';
COMMENT ON COLUMN jkr.v_ei_erilliskeraysalueet.nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_ei_erilliskeraysalueet.geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_ei_erilliskeraysalueet.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_ei_erilliskeraysalueet.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_ei_erilliskeraysalueet.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_ei_erilliskeraysalueet.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi).';
-- v_enint_4_huoneistoa_biojatteen_erilliskeraysalue
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id).';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue.nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue.geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_biojatteen_erilliskeraysalue.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi).';
-- v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id).';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue.nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue.geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_enint_4_huoneistoa_ei_biojatteen_erilliskeraysalue.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi).';
-- v_erilliskeraysalueet
COMMENT ON COLUMN jkr.v_erilliskeraysalueet.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id).';
COMMENT ON COLUMN jkr.v_erilliskeraysalueet.nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_erilliskeraysalueet.geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_erilliskeraysalueet.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_erilliskeraysalueet.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_erilliskeraysalueet.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_erilliskeraysalueet.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi).';
-- v_hapa_kohde
COMMENT ON COLUMN jkr.v_hapa_kohde.id IS E'Hapa-kohteen yksilöivä tunniste (jkr.kohde.id, kohdetyyppi 5).';
-- v_kaivotiedot
COMMENT ON COLUMN jkr.v_kaivotiedot.id IS E'Kaivotiedon yksilöivä tunniste (jkr.kaivotieto.id).';
COMMENT ON COLUMN jkr.v_kaivotiedot.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_kaivotiedot.kohde_nimi IS E'Kohteen nimi (jkr.kohde.nimi).';
COMMENT ON COLUMN jkr.v_kaivotiedot.kaivotietotyyppi_id IS E'Viittaus kaivotietotyyppiin (jkr_koodistot.kaivotietotyyppi).';
COMMENT ON COLUMN jkr.v_kaivotiedot.kaivotietotyyppi IS E'Kaivotietotyypin selite (jkr_koodistot.kaivotietotyyppi.selite).';
COMMENT ON COLUMN jkr.v_kaivotiedot.alkupvm IS E'Kaivotiedon alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kaivotiedot.loppupvm IS E'Kaivotiedon päättymispäivämäärä.';
COMMENT ON COLUMN jkr.v_kaivotiedot.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä kaivotiedon voimassaololle.';
COMMENT ON COLUMN jkr.v_kaivotiedot.tietolahde IS E'Tiedon lähde (Excel-tiedoston Tietolähde-sarake).';
COMMENT ON COLUMN jkr.v_kaivotiedot.tiedontuottaja_tunnus IS E'Tiedontuottajan tunnus.';
COMMENT ON COLUMN jkr.v_kaivotiedot.tiedontuottaja_nimi IS E'Tiedontuottajan nimi.';
COMMENT ON COLUMN jkr.v_kaivotiedot.luotu IS E'Rivin luontiajankohta.';
COMMENT ON COLUMN jkr.v_kaivotiedot.muokattu IS E'Rivin viimeisin muokkausajankohta.';
-- v_kohdehaku
COMMENT ON COLUMN jkr.v_kohdehaku.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_kohdehaku.kohteen_nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_kohdehaku.kohteen_alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_kohdehaku.kohteen_loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_kohdehaku.kohde_geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_kohdehaku.ulkoinen_jarjestelma IS E'Ulkoisen asiakastiedon toimittaneen tiedontuottajan tunnus.';
COMMENT ON COLUMN jkr.v_kohdehaku.ulkoinen_asiakasnumero IS E'Asiakkaan tunniste ulkoisessa järjestelmässä (jkr.ulkoinen_asiakastieto.ulkoinen_id).';
COMMENT ON COLUMN jkr.v_kohdehaku.osapuolenrooli_id IS E'Viittaus osapuolen rooliin kohteessa (jkr_koodistot.osapuolenrooli).';
COMMENT ON COLUMN jkr.v_kohdehaku.osapuoli_nimi IS E'Osapuolen nimi.';
COMMENT ON COLUMN jkr.v_kohdehaku.osapuoli_osoite IS E'Osapuolen katuosoite.';
COMMENT ON COLUMN jkr.v_kohdehaku.osapuoli_postinumero IS E'Osapuolen postinumero.';
COMMENT ON COLUMN jkr.v_kohdehaku.osapuoli_kunta IS E'Osapuolen kotikunta.';
COMMENT ON COLUMN jkr.v_kohdehaku.rakennuksen_prt IS E'Rakennuksen yksilöivä 10-merkkinen rakennustunnus (PRT).';
COMMENT ON COLUMN jkr.v_kohdehaku.rakennuksen_kiinteistotunnus IS E'Rakennuksen tekstimuotoinen kiinteistötunnus.';
COMMENT ON COLUMN jkr.v_kohdehaku.rakennuksen_katunimi IS E'Rakennuksen osoitteen kadun nimi suomeksi.';
COMMENT ON COLUMN jkr.v_kohdehaku.rakennuksen_osoitenumero IS E'Rakennuksen osoitteen talon ja/tai rapun ja/tai asunnon numero.';
COMMENT ON COLUMN jkr.v_kohdehaku.rakennuksen_kunta IS E'Rakennuksen sijaintikunnan nimi suomeksi.';
COMMENT ON COLUMN jkr.v_kohdehaku.rakennuksen_postinumero IS E'Rakennuksen osoitteen postinumero.';
COMMENT ON COLUMN jkr.v_kohdehaku.rakennuksen_postitoimipaikka IS E'Rakennuksen osoitteen postitoimipaikan nimi suomeksi.';
-- v_kohdevelvoitteet_distinct
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.velvoite_id IS E'Velvoitteen yksilöivä tunniste (jkr.velvoite.id).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.kohde_id IS E'Viittaus kohteeseen, jota velvoite koskee.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.velvoitemalli_id IS E'Viittaus velvoitemalliin, jonka perusteella velvoite on muodostettu.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.velvoitemalli_selite IS E'Velvoitemallin selite (jkr.velvoitemalli.selite).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.velvoitemalli_kuvaus IS E'Velvoitemallin kuvaus, johon on liitetty velvoitteen loppupäivämäärä sulkeissa, jos se on määritelty.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.voimassaolo IS E'Velvoitemallin voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.voimassa IS E'Onko velvoitemalli voimassa kuluvana päivänä.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.status_id IS E'Velvoitteen tilarivin tunniste (jkr.velvoite_status.id).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.status_ok IS E'Täyttyykö velvoite tilarivin mukaan.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.status_tallennuspvm IS E'Velvoitteen tilanteen tallennuspäivämäärä.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.status_jakso IS E'Ajanjakso, jolla velvoitteen täyttyminen on tarkistettu (range-tyyppi).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.jakso IS E'Tilarivin tarkistusjakso tekstimuodossa (alku - loppu).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_distinct.nykystatus IS E'Onko tilarivi voimassa kuluvana päivänä (nykyhetken tilanne).';
-- v_kohdevelvoitteet_status
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.velvoite_id IS E'Velvoitteen yksilöivä tunniste (jkr.velvoite.id).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.kohde_id IS E'Viittaus kohteeseen, jota velvoite koskee.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.velvoitemalli_id IS E'Viittaus velvoitemalliin, jonka perusteella velvoite on muodostettu.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.velvoitemalli_selite IS E'Velvoitemallin selite (jkr.velvoitemalli.selite).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.velvoitemalli_kuvaus IS E'Velvoitemallin kuvaus (jkr.velvoitemalli.kuvaus).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.voimassaolo IS E'Velvoitemallin voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.voimassa IS E'Onko velvoitemalli voimassa kuluvana päivänä.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.status_id IS E'Velvoitteen tilarivin tunniste (jkr.velvoite_status.id).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.status_ok IS E'Täyttyykö velvoite tilarivin mukaan.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.status_tallennuspvm IS E'Velvoitteen tilanteen tallennuspäivämäärä.';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.status_jakso IS E'Ajanjakso, jolla velvoitteen täyttyminen on tarkistettu (range-tyyppi).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.nykystatus IS E'Onko tilarivi voimassa kuluvana päivänä (nykyhetken tilanne).';
COMMENT ON COLUMN jkr.v_kohdevelvoitteet_status.velvoite_loppupvm IS E'Velvoitteen päättymispäivämäärä.';
-- v_kohteen_kompostorin_tiedot
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.gid IS E'QGIS:n vaatima juokseva rivitunniste (ei pysyvä).';
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.kohde_id IS E'Viittaus kohteeseen, joka käyttää kompostoria.';
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.kompostori_id IS E'Viittaus kompostoriin.';
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.alkupvm IS E'Kompostoinnin alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.loppupvm IS E'Kompostoinnin päättymispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.voimassaolo IS E'Automaattisesti luotu aikaväli-kenttä kompostoinnin voimassaololle.';
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.onko_kimppa IS E'Tieto siitä, onko kyseessä usean kohteen yhteinen kimppakompostori.';
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.osoite_id IS E'Viittaus osoitteeseen, jossa kompostori sijaitsee.';
COMMENT ON COLUMN jkr.v_kohteen_kompostorin_tiedot.osapuoli_id IS E'Viittaus osapuoleen, joka vastaa kompostorista (kompostoinnista ilmoittanut).';
-- v_kohteen_lietetiedot
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot.id IS E'QGIS:n vaatima juokseva rivitunniste (ei pysyvä).';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot."Viemäriverkostoliittymä alkupvm" IS E'Kohteen viemäriverkostoon liittymisen alkamispäivämäärä (varhaisin voimassa oleva liitos).';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot."Saostussäiliö alkupvm" IS E'Voimassa olevan saostussäiliö-kaivotiedon alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot."Pienpuhdistamo alkupvm" IS E'Voimassa olevan pienpuhdistamo-kaivotiedon alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot."Umpisäiliö alkupvm" IS E'Voimassa olevan umpisäiliö-kaivotiedon alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot."Vain harmaat vedet alkupvm" IS E'Voimassa olevan vain harmaat vedet -kaivotiedon alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot."Kantovesi-ilmoitus alkupvm" IS E'Voimassa olevan kantovesi-kaivotiedon alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot."Lietteen kompostointi-ilmoitus alkupvm" IS E'Lietteen kompostointi-ilmoituksen alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteen_lietetiedot."Lietteen kompostointi-ilmoitus loppupvm" IS E'Lietteen kompostointi-ilmoituksen päättymispäivämäärä.';
-- v_kohteen_osapuolet
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.osapuolenrooli_id IS E'Viittaus osapuolen rooliin kohteessa (jkr_koodistot.osapuolenrooli).';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.id IS E'Osapuolen yksilöivä tunniste (jkr.osapuoli.id).';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.katuosoite IS E'Katuosoite.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.postitoimipaikka IS E'Postitoimipaikka.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.erikoisosoite IS E'Ulkomaanosoitteet.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.ytunnus IS E'Y-tunnus, jos osapuoli on yritys / yhteisö.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.ulkoinen_id IS E'Vierasavain ulkoisesta lähteestä tuotavien henkilötietojen yksilöintiin.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.postinumero IS E'Postinumero.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.osapuolenlaji_koodi IS E'Viittaus osapuolen lajiin (jkr_koodistot.osapuolenlaji).';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.nimi IS E'Osapuolen nimi.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.kunta IS E'Osapuolen kotikunta.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.henkilotunnus IS E'Osapuolen henkilötunnus (vain henkilöasiakkailla).';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet.tiedontuottaja_tunnus IS E'Osapuolitiedon toimittaneen tiedontuottajan tunnus.';
-- v_kohteen_osapuolet_roolilla
COMMENT ON COLUMN jkr.v_kohteen_osapuolet_roolilla.gid IS E'QGIS:n vaatima juokseva rivitunniste (ei pysyvä).';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet_roolilla.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet_roolilla.osapuoli_id IS E'Viittaus osapuoleen.';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet_roolilla.osapuolenrooli_id IS E'Viittaus osapuolen rooliin kohteessa (jkr_koodistot.osapuolenrooli).';
COMMENT ON COLUMN jkr.v_kohteen_osapuolet_roolilla.osapuoli IS E'Osapuolenroolin selite (jkr_koodistot.osapuolenrooli.selite).';
-- v_kohteet_ilman_rakennuksia
COMMENT ON COLUMN jkr.v_kohteet_ilman_rakennuksia.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id).';
COMMENT ON COLUMN jkr.v_kohteet_ilman_rakennuksia.nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_kohteet_ilman_rakennuksia.geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_kohteet_ilman_rakennuksia.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteet_ilman_rakennuksia.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_kohteet_ilman_rakennuksia.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_kohteet_ilman_rakennuksia.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi).';
-- v_kuljetukset_tiedontuottajalla
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.id IS E'Kuljetustapahtuman yksilöivä tunniste (jkr.kuljetus.id).';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.alkupvm IS E'Kuljetustapahtumien raportointiaikavälin alkamispäivämäärä.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.loppupvm IS E'Kuljetustapahtumien raportointiaikavälin päättymispäivämäärä.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.tyhjennyskerrat IS E'Raportointiaikavälin aikana suoritettujen kuljetusten lukumäärä.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.massa IS E'Raportointiaikavälin aikana suoritettujen kuljetusten sisältämä massa kilogrammoina.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.tilavuus IS E'Raportointiaikavälin aikana suoritettujen kuljetusten sisältämä tilavuus litroina.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.aikavali IS E'Kuljetustapahtumien raportointiaikaväli.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.kohde_id IS E'Viittaus kohteeseen, jota kuljetustapahtuma koskee.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.jatetyyppi_id IS E'Viittaus kuljetetun jätteen tyyppiin (jkr_koodistot.jatetyyppi).';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.jatetyyppi_selite IS E'Jätetyypin selite (jkr_koodistot.jatetyyppi.selite).';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.tiedontuottaja_tunnus IS E'Kuljetustiedon toimittaneen tiedontuottajan tunnus.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.tiedontuottaja_nimi IS E'Tiedontuottajan nimi.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.tyhjennysvali IS E'Kuljetukseen liittyvän sopimuksen tyhjennysväli viikoissa.';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.lietteentyhjennyspaiva IS E'Lietteen tyhjennyspäivämäärä (LIETE-aineisto).';
COMMENT ON COLUMN jkr.v_kuljetukset_tiedontuottajalla.jatelaji IS E'Jätteen kuvaus LIETE-aineistosta (jkr.kuljetus.jatteen_kuvaus).';
-- v_rakennusten_osoitteet
COMMENT ON COLUMN jkr.v_rakennusten_osoitteet.id IS E'Osoitteen yksilöivä tunniste (jkr.osoite.id).';
COMMENT ON COLUMN jkr.v_rakennusten_osoitteet.rakennus_id IS E'Viittaus rakennukseen, jolle osoite kuuluu.';
COMMENT ON COLUMN jkr.v_rakennusten_osoitteet.katunimi IS E'Kadun nimi suomeksi (jkr_osoite.katu.katunimi_fi).';
COMMENT ON COLUMN jkr.v_rakennusten_osoitteet.osoitenumero IS E'Katuosoitteeseen liittyvä talon ja/tai rapun ja/tai asunnon numero.';
COMMENT ON COLUMN jkr.v_rakennusten_osoitteet.kunta IS E'Kunnan nimi suomeksi (jkr_osoite.kunta.nimi_fi).';
COMMENT ON COLUMN jkr.v_rakennusten_osoitteet.postinumero IS E'Osoitteen postinumero (jkr_osoite.posti.numero).';
COMMENT ON COLUMN jkr.v_rakennusten_osoitteet.postitoimipaikka IS E'Postitoimipaikan nimi suomeksi (jkr_osoite.posti.nimi_fi).';
-- v_sopimus_tiedontuottajalla
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.id IS E'Sopimuksen yksilöivä tunniste (jkr.sopimus.id).';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.alkupvm IS E'Sopimuksen voimaantulopäivämäärä.';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.loppupvm IS E'Sopimuksen päättymispäivämäärä.';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.voimassaolo IS E'Sopimuksen voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.kimppaisanta_kohde_id IS E'Kimppasopimuksessa viittaus kimppaisäntänä toimivaan kohteeseen.';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.kohde_id IS E'Viittaus kohteeseen, jota sopimus koskee.';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.jatetyyppi_id IS E'Viittaus sopimuksen jätetyyppiin (jkr_koodistot.jatetyyppi).';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.jatetyyppi_selite IS E'Jätetyypin selite (jkr_koodistot.jatetyyppi.selite).';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.jatetyyppi_ewc IS E'Jätetyypin kuusinumeroinen jätekoodi (EWC-koodi).';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.sopimustyyppi_id IS E'Viittaus sopimustyyppiin (jkr_koodistot.sopimustyyppi).';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.sopimustyyppi_selite IS E'Sopimustyypin selite (jkr_koodistot.sopimustyyppi.selite).';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.tiedontuottaja_tunnus IS E'Sopimustiedon toimittaneen tiedontuottajan tunnus.';
COMMENT ON COLUMN jkr.v_sopimus_tiedontuottajalla.tiedontuottaja_nimi IS E'Tiedontuottajan nimi.';
-- v_ulkoinen_asiakastieto_tiedontuottajalla
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.id IS E'Ulkoisen asiakastiedon yksilöivä tunniste (jkr.ulkoinen_asiakastieto.id).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.tiedontuottaja_tunnus IS E'Asiakastiedon toimittaneen tiedontuottajan tunnus.';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.tiedontuottaja_nimi IS E'Tiedontuottajan nimi.';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.ulkoinen_id IS E'Asiakkaan tunniste ulkoisessa järjestelmässä.';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kohde_id IS E'Viittaus kohteeseen, johon asiakastieto liittyy.';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.urakoitsija_id IS E'Urakoitsijan tunniste (JSON-kenttä UrakoitsijaId).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.urakoitsijan_kohde_id IS E'Kohteen tunniste urakoitsijan järjestelmässä (JSON-kenttä UrakoitsijankohdeId).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kiinteistotunnus IS E'Kiinteistötunnus (JSON-kenttä Kiinteistotunnus).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kiinteiston_katuosoite IS E'Kiinteistön katuosoite (JSON-kenttä Kiinteistonkatuosoite).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kiinteiston_posti IS E'Kiinteistön postitiedot (JSON-kenttä Kiinteistonposti).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.haltijan_nimi IS E'Haltijan nimi (JSON-kenttä Haltijannimi).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.haltijan_yhteyshlo IS E'Haltijan yhteyshenkilö (JSON-kenttä Haltijanyhteyshlo).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.haltijan_katuosoite IS E'Haltijan katuosoite (JSON-kenttä Haltijankatuosoite).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.haltijan_posti IS E'Haltijan postitiedot (JSON-kenttä Haltijanposti).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.haltijan_maakoodi IS E'Haltijan maakoodi (JSON-kenttä Haltijanmaakoodi).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.haltijan_ulkomaan_paikkakunta IS E'Haltijan ulkomaan paikkakunta (JSON-kenttä Haltijanulkomaanpaikkakunta).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.pvm_alkaen IS E'Asiakastiedon voimassaolon alkamispäivämäärä (JSON-kenttä Pvmalk).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.pvm_asti IS E'Asiakastiedon voimassaolon päättymispäivämäärä (JSON-kenttä Pvmasti).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.jatetyyppi_ewc IS E'Jätetyypin EWC-koodi (JSON-kenttä tyyppiIdEWC).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.astiamaara IS E'Astioiden lukumäärä (JSON-kenttä astiamaara).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.astian_koko IS E'Astian koko (JSON-kenttä koko).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kunta_tunnus IS E'Kuntatunnus (JSON-kenttä Kuntatun).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kimppakohde_id IS E'Kimppakohteen tunniste (JSON-kenttä palveluKimppakohdeId).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kimpan_nimi IS E'Kimpan nimi (JSON-kenttä kimpanNimi).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kimpan_yhteyshlo IS E'Kimpan yhteyshenkilö (JSON-kenttä Kimpanyhteyshlo).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kimpan_katuosoite IS E'Kimpan katuosoite (JSON-kenttä Kimpankatuosoite).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kimpan_posti IS E'Kimpan postitiedot (JSON-kenttä Kimpanposti).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.keskeytys_alkaen IS E'Keskeytyksen alkamispäivämäärä (JSON-kenttä Keskeytysalkaen).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.keskeytys_asti IS E'Keskeytyksen päättymispäivämäärä (JSON-kenttä Keskeytysasti).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.kaynnit IS E'Tyhjennyskäyntien tiedot (JSON-kenttä kaynnit).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.paino IS E'Punnitustiedot (JSON-kenttä paino).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.tyhjennysvali IS E'Tyhjennysväli (JSON-kenttä tyhjennysvali).';
COMMENT ON COLUMN jkr.v_ulkoinen_asiakastieto_tiedontuottajalla.alkuperainen_json IS E'Ulkoisen asiakastiedon alkuperäinen JSON-sisältö.';
-- v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id).';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue.nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue.geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_ei_hyotyjatteen_erilliskeraysalue.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi).';
-- v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id).';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue.nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue.geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_vah_5_huoneistoa_hyotyjatteen_erilliskeraysalue.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi).';
-- v_velvoite_status
COMMENT ON COLUMN jkr.v_velvoite_status.id IS E'Velvoitteen tilarivin yksilöivä tunniste (jkr.velvoite_status.id).';
COMMENT ON COLUMN jkr.v_velvoite_status.jakso IS E'Tarkistusjakso tekstimuodossa (alku - loppu).';
COMMENT ON COLUMN jkr.v_velvoite_status.ok IS E'Täyttyykö velvoite kyseisenä ajanhetkenä.';
COMMENT ON COLUMN jkr.v_velvoite_status.velvoite_id IS E'Viittaus velvoitteeseen, jonka tilaa rivi kuvaa.';
COMMENT ON COLUMN jkr.v_velvoite_status.tallennuspvm IS E'Velvoitteen tilanteen tallennuspäivämäärä.';
-- v_velvoiteyhteenveto_status
COMMENT ON COLUMN jkr.v_velvoiteyhteenveto_status.id IS E'Velvoiteyhteenvedon tilarivin yksilöivä tunniste (jkr.velvoiteyhteenveto_status.id).';
COMMENT ON COLUMN jkr.v_velvoiteyhteenveto_status.jakso IS E'Tarkistusjakso tekstimuodossa (alku - loppu).';
COMMENT ON COLUMN jkr.v_velvoiteyhteenveto_status.ok IS E'Täyttyykö velvoiteyhteenveto kyseisellä ajanjaksolla.';
COMMENT ON COLUMN jkr.v_velvoiteyhteenveto_status.velvoiteyhteenveto_id IS E'Viittaus velvoiteyhteenvetoon, jonka tilaa rivi kuvaa.';
COMMENT ON COLUMN jkr.v_velvoiteyhteenveto_status.tallennuspvm IS E'Velvoiteyhteenvedon tilanteen tallennuspäivämäärä.';
