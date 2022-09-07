ALTER TABLE jkr.facta_asia
RENAME COLUMN tapahumalaji TO tapahtumalaji;
COMMENT ON COLUMN jkr.facta_asia.tapahtumalaji IS E'Factasta haettavan päätöksen tapahtumalaji';

COMMENT ON TABLE jkr.kohde IS E'Kohteet sisältävä taulu. Kohde koostuu yhden omistajan hallinnoimista lähekkäisistä rakennuksista. Rakennukset voivat sijaita myös eri kiinteistöillä. Yhdellä kiinteistöllä voi olla useita kohteita.';

COMMENT ON COLUMN jkr.kohde.nimi IS E'Kohteen nimi';

COMMENT ON COLUMN jkr.kohde.geom IS E'Kohteen pseudogeometria. Generoidaan automaattisesti (konveksi peite kohteeseen kuuluvista rakennuksista)';

COMMENT ON COLUMN jkr.kohde.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä. Käytännössä milloin asiakas on muuttanut rakennukseen';

COMMENT ON COLUMN jkr.kohde.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä. Käytännössä milloin asiakas on muuttanut pois rakennuksesta';

COMMENT ON COLUMN jkr.kohde.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli. Oletusarvo johdetaan lausekkeella muiden sarakkeiden arvoista';

COMMENT ON TABLE jkr.velvoitemalli IS E'Taulu, joka sisältää mahdolliset velvoitemallit eli tiedon siitä millaisia velvoitteita kohteeseen voi liittyä ja millaisella kyselyllä kunkin velvoitteen toteutumista voidaan tarkastella';

COMMENT ON COLUMN jkr.velvoitemalli.selite IS E'Kuvaus tietyn tunnisteen omaavasta velvoitemallista';

COMMENT ON COLUMN jkr.velvoitemalli.saanto IS E'Velvoitteeseen liittymisen sääntö SQL-kyselynä. SQL-kyselyn ajamalla saadaan selville kohteet, joita velvoite koskee';

COMMENT ON COLUMN jkr.velvoitemalli.tayttymissaanto IS E'SQL-kysely, joka palauttaa kohde_velvoite-instanssille tosi / epätosi riippuen siitä, onko velvoite kunnossa';

COMMENT ON TABLE jkr_koodistot.jatetyyppi IS E'Taulu, joka sisältää mahdolliset jätetyypit';

COMMENT ON COLUMN jkr_koodistot.jatetyyppi.selite IS E'Kuvaus tietyn tunnisteen omaavasta jätetyypistä';

COMMENT ON COLUMN jkr_koodistot.jatetyyppi.ewc IS E'Kuusinumeroinen jätekoodi (EWC-koodi)';

COMMENT ON TABLE jkr.velvoite IS E'Taulu, joka sisältää kohteeseen liittyvät velvoitteet';

COMMENT ON COLUMN jkr.velvoite.alkupvm IS E'Velvoitteen alkamispäivämäärä';

COMMENT ON COLUMN jkr.velvoite.loppupvm IS E'Velvoitteen päättymispäivämäärä';

COMMENT ON TABLE jkr.kiinteisto IS E'Kiinteistöt sisältävä taulu';

COMMENT ON COLUMN jkr.kiinteisto.kiinteistotunnus IS E'Tekstimuotoinen kiinteistötunnus';

COMMENT ON COLUMN jkr.kiinteisto.geom IS E'Kiinteistön geometria';

COMMENT ON TABLE jkr.osapuoli IS E'Kohteen, rakennuksen ja kiinteistön osapuolien tiedot sisältävä taulu';

COMMENT ON COLUMN jkr.osapuoli.nimi IS E'Osapuolen nimi';

COMMENT ON COLUMN jkr.osapuoli.katuosoite IS E'Katuosoite';

COMMENT ON COLUMN jkr.osapuoli.postitoimipaikka IS E'Postitoimipaikka';

COMMENT ON COLUMN jkr.osapuoli.ytunnus IS E'Y-tunnus, jos osapuoli on yritys / yhteisö';

COMMENT ON COLUMN jkr.osapuoli.facta_id IS E'Apu-id, jonka avulla voidaan yksilöidä Factasta tuotavat henkilötiedot. Estää sen, ettei päivittäessä tuoda jo olemassa olevia henkilöitä uudelleen.';

COMMENT ON COLUMN jkr.osapuoli.postinumero IS E'Postinumero';

COMMENT ON TABLE jkr.rakennus IS E'Rakennukset sisältävä taulu';

COMMENT ON COLUMN jkr.rakennus.prt IS E'Yksilöivä 10-merkkinen rakennustunnus';

COMMENT ON COLUMN jkr.rakennus.huoneistomaara IS E'Rakennukseen kuuluvien huoneistojen lukumäärä';

COMMENT ON COLUMN jkr.rakennus.kiinteistotunnus IS E'Tekstimuotoinen kiinteistötunnus';

COMMENT ON COLUMN jkr.rakennus.onko_viemari IS E'Totuusarvo, joka kertoo sen kuuluuko rakennus viemäriverkostoon vai ei';

COMMENT ON COLUMN jkr.rakennus.geom IS E'Rakennuksen geometria';

COMMENT ON COLUMN jkr.rakennus.kayttoonotto_pvm IS E'Rakennuksen käyttöönottopäivämäärä';

COMMENT ON COLUMN jkr.rakennus.kaytostapoisto_pvm IS E'Rakennuksen käytöstäpoistopäivämäärä';

COMMENT ON TABLE jkr.kuljetus IS E'Taulu, joka sisältää 4 kertaa vuodessa toimitettavat kuljetustiedot';

COMMENT ON COLUMN jkr.kuljetus.alkupvm IS E'Kujetustapahtumien raportointiaikavälin alkamispäivämäärä';

COMMENT ON COLUMN jkr.kuljetus.loppupvm IS E'Kujetustapahtumien raportointiaikavälin päättymispäivämäärä';

COMMENT ON COLUMN jkr.kuljetus.tyhjennyskerrat IS E'Raportointiaikavälin aikana suoritettujen kuljetusten lukumäärä';

COMMENT ON COLUMN jkr.kuljetus.massa IS E'Raportointiaikavälin aikana suoritettujen kuljetusten sisältämä massa kilogrammoina';

COMMENT ON COLUMN jkr.kuljetus.tilavuus IS E'Raportointiaikavälin aikana suoritettujen kuljetusten sisältämä tilavuus litroina';

COMMENT ON COLUMN jkr.kuljetus.aikavali IS E'Kuljetustapahtumien raportointiaikaväli. Oletusarvo johdetaan lausekkeella muiden sarakkeiden arvoista';

COMMENT ON TABLE jkr.keraysvaline IS E'Taulu, joka sisältää tiedot sopimukseen liittyvistä keräysvälineistä. Jätteenkuljettajien on toimitettava neljä kertaa vuodessa tiedot kuljetukseen kuuluvien jäteastioiden ko''oista ja määristä jätelajeittain (esim. asiakkaalla xxx on 2 kpl 660 litran sekajäte-astioita ja 1 kpl 200 litran sekajäte-astioita sekä 1 kpl 200 litran metallinkeräysastioita)';

COMMENT ON COLUMN jkr.keraysvaline.pvm IS E'Päivämäärä, jolloin kuljettajat ovat keränneet raportoitavat tiedot';

COMMENT ON COLUMN jkr.keraysvaline.koko IS E'Keräysväline(id)en koko litroina';

COMMENT ON COLUMN jkr.keraysvaline.maara IS E'Keräysvälineiden lukumäärä';

COMMENT ON TABLE jkr.taajama IS E'Taajamat sisältävä taulu. Biojätevelvoite koskee kiinteistöjä, jotka sijaitsevat vähintään 10 000 asukkaan taajamassa';

COMMENT ON COLUMN jkr.taajama.geom IS E'Taajamakohteen geometria';

COMMENT ON TABLE jkr.facta_asia IS E'Facta-päätöksiin liittyvät tiedot sisältävä taulu';

COMMENT ON COLUMN jkr.facta_asia.hakusanat IS E'Hakusanat, joita käyttämällä päätös on Factasta haettu';

COMMENT ON COLUMN jkr.facta_asia.paatoslaji IS E'Factasta haettavan päätöksen päätöslaji';

COMMENT ON COLUMN jkr.facta_asia.paattaja IS E'Factasta haettavan päätöksen päättäjä';

COMMENT ON COLUMN jkr.facta_asia.paatostulos IS E'Factasta haettavan päätöksen tulos';

COMMENT ON COLUMN jkr.facta_asia.kasittelija IS E'Factasta haettavan päätöksen käsittelijä';

COMMENT ON COLUMN jkr.facta_asia.paatettavaksipvm IS E'Päivämäärä, jolloin Factasta haettava päätös on jätetty päätettäväksi';

COMMENT ON COLUMN jkr.facta_asia.kasittelypvm IS E'Factasta haettavan päätöksen käsittelypäivämäärä';

COMMENT ON COLUMN jkr.facta_asia.paatospvm IS E'Factasta haettavan päätöksen päätöspäivämäärä';

COMMENT ON COLUMN jkr.facta_asia.paatosvoimassapvm IS E'Päivämäärä, johon asti Factasta haettava päätös on voimassa';

COMMENT ON COLUMN jkr.facta_asia.paatospykala IS E'Factasta haettavaan päätökseen liittyvä päätöspykälä';

COMMENT ON COLUMN jkr.facta_asia.sisalto IS E'Factasta haettavan päätöksen sisältö';

COMMENT ON COLUMN jkr.facta_asia.perustelu IS E'Factasta haettavaan päätökseen liittyvät perustelut';

COMMENT ON COLUMN jkr.facta_asia.lisatieto IS E'Factasta haettavaan päätökseen liittyvä lisätieto';

COMMENT ON TABLE jkr.pohjavesialue IS E'Pohjavesialueet sisältävä taulu';

COMMENT ON COLUMN jkr.pohjavesialue.geom IS E'Pohjavesialueen geometria';

COMMENT ON TABLE jkr.jatteenkuljetusalue IS E'Jätteenkuljetusalueet sisältävä taulu. Jätteenkuljetusalueiden ulkopuoliset kiinteistöt liittyvät aluejätekeräykseen';

COMMENT ON COLUMN jkr.jatteenkuljetusalue.geom IS E'Jätteenkuljetusalueen geometria';

COMMENT ON TABLE jkr.keskeytys IS E'Sopimuksen keskeytystapahtumien tiedot sisältävä taulu';

COMMENT ON COLUMN jkr.keskeytys.alkupvm IS E'Keskeytystapahtuman alkamispäivämäärä';

COMMENT ON COLUMN jkr.keskeytys.loppupvm IS E'Keskeytystapahtuman päättymispäivämäärä';

COMMENT ON COLUMN jkr.keskeytys.selite IS E'Kuvaus tietyn tunnisteen omaavasta keskeytys-tapahtumasta';

COMMENT ON TABLE jkr.tyhjennysvali IS E'Sopimukseen liittyvät tyhjennysvälitiedot sisältävä taulu';

COMMENT ON COLUMN jkr.tyhjennysvali.alkuvko IS E'Viikkonumero, josta alkaen astiat tyhjennetään X viikon välein. Oletusarvo on se, että tyhjennysväli asetetaan vuodeksi kerrallaan (eli alkaa vuoden ensimmäisestä viikosta)';

COMMENT ON COLUMN jkr.tyhjennysvali.loppuvko IS E'Viikkonumero, johon päättyy astioiden tyhjentäminen X viikon välein. Oletusarvo on se, että tyhjennysväli asetetaan vuodeksi kerrallaan (eli päättyy vuoden viimeisenä viikkona)';

COMMENT ON COLUMN jkr.tyhjennysvali.tyhjennysvali IS E'Tyhjennysväli viikoissa';

COMMENT ON TABLE jkr_osoite.katu IS E'Katuosoitteen tiedot sisältävä taulu';

COMMENT ON COLUMN jkr_osoite.katu.katunimi_fi IS E'Kadun nimi suomeksi';

COMMENT ON COLUMN jkr_osoite.katu.katunimi_sv IS E'Kadun nimi ruotsiksi';

COMMENT ON TABLE jkr.osoite IS E'Osoitetiedot sisältävä taulu';

COMMENT ON COLUMN jkr.osoite.osoitenumero IS E'Katuosoitteeseen liittyvä talon ja/tai rapun ja/tai asunnon numero';

COMMENT ON TABLE jkr_osoite.kunta IS E'Osoitteeseen liittyvän kunnan tiedot sisältävä taulu';

COMMENT ON COLUMN jkr_osoite.kunta.koodi IS E'Kolminumeroinen kuntakoodi';

COMMENT ON COLUMN jkr_osoite.kunta.nimi_fi IS E'Kunnan nimi suomeksi';

COMMENT ON COLUMN jkr_osoite.kunta.nimi_sv IS E'Kunnan nimi ruotsiksi';

COMMENT ON FUNCTION jkr.qgis_notify() IS E'Triggeröinti-funktio, joka käynnistää QGIS-tasojen automaattisen päivityksen';

COMMENT ON TRIGGER notify_qgis_edit ON jkr.kohde IS E'Triggeri, joka aktivoituu kun uusi kohde luodaan, kohdetta muokataan, kohde poistetaan tai kaikki kohteet poistetaan. Triggeri käynnistää qgis_notify-nimisen funktion';

COMMENT ON FUNCTION jkr.create_kohde_geom(integer) IS E'Funktio, joka luo uudelle kohteelle geometrian luomalla kohteeseen liittyvien rakennusten geometrian/geometroiden ympärille bufferin ja muodostamalla näistä konveksin peitteen';

COMMENT ON FUNCTION jkr.update_kohde_geom() IS E'Triggeröinti-funktio, joka päivittää kohteeseen liittyvien rakennusten listaa ja käynnistää tarvittaessa kohteen geometrian luonnista vastaavan funktion uudella kohdetunnisteella tai asettaa kohteen geometrian tyhjäksi (mikäli viimeinen kohteen rakennus poistuu käytöstä)';

COMMENT ON TABLE jkr_koodistot.kohdetyyppi IS E'Taulu, joka sisältää mahdolliset kohdetyypit';

COMMENT ON COLUMN jkr_koodistot.kohdetyyppi.selite IS E'Kuvaus tietyn tunnisteen omaavasta kohdetyypistä';

COMMENT ON TABLE jkr_koodistot.tiedontuottaja IS E'Taulu, joka sisältää mahdolliset tiedontuottajat';

COMMENT ON COLUMN jkr_koodistot.tiedontuottaja.tunnus IS E'Taulun avaimena toimiva uniikki tekstimuotoinen tunniste';

COMMENT ON COLUMN jkr_koodistot.tiedontuottaja.nimi IS E'Tiedontuottajan nimi';

COMMENT ON TABLE jkr_osoite.posti IS E'Postitoimipaikan tiedot sisältävä taulu';

COMMENT ON COLUMN jkr_osoite.posti.numero IS E'Taulun avaimena toimiva uniikki viisinumeroinen postinumero';

COMMENT ON COLUMN jkr_osoite.posti.nimi_fi IS E'Postitoimipaikan nimi suomeksi';

COMMENT ON COLUMN jkr_osoite.posti.nimi_se IS E'Postitoimipaikan nimi ruotsiksi';

COMMENT ON TABLE jkr_koodistot.rakennuksenkayttotarkoitus IS E'Taulu, joka sisältää mahdolliset rakennuksen käyttötarkoitukset';

COMMENT ON COLUMN jkr_koodistot.rakennuksenkayttotarkoitus.koodi IS E'Taulun avaimena toimiva uniikki tekstimuotoinen tunniste';

COMMENT ON COLUMN jkr_koodistot.rakennuksenkayttotarkoitus.selite IS E'Kuvaus tietyn tunnisteen omaavasta rakennuksen käyttötarkoituksesta';

COMMENT ON TABLE jkr_koodistot.rakennuksenolotila IS E'Taulu, joka sisältää mahdolliset rakennuksen olotilat';

COMMENT ON COLUMN jkr_koodistot.rakennuksenolotila.koodi IS E'Taulun avaimena toimiva uniikki tekstimuotoinen tunniste';

COMMENT ON COLUMN jkr_koodistot.rakennuksenolotila.selite IS E'Kuvaus tietyn tunnisteen omaavasta rakennuksen olotilasta';

COMMENT ON TABLE jkr_koodistot.osapuolenlaji IS E'Taulu, joka sisältää mahdolliset osapuolen lajit';

COMMENT ON COLUMN jkr_koodistot.osapuolenlaji.koodi IS E'Taulun avaimena toimiva uniikki tekstimuotoinen tunniste';

COMMENT ON COLUMN jkr_koodistot.osapuolenlaji.selite IS E'Kuvaus tietyn tunnisteen omaavasta osapuolenlajista';

COMMENT ON TABLE jkr.sopimus IS E'Taulu, joka sisältää tiedot kohteeseen liittyvistä sopimuksista';

COMMENT ON COLUMN jkr.sopimus.alkupvm IS E'Sopimuksen voimaantulopäivämäärä';

COMMENT ON COLUMN jkr.sopimus.loppupvm IS E'Sopimuksen päättymispäivämäärä';

COMMENT ON COLUMN jkr.sopimus.voimassaolo IS E'Sopimuksen voimassaoloaikaväli. Oletusarvo johdetaan lausekkeella muiden sarakkeiden arvoista';

COMMENT ON TABLE jkr.ulkoinen_asiakastieto IS E'Mitä vain jostain ulkoisesta järjestelmästä (PJH, Facta, Nokian lietekuskit jne.) löytyvää asiakastietoa sisältävä taulu';

COMMENT ON COLUMN jkr.ulkoinen_asiakastieto.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';

COMMENT ON COLUMN jkr.ulkoinen_asiakastieto.ulkoinen_id IS E'Apu-id, jonka avulla saadaan haettua asiakkaiden tiedot kaikista muista järjestelmistä. Käytännössä asikasnumero kussakin ulkoisessa järjestelmässä';

COMMENT ON COLUMN jkr.ulkoinen_asiakastieto.ulkoinen_asiakastieto IS E'Mitä vain ulkoisesta järjestelmästä löytyvää tietoa asiakkaasta. Tallennetaan json-muodossa';

COMMENT ON TABLE jkr_koodistot.osapuolenrooli IS E'Taulu, joka sisältää mahdolliset osapuolen roolit';

COMMENT ON COLUMN jkr_koodistot.osapuolenrooli.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';

COMMENT ON COLUMN jkr_koodistot.osapuolenrooli.selite IS E'Kuvaus tietyn tunnisteen omaavasta osapuolenroolista';

COMMENT ON TABLE jkr.kohteen_osapuolet IS E'Kohteen osapuolet sisältävä taulu';

COMMENT ON TABLE jkr.kohteen_rakennukset IS E'Kohteeseen liittyvät rakennukset sisältävä taulu';

COMMENT ON TRIGGER trg_after_kohde_rakennus_change ON jkr.kohteen_rakennukset IS E'Triggeri, joka aktivoituu kun kohteelle on lisätty rakennus, kohteeseen liittyvien rakennusten listaa on päivitetty tai jokin kohteeseen liittyvistä rakennuksista on poistettu. Triggeri käynnistää update_kohde_geom-nimisen funktion';

COMMENT ON TRIGGER trg_after_truncate ON jkr.kohteen_rakennukset IS E'Triggeri, joka aktivoituu kun kohteelta poistetaan kaikki rakennukset. Triggeri käynnistää update_kohde_geom-nimisen funktion';

COMMENT ON TABLE jkr.rakennuksen_omistajat IS E'Rakennuksen omistajat sisältävä taulu';

COMMENT ON COLUMN jkr.rakennuksen_omistajat.rakennus_id IS E'Rakennuksen yksilöivä sarjanumeromuotoinen tunniste';

COMMENT ON COLUMN jkr.rakennuksen_omistajat.osapuoli_id IS E'Osapuolen yksilöivä sarjanumeromuotoinen tunniste';

COMMENT ON TABLE jkr.kiinteiston_omistajat IS E'Kiinteistön omistajat sisältävä taulu';

COMMENT ON COLUMN jkr.kiinteiston_omistajat.kiinteisto_id IS E'Kiinteistön yksilöivä sarjanumeromuotoinen tunniste';

COMMENT ON COLUMN jkr.kiinteiston_omistajat.osapuoli_id IS E'Osapuolen yksilöivä sarjanumeromuotoinen tunniste';

COMMENT ON TABLE jkr_koodistot.sopimustyyppi IS E'Taulu, joka sisältää mahdolliset sopimustyypit';

COMMENT ON COLUMN jkr_koodistot.sopimustyyppi.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';

COMMENT ON COLUMN jkr_koodistot.sopimustyyppi.selite IS E'Kuvaus tietyn tunnisteen omaavasta sopimustyypistä';
