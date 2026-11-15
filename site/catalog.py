"""Shared product groups: maps each store's own category (or, when a store gives none, the product name)
onto one common list of groups, so the page can filter all stores the same way."""
import re

CAT_ORDER = ["Hedelmät ja vihannekset", "Liha ja kala", "Maito ja juusto", "Leivät ja leivonnaiset",
             "Valmisruoat ja pakasteet", "Kuivat, mausteet ja kastikkeet", "Makeiset ja naposteltavat",
             "Juomat ja kahvi", "Ruoka, muut", "Lemmikit", "Lapset ja lelut", "Koti, keittiö ja siivous",
             "Vaatteet ja kengät", "Kauneus ja terveys", "Urheilu ja vapaa-aika", "Elektroniikka ja kodinkoneet",
             "Työkalut, remontti ja autoilu", "Piha, kukat ja puutarha", "Kirjat ja toimisto", "Muut"]

# Store categories (K-Ruoka, S-kaupat, Lidl, Kärkkäinen, Prisma.fi) -> group. First match wins.
RULES = [
    (r"hedelm|vihann", "Hedelmät ja vihannekset"),
    (r"lemmik", "Lemmikit"),
    (r"laps|lasten|lelu|vauva", "Lapset ja lelut"),
    (r"valmisruo|pakaste|jäätelö", "Valmisruoat ja pakasteet"),
    (r"liha|kala|merenel|äyriäis|kasviprote|leikkele", "Liha ja kala"),
    (r"maito|juust|kananmun|munat", "Maito ja juusto"),
    (r"kuiva|mauste|öljy|texmex|maailman maut|murot|säilyk|kastik|pasta|riisi|nuudel|leivonta|aamiai", "Kuivat, mausteet ja kastikkeet"),
    (r"makeis|napostel|snack|karkit|suklaa", "Makeiset ja naposteltavat"),
    (r"leiv|leivon|paistopiste|keksi", "Leivät ja leivonnaiset"),
    (r"juoma|kahvi|olut|siideri|alkoholi|mehu", "Juomat ja kahvi"),
    (r"vaat|kenk|kengä|muoti|pukeutu", "Vaatteet ja kengät"),
    (r"kosmet|kauneu|hygien|hyvinvoin|terveys|itsehoito|urheiluravin", "Kauneus ja terveys"),
    (r"urheilu|vapaa-aika|erä |retkeily|käsityö|harraste", "Urheilu ja vapaa-aika"),
    (r"kodinkone|elektroniikka|pelaaminen", "Elektroniikka ja kodinkoneet"),
    (r"sähkö|pienrauta|auto|työkalu|remont|koneet", "Työkalut, remontti ja autoilu"),
    (r"kynttil|huonetuoks", "Koti, keittiö ja siivous"),
    (r"piha|puutarha|kukat|kasvit", "Piha, kukat ja puutarha"),
    (r"koti|keittiö|sisustus|kodinhoito|taloustarv|kodinteks|kattaus", "Koti, keittiö ja siivous"),
    (r"kirjat|lehdet|paperitarv", "Kirjat ja toimisto"),
    (r"ruoka|elintarvik", "Ruoka, muut"),
]

# Product name -> group, for stores that give no usable category.
NAME_RULES = [
    (r"pyykinpes|astianpesu|pesujauhe|pesuaine|puhdistusaine|huuhtelu|ilmanraikast|\bcif\b", "Koti, keittiö ja siivous"),
    (r"after shave|partavesi|kasvovesi|hiusvesi|vitamiini", "Kauneus ja terveys"),
    (r"salaattikastike|majonee|ketsup|sinappi|relish|kurkku", "Kuivat, mausteet ja kastikkeet"),
    (r"piltti|hedelmäsose|annospussi", "Lapset ja lelut"),
    (r"gourmet|best friend|jyrsij", "Lemmikit"),
    (r"wd-40|wurth|kulmalevy|naulauslevy", "Työkalut, remontti ja autoilu"),
    (r"perlana|desinfiointi|tahranpoisto", "Koti, keittiö ja siivous"),
    (r"\blv\b|derma by|kondomi|antiperspir|lotion|serum|cream|mask\b|mousse|hairspray|got2b|lavera|veet|syoss|kiharru|kreatiini|creatine|lämpösuoja|l300", "Kauneus ja terveys"),
    (r"dolce gusto|\btea\b", "Juomat ja kahvi"),
    (r"\blaku|makeinen|patukka|protein bar|doritos|nacho", "Makeiset ja naposteltavat"),
    (r"wasa|näkki", "Leivät ja leivonnaiset"),
    (r"granola|siirappi|mayo|salsa|taateli|luumu|kuutio|punasipul|lihavalmiste|superfood", "Kuivat, mausteet ja kastikkeet"),
    (r"led |airfryer", "Elektroniikka ja kodinkoneet"),
    (r"kissan|koiran|kissalle|koiralle|latz|pedigree|whiskas|sheba|kissanhiekka|lintu(jen|ruoka)|talipallo|purina|dentastix|friskies", "Lemmikit"),
    (r"vaippa|libero|pampers|lasten|vauvan|lelu|lego|barbie|nukke|palapeli|pehmo|leikki|hot wheels|paw patrol|ryhmä hau", "Lapset ja lelut"),
    (r"kahvi|tee\b|teepuss|mehu|limsa|virvoitus|juoma|vesi\b|kivennäis|coca|pepsi|jaffa|energia|kaakao|glögi|cola|nescafe|pommac", "Juomat ja kahvi"),
    (r"suklaa|karkki|karamell|makeis|lakrits|sipsi|pähkinä|keksi|pastill|purukum|popcorn|fazer|marabou|panda|haribo|malaco|tikkari|toffee|konveht|joulukalenteri|naposte|taffel|estrella|pringles|salmiak|cloetta|maltesers|m&m|snickers|twix|kinder|dumle|geisha|wiener|lakt?ritsi", "Makeiset ja naposteltavat"),
    (r"juusto|maito|jogurt|voi\b|margariini|kerma|rahka", "Maito ja juusto"),
    (r"leipä|näkkileip|korppu|kakku|pulla|piparkak|piparit", "Leivät ja leivonnaiset"),
    (r"jauho|sokeri|pasta|riisi|makaroni|muro|mysli|hiutale|puuro|mauste|ketsup|sinappi|kastike|öljy|suola|säilyke|tonnikala|hillo|hunaja|keitto|nuudel|spagetti|tomaatti|papu|ananas|persik|majonee|marmela|leivinpap|liivate|rusina|manteli|siemen", "Kuivat, mausteet ja kastikkeet"),
    (r"shampoo|hoitoaine|saippua|suihku|deodorant|hammas|voide|rasva|meikki|ripsiväri|huuli|kynsi|hius|partaa|parran|höylä|terä|dušš|dusch|tamponi|terveysside|pikkuhousunsuoja|vanulap|vanupuik|vitamiini|laastari|kosteus|puhdistusliina|käsidesi|tuoksu|parfy|edt|after shave|lumene|nivea|schwarzkopf|gliss|l'oreal|loreal|garnier|dove|rexona|colgate|pepsodent|oral-b|gillette|always|libresse|kasvo|seerumi|naamio|geeli|rakkolaast|magnesium|d-vitamiini|kalaöljy|maitohappo", "Kauneus ja terveys"),
    (r"sukat|sukka|housu|paita|takki|pipo|hanska|käsine|lapaset|kengät|kenkä|saappaa|tossu|alus|bokser|rintaliiv|pyjama|huppari|college|legging|trikoo|farku|villapaita|neule|kaulahuiv|huivi|vyö|lippis|asu\b|mekko|hame|sukkahousu|kerrasto|tennar|lenkkar|sandaal|aamutakki|yöpaita", "Vaatteet ja kengät"),
    (r"kuuloke|kaiutin|laturi|kaapeli|usb|paristo|akku|puhelin|televisio|\btv\b|hiiri|näppäimistö|tabletti|kello|radio|lamppu led|led-lamppu|led lamppu|polttimo|imuri|mikro|vedenkeitin|kahvinkeitin|leivänpaahdin|vatkain|tehosekoitin|blender|silitysrauta|hiustenkuivaa|suoristus|parranajokone|trimmer|kamera|muistikortti|hdmi|virtapankki|jatkojohto|valosarja|jbl|philips|samsung|otsalamppu|taskulamppu", "Elektroniikka ja kodinkoneet"),
    (r"ruuvi|pora|vasara|työkalu|maali|teippi|liima|tiiviste|lukko|pensseli|sivellin|hiomapap|mittanauha|tikkaat|lasinpesu|pesuneste|moottoriöljy|autoshampoo|auton|pyyhkijän|akkulatur|jäätymisenesto|jääskraba|lumiharja|lumilapio|lapio|kärry|silikoni|vaahto|kiintoavain|ruuvimeisseli|pihdit|saha|taltta|puukko|hylsy|ruuvitaltta|terassi|öljynsuod", "Työkalut, remontti ja autoilu"),
    (r"multa|lannoite|kukka|ruukku|siemenet|kastelu|puutarha|grilli|hiili|sytytys|lintulauta|haravа|harava|kynttilälyhty|ulkovalo|hauta", "Piha, kukat ja puutarha"),
    (r"pallo|pyörä|kypärä|luistim|sukset|sauvat|kahvakuula|käsipaino|jooga|treeni|uima|retki|teltta|makuupussi|onki|vapa|uistin|viehe|kelkka|pulkka|liukuri|kortit|peli\b|lautapeli|reppu|termos|juomapullo|heijastin", "Urheilu ja vapaa-aika"),
    (r"kirja|vihko|kynä|paperi(?!pyyh)|kansio|tussi|väri(kynä|liitu)|askartelu|lanka|puikot|virkkuu|kalenteri|kortti|kirjekuor|lahjapaperi|teippirulla|lehtiö|liitu|muistikirja", "Kirjat ja toimisto"),
    (r"pesuaine|pyykki|huuhteluaine|astianpesu|tiskiaine|konetiski|yleispuhdist|wc-|wc |talouspaperi|vessapaperi|paperipyyh|roskapussi|jätesäkki|pakastepussi|leivinpaperi|folio|kelmu|siivous|moppi|harja|sieni|tiskiharja|liina|pyyhe|lakana|pussilakana|tyyny|peitto|peite|matto|verho|kynttilä|tuikku|lautanen|lasi\b|lasit|muki|kuppi|kattila|pannu|veitsi|haarukka|lusikka|aterin|kulho|vuoka|purkki|rasia|säilytys|kori|laatikko|henkari|pyykkipoik|ilmanraikast|omo|ariel|fairy|finish|lambi|lotus|serla|kotimaista|tolu|ajax|cif|domestos|bio luvil|mini risk|comfort|vanish|servetti|kertakäyttö|tulitik|sytytin|joulu|kuusen|koriste|valo|taulu|kehys|peili|lyhty|maljakko|tarjotin|pöytäliina|patja|torkkupeit|viltti|suihkuverho|wc-harja|pesuvati|ämpäri|sanko", "Koti, keittiö ja siivous"),
]

FIRST_RULES = [
    (r"bolsius|kynttilä|huonetuoksu", "Koti, keittiö ja siivous"),
    (r"calluna|kukka|ruukku", "Piha, kukat ja puutarha"),
    (r"taste of the wild|tintin|herkkutanko|koiran|kissan", "Lemmikit"),
    (r"vuokkoset|\bside\b|ohutside|yöside|co-test|eye patch|kangasmaski|kangasnaamio|piiink|cutrin|gunry|hand soap|hoitosuihke", "Kauneus ja terveys"),
    (r"yale|lukitusvaijeri", "Työkalut, remontti ja autoilu"),
    (r"candy|allstar mix|karkki", "Makeiset ja naposteltavat"),
    (r"noodles|nuudel|torttupohja", "Kuivat, mausteet ja kastikkeet"),
    (r"limppu", "Leivät ja leivonnaiset"),
    (r"kurpitsa", "Hedelmät ja vihannekset"),
    (r"levite|oivariini|voi\b", "Maito ja juusto"),
]

FOOD_RULES = [
    (r"naudan|ulkofilee|entrecote|filee", "Liha ja kala"),
    (r"jauheliha|broileri|kana|kalkkuna|possu|sian|nauta|liha|makkara|nakki|pekoni|kinkku|leikkele|burgeri|lohi|silli|kala|tonnikala|katkarap|seiti|muikku", "Liha ja kala"),
    (r"maito|jogurt|rahka|juusto|voi\b|levite|kerma|vanukas|viili|kefiiri|oltermanni|valio|arla|munat|kananmun|margariini|oivariini", "Maito ja juusto"),
    (r"omena|banaani|appelsiini|mandariini|peruna|porkkana|sipuli|tomaatti|kurkku|salaatti|paprika|kaali|marja|mustikka|puolukka|hedelmä|vihannes|sieni|herne|avokado|sitruuna|päärynä|viinirypäl|klementiini", "Hedelmät ja vihannekset"),
    (r"pizza|pakaste|valmisruoka|laatikko|keitto|lasagne|piirakka|pyttipannu|ateria|lihapull|kebab", "Valmisruoat ja pakasteet"),
    (r"leipä|sämpylä|patonki|ruisleip|kakku|pulla|korvapuusti|croissant|tortilla", "Leivät ja leivonnaiset"),
    (r"olut|siideri|lonkero|viini|limonadi|virvoitus|mehu|kahvi|tee\b|kaakao|smoothie|vesi\b|energiajuoma|juoma", "Juomat ja kahvi"),
]


# Names that the lists above miss (mostly Tokmanni, which gives no category at all).
EXTRA_RULES = [
    (r"rengas|venttiili|polkupyör|pyöräil|satula|lattiapumppu|pinna-avain|vaihdepyör|\bketju", "Urheilu ja vapaa-aika"),
    (r"brio|junarata|playmobil|pelikortit|nalle|leikkiset", "Lapset ja lelut"),
    (r"pururulla|puruluu|koiranherk|kissanherk|ankka.*kpl", "Lemmikit"),
    (r"trolli|karkit|purkka", "Makeiset ja naposteltavat"),
    (r"talja|roskakassi|rullavaunu|säilytys|koriste|joulukuus|tonttu|kuusenkoriste|led-valo|valoverho|pöytäliina", "Koti, keittiö ja siivous"),
    (r"irtolyijy|lyijytäyte|sakset|nitoja", "Kirjat ja toimisto"),
    (r"mäyräkoira|pehmolelu|pehmo", "Lapset ja lelut"),
]


def by_rules(text, rules):
    low = (text or "").lower() + " "
    for rx, group in rules:
        if re.search(rx, low):
            return group
    return None


def categorize(raw_cat, name):
    """Group for one offer: the store's category first, then guesses from the product name.
    raw_cat may be a path "most specific > ... > top level"; the most specific level that matches wins."""
    specific = RULES[:-1]  # the last rule ("ruoka") is only a fallback: "Kissan märkäruoka" is a pet product
    for part in (raw_cat or "").split(" > "):
        g = by_rules(part, specific)
        if g:
            return g
    return (by_rules(name, FIRST_RULES) or by_rules(name, NAME_RULES) or by_rules(name, FOOD_RULES) or by_rules(name, EXTRA_RULES)
            or by_rules(raw_cat, RULES[-1:]) or "Muut")
