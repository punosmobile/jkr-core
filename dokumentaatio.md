# Järjestelmädokumentaatio

## Sisällysluettelo
1. [Johdanto](#1-johdanto)
2. [Järjestelmän yleiskuvaus](#2-järjestelmän-yleiskuvaus)
   1. [Ympäristö](#21-ympäristö)
   2. [Tietokannat ja tietomalli](#22-tietokannat-ja-tietomalli)
3. [Kohteiden luonti ja päivittäminen DVV-aineistosta](#3-kohteiden-luonti-ja-päivittäminen-dvv-aineistosta)
   1. [DVV-aineiston lisääminen ja päivittäminen](#31-dvv-aineiston-lisääminen-ja-päivittäminen)
   2. [Kohteiden luonti](#32-kohteiden-luonti)
   3. [Kohteiden nimeäminen](#33-kohteiden-nimeäminen)
   4. [DVV-aineistosta muodostettavat osapuolen roolit](#34-dvv-aineistosta-muodostettavat-osapuolen-roolit)
4. [Kuljetustiedot](#4-kuljetustiedot)
5. [Viranomaispäätökset](#5-viranomaispäätökset)
6. [Kompostointi-ilmoitukset](#6-kompostointi-ilmoitukset)
7. [Velvoitteet ja velvoitetarkistukset](#7-velvoitteet-ja-velvoitetarkistukset)
   1. [Velvoitemallit](#71-velvoitemallit)
   2. [Velvoitetarkistusten suorittaminen](#72-velvoitetarkistusten-suorittaminen)
   3. [Velvoitetarkistusten tulokset](#73-velvoitetarkistusten-tulokset)
   4. [Velvoiteyhteenvedot](#74-velvoiteyhteenvedot)
   5. [HAPA-aineiston vaikutus velvoitteisiin](#75-hapa-aineiston-vaikutus-velvoitteisiin)
8. [Jätehuollon seurantaraportti](#8-jätehuollon-seurantaraportti)

[Liite 1: Velvoitemallit](#liite-1-velvoitemallit)

## 1 Johdanto

Tässä järjestelmädokumentaatiossa kuvataan Lahden seudun jätehuoltoviranomaiselle toteutetun jätteenkuljetusrekisterin toiminta.

Järjestelmän toteutus löytyy avoimena lähdekoodina GitHubista:
- [jkr-core](https://github.com/punosmobile/jkr-core)
- [jkr-lahti](https://github.com/punosmobile/jkr-lahti)

## 2 Järjestelmän yleiskuvaus

Jätteenkuljetusrekisteriin voidaan syöttää jätteenkuljetustietojen lisäksi tietoja jätehuoltoa koskevista viranomaispäätöksistä sekä tietoa kiinteistöillä tapahtuvasta kompostoinnin aloittamisesta ja lopettamisesta. Järjestelmään syötettyjen tietojen avulla voidaan tarkastella jätehuoltovelvoitteiden täyttymistä jätehuoltoviranomaisen toimialueella.

### 2.1 Ympäristö

Järjestelmä koostuu kahdesta PostgreSQL/PostGIS-tietokannasta sekä QGIS-käyttöliittymästä, jotka kaikki toimivat Lahden Azure Virtual Desktop -ympäristössä (AVD).

AVD-ympäristössä tehdään automaattisia päivitysajoja Lahden IT-toimittajan toimesta. Päivitysten yhteydessä jätteenkuljetusrekisterijärjestelmän viimeisin päivitysversio (release) haetaan GitHubista ([https://github.com/punosmobile/jkr-core/releases](https://github.com/punosmobile/jkr-core/releases)) ja asennetaan automaattisesti AVD-ympäristöön jätehuoltoviranomaisen käyttöön. 

Automaattisten päivitysten ajoitus ei ole jätehuoltoviranomaisen tiedossa, mutta niitä tehdään arvion mukaan noin kerran kuussa. Normaalitilanteessa automaattinen päivitys ei vaadi toimenpiteitä jätteenkuljetusjärjestelmän käyttäjältä tai ylläpidolta.

Jos päivitysten välissä on tarpeen julkaista uusi päivitys, joka halutaan jätehuoltoviranomaisen käyttöön ennen automaattipäivitystä, tämä voidaan tehdä manuaalisesti:
1. Lataa GitHubista (Releasen Assets-kohdan alta) uusimman releasen `jkr-x.x.x.zip`-tiedosto
2. Pura tiedoston sisältö kansioon `C:/jkr`
3. Varmista, että purku on tehty oikein tarkistamalla, että kaikki tarvittavat tiedostot löytyvät `C:/jkr`-polusta

### 2.2 Tietokannat ja tietomalli

Jätehuoltoviranomainen käyttää työssään järjestelmän "test"-tietokantaa. "Dev"-tietokanta on järjestelmän kehityksessä käytettävä kanta, jota jätehuoltoviranomaisen ei tarvitse käyttää päivittäisessä työssään.

QGIS-käyttöliittymä on QGIS-projekti, joka löytyy tietokannan jkr_qgis_projektit-skeemasta.

Molemmat tietokannat sijaitsevat Lahden kaupungin Azure-ympäristössä ja järjestelmää käytetään kaupungin sisäverkossa Azure Virtual Desktopilta. On huomattava, että tietokannat on nimetty eri tavoin Azuressa kuin mitä niistä käytetään "yleisnimenä" käyttäjien toimesta, tässä järjestelmädokumentaatiossa sekä järjestelmän käyttöohjeessa.

| Tietokannan yleisnimi | Tietokannan nimi Azuressa | Käyttötarkoitus |
|-----------------------|---------------------------|-----------------|
| test | prod | Jätehuoltoviranomaisen käyttämä tietokanta |
| dev | test | Järjestelmän kehitystyössä kehittäjien käyttämä tietokanta |

Tietomallista on olemassa oheinen kuva, joka löytyy GitHubista sekä Teamsin Dokumentaatio-kansiosta nimellä `Lahti_jkr_db_model_12_4_2024.png`.

## 3 Kohteiden luonti ja päivittäminen DVV-aineistosta

Tässä kappaleessa kuvaillaan Lahden kaupungin jätehuoltoviranomaisen kanssa yhteistyössä laaditun Digi- ja Väestöviraston tuottaman DVV-pohja-aineiston lisäämisen ja päivittämisen, sekä kohteiden luomisen sekä kohteiden tietojen päivittämisen prosessin.

Kohteiden luontivaiheessa vaadittavat aineistot ovat:
- DVV-aineisto, jossa mukana rakennus-, omistaja- ja asukastiedot
- Postinumeroaineisto (vain ensimmäisellä kerralla)
- Lahden jätehuoltoviranomaisen tuottama perusmaksurekisteriaineisto (vain ensimmäisellä kerralla)

Kohteiden päivittämiseen tarvittava aineisto:
- DVV-aineiston päivitysversio

Kohteiden luomisen ja päivittämisen skriptien ajo suoritetaan järjestyksessä:

1. Tuodaan postinumeroaineisto ajamalla `import_posti.bat`

2. Ajetaan `import_dvv.bat` ensimmäisen dvv-aineiston lisäämiseksi. Syötetään parametrina poimintapäivä muodossa P.K.VVVV (esim. 1.1.2022)

3. Ajetaan `jkr create_dvv_kohteet` kohteiden kohteiden luomiseksi. Parametreinä annetaan dvv-aineiston poimintapäivämäärä muodossa P.K.VVVV (esim. 1.1.2022) sekä tiedostopolku perusmaksurekisteriin.

Päivitettäessä kohteet ajetaan skriptit:

1. Ajetaan `import_dvv.bat` dvv-aineistopäivityksen tekemiseksi. Parametrina annetaan uuden aineiston poimintapäivämäärä muodossa P.K.VVVV (esim. 1.1.2023)

2. Ajetaan `jkr create_dvv_kohteet` kohteiden päivittämiseksi, ja mahdollisten uusien kohteiden luomiseksi. Parametrina päivittäessä annetaan vain dvv-aineiston poimintapäivämäärä muodossa P.K.VVVV (esim. 1.1.2023).

Kummatkin näistä voidaan suorittaa yhdellä komennolla käyttäen `jkr_importer`-työkalua, tai suorittamalla skriptit yksi kerrallaan.

Säännöt on toteutettu avoimena sql- ja python-koodina. Koodit löytyvät osoitteista:
- DVV-aineiston tuonti: [import_dvv.sql](https://github.com/punosmobile/jkr-core/blob/b362b94435b59f1dec6701c9d168a5bcdbfac15f/scripts/import_dvv.sql)
- Kohteiden luonti: [dbprovider.py](https://github.com/punosmobile/jkr-core/blob/d3398447228284aeff9b171e4bac33e5d755364c/jkrimporter/providers/db/dbprovider.py)

### 3.1 DVV-aineiston lisääminen ja päivittäminen

1. Asetetaan syötetty DVV-aineiston poimintapäivämäärä muuttujaksi. Tätä arvoa käytetään myöhemmin loppupäivämäärien asettamisessa.

2. Luodaan funktiot omistajien, vanhimpien ja rakennusten loppupäivämäärien asettamiseksi. Lisäksi luodaan y-tunnuksellisten ja henkilötunnuksellisten osapuolien päivitysfunktiot.

3. Asetetaan `jkr_koodistot.tiedontuottaja`-tauluun tieto 'dvv'.

4. Lisätään rakennukset `jkr_rakennuksiin`. Jos tietokannasta löytyy jo rakennus samalla prt:llä, rakennuksen tiedot päivitetään. Kaikille dvv-ainteistosta löytyville rakennuksille lisätään myös väliaikainen `found_in_dvv = 'true'`, jonka avulla saadaan helposti eroteltua rakennukset, jotka löytyvät uusimmasta dvv-aineistosta.

5. Päivitetään rakennusten `kaytostapoisto_pvm` rakennuksille, joita ei enää löydy dvv-aineistosta ja joiden `kaytostapoisto_pvm` arvo on tyhjä. Arvoksi asetetaan syötetty poimintapäivämäärä.

6. Kadut lisätään `jkr_osoite.katu`-tauluun. Tauluun syötetään dvv-aineistosta osoitevälilehdeltä tiedot:
   - kadunnimi suomeksi
   - kadunnimi ruotsiksi
   - sijainti_kunta

   Kadut lisätään kahdessa osassa:
   - Ensimmäiseksi lisätään kadut, joilta löytyy suomen- ja ruotsinkielinen nimi
   - Toisessa osuudessa lisätään kadut, joilta löytyy vain suomen- tai ruotsinkielinen nimi

   Jaon avulla varmistetaan, että katuja, joilla on molemmat tiedot ei ylikirjoiteta kaduilla joista puuttuu tietoa. Jokaiselle kunnalle lisätään myös "tyhjä katu", jolla ei ole suomen- tai ruotsinkielistä nimeä. Katuja ei päivitetä, vaan luodaan aina uusi katu (esim. jos kadun nimi on kirjoitettu eri tavalla, ei lähdetä arvaamaan mikä on oikein kirjoitettu). Uudet kadut lisätään aina tauluun, jos niitä ei ole siellä ennestään.

7. Lisätään rakennusten osoitteet `jkr.osoite`-tauluun. Osoitenumeroksi valitaan dvv-aineistosta osoite-välilehdeltä `katu_numero`. `Katu_id` pyritään asettamaan ensin suomenkielisen kadunnimen + kuntakoodin perusteella, ja jos suomenkielistä nimeä ei ole, ruotsinkielisen kadunnimen + kuntakoodin perusteella. Jos molemmat kadunnimet ovat tyhjät, valitaan edellisessä kohdassa luotu tyhjä katu + kuntakoodi. Rakennukset valitaan dvv-aineiston rakennustunnuksen ja `jkr.rakennus`-taulun prt:n perusteella. `Posti_numero` valitaan dvv-aineiston posti_numero-kentän perusteella. Dvv-aineistossa 00000-postinumerolla olevat osoitteet ohjataan tyhjälle kadulle.

8. Rakennuksen omistajat lisätään `jkr.osapuoli`-tauluun kolmessa osassa. Jokaisessa osassa tiedot valitaan dvv-aineiston omistaja-välilehdeltä:
   - Ensimmäisessä osassa lisätään tai päivitetään vain henkilötunnukselliset omistajat henkilötunnuksen perusteella niin, että omistaja-osapuolen tiedot päivittyvät jokaisessa hänen omistamassaan kohteessa
   - Toisessa vaiheessa lisätään tai päivitetään y-tunnukselliset omistajat y-tunnuksen perusteella
   - Kolmannessa vaiheessa lisätään henkilö- ja y-tunnuksettomat omistajat niiden nimen, katuosoitteen, postitoimipaikan, postinumeron, sekä rakennustunnuksen perusteella

DVV-päivityksen yhteydessä, ennen tiedon lisäämistä tauluun, tarkistetaan rakennuksista, ettei niistä jo löydy omistajaa samalla nimellä.

**Huomioitavaa!**
Tapauksissa, joissa henkilö- ja y-tunnukseton omistaja omistaa useamman rakennuksen, luodaan jokaiselle rakennukselle oma osapuoli. Tämä johtuu siitä, että omistajaa ei voida yksilöidä henkilö- tai y-tunnuksen perusteella.

### 3.2 Kohteiden luonti

Järjestelmä luo kohteet DVV-aineistosta seuraavassa järjestyksessä:

1. **Perusmaksurekisterin kohteet**
   - Rivitalot, kerrostalot ja muut useamman asunnon kohteet
   - Yhdistää saman asiakasnumeron rakennukset samaan kohteeseen
   - Huomioi seuraavat rakennustyypit (Rakennusluokitus 2018):
     - 0110: Paritalot
     - 0210: Rivitalot
     - 0220: Ketjutalot
     - 0320: Luhtitalot
     - 0390: Muut asuinkerrostalot
   - Jos 2018 luokitus puuttuu, käytetään vanhempaa luokitusta:
     - 012: Kahden asunnon talot
     - 021: Rivitalot
     - 022: Ketjutalot
     - 032: Luhtitalot
     - 039: Muut asuinkerrostalot

2. **Yhden asunnon kohteet**
   - Omakotitalot ja paritalot
   - Luodaan kohde jokaiselle rakennukselle, jolla ei vielä ole kohdetta
   - Yhdistää samaan kohteeseen vain yhden rakennuksen per kiinteistö

3. **Muut kohteet**
   - Kaikki jäljellä olevat rakennukset
   - Useita rakennuksia sisältävät kiinteistöt
   - Asumattomat rakennukset

**Apurakennusten käsittely:**
- Saunat ja piharakennukset liitetään päärakennusten kohteisiin jos:
  - Sama omistaja/asukas kuin kohteen päärakennuksella
  - Sama osoite kuin kohteen päärakennuksella
  - Sijainti enintään 300m päässä kohteen päärakennuksista

**Kohteen nimeäminen:**
Kohteen nimi määräytyy seuraavassa prioriteettijärjestyksessä:
1. Asunto-osakeyhtiön nimi
2. Yrityksen nimi
3. Yhteisön nimi
4. Vanhimman asukkaan nimi
5. Omistajan nimi
6. Jos mikään edellisistä ei ole saatavilla, nimeksi asetetaan "Tuntematon"

**Kohteen voimassaolo:**
- Alkupäivämäärä määräytyy DVV-aineiston poimintapäivän mukaan
- Jos kyseessä on vanhan kohteen päivitys, alkupäivämäärä määräytyy rakennusten historian perusteella
- Loppupäivämäärä on oletuksena 31.12.2100, ellei toisin määritelty

### 3.3 Kohteiden nimeäminen

Kohteen nimen muodostamisessa noudatetaan seuraavia tarkentavia sääntöjä:

1. **Usean omistajan tai asukkaan tapaukset**
   - Jos kohteella on useampi omistaja tai useampi vanhin asukas, valitaan aakkosissa ensimmäinen
   - Tämä ehkäisee kohteen nimen satunnaista vaihtumista, kun omistajissa/vanhimmissa ei ole tapahtunut todellista muutosta

2. **Nimen muodostamisen erityistapaukset**
   - Perusmaksurekisterin kohteilla ei ole asukkaita osapuolena
   - Luonnollisen henkilön tapauksessa käytetään vain sukunimeä
   - Asunto-osakeyhtiöiden, yritysten ja yhteisöjen nimet tallennetaan kokonaisuudessaan

3. **Nimen päivittyminen**
   - Kohteen nimi päivittyy automaattisesti DVV-aineiston päivityksen yhteydessä
   - Päivitys noudattaa samaa prioriteettijärjestystä kuin uuden kohteen luonti
   - Jos kaikki nimenmuodostukseen tarvittavat tiedot puuttuvat, nimeksi asetetaan "Tuntematon"

### 3.4 DVV-aineistosta muodostettavat osapuolen roolit

DVV-aineistosta muodostetaan seuraavat osapuolen roolit:

#### 1. VANHIN_ASUKAS
- Lähde: DVV:n asukasaineisto
- Muodostaminen: Kaikki rakennuksen asukkaat lisätään VANHIN_ASUKAS -roolilla
- Käyttötarkoitus: Kohteen tunnistaminen ja nimeäminen
- Huomioitavaa: Perusmaksurekisterin kohteilla ei ole asukkaita osapuolena

#### 2. OMISTAJA
- Lähde: DVV:n omistajatiedot
- Muodostaminen: Kaikki rakennuksen omistajat lisätään OMISTAJA-roolilla
- Käyttötarkoitus: 
  - Kohteen tunnistaminen myöhemmissä tuonneissa
  - Kohteen nimeäminen (jos ei asukkaita)
- Erityistapaukset:
  - Asunto-osakeyhtiöt
  - Yritykset
  - Yhteisöt
  - Yksityishenkilöt

#### 3. Jätehuollon roolit
Kuljetustiedoista muodostuvat roolit:

##### Kimppaisännät
- SEKAJATE_KIMPPAISANTA
- BIOJATE_KIMPPAISANTA
- LASI_KIMPPAISANTA
- KARTONKI_KIMPPAISANTA
- METALLI_KIMPPAISANTA
- MUOVI_KIMPPAISANTA

##### Kimppaosakkaat
- SEKAJATE_KIMPPAOSAKAS
- BIOJATE_KIMPPAOSAKAS
- LASI_KIMPPAOSAKAS
- KARTONKI_KIMPPAOSAKAS
- METALLI_KIMPPAOSAKAS
- MUOVI_KIMPPAOSAKAS

##### Tilaajat
- SEKAJATE_TILAAJA
- BIOJATE_TILAAJA
- LASI_TILAAJA
- KARTONKI_TILAAJA
- METALLI_TILAAJA
- MUOVI_TILAAJA
- LIETE_TILAAJA

#### 4. Muut roolit
- KOMPOSTI_YHTEYSHENKILO: Kompostointi-ilmoituksen vastuuhenkilö

**Huomioitavaa rooleista:**
- Sama osapuoli voi olla useassa roolissa (esim. sekä omistaja että asukas)
- Roolit ovat kohdekohtaisia
- Roolien voimassaolo määräytyy kohteen voimassaolon mukaan
- Tiedontuottajan tunniste tallennetaan roolin yhteyteen

## 4 Kuljetustiedot

Tässä kappaleessa kuvaillaan kuljetustietojen lukeminen tietokantaan ja kohdentaminen kohteille.

### 4.1 Kuljetustietojen tuonti

Kuljetustiedot tuodaan järjestelmään kvartaaleittain CSV-muodossa. Tuonti tapahtuu `jkr import` -komennolla, jolle annetaan seuraavat parametrit:
- Tiedostopolku kuljetustietojen kansioon
- Tiedontuottajan tunnus (esim. "LSJ")
- Kvartaalin alkupäivämäärä (muodossa PP.KK.VVVV)
- Kvartaalin loppupäivämäärä (muodossa PP.KK.VVVV)

Esimerkki tuontikomennosta:
```bash
jkr import ../data/Kuljetustiedot/Kuljetustiedot_2024/Q1 LSJ 1.1.2024 31.3.2024
```

#### 4.1.1 Pakolliset tiedot

Jokaisella CSV-tiedoston rivillä on oltava seuraavat pakolliset tiedot:
- `UrakoitsijaId` - yksilöi kuljetusyrityksen
- `Pvmalk` - kvartaalin alkupäivämäärä
- `Pvmasti` - kvartaalin loppupäivämäärä
- `tyyppiIdEWC` - jätelaji tai aluekeräyspiste/monilokero
- `COUNT(kaynnit)` - käyntien lukumäärä (voi olla 0, mutta ei voi olla tyhjä)

#### 4.1.2 Tietojen tallentaminen

Kuljetustiedot tallennetaan seuraaviin tietokannan tauluihin:

| Taulu | Kuvaus |
|-------|---------|
| jkr.kuljetus | Kuljetusten perustiedot (ajankohta, määrät) |
| jkr.sopimus | Kuljetussopimukset |
| jkr.keraysvaline | Keräysvälineiden tiedot |
| jkr.tyhjennysvali | Tyhjennysvälit |
| jkr.keskeytys | Keskeytysjaksot |
| jkr.osapuoli | Tilaajat ja kimppaisännät |
| jkr.ulkoinen_asiakastieto | Ulkoiset tunnisteet ja lisätiedot |

### 4.2 Kohdentaminen

Kuljetustieto kohdennetaan kohteelle seuraavassa järjestyksessä:

1. Tiedontuottajan tunnus ja ulkoinen asiakastunnus
   - Ensisijainen kohdentamistapa
   - Käyttää kenttiä `UrakoitsijaId` ja `UrakoitsijankohdeId`

2. Rakennustunnus (PRT)
   - Toissijainen kohdentamistapa
   - Käyttää kenttää `Rakennustunnus`

3. Kiinteistötunnus
   - Kolmassijainen kohdentamistapa
   - Käyttää kenttää `Kiinteistotunnus`

4. Osoite
   - Viimesijainen kohdentamistapa
   - Käyttää kenttiä `Kiinteistonkatuosoite` ja `Kiinteistonposti`

**Huomioitavaa:**
- Kuljetustiedoista ei muodosteta uusia kohteita
- Jos kohdentamisessa ilmenee ongelmia (esim. rakennusta ei löydy), tallennetaan tieto kohdentamattomista ilmoituksista erilliseen tiedostoon.

### 4.3 Sopimusten muodostaminen

Kuljetustiedoista muodostetaan uusi sopimus, kun:
1. Kuljetus kohdentuu kohteelle
2. Vastaavaa sopimusta ei ole olemassa

Vastaavaksi sopimukseksi katsotaan sopimus, jolla on:
- Sama kohde
- Sama tiedontuottaja
- Sama sopimustyyppi
- Sama jätetyyppi
- Päällekkäinen voimassaoloaika
- Kimppasopimusten osalta sama kimppaisäntä

### 4.4 Kimpat

Kuljetustieto käsitellään kimppaan kuuluvana, jos seuraavat kentät on täytetty:
- `palveluKimppakohdeId` - kimpan tunniste
- `KimpanNimi` - kimpan nimi
- `Kimpankatuosoite` - kimpan osoite
- `Kimpanposti` - kimpan postiosoite

Kimpan jäsenille luodaan omat sopimukset, jotka linkitetään kimppaisäntään.

### 4.5 Jätetyypit

Tuetut jätetyypit:
- Biojäte (1)
- Sekajäte (2)
- Kartonki (3)
- Lasi (4)
- Liete (5)
- Mustaliete (6)
- Harmaaliete (7)
- Metalli (8)
- Muovi (9)
- Pahvi (10)
- Paperi (11)
- Perusmaksu (12)
- Energia (13)
- Muu (99)

## 5 Viranomaispäätökset

### 5.1 Päätöstyypit

Järjestelmä käsittelee seuraavia viranomaispäätöstyyppejä:

- **Tyhjennysväli**: Jäteastian tyhjennysvälin pidentäminen
- **AKP (Aluekeräyspisteestä poikkeaminen)**: Vapautus aluekeräyspisteen käytöstä
- **Perusmaksu**: Vapautus perusmaksusta 
- **Keskeyttäminen**: Jätteenkuljetuksen keskeytys
- **Erilliskeräyksestä poikkeaminen**: Vapautus erilliskeräysvelvoitteesta

### 5.2 Päätösten rakenne

Päätökset tallennetaan tietokantaan seuraavilla tiedoilla:

- **Paatosnumero**: Yksilöivä tunniste
- **Alkupvm ja loppupvm**: Voimassaoloaika
- **Tapahtumalaji**: Päätöksen tyyppi (esim. TYHJENNYSVALI)
- **Paatostulos**: Myönteinen (1) tai kielteinen (0)
- **Tyhjennysvali**: Myönnetty tyhjennysväli viikkoina
- **Rakennus**: Mihin rakennukseen päätös kohdistuu

### 5.3 Päätösten kohdentaminen

Viranomaispäätökset kohdennetaan rakennuksille seuraavasti:

1. Päätös kohdistetaan suoraan rakennukseen `viranomaispaatokset.rakennus_id` -kentän avulla
2. Päätöksen vaikutus kohdistuu kaikkiin kohteen rakennuksiin `kohteen_rakennukset` -taulun kautta
3. Kohdentuminen näkyy näkymässä `v_kohteen_viranomaispaatokset`

Kohdentamisen hierarkia:
- Rakennus -> Päätös (suora kohdistus)
- Kohde -> Kohteen rakennukset -> Päätökset (välillinen kohdistus)

Kohdentamisen vaikutukset:
- Päätökset vaikuttavat kohteen velvoitteisiin vain voimassaoloaikana
- Myönteiset päätökset voivat muuttaa:
  - Tyhjennysväliä (TYHJENNYSVALI)
  - Aluekeräyspisteen käyttöä (AKP)
  - Perusmaksua (PERUSMAKSU)
  - Jätteenkuljetuksen keskeytystä (KESKEYTTAMINEN)
  - Erilliskeräysvelvoitetta (ERILLISKERAYKSESTA_POIKKEAMINEN)

### 5.4 Päätösten vaikutus

Päätökset vaikuttavat kohteen velvoitteisiin seuraavasti:

- Myönteiset päätökset voivat:
  - Pidentää tyhjennysväliä
  - Vapauttaa velvoitteista määräajaksi
  - Keskeyttää palvelun
- Voimassaolevat päätökset tarkistetaan velvoitteiden päivityksen yhteydessä

### 5.5 Raportointi

Päätöstietoja voidaan tarkastella seuraavasti:

- Päätökset näkyvät kohteen tiedoissa (`v_kohteen_viranomaispaatokset`)
- Päätösten vaikutukset näkyvät velvoiteyhteenvedossa
- QGIS-tarkastelua varten on oma näkymä

## 6 Kompostointi-ilmoitukset

Tässä kappaleessa kuvataan kompostointi-ilmoitustietojen sekä kompostoinnin lopetusilmoitusten lukeminen tietokantaan ja kohdentaminen kohteille. Toteutus on julkaistu avoimena python-koodina osoitteessa [jkr.py](https://github.com/punosmobile/jkr-core/blob/9107d99c17b829f520f81a7b9c5d3268040188ec/jkrimporter/cli/jkr.py#L184) (funktiot `import_ilmoitukset` ja `import_lopetusilmoitukset`).

### 6.1 Kompostointi-ilmoitusten luku tietokantaan

Kompostointi-ilmoitukset luetaan Excel-tiedostosta (.xlsx), jossa yksi rivi vastaa yhtä ilmoitusta. Jokaisella rivillä on oltava seuraavat tiedot, jotta lukeminen onnistuu:
- Vastausaika (ilmoituksen jättöpäivä)
- Alkupvm (kompostoinnin aloituspäivä)
- Voimassaasti (kompostoinnin loppupäivä)
- Onko kimppa (tieto siitä, onko kyseessä useamman kiinteistön yhteinen kompostori)
- Vastuuhenkilön tiedot (sukunimi, etunimi, osoite, postinumero, postitoimipaikka)
- Sijainti_prt (rakennustunnus, jossa kompostori sijaitsee)
- Käyttäjän tiedot (sukunimi, etunimi) ja prt (rakennustunnus)

### 6.2 Kompostointi-ilmoitusten kohdentaminen

Kompostointi-ilmoitus kohdennetaan kohteille seuraavassa järjestyksessä:

1. Haetaan kompostorin sijainnin kohde rakennustunnuksen (sijainti_prt) perusteella
2. Luodaan tai päivitetään kompostorin vastuuhenkilö (osapuoli)
3. Haetaan kompostorin osoite_id rakennustunnuksen perusteella
4. Luodaan uusi kompostori tai käytetään olemassa olevaa:
   - Jos täsmälleen sama kompostori löytyy (sama alkupvm, loppupvm, osoite_id, onko_kimppa, osapuoli_id), käytetään sitä
   - Muuten luodaan uusi kompostori
5. Haetaan kompostorin käyttäjien kohteet rakennustunnusten (prt) perusteella
6. Lisätään kohteet kompostorin kohteiksi (kompostorin_kohteet)

Jos kohdentamisessa ilmenee ongelmia (esim. rakennusta ei löydy), tallennetaan tieto kohdentumattomista ilmoituksista erilliseen tiedostoon.

### 6.3 Kompostointi-ilmoituksista luotavat osapuolet

Kompostointi-ilmoituksista luodaan vain kompostorin vastuuhenkilö osapuoleksi. Muita käyttäjiä ei tallenneta osapuolina.

### 6.4 Kompostoinnin lopetusilmoitusten luku tietokantaan

Kompostoinnin lopetusilmoitukset luetaan Excel-tiedostosta (.xlsx), jossa yksi rivi vastaa yhtä ilmoitusta. Jokaisella rivillä on oltava seuraavat tiedot:
- Vastausaika (lopetusilmoituksen päivämäärä)
- Rakennustunnus (prt)

### 6.5 Kompostoinnin lopetusilmoitusten kohdentaminen

Lopetusilmoitus kohdennetaan kompostoreihin seuraavassa järjestyksessä:
1. Haetaan rakennuksen osoite_id rakennustunnuksen perusteella
2. Etsitään kaikki voimassaolevat kompostorit kyseisellä osoite_id:llä lopetusilmoituksen vastausajankohtana
3. Asetetaan löydetyille kompostoreille loppupäivämääräksi lopetusilmoituksen vastausaika

Jos kohdentamisessa ilmenee ongelmia (esim. rakennusta ei löydy tai voimassaolevia kompostoreita ei löydy), tallennetaan tieto kohdentumattomista lopetusilmoituksista erilliseen tiedostoon.

### 6.6 Kompostoinnin lopetusilmoituksista luotavat osapuolet

Lopetusilmoituksista ei luoda osapuolia. Niiden perusteella asetetaan vain kohteen voimassaoleville kompostoreille loppupäivämääräksi lopetusilmoituksen ajankohta.

## 7 Velvoitteet ja velvoitetarkistukset

Tässä kappaleessa kuvataan jätehuollon velvoitteiden tarkistaminen ja velvoitemallien toiminta. Velvoitetarkistukset suoritetaan automaattisesti kohteille määriteltyjen velvoitemallien mukaisesti.

### 7.1 Velvoitemallit

Velvoitemallit määrittelevät, mitä jätehuoltopalveluita kohteella tulee olla. Velvoitemalli koostuu seuraavista osista:
- Jätetyyppi (esim. sekajäte, biojäte, kartonki, metalli, lasi, muovi)
- Sääntö (kohteen ominaisuuksiin perustuva ehto, esim. huoneistomäärä ja sijainti erilliskeräysalueella)
- Täyttymissääntö (jätehuoltopalveluihin perustuva ehto, esim. tyhjennysväli ja kompostointi)
- Kuvaus (sanallinen kuvaus velvoitteesta)
- Voimassaoloaika (milloin velvoite on voimassa)

Velvoitemalleja on määritelty seuraaville jätetyypeille:
1. **Sekajäte**
   - Kaikilla kohteilla tulee olla sekajätteen keräys
   - Tyhjennysväli riippuu biojätteen keräyksestä ja kompostoinnista
   - Pidennetty tyhjennysväli vaatii erillisen päätöksen

2. **Biojäte**
   - Vähintään 5 huoneiston kiinteistöt erilliskeräysalueella
   - Alle 5 huoneiston kiinteistöt voivat kompostoida
   - Tyhjennysväli enintään 4 viikkoa

3. **Kartonki, muovi, lasi ja metalli**
   - Vähintään 5 huoneiston kiinteistöt hyötyjätteen erilliskeräysalueella
   - Tyhjennysvälit:
     - Kartonki ja muovi: enintään 12 viikkoa
     - Lasi ja metalli: enintään 26 viikkoa

### 7.2 Velvoitetarkistusten suorittaminen

Velvoitetarkistukset suoritetaan kohteille seuraavassa järjestyksessä:

1. **Kohteen perustiedot**
   - Tarkistetaan kohteen rakennusluokka ja huoneistojen lukumäärä
   - Tarkistetaan kohteen sijainti suhteessa erilliskeräysalueisiin

2. **Jätehuoltopalvelut**
   - Tarkistetaan voimassaolevat jätehuoltosopimukset
   - Huomioidaan sekä suorat sopimukset että kimppasopimukset
   - Tarkistetaan sopimusten tyhjennysvälit

3. **Kompostointi**
   - Tarkistetaan voimassaolevat kompostointi-ilmoitukset
   - Huomioidaan kompostoinnin vaikutus tyhjennysvälivaatimuksiin

4. **Viranomaispäätökset**
   - Tarkistetaan voimassaolevat poikkeamispäätökset
   - Huomioidaan päätösten vaikutus velvoitteisiin

### 7.3 Velvoitetarkistusten tulokset

Velvoitetarkistusten tulokset tallennetaan tietokantaan. Tulokset luokitellaan neljään kategoriaan:

1. **Kunnossa (vihreä)**
   - Kohteella on kaikki vaaditut palvelut
   - Tyhjennysvälit ovat sallituissa rajoissa
   - Mahdolliset poikkeamat perustuvat voimassaoleviin päätöksiin

2. **Väärä tyhjennysväli (keltainen)**
   - Palvelu on olemassa, mutta tyhjennysväli on liian pitkä
   - Pidennetty tyhjennysväli ilman voimassaolevaa päätöstä

3. **Puuttuu (oranssi)**
   - Vaadittu jätehuoltopalvelu puuttuu kokonaan
   - Ei voimassaolevaa sopimusta tai kimppasopimusta

4. **Ei velvoitetta (harmaa)**
   - Kohde ei sijaitse erilliskeräysalueella
   - Kohteella on alle 5 huoneistoa (hyötyjätteet)
   - Kohteella on voimassaoleva kompostointi-ilmoitus (biojäte)

### 7.4 Velvoiteyhteenvedot

Velvoiteyhteenvedot kokoavat yhteen kohteen kaikkien jätetyyppien velvoitetarkistusten tulokset. Yhteenvedot luokitellaan seuraavasti:

1. **Jätteenkuljetus kunnossa (vihreä)**
   - Kaikki vaaditut palvelut ovat kunnossa
   - Tyhjennysvälit ovat sallituissa rajoissa

2. **Puutteellinen jätehuolto (keltainen)**
   - Jokin palvelu puuttuu tai tyhjennysväli on väärä
   - Eritellään puuttuva jätetyyppi (esim. "biojäte puuttuu")

3. **Ei jätehuoltoa (oranssi)**
   - Sekajätteen keräys puuttuu kokonaan
   - Ei voimassaolevia jätehuoltosopimuksia

### 7.5 HAPA-aineiston vaikutus velvoitteisiin

HAPA-aineisto vaikuttaa kohteen tyyppiin ja sitä kautta velvoitteisiin. Kohdetyypin määräytyminen HAPA-aineiston perusteella noudattaa seuraavia sääntöjä:

1. **BIOHAPA-kohteet**
   - Jos kohteen rakennus on HAPA-aineistossa merkitty BIOHAPA-tyyppiseksi
   - Kohde ei sijaitse biojätteen erilliskeräysalueella
   - Kohdetyypiksi asetetaan BIOHAPA (6)

2. **HAPA-kohteet**
   - Jos kohteen rakennus on HAPA-aineistossa merkitty HAPA-tyyppiseksi
   - Kohde ei ole tyypiltään asuinkiinteistö
   - Kohdetyypiksi asetetaan HAPA (5)

3. **Asuinkiinteistöt**
   - Kohdetyyppi säilyy asuinkiinteistönä (7) jos:
     - Kohde on biojätteen erilliskeräysalueella TAI
     - Kohde on hyötyjätealueella ja siinä on vähintään 5 huoneistoa

Kohdetyypin muutokset vaikuttavat velvoitetarkistusten tuloksiin, koska eri kohdetyypeillä on erilaiset velvoitteet. HAPA- ja BIOHAPA-kohteilla voi olla lievemmät velvoitteet kuin tavallisilla asuinkiinteistöillä.

## 8 Jätehuollon seurantaraportti

Jätehuollon seurantaraportti koostuu seuraavista osista:
1. Kohteiden rakennustiedot
2. Kohteiden velvoitteet
3. Kohteiden kuljetukset
4. Kohteiden päätökset

### 8.1 Raportin kokoaminen

Raportin kokoamiseen käytetään seuraavia funktioita:

| Funktio | Kuvaus |
|---------|---------|
| `jkr.kohteiden_rakennustiedot()` | Kokoaa raporttiin kohteiden rakennustiedot-osuuden |
| `jkr.kohteiden_velvoitteet()` | Kokoaa raporttiin kohteiden velvoitteet-osuuden |
| `jkr.kohteiden_kuljetukset()` | Kokoaa raporttiin kohteiden kuljetukset-osuuden |
| `jkr.kohteiden_paatokset()` | Kokoaa raporttiin kohteiden päätökset-osuuden |

## Liite 1: Velvoitemallit

### Sekajätteen velvoitemallit

| Velvoite | Tulos | Rakennusluokka | Huoneistomäärä | Erilliskeräysalue | Palvelu | Tyhjennysväli | Kompostointi-ilmoitus | Päätös | Väri |
|----------|--------|----------------|-----------------|-------------------|----------|----------------|----------------------|---------|------|
| Sekajäte | Sekajäte kunnossa | 0-4 huoneistoa biojätteen erilliskeräysalue | - | - | Tyhjennysväli ≤4 viikkoa | - | - | - | Vihreä |
| Sekajäte | Sekajäte kunnossa | 0-4 huoneistoa biojätteen erilliskeräysalue | - | - | - | - | voimassa | - | Vihreä |
| Sekajäte | Sekajäte puuttuu | 0-4 huoneistoa biojätteen erilliskeräysalue | - | - | puuttuu | - | - | - | oranssi |

### Biojätteen velvoitemallit

| Velvoite | Tulos | Rakennusluokka | Huoneistomäärä | Erilliskeräysalue | Palvelu | Tyhjennysväli | Kompostointi-ilmoitus | Päätös | Väri |
|----------|--------|----------------|-----------------|-------------------|----------|----------------|----------------------|---------|------|
| Biojäte | Biojäte kunnossa | 0-4 huoneistoa biojätteen erilliskeräysalue | - | - | Tyhjennysväli ≤4 viikkoa | - | - | - | Vihreä |
| Biojäte | Biojäte kunnossa | 0-4 huoneistoa biojätteen erilliskeräysalue | - | - | - | - | voimassa | - | Vihreä |
| Biojäte | Biojäte puuttuu | ≥5 huoneistoa hyötyjätteiden erilliskeräysalue | - | - | puuttuu | - | - | - | oranssi |

### Muovipakkausten velvoitemallit

| Velvoite | Tulos | Rakennusluokka | Huoneistomäärä | Erilliskeräysalue | Palvelu | Tyhjennysväli | Kompostointi-ilmoitus | Päätös | Väri |
|----------|--------|----------------|-----------------|-------------------|----------|----------------|----------------------|---------|------|
| Muovi | Muovipakkaus puuttuu | - | ≥5 huoneistoa | hyötyjätteiden erilliskeräysalue | puuttuu | - | - | - | oranssi |
| Muovi | Muovipakkaus väärä tyhjennysväli | - | ≥5 huoneistoa | hyötyjätteiden erilliskeräysalue | - | Tyhjennysväli >12 viikkoa | - | - | keltainen |
| Muovi | Muovipakkaus kunnossa | - | ≥5 huoneistoa | hyötyjätteiden erilliskeräysalue | - | Tyhjennysväli ≤12 viikkoa | - | - | vihreä |

### Velvoiteyhteenvedot

| Velvoite | Tulos | Rakennusluokka | Huoneistomäärä | Erilliskeräysalue | Palvelu | Status | Kompostointi | Metalli | Lasi | Kartonki | Muovi | Väri |
|----------|--------|----------------|-----------------|-------------------|----------|---------|--------------|---------|------|-----------|--------|------|
| Velvoiteyhteenveto sekajäte väärä tyhjennysväli | Velvoiteyhteenveto sekajäte väärä tyhjennysväli | 0-4 huoneistoa biojätteen erilliskeräysalue | - | - | Sekajäte velvoite on saanut stauksen väärä tyhjennysväli | Palvelu löytyy | - | - | - | - | - | Vihreä |
| Velvoiteyhteenveto sekajäte väärä tyhjennysväli | Velvoiteyhteenveto sekajäte väärä tyhjennysväli | 0-4 huoneistoa biojätteen erilliskeräysalue | - | - | Sekajäte velvoite on saanut stauksen väärä tyhjennysväli | - | Voimassa | - | - | - | - | Vihreä |
| Velvoiteyhteenveto sekajäte väärä tyhjennysväli | Velvoiteyhteenveto sekajäte väärä tyhjennysväli | - | 0-4 huoneistoa muut alueet | ≥5 huoneistoa muut alueet | Sekajäte velvoite on saanut stauksen väärä tyhjennysväli | - | - | - | - | - | - | Vihreä |
| Velvoiteyhteenveto biojäte väärä tyhjennysväli | Velvoiteyhteenveto biojäte väärä tyhjennysväli | 0-4 huoneistoa biojätteen erilliskeräysalue | - | - | palvelu löytyy | Biojätevelvoite on saanut statuksen väärä tyhjennysväli | - | - | - | - | - | Vihreä |
| Velvoiteyhteenveto biojäte väärä tyhjennysväli | Velvoiteyhteenveto biojäte väärä tyhjennysväli | - | - | ≥5 huoneistoa hyötyjätteiden erilliskeräysalue | palvelu löytyy | Biojätevelvoite on saanut statuksen väärä tyhjennysväli | palvelu löytyy | palvelu löytyy | palvelu löytyy | palvelu löytyy | - | Vihreä |