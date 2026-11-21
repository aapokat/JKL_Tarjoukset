# Jyväskylän tarjoukset

Jyväskylän kauppojen tarjoukset yhdellä sivulla: kuvat, haku, kauppa- ja tuoteryhmärajaukset,
hintavertailu saman tuotteen välillä ja hintavahdit sähköposti-ilmoituksilla.

Pohjana on Ylivieskan tarjoukset -sivu, mutta tämä versio on tehty Jyväskylään ja rakennettu osin uudelleen.

## Mitä sivulla on

- **Vain myymäläalennukset, vähintään 20 %.** Pienemmät alennukset ja tuotteet, joille kauppa ei kerro normaalihintaa, jätetään
  pois (`minDiscountPercent` tiedostossa `site/data/stores.json`). Sivulla voi tiukentaa rajaa 30, 40, 50 tai 70 prosenttiin.
- **Kaupat:** kaikki 25 Jyväskylän K-kauppaa (Citymarketit, Supermarketit ja K-Marketit, myös K-Ruoka-sovelluksen mobiiliedut),
  Prismat ja verkkokaupalliset S-marketit, Lidl, Tokmanni, Kärkkäinen (Jyväskylän myymälä) ja Rusta. Kaupat valitaan `site/data/stores.json`-tiedostossa.
- **Tuotekuvat** jokaisessa kortissa, ja etusivun yläosassa päivän isoimmat alet.
- **Saman tarjouksen yhdistäminen**: ketjun tarjous, joka on voimassa monessa kaupassa, on yksi kortti ("8 kauppaa").
- **Hintavertailu**: jos sama tuote (sama EAN) on tarjouksessa eri hinnoilla, halvin saa vihreän "Edullisin"-merkin.
- **Suosikit**: sydän kortin kuvassa. Suosikit säilyvät selainistunnon ajan (sessionStorage), ja niillä on oma näkymänsä.
- **Rajaukset**: tuoteryhmä, kaupat ketjuittain tai kauppa kerrallaan, alennusraja ja järjestys. Valinnat muistetaan selaimessa.
- **Hintavahdit** viidellä tavalla: hakusana, tuoteperhe tai merkki, tuoteryhmä, kauppa tai tietty tuote (kortin "Vahdi"-napista).
  Sivua käytetään ilman kirjautumista: vahdit tallentuvat selaimeen. Sähköpostiosoitteen antamalla vahti hälyttää myös sähköpostiin.

### Mitä ei ole mukana ja miksi

- **S-kauppojen tuotteet, joita ei myydä verkossa**, ja kaupat ilman verkkokauppaa (esim. S-market Mäki-Matti, Sale Kortepohja).
  S-ryhmällä ei ole julkista näköislehteä: Prisman mukaan myymälöiden omat tarjoukset näkyvät paikallislehtien mainoksissa ja somessa.
- **Näköislehdet** muilta osin: K-kauppojen, Lidlin ja Tokmannin lehtien tarjoukset tulevat jo mukaan kauppojen omista tarjousrajapinnoista,
  joten lehtien kuvista lukeminen ei toisi lisää vaan pelkkiä lukuvirheitä.
- **Puuilo ja Motonet**: niiden kampanjatuotteilla ei ole normaalihintaa, joten alennusprosenttia ei voi laskea.
- **Jula**: tiedot olisivat hyvät, mutta tuotelistan jatko latautuu rajapinnasta, jota ei vielä ole selvitetty.
- **Henkilökohtaiset edut** (S-mobiili, OmaPlussa) ovat jokaisella omat.

## Rakenne

- **GitHub Actions** (`.github/workflows/site.yml`) hakee tarjoukset joka toinen aamu klo 05.20 UTC (talvella 7.20, kesällä 8.20 Suomen aikaa), committaa datan, rakentaa sivun
  (`python3 site/build.py`) ja julkaisee kansion `public/` **GitHub Pagesiin**. Sama workflow julkaisee sivun uudelleen jokaisesta
  pushista mainiin.
- **Ajastettu funktio** `vahdit-tarkistus` ajetaan joka aamu klo 06.40 UTC (8.40 tai 9.40 Suomen aikaa) ja lähettää sähköpostit.

| Lähde | Miten | Tiedosto |
| --- | --- | --- |
| S-kaupat (Prismat, S-marketit) | `fetch_offers.py` lukee api.s-kaupat.fi:tä, kauppakohtaiset hinnat | `data/offers.json` |
| Lidl, Kärkkäinen, Tokmanni, Rusta | `fetch_offers.py` | `data/offers.json` |
| K-Ruoka (K-Citymarketit, K-Supermarketit) | Cloudflare estää skriptit, joten haku tehdään oikealla selaimella: `collect_browser.py` (Playwright) tai `collectors/k-ruoka.js` selaimen konsolissa | `data/k-ruoka-snapshot.json` |

Actions yrittää myös K-Ruokaa Playwrightilla. Jos Cloudflare estää sen, edellinen K-haku jää voimaan ja sivu kertoo sen päivämäärän.
Jos jokin muu kauppa ei vastaa, sen edellisen haun tarjoukset pidetään, eikä yksi rikki mennyt kauppa kaada muita.

## Käyttöönotto GitHub Pagesissa

1. Repon **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. **Settings → Actions → General → Workflow permissions: Read and write**, jotta päivittäinen haku voi committaa datan.
3. **Actions → Päivitä ja julkaise → Run workflow**. Sivu tulee osoitteeseen `https://alet.aaje.fi/`.

GitHub Pages on ilmainen eikä rajoita julkaisujen määrää. Netlifyn ilmaistaso ei sovi tähän: jokainen julkaisu maksaa
15 krediittiä 300:sta kuukaudessa, ja tarjoukset julkaistaan joka päivä.

## Android-sovellus

Lataus: https://github.com/aapokat/JKL_Tarjoukset/releases/download/android-latest/jkl-tarjoukset.apk
(puhelimessa pitää sallia asennus tuntemattomista lähteistä).

- Sovellus avaa saman sivun (`android/`, Java, WebView), joten sivun muutokset näkyvät siinä heti ilman uutta APK:ta.
- Suosikit säilyvät pysyvästi, ja niiden voimassaolo näkyy kortissa ("Päättyy huomenna", "Päättynyt").
- `OfferWorker` hakee `offers.json`:n noin 3 tunnin välein ja ilmoittaa vahtien osumista, uusista aleista usein
  katsottujen tuotteiden kaltaisista tuotteista ja tallennetuista tarjouksista, jotka päättyvät tänään tai huomenna.
  Katseluhistoria (avatut, tallennetut ja vahditut tuotteet) pysyy puhelimessa; sen voi tyhjentää Hintavahdit-paneelista.
- `.github/workflows/android.yml` rakentaa APK:n aina kun `android/`-kansio muuttuu ja vaihtaa sen yllä olevaan osoitteeseen.
- Allekirjoitusavain `android/app/debug.keystore` on repossa, jotta uusi versio asentuu vanhan päälle. Koska repo on julkinen,
  oman avaimen voi siirtää salaisuuksiin: `APP_KEYSTORE_B64` (avain base64-muodossa), `APP_KEYSTORE_PASSWORD`, `APP_KEY_ALIAS`,
  `APP_KEY_PASSWORD`. Avaimen vaihto vaatii sovelluksen poistamisen ja uudelleenasennuksen kerran.

## Hintavahdit

Vahdit tallentuvat käyttäjän selaimeen (localStorage), eikä niitä lähetetä minnekään. Kun käyttäjä palaa sivulle,
sivu vertaa vahtien nykyisiä osumia edellisen käynnin osumiin ja kertoo uusista ("Vahtisi löysivät 4 uutta tarjousta").
Puhelinilmoitukset tulevat Android-sovelluksesta. Sähköposti-ilmoitukset poistettiin: niiden ilmainen lähetys ei
riittäisi noin sadalle käyttäjälle luotettavasti.

## K-kaupat omalta koneelta

K-Ruoka (Cloudflare) estää GitHubin palvelimet, joten K-kauppojen tarjoukset kerää kotona aina päällä oleva
Windows-kone (`tools/windows/`). Se avaa k-ruoka.fi:n Edgessä, ajaa keräimen (`site/collectors/k-ruoka.js`)
kaikille kaupoille, tallentaa `site/data/k-ruoka-snapshot.json`:n ja pushaa sen. Push julkaisee sivun.

1. Asenna Git (git-scm.com) ja Python (python.org, rasti kohtaan *Add python.exe to PATH*).
2. `git clone https://github.com/aapokat/JKL_Tarjoukset.git C:\JKL_Tarjoukset` ja `cd C:\JKL_Tarjoukset`
3. `powershell -ExecutionPolicy Bypass -File tools\windows\asenna.ps1` (asentaa Playwrightin ja ajastuksen joka toiselle aamulle)
4. Aja kerran käsin: `powershell -ExecutionPolicy Bypass -File tools\windows\kerays.ps1`. Ensimmäinen push avaa
   GitHub-kirjautumisen, joka tallentuu Windowsin tunnuksiin.

Ajastus ajaa keräyksen kirjautuneena käyttäjänä, koska keräys avaa selainikkunan. Viimeisimmän ajon tuloste on
`tools\windows\kerays.log`. Jos keräys epäonnistuu, sivulle jää edellinen K-haku ja sen päivämäärä näkyy sivun alalaidassa.

## Jos kaupan sivusto muuttuu

Rustan kampanjasivun osoite on `stores.json`-tiedostossa (`rustaCampaignUrl`). Jos Rusta vaihtaa sen, päivitä osoite sinne.


S-kaupat käyttää GraphQL-kyselyä, jonka tunniste (`skaupatQueryHash` tiedostossa `stores.json`) voi vaihtua, kun sivusto päivittyy.
Silloin `fetch_offers.py` kertoo virheen ja käyttää edellistä hakua. Uuden tunnisteen saa avaamalla s-kaupat.fi:n hakusivun,
F12 → Network, suodatus `RemoteFilteredProducts`, ja kopioimalla pyynnön `sha256Hash`-arvon. Varalla on myös
`collectors/s-kaupat.js`, joka toimii samalla tavalla kuin K-Ruokan keräin.

## Tiedostot

| Tiedosto | Mitä tekee |
| --- | --- |
| `site/data/stores.json` | Mitkä K- ja S-kaupat haetaan (kaupan tunnus → nimi). |
| `site/fetch_offers.py` | Hakee skriptillä luettavat kaupat. Vain Pythonin vakiokirjasto. `python site/fetch_offers.py lidl` hakee vain yhden lähteen. |
| `site/collect_browser.py` | Ajaa `collectors/k-ruoka.js`:n oikeassa selaimessa (Playwright). |
| `site/collectors/*.js` | Selainkeräimet K-Ruokalle (myös mobiiliedut) ja (varalla) S-kaupoille. |
| `site/catalog.py` | Yhteiset tuoteryhmät: kauppojen omat kategoriat ja tuotenimet → 19 ryhmää. |
| `site/build.py` | Yhdistää datan ja samat tarjoukset, laskee hintavertailun ja kirjoittaa `public/index.html` ja `public/offers.json`. Lisäksi `preview.html`, jossa data on sivun sisällä. |
| `site/template.html` | Sivu. |
| `android/` | Android-sovellus (WebView + taustatarkistus ja ilmoitukset). |
| `tools/windows/` | K-keräys kotikoneelta ja sen ajastus. |

Tarjousrivi kauppojen hakutiedostoissa: `[kauppa, kaupan kategoria, nimi, hinta, yksikkö, normaalihinta, alennus-%, huomautus, voimassa, linkki, kuva, tuotetunnus, merkki]`.

## Paikallinen kehitys

```
python3 site/build.py      # kirjoittaa public/ ja preview.html (data sivun sisällä, avautuu suoraan selaimessa)
python3 -m http.server -d public 8000
```

Hinnat kopioidaan kauppojen omilta sivuilta. Tarkista hinta aina kaupassa.
