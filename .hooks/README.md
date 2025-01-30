# Git Hooks

Tämä hakemisto sisältää projektin Git hookit. Ottaaksesi hookit käyttöön, suorita seuraava komento projektin juurihakemistossa:

```bash
git config core.hooksPath .hooks
```

## Pre-commit hook

Pre-commit hook estää arkaluontoisen datan committaamisen. Se tarkistaa seuraavat kielletyt termit:
- PRIVATE_KEY
- API_SECRET
- password=
- PASSWORD=
- apikey=

Jos haluat commitoida tiedoston joka sisältää jonkin kielletyistä termeistä, lisää tiedoston polku `.allowCommit` tiedostoon (yksi tiedosto per rivi).
