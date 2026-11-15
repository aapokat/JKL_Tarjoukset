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

- **GitHub Actions** (`.github/workflows/site.yml`) hakee tarjoukset joka aamu klo 03.17 UTC, committaa datan, rakentaa sivun
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
3. **Actions → Päivitä ja julkaise → Run workflow**. Sivu tulee osoitteeseen `https://aapokat.github.io/JKL_Tarjoukset/`.

GitHub Pages on ilmainen eikä rajoita julkaisujen määrää. Netlifyn ilmaistaso ei sovi tähän: jokainen julkaisu maksaa
15 krediittiä 300:sta kuukaudessa, ja tarjoukset julkaistaan joka päivä.

Sähköposti-ilmoitukset tarvitsevat palvelimen, jota GitHub Pagesissa ei ole. Ilman sitä vahdit toimivat selaimessa (osumat
merkitään sivulla), ja sähköpostikenttä on piilossa. Kun vahtipalvelu on pystyssä, sen osoite laitetaan repon muuttujaan
**Settings → Secrets and variables → Actions → Variables → `ALERT_API`**, ja seuraava julkaisu ottaa sen käyttöön.
Kansion `netlify/` funktiot ovat valmiina, jos sivu joskus siirretään maksulliselle Netlify-tasolle.

## Sähköpostivahdit (Netlify-versio)

Kun käyttäjä lisää vahdin ja antaa sähköpostin, sivu lähettää sen funktiolle `/api/vahti`. Vahti tallentuu Netlify Blobsiin
tilassa "odottaa", ja käyttäjä saa vahvistusviestin. Vahti alkaa vasta, kun linkkiä klikataan, joten kukaan ei voi tilata viestejä
toisen osoitteeseen. Heti vahvistuksen jälkeen lähtee ensimmäinen kooste tarjouksista, jotka sopivat vahtiin jo nyt.
Sen jälkeen ajastettu tarkistus lähettää joka aamu yhden koosteen uusista osumista. Sama tarjous lähetetään vain kerran.

- Jokaisessa viestissä on linkit yhden tai kaikkien vahtien poistoon. Poisto pyytää vielä napin painalluksen, jotta sähköpostin
  linkkiskannerit eivät poista vahteja vahingossa. Viesteissä on myös List-Unsubscribe-otsake (Gmailin "Peru tilaus" -nappi).
- Poistettu vahti poistetaan kokonaan, sähköpostiosoite mukaan lukien. Vahvistamaton vahti poistuu viikon kuluttua.
- Rajat: 20 vahtia per osoite, 8 uutta per osoite per vuorokausi ja 150 uutta vuorokaudessa yhteensä. Lomakkeessa on piilokenttä botteja vastaan.

### Sähköpostin lähetys: valitse toinen

Netlify ei lähetä sähköpostia itse, joten tarvitaan lähetyspalvelu. Ympäristömuuttujat asetetaan Netlifyssä
**Project configuration → Environment variables**.

**A. Gmail (nopein aloittaa).** Ota Google-tilillä käyttöön kaksivaiheinen tunnistus ja luo sovellussalasana
(myaccount.google.com → Turvallisuus → Sovellussalasanat).

| Muuttuja | Arvo |
| --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USER` | Gmail-osoitteesi |
| `SMTP_PASS` | sovellussalasana (16 merkkiä) |
| `MAIL_FROM` | `Jyväskylän tarjoukset <Gmail-osoitteesi>` |

Gmailin raja on noin 500 viestiä vuorokaudessa, mikä riittää hyvin.

**B. Resend (siistimpi, oma lähettäjäosoite).** Luo tili resend.comissa, lisää oma verkkotunnus ja sen DNS-tietueet
(esim. Cloudflaressa), ja luo API-avain.

| Muuttuja | Arvo |
| --- | --- |
| `RESEND_API_KEY` | `re_...` |
| `MAIL_FROM` | `Jyväskylän tarjoukset <vahti@oma-verkkotunnus.fi>` |

Ilmaisessa tasossa on 3 000 viestiä kuukaudessa ja 100 vuorokaudessa.

Jos lähetystä ei ole asetettu, sivu toimii silti ja vahdit näkyvät selaimessa, mutta sähköpostitilaus kertoo, ettei ilmoituksia ole vielä käytössä.

### Lokit

Netlifyssä **Logs → Functions → vahdit-tarkistus** näyttää jokaisen aamun tuloksen, esim. `alert check: {"emails":3,"items":12,"errors":[]}`.

## K-kaupat omalta koneelta

Kotiverkosta K-Ruoka toimii yleensä varmemmin kuin GitHubin palvelimilta:

```
pip install playwright
python -m playwright install chromium
python site/collect_browser.py          # tai --show, jos haluat nähdä selaimen
git add site/data/k-ruoka-snapshot.json && git commit -m "K-Ruoka" && git push
```

Ilman Pythonia: avaa https://www.k-ruoka.fi/kauppa/tarjoushaku, liitä `site/collectors/k-ruoka.js` selaimen konsoliin
(F12 → Console) ja tallenna ladattu `k-ruoka-snapshot.json` kansioon `site/data/`. Haku kestää noin 15 minuuttia (25 kauppaa).
Jos jokin kauppa ei vastaa, muut kerätään silti, ja `collect_browser.py` pitää sen kaupan edellisen haun.

## Jos kaupan sivusto muuttuu

Rustan kampanjasivun osoite on `stores.json`-tiedostossa (`rustaCampaignUrl`). Jos Rusta vaihtaa sen, päivitä osoite sinne.


S-kaupat käyttää GraphQL-kyselyä, jonka tunniste (`skaupatQueryHash` tiedostossa `stores.json`) voi vaihtua, kun sivusto päivittyy.
Silloin `fetch_offers.py` kertoo virheen ja käyttää edellistä hakua. Uuden tunnisteen saa avaamalla s-kaupat.fi:n hakusivun,
F12 → Network, suodatus `RemoteFilteredProducts`, ja kopioimalla pyynnön `sha256Hash`-arvon. Varalla on myös
`collectors/s-kaupat.js`, joka toimii samalla tavalla kuin K-Ruokan keräin.

## Tiedostot

| Tiedosto | Mitä tekee |
| --- | --- |
| `netlify.toml` | Netlifyn build-asetukset. |
| `netlify/functions/vahti.mjs` | Vahdin tilaus (`/api/vahti`), vahvistus- ja poistolinkit (`/vahti`). |
| `netlify/functions/vahdit-tarkistus.mjs` | Päivittäinen tarkistus ja koosteviestit. |
| `netlify/functions/lib/` | Tallennus (Blobs), täsmäys, viestipohjat ja lähetys (Resend tai SMTP). |
| `site/data/stores.json` | Mitkä K- ja S-kaupat haetaan (kaupan tunnus → nimi). |
| `site/fetch_offers.py` | Hakee skriptillä luettavat kaupat. Vain Pythonin vakiokirjasto. `python site/fetch_offers.py lidl` hakee vain yhden lähteen. |
| `site/collect_browser.py` | Ajaa `collectors/k-ruoka.js`:n oikeassa selaimessa (Playwright). |
| `site/collectors/*.js` | Selainkeräimet K-Ruokalle (myös mobiiliedut) ja (varalla) S-kaupoille. |
| `site/catalog.py` | Yhteiset tuoteryhmät: kauppojen omat kategoriat ja tuotenimet → 19 ryhmää. |
| `site/build.py` | Yhdistää datan ja samat tarjoukset, laskee hintavertailun ja kirjoittaa `public/index.html` ja `public/offers.json`. Lisäksi `preview.html`, jossa data on sivun sisällä. |
| `site/template.html` | Sivu. |

Tarjousrivi kauppojen hakutiedostoissa: `[kauppa, kaupan kategoria, nimi, hinta, yksikkö, normaalihinta, alennus-%, huomautus, voimassa, linkki, kuva, tuotetunnus, merkki]`.

## Paikallinen kehitys

```
npm install
python3 site/build.py
npx netlify dev        # sivu ja funktiot osoitteessa http://localhost:8888
```

Sähköpostin voi testata paikallisesti kirjoittamalla SMTP-asetukset tiedostoon `.env` (ei mene gitiin).
Ajastetun tarkistuksen voi ajaa käsin: `curl -X POST http://localhost:8888/.netlify/functions/vahdit-tarkistus`.

Hinnat kopioidaan kauppojen omilta sivuilta. Tarkista hinta aina kaupassa.
