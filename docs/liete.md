# JKR Liete - Määrittelydokumentti

> **Versio:** 17.11.2025  
> **Lähde:** Lietemäärittelyjen sanallinen kuvaus 17112025.docx, JKR Lietemäärittelyt 17112025.xlsx

---

## Sisällysluettelo

1. [Yleiskuvaus](#yleiskuvaus)
2. [Tietokantakentät](#tietokantakentät)
3. [Aineistot ja tietovirrat](#aineistot-ja-tietovirrat)
   - [Kuljetustiedot](#kuljetustiedot)
   - [Kaivotiedot](#kaivotiedot)
   - [Kaivotiedon lopetus](#kaivotiedon-lopetus)
   - [Viemäriverkosto](#viemäriverkosto)
   - [Viemäriverkoston lopetus](#viemäriverkoston-lopetus)
   - [Lietteen kompostointi-ilmoitus](#lietteen-kompostointi-ilmoitus)
4. [Lietevelvoitteet](#lietevelvoitteet)
5. [Tietojen siirtyminen kohteen vaihtuessa](#tietojen-siirtyminen-kohteen-vaihtuessa)
6. [Käyttöliittymän taulut](#käyttöliittymän-taulut)
7. [Raportointi](#raportointi)
8. [Kohdentaminen](#kohdentaminen)
9. [Virheraportointi](#virheraportointi)

---

## Yleiskuvaus

JKR Liete -moduuli käsittelee jätevesilietteiden kuljetustietoja, kaivotietoja, viemäriverkostoliittymiä ja lietevelvoitteita. Tiedot kohdennetaan rakennuksille pysyvän rakennustunnuksen (PRT) tai osoitetietojen perusteella.

---

## Tietokantakentät

Tietokantaan tarvitaan seuraavat kentät:

### Kuljetustiedot
| Kenttä | Kuvaus |
|--------|--------|
| `tyhjennyspaivamaara` | Lietteen tyhjennyksen päivämäärä |
| `jatelaji` | umpisäiliö / saostussäiliö / pienpuhdistamo / ei tiedossa |
| `tilavuus` | Tilavuus kuutioina (m³) |
| `lietteen_tyyppi` | musta / harmaa / ei tietoa |

### Viemäriverkosto
| Kenttä | Kuvaus |
|--------|--------|
| `viemariverkosto_alkupvm` | Viemäriverkostoliittymän alkamispäivämäärä |
| `viemariverkosto_loppupvm` | Viemäriverkostoliittymän päättymispäivämäärä |

### Kaivotiedot
| Kenttä | Kuvaus |
|--------|--------|
| `kantovesi_alkupvm` | Kantovesi-ilmoituksen alkupäivämäärä |
| `kantovesi_loppupvm` | Kantovesi-ilmoituksen loppupäivämäärä |
| `saostussailio_alkupvm` | Saostussäiliön alkupäivämäärä |
| `saostussailio_loppupvm` | Saostussäiliön loppupäivämäärä |
| `pienpuhdistamo_alkupvm` | Pienpuhdistamon alkupäivämäärä |
| `pienpuhdistamo_loppupvm` | Pienpuhdistamon loppupäivämäärä |
| `umpisailio_alkupvm` | Umpisäiliön alkupäivämäärä |
| `umpisailio_loppupvm` | Umpisäiliön loppupäivämäärä |
| `harmaat_vedet_alkupvm` | Vain harmaat vedet -tiedon alkupäivämäärä |
| `harmaat_vedet_loppupvm` | Vain harmaat vedet -tiedon loppupäivämäärä |

### Kompostointi
| Kenttä | Kuvaus |
|--------|--------|
| `lietteen_kompostointi_alkupvm` | Lietteen kompostointi-ilmoituksen alkupäivämäärä |
| `lietteen_kompostointi_loppupvm` | Lietteen kompostointi-ilmoituksen loppupäivämäärä |

### Velvoitteet
| Kenttä | Kuvaus |
|--------|--------|
| `jakso` | Velvoitetarkistuksen jakso |
| `lietevelvoite` | Velvoitteen tila |

---

## Aineistot ja tietovirrat

### Kuljetustiedot

**Lähde:** Siirtorekisteri (kuljetustiedot ja peltolevitys)

#### Vietävät kentät

| Lähteen sarake | JKR-kenttä | Huomio |
|----------------|------------|--------|
| Siirron alkamisaika | `tyhjennyspaivamaara` | |
| Jätteen kuvaus | `jatelaji` | umpisäiliö / saostussäiliö / pienpuhdistamo / ei tiedossa |
| Jätteen tilavuus (m³) | `tilavuus` | |
| Lietteen tyyppi | `lietteen_tyyppi` | musta / harmaa / ei tietoa |
| Kuljettaja | `kuljetusyritys` | Y-tunnus |
| Jätteen tuottaja tai muu haltija | `osapuoli_nimi` | |
| Jätteen tuottajan/haltijan katuosoite | `osapuoli_katuosoite` | |
| Jätteen tuottajan/haltijan postinumero | `osapuoli_postinumero` | |

#### Kohdentaminen

1. **Ensisijainen:** Pysyvä rakennustunnus (PRT)
2. **Toissijainen:** Siirron alkamispaikan katuosoite + postinumero

> **HUOM:** Kiinteistötunnusta EI käytetä kohdentamiseen.

#### Ei viedä tietokantaan
- ID-tunnus
- Jätteen tuottajan/haltijan osoite (yhdistelmäkenttä)
- Siirron alkamispaikka
- Vastaanottaja
- Siirron päättymispaikka ja -osoite
- Siirron päättymisaika
- Jätteen paino
- Kiinteistötunnus

---

### Kaivotiedot

**Lähde:** Kaivotietokysely (Salpakierto, Liete-kysely)

#### Vietävät kentät

| Lähteen sarake | JKR-kenttä | Huomio |
|----------------|------------|--------|
| Vastausaika | alkupvm | Viedään rivillä olevan kaivotiedon alkupäivämääräksi |
| PRT | - | Kohdentamiseen |
| Kantovesi | `kantovesi_alkupvm` | Jos ruksattu |
| Saostussäiliö | `saostussailio_alkupvm` | Jos ruksattu |
| Pienpuhdistamo | `pienpuhdistamo_alkupvm` | Jos ruksattu |
| Umpisäiliö | `umpisailio_alkupvm` | Jos ruksattu |
| Vain harmaat vedet | `harmaat_vedet_alkupvm` | Jos ruksattu |
| Tietolähde | `tietolahde` | Salpakierto / Liete-kysely |

#### Kohdentaminen

- **Pysyvä rakennustunnus (PRT)**

#### Päällekkäisyyden käsittely

Jos kohteella on jo sama tieto (esim. saostussäiliö alkupvm), uutta tietoa **ei viedä päälle** ja rivi jää kohdentumatta.

#### Ei viedä tietokantaan
- Etunimi, Sukunimi
- Katuosoite, Postinumero, Postitoimipaikka

---

### Kaivotiedon lopetus

**Tarkoitus:** Lopettaa olemassa olevan kaivotiedon.

#### Vietävät kentät

| Lähteen sarake | JKR-kenttä |
|----------------|------------|
| Vastausaika | loppupvm |
| Kantovesi | `kantovesi_loppupvm` |
| Saostussäiliö | `saostussailio_loppupvm` |
| Pienpuhdistamo | `pienpuhdistamo_loppupvm` |
| Umpisäiliö | `umpisailio_loppupvm` |
| Vain harmaat vedet | `harmaat_vedet_loppupvm` |

#### Kohdentaminen

- **Pysyvä rakennustunnus (PRT)**

#### Edellytykset

- Lopetus edellyttää, että kohteella on vastaava tieto alkanut
- Jos kohteella on useita samoja alkaneita kaivotietoja, lopetuspäivämäärä lopettaa **kaikki** vastaavat kaivotiedot

---

### Viemäriverkosto

**Lähde:** Viemäriverkostotiedot

#### Vietävät kentät

| Lähteen sarake | JKR-kenttä |
|----------------|------------|
| Viemäriverkosto alkupvm | `viemariverkosto_alkupvm` |
| Viemäriverkosto loppupvm | `viemariverkosto_loppupvm` |

#### Kohdentaminen

- **Pysyvä rakennustunnus (PRT)** - sarakkeet PRT, PRT2...PRT11

#### Ei viedä tietokantaan
- Nimi, Nimenjatke
- Lähiosoite, Postinumero, Postitoimipaikka
- Kiinteistötunnus, Maksajan nimi

---

### Viemäriverkoston lopetus

**Tarkoitus:** Lopettaa olemassa olevan viemäriverkostotiedon.

#### Vietävät kentät

| Lähteen sarake | JKR-kenttä |
|----------------|------------|
| Viemäriverkosto loppupvm | `viemariverkosto_loppupvm` |

#### Kohdentaminen

- **Pysyvä rakennustunnus (PRT)**

---

### Lietteen kompostointi-ilmoitus

**Lähde:** Lietteen kompostointi-ilmoitukset

> **HUOM:** Hylättyjä ilmoituksia ei viedä. Ne poistetaan aineistomuokkauksessa ennen vientiä.

#### Vietävät kentät

| Lähteen sarake | JKR-kenttä | Huomio |
|----------------|------------|--------|
| Vastausaika | `pienpuhdistamo_alkupvm` | Viedään kaivotietoihin |
| Lietteen kompostoijan yhteystiedot: Etunimi | `osapuoli_etunimi` | |
| Lietteen kompostoijan yhteystiedot: Sukunimi | `osapuoli_sukunimi` | |
| Lietteen kompostoijan yhteystiedot: Postiosoite | `osapuoli_katuosoite` | |
| Lietteen kompostoijan yhteystiedot: Postinumero | `osapuoli_postinumero` | |
| Ilmoitan lietteen kompostoinnista ajalla: Aloituspäivämäärä | `lietteen_kompostointi_alkupvm` | |
| Ilmoitan lietteen kompostoinnista ajalla: Loppumispäivämäärä | `lietteen_kompostointi_loppupvm` | |

#### Kohdentaminen

- **Pysyvä rakennustunnus (PRT)** - sarake "Tiedot kiinteistöstä, jonka liete kompostoidaan: PRT"

#### Päällekkäisyyden käsittely

Jos kohteella on jo "Pienpuhdistamo alkupvm", uutta tietoa **ei viedä päälle** ja rivi jää kohdentumatta.

---

## Lietevelvoitteet

### Velvoitetyypit ja värikoodit

| Velvoite | Väri | Kuvaus |
|----------|------|--------|
| **Viemäriverkostossa** | 🔵 Sininen | Kohde on viemäriverkostossa |
| **Vapautettu** | 🟢 Vihreä | Myönteinen perusmaksupäätös tai keskeytyspäätös voimassa |
| **Kantovesi** | 🟢 Vihreä | Kantovesi-ilmoitus voimassa |
| **Lietteenkuljetus kunnossa: saostussäiliö/pienpuhdistamo** | 🟢 Vihreä | Tyhjennys edellisen 1-5 kvartaalin aikana |
| **Lietteenkuljetus kunnossa: umpisäiliö/ei tietoa** | 🟢 Vihreä | Tyhjennys edellisen 1-9 kvartaalin aikana |
| **Lietteenkuljetus kunnossa: harmaat vedet** | 🟢 Vihreä | Tyhjennys edellisen 1-13 kvartaalin aikana |
| **Väärä tyhjennysväli: saostussäiliö/pienpuhdistamo** | 🟡 Keltainen | Tyhjennys 6-9 kvartaalin aikana |
| **Väärä tyhjennysväli: umpisäiliö/ei tietoa** | 🟡 Keltainen | Tyhjennys 10-13 kvartaalin aikana |
| **Väärä tyhjennysväli: harmaat vedet** | 🟡 Keltainen | Tyhjennys 14-17 kvartaalin aikana |
| **Ei lietteenkuljetusta: saostussäiliö/pienpuhdistamo** | 🔴 Punainen | Ei tyhjennystä viimeisen 9 kvartaalin aikana |
| **Ei lietteenkuljetusta: umpisäiliö/ei tietoa** | 🔴 Punainen | Ei tyhjennystä viimeisen 13 kvartaalin aikana |
| **Ei lietteenkuljetusta: harmaat vedet** | 🔴 Punainen | Ei tyhjennystä viimeisen 17 kvartaalin aikana |

### Velvoitteen laskentasäännöt

#### Edellytykset velvoitteelle
- **Kiinteistötyyppi:** Asuminen tai hapa tai biohapa
- **Viemäriverkosto:** Ei (paitsi "Viemäriverkostossa"-velvoite)

#### Tyhjennysvälit kaivotyypin mukaan

| Kaivotyyppi | Kunnossa | Väärä väli | Ei kuljetusta |
|-------------|----------|------------|---------------|
| Saostussäiliö / Pienpuhdistamo | 1-5 kvartaalia | 6-9 kvartaalia | >9 kvartaalia |
| Umpisäiliö / Ei tietoa | 1-9 kvartaalia | 10-13 kvartaalia | >13 kvartaalia |
| Harmaat vedet | 1-13 kvartaalia | 14-17 kvartaalia | >17 kvartaalia |

#### Poikkeukset
- **Vapautettu:** Myönteinen perusmaksupäätös tai keskeytyspäätös kaikilla kohteen velvoiterakennuksilla
- **Kantovesi:** Kantovesi-ilmoitus voimassa, ei perusmaksupäätöstä
- **Kompostointi:** Jos pienpuhdistamo ja voimassa oleva kompostointi-ilmoitus → kunnossa

---

## Tietojen siirtyminen kohteen vaihtuessa

| Tieto | Siirtyy uudelle kohteelle |
|-------|---------------------------|
| Kantovesi-ilmoitus | ✅ Kyllä |
| Kuljetustieto | ✅ Kyllä |
| Umpisäiliö | ✅ Kyllä |
| Saostussäiliö | ✅ Kyllä |
| Pienpuhdistamo | ✅ Kyllä |
| Viemäriverkosto | ✅ Kyllä |
| Harmaat vedet | ✅ Kyllä |
| **Lietteen kompostointi-ilmoitus** | ❌ **Ei siirry** |

---

## Käyttöliittymän taulut

### Liete kuljetustiedot -taulu

| Kenttä | Sisältö | Huomio |
|--------|---------|--------|
| Tyhjennyspäivämäärä | pvm | Vanhat tiedot sivulle kuten kiinteän kuljetustiedoissa |
| Jätelaji | umpisäiliö / saostussäiliö / pienpuhdistamo / ei tiedossa | |
| Tilavuus | m³ | |
| Lietteen tyyppi | musta / harmaa / ei tietoa | |

### Liete-taulu

| Kenttä | Sisältö | Huomio |
|--------|---------|--------|
| Viemäriverkostoliittymä | Viemäriverkossa | Voimassa oleva |
| Viemäriverkosto alkupvm | pvm | |
| Kantovesi-ilmoitus | Kantovesi | Voimassa oleva |
| Kantovesi-ilmoitus alkupvm | pvm | |
| Lietteen kompostointi-ilmoitus | Lietteen kompostointi-ilmoitus | Uusin (voimassa tai päättynyt) |
| Lietteen kompostointi alkupvm | pvm | |
| Saostussäiliö | Saostussäiliö | Voimassa oleva |
| Saostussäiliö alkupvm | pvm | |
| Pienpuhdistamo | Pienpuhdistamo | Voimassa oleva |
| Pienpuhdistamo alkupvm | pvm | |
| Umpisäiliö | Umpisäiliö | Voimassa oleva |
| Umpisäiliö alkupvm | pvm | |
| Vain harmaita vesiä | Vain harmaita vesiä | Voimassa oleva |
| Harmaat vedet alkupvm | pvm | |

### Lietevelvoite-taulu

| Kenttä | Sisältö | Huomio |
|--------|---------|--------|
| Jakso | pvm | Viimeisimmän kyselyn pvm |
| Lietevelvoite | Velvoitteen nimi | Viimeisin positiivinen tulos, vanhat sivuun selattavaksi |

---

## Raportointi

### Raportin rajaustekijät

| Rajaustekijä | Kuvaus |
|--------------|--------|
| Tarkastelupvm | Rajaa kuljetustiedon, kohteiden ja päätöstietojen voimassaolon |
| Kohdetyyppi | asuinkiinteistö / hapa / biohapa / muu |
| Viemäriverkostossa | Viemäriverkostossa / tyhjä |
| Kunta | Kohteen rakennuksen 1 sijaintikunta |
| Huoneistolukumäärä | Kohteen rakennusten yhteenlaskettu huoneistolukumäärä |
| Velvoitteen tallennuspvm | Milloin velvoite on ajettu |
| Yli 10 000 taajama | SYKE taajaman nimi |
| 200 asukkaan taajama | SYKE taajaman nimi |

### Raportin sisältö

#### Kohteen tiedot
- Kohde id
- Osapuolet (kompostointi-ilmoituksen tekijä, kuljetuksen tilaajat, omistajat, vanhin asukas)
- Kaivotiedot (kantovesi, saostussäiliö, umpisäiliö, pienpuhdistamo, kompostoi, harmaat vedet)

#### Lietteen velvoitteet
- Velvoiteyhteenveto liete (kaikki velvoitetyypit)

#### Lietteen kuljetustiedot
- Saostussäiliö (viimeisin tyhjennys 5 vuotta)
- Umpisäiliö (viimeisin tyhjennys 5 vuotta)
- Pienpuhdistamo (viimeisin tyhjennys 5 vuotta)
- Lietetyyppi ei tiedossa (viimeisin tyhjennys 5 vuotta)
- Kuljetusliikkeen nimi

#### Päätöstiedot ja ilmoitustiedot
- Kompostoi (voimassaolon päättymispäivämäärä)
- Perusmaksupäätös
- Tyhjennysvälipäätös
- AKP-kohtuullistaminen
- Keskeytys
- Erilliskeräysvelvoitteesta poikkeaminen

#### Kohteen rakennustiedot
- PRT (max 17 kpl)
- Käyttötila, käyttötarkoitus, rakennusluokka
- Katuosoite, postinumero, postitoimipaikka
- Sijaintikiinteistö
- X- ja Y-koordinaatit

---

## Kohdentaminen

### Kohdentamisen prioriteetti

1. **Ensisijainen:** Pysyvä rakennustunnus (PRT)
2. **Toissijainen:** Siirron alkamispaikan katuosoite + postinumero

### Kohdentaminen aineistotyypeittäin

| Aineisto | Kohdentamiskenttä |
|----------|-------------------|
| Kuljetustiedot | PRT tai katuosoite + postinumero |
| Kaivotiedot | PRT |
| Kaivotiedon lopetus | PRT |
| Viemäriverkosto | PRT (PRT...PRT11) |
| Viemäriverkoston lopetus | PRT |
| Lietteen kompostointi | PRT |

---

## Virheraportointi

### Kohdentumattomien rivien raportointi

- Kohdentumattomista riveistä tuotetaan **virheraportti**
- Sarakkeiden otsikot ja tietosisältö sama kuin sisään ajetussa aineistossa

### Poikkeukset virheraportoinnissa

Virheraporttia **ei tuoteta** seuraavissa tapauksissa:
- Kaivotiedot, jos kohteella on jo sama alkupvm
- Viemäriverkostotiedot, jos kohteella on jo sama alkupvm

---

## QGIS-näkymä

- Lietevelvoitteet omalla karttatasollaan, erillään kiinteän jätteen velvoitteista
- Viemäriverkostoalue karttarajauksena näkyviin

---

## Pseudonymisointi

### EI pseudonymisoida
- Kuljettaja (Y-tunnus)
- Vastaanottaja
- Siirron päättymispaikan katuosoite

### Pseudonymisoidaan
- Jätteen tuottaja tai muu haltija
- Siirron alkamispaikan katuosoite
- Kaikki henkilötiedot (etunimi, sukunimi)
