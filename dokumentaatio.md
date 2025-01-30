# Järjestelmädokumentaatio

## Sisällysluettelo
1. [Johdanto](#1-johdanto)
2. [Järjestelmän yleiskuvaus](#2-järjestelmän-yleiskuvaus)
   1. [Ympäristö](#21-ympäristö)
   2. [Tietokannat ja tietomalli](#22-tietokannat-ja-tietomalli)
3. [Kohteiden luonti ja päivittäminen DVV-aineistosta](#3-kohteiden-luonti-ja-päivittäminen-dvv-aineistosta)
   1. [DVV-aineiston lisääminen ja päivittäminen](#31-dvv-aineiston-lisääminen-ja-päivittäminen)
   2. [Perusmaksukohteiden luonti](#32-perusmaksukohteiden-luonti)
   3. [Kohteiden luonti](#33-kohteiden-luonti)
   4. [Kohteiden nimeäminen](#34-kohteiden-nimeäminen)
   5. [DVV-aineistosta muodostettavat osapuolen roolit](#35-dvv-aineistosta-muodostettavat-osapuolen-roolit)
   6. [Huoneistomäärän päivitys](#36-huoneistomäärän-päivitys)
   7. [HAPA-aineiston tuonti](#37-hapa-aineiston-tuonti)
4. [Kuljetustiedot](#4-kuljetustiedot)
   1. [Kuljetustietojen tuonti](#41-kuljetustietojen-tuonti)
   2. [Jätelaji- ja sopimusluokat](#42-jäte-ja-sopimusluokat)
   3. [Keräysvälineet ja tyhjennykset](#43-keräysvälineet-ja-tyhjennykset)
   4. [Keskeytykset](#44-keskeytykset)
   5. [Velvoitteiden ja tietojen kvartaalipäivitys](#45-velvoitteiden-ja-tietojen-kvartaalipäivitys)
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

### 3.1 DVV-aineiston lisääminen ja päivittäminen

DVV-aineiston käsittely tapahtuu seuraavassa järjestyksessä:

1. Taajamarajaukset
   ```bash
   sh import_taajama.sh 2020-01-01
   ```

2. Kunnat ja postinumerot
   ```bash
   psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_posti.sql
   ```

3. DVV-aineiston tuonti

   DVV-aineiston tuontiin käytetään käyttöjärjestelmästä riippuen joko:
   - Windows: `scripts/import_dvv.bat`
   - Linux/Mac: `scripts/import_dvv.sh`

   Huom: Tietokantayhteyden tiedot (HOST, PORT, DB_NAME, USER) määritellään skriptissä. Salasana tulee määritellä `%APPDATA%\postgresql\pgpass.conf` tiedostossa.

### 3.2 Perusmaksukohteiden luonti

Perusmaksukohteiden luonti tapahtuu ensimmäisenä ennen muiden kohteiden luontia. Prosessi etenee seuraavasti:

1. Haetaan rakennukset, joilla ei ole voimassaolevaa kohdetta annetulle aikavälille
2. Luetaan perusmaksurekisterin Excel-tiedosto, joka sisältää asiakasnumerot ja rakennusten PRT-tunnukset
3. Ryhmitellään rakennukset asiakasnumeron perusteella
4. Luodaan yksi kohde jokaiselle asiakasnumeroryhmälle, joka sisältää kaikki kyseisen asiakasnumeron rakennukset
5. Kohteille asetetaan kiinteä loppupäivämäärä (31.12.2100)

Kohteiden luonti suoritetaan komennolla:
```bash
jkr create_dvv_kohteet 28.1.2022 ../data/Perusmaksuaineisto.xlsx
```

### 3.3 Kohteiden luonti

Kohteiden luonti DVV-aineistosta tapahtuu seuraavasti:

1. Haetaan rakennukset, joilla ei ole voimassaolevaa kohdetta annetulle aikavälille
2. Rakennukset ryhmitellään kiinteistötunnuksen perusteella
3. Kiinteistön rakennukset jaetaan klustereihin seuraavien ehtojen perusteella:
   - Etäisyys toisistaan max 300m JA
   - Samat omistajat/asukkaat JA
   - Sama osoite

4. Klusteroidut rakennukset käsitellään seuraavasti:
   - Jos kaikki rakennukset ovat saman asunto-osakeyhtiön omistamia, luodaan yksi kohde
   - Muuten käsitellään omistajittain:
     * Ensimmäinen kohde sisältää eniten rakennuksia omistavan omistajan rakennukset
     * Toinen kohde sisältää toiseksi eniten rakennuksia omistavan rakennukset
     * Prosessi jatkuu kunnes kaikilla rakennuksilla on kohde
     * Ilman omistajaa olevat rakennukset saavat oman kohteensa

5. Saman omistajan rakennukset erotellaan osoitteen perusteella, paitsi jos kyseessä on asunto-osakeyhtiö

### 3.4 Kohteiden nimeäminen

Kohteen nimeäminen priorisoidaan seuraavassa järjestyksessä:
1. Asunto-osakeyhtiön nimi
2. Yrityksen nimi 
3. Yhteisön nimi
4. Vanhimman asukkaan nimi
5. Omistajan nimi

Jos mitään edellä mainituista ei löydy, kohde nimetään "Tuntematon".

### 3.5 DVV-aineistosta muodostettavat osapuolen roolit

DVV-aineistosta luodaan seuraavat osapuolten roolit:

#### Omistajat ja asukkaat
- OMISTAJA
- VANHIN_ASUKAS

#### Jätehuollon tilaajat
- SEKAJATE_TILAAJA
- BIOJATE_TILAAJA
- MUOVI_TILAAJA
- KARTONKI_TILAAJA
- LASI_TILAAJA
- METALLI_TILAAJA
- MONILOKERO_TILAAJA
- LIETE_TILAAJA

#### Kimppaisännät
- SEKAJATE_KIMPPAISANTA
- BIOJATE_KIMPPAISANTA
- MUOVI_KIMPPAISANTA
- KARTONKI_KIMPPAISANTA
- LASI_KIMPPAISANTA
- METALLI_KIMPPAISANTA

#### Kimppaosakkaat
- SEKAJATE_KIMPPAOSAKAS  
- BIOJATE_KIMPPAOSAKAS
- MUOVI_KIMPPAOSAKAS
- KARTONKI_KIMPPAOSAKAS
- LASI_KIMPPAOSAKAS
- METALLI_KIMPPAOSAKAS

#### Muut roolit
- KOMPOSTI_YHTEYSHENKILO

Osapuolten lajit:
- ASOY (Asunto-oy tai asunto-osuuskunta)
- JULKINEN (Valtio- tai kuntaenemmistöinen yritys)

### 3.6 Huoneistomäärän päivitys

Huoneistomäärän päivitys tapahtuu seuraavasti:

1. Tuodaan huoneistomäärätiedot:
   ```bash
   ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" -nln huoneistomaara ../data/Huoneistomäärät_2022.xlsx "Huoneistolkm"
   ```

2. Päivitetään huoneistomäärät:
   ```bash
   psql -h $JKR_DB_HOST -p $JKR_DB_PORT -d $JKR_DB -U $JKR_USER -f update_huoneistomaara.sql
   ```

### 3.7 HAPA-aineiston tuonti

HAPA-aineisto tuodaan seuraavalla komennolla:
```bash
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "\copy jkr.hapa_aineisto(rakennus_id_tunnus, kohde_tunnus, sijaintikunta, asiakasnro, rakennus_id_tunnus2, katunimi_fi, talon_numero, postinumero, postitoimipaikka_fi, kohdetyyppi) FROM '../data/Hapa-kohteet_aineisto_2022.csv' WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8', NULL '');"
```

## 4 Kuljetustiedot

### 4.1 Kuljetustietojen tuonti

Kuljetustietojen tuonti tapahtuu seuraavasti:

1. Kuljetustiedot tuodaan siirtotiedostosta, joka sisältää:
   - Asiakasnumerot
   - Sopimustiedot
   - Tyhjennystapahtumat
   - Toimituspaikat
   - Keskeytykset

2. Jokaiselle asiakkaalle tallennetaan:
   - Asiakasnumero
   - Voimassaoloaika
   - Haltijan tiedot
   - Yhteyshenkilön tiedot
   - Kiinteistötunnukset
   - Rakennustunnukset
   - Sopimukset
   - Tyhjennystapahtumat

### 4.2 Jätelaji- ja sopimusluokat

#### Jätelajit
- Sekajäte
- Biojäte
- Lasi
- Paperi
- Kartonki
- Muovi
- Metalli
- Liete (harmaa- ja mustaliete)
- Pahvi
- Energia

#### Sopimustyypit
- Tyhjennyssopimus
- Kimppasopimus
- Aluekeräyssopimus
- Putkikeräyssopimus

### 4.3 Keräysvälineet ja tyhjennykset

#### Keräysvälinetyypit
- Pintakeräys
- Syväkeräys
- Sakokaivo
- Umpikaivo
- Rullakko
- Säiliö
- Pienpuhdistamo
- Pikakontti
- Nostokontti
- Vaihtolava
- Jätesäkki
- Puristinsäiliö
- Puristin
- Vaihtolavasäiliö
- Paali
- Monilokero

#### Tyhjennystapahtuman tiedot
- Jätelaji
- Alkupäivämäärä
- Loppupäivämäärä
- Tyhjennyskerrat
- Tilavuus
- Massa

### 4.4 Keskeytykset

Sopimuksille voidaan tallentaa keskeytyksiä, jotka sisältävät:
- Alkupäivämäärä
- Loppupäivämäärä
- Selite

### 4.5 Velvoitteiden ja tietojen kvartaalipäivitys

Velvoitteiden ja tietojen päivitys tapahtuu kvartaaleittain seuraavassa järjestyksessä:

1. Päivitetään velvoitteet:
   ```bash
   # Tarkistaa ja päivittää millaisia velvoitteita kohteella on
   psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "SELECT jkr.update_velvoitteet();"
   ```

2. Tuodaan kvartaalin tiedot (esimerkki Q1 2022):

   a) Päätösten tuonti:
   ```bash
   jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/Q1/Paatokset_2022Q1.xlsx
   ```

   b) Kompostointi-ilmoitusten tuonti:
   ```bash
   jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/Q1/Kompostointi-ilmoitus_2022Q1.xlsx
   ```

   c) Kompostoinnin lopetusilmoitusten tuonti:
   ```bash
   jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/Q1/Kompostoinnin_lopettaminen_2022Q1.xlsx
   ```

   d) Kuljetustietojen tuonti:
   ```bash
   jkr import ../data/Kuljetustiedot/Kuljetustiedot_2022/Q1 LSJ 1.1.2022 31.3.2022
   ```

3. Tallennetaan kvartaalin velvoitestatukset:
   ```bash
   # Tallentaa velvoitteiden tilan kvartaalin lopussa
   psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "select jkr.tallenna_velvoite_status('2022-03-31');"
   ```

Vastaavat komennot toistetaan muille kvartaaleille (Q2, Q3, Q4) päivämääriä muuttaen:
- Q2: 1.4.2022 - 30.6.2022
- Q3: 1.7.2022 - 30.9.2022
- Q4: 1.10.2022 - 31.12.2022

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