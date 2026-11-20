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
    (r"kosmetiikkalaukku|vartalovoi|co-test|kylpymaito|vartalomaito|puhdistusmaito|kylpyvaahto|kylpysuola", "Kauneus ja terveys"),
    (r"semper|piltti|muru baby|\d+ ?kk\b", "Lapset ja lelut"),
    (r"rukkaset|lapaset|sormikkaat|hanskat", "Vaatteet ja kengät"),
    (r"kahvinkeitin|kahvimylly|kahvikone|espressokone|vedenkeitin", "Elektroniikka ja kodinkoneet"),
    (r"kahvikuppi|kahvimuki|teekannu|teemuki|kahvikannu|kahvisuoda|kahvipurkki|teekuppi|termosmuki", "Koti, keittiö ja siivous"),
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


FOOD_GROUPS = {"Hedelmät ja vihannekset", "Liha ja kala", "Maito ja juusto", "Leivät ja leivonnaiset", "Valmisruoat ja pakasteet",
               "Kuivat, mausteet ja kastikkeet", "Makeiset ja naposteltavat", "Juomat ja kahvi", "Ruoka, muut"}
# Tokmanni's own non-food ranges: "Penaali Miny hedelmät" is a pencil case, not fruit.
NOT_FOOD = re.compile(r"\bminy\b|kotikulta|penaali|mukeja|\bmuki\b|lautanen|tyynynpäällinen|tarra|koriste")


def categorize(raw_cat, name):
    group = _categorize(raw_cat, name)
    if group in FOOD_GROUPS and not raw_cat and NOT_FOOD.search((name or "").lower()):
        return "Muut"   # build.py then finds the right non-food group from the product families
    return group


def _categorize(raw_cat, name):
    """Group for one offer: the store's category first, then guesses from the product name.
    raw_cat may be a path "most specific > ... > top level"; the most specific level that matches wins."""
    specific = RULES[:-1]  # the last rule ("ruoka") is only a fallback: "Kissan märkäruoka" is a pet product
    for part in (raw_cat or "").split(" > "):
        g = by_rules(part, specific)
        if g:
            return g
    return (by_rules(name, FIRST_RULES) or by_rules(name, NAME_RULES) or by_rules(name, FOOD_RULES) or by_rules(name, EXTRA_RULES)
            or by_rules(raw_cat, RULES[-1:]) or "Muut")


# Second level: product families inside each group, e.g. "Maito ja juusto" > "Tuorejuustot".
# Matched against the product name and the store's own most specific category; the first match wins, so the
# narrower families come first ("kermajuusto" is a cheese, "maitorahka" a quark, "kauramaito" plant-based).
# Offers that match nothing stay in the group without a family ("Muut" on the page).
SUBCATS = {
    "Hedelmät ja vihannekset": [
        ("Marjat", r"marja|mustikka|puolukka|mansikka|vadelma|karpalo|lakka|herukka|tyrni|karhunvatukka"),
        ("Hedelmät", r"omena|banaani|appelsiini|mandariini|klementiini|päärynä|viinirypäl|rypäle|ananas|kiivi|meloni|sitruuna|lime|granaattiomena|persimon|luumu|nektariini|persikka|mango|hedelm"),
        ("Sienet", r"sieni|herkkusien|siitake|kantarelli|osterivinokas"),
        ("Salaatit ja yrtit", r"salaatti|rucola|pinaatti|yrtti|basilika|persilja|tilli|ruohosipuli|korianteri|minttu|versot|lehtikaali|salaatit"),
        ("Perunat ja juurekset", r"peruna|porkkana|juures|lanttu|nauris|punajuuri|palsternakka|bataatti|sipuli|inkivääri|selleri|retiisi"),
        ("Vihannekset", r"tomaatti|kurkku|paprika|kaali|kesäkurpitsa|kurpitsa|herne|papu|maissi|avokado|munakoiso|parsa|purjo|chili|vihann|kasvikset"),
    ],
    "Liha ja kala": [
        ("Kasviproteiinit", r"kasviprote|härkis|nyhtökaura|pulled oats|tofu|tempeh|soija|quorn|vegaani|oumph|seitan|kasvispihvi|kasvispyöry|härkäpapu"),
        ("Kala ja äyriäiset", r"\bkala|mustekala|silakka|kalat|lohi|silli|seiti|muikku|tonnikala|katkarap|äyriäi|kirjolohi|ahven|kuha|siika|surimi|mäti|turska|sardiini|anjovis|simpuk|rapu"),
        ("Jauheliha", r"jauheliha"),
        ("Makkarat ja nakit", r"makkara|wursti|nakki|nakit|wieneri|chorizo|grillimakk|lenkki"),
        ("Leikkeleet", r"palvi|leike|leikkele|kinkku|salami|meetvursti|pekoni|kalkkunaleike|kokolihaleikk|pastrami|serrano|prosciutto"),
        ("Broileri ja kalkkuna", r"broiler|kana|kalkkun|siipi|siivet|koipi"),
        ("Nauta, possu ja muut lihat", r"suikale|suikalo|kebab|nauta|naudan|possu|sian|porsas|härkä|entrecote|ulkofilee|sisäfilee|pihvi|kassler|lammas|riista|poro|hirvi|kylkiluu|ribs|paisti|liha"),
    ],
    "Maito ja juusto": [
        ("Kasvipohjaiset", r"kaurajuoma|kauramaito|kaurajog|kauravälipala|kaurapohj|soijajuoma|mantelijuoma|riisijuoma|kookosjuoma|oatly|alpro|kasvipohj|planti|kaura(?!.*juust)"),
        ("Tuorejuustot", r"tuorejuust|mascarpone|philadelphia|raejuust|kotijuust|ricotta|kermajuustolevit|tuorejuustot"),
        ("Juustot", r"babybel|juust(?!oportti)|cheddar|mozzarella|feta|parmesan|parmigiano|emmental|gouda|edam|brie|camembert|halloumi|grana padano|pecorino|gorgonzola"),
        ("Rahkat ja vanukkaat", r"proteiinivan|profit|rahka|vanukas|vanukkaat|pudding|välipala|proteiinijuoma|protein"),
        ("Kermat", r"fraiche|kerma|smetana|crème|creme fraiche|ranskankerm|vispikerm"),
        ("Jogurtit ja viilit", r"jogurt|viili|skyr|kreikkalai|kefiiri|ylä|a\+|bio"),
        ("Maidot ja piimät", r"kaakaojuom|shake|maito|piimä|maitojuoma|kevytmaito|rasvaton|täysmaito|maidot"),
        ("Voit ja levitteet", r"\bvoi\b|voit\b|levite|margariini|oivariini|becel|keiju|flora|rasvat|voi-"),
        ("Munat", r"muna|munat|kananmun"),
    ],
    "Leivät ja leivonnaiset": [
        ("Keksit", r"keksi|biscuit|cookie|digestive|domino|oreo|pipar|vohveli|kaurakeks|marie"),
        ("Näkkileivät ja korput", r"näkki|hapankorp|wasa|korppu|riisikakk|maissikakk|crisp|ryvita|finn crisp|näkkileivät"),
        ("Suolaiset leivonnaiset", r"piirakka|piiras|karjalan|pasteija|samosa|lihapii|pizzapohja|pizzataikin|lehtitaikin|taikina"),
        ("Pullat ja makeat leivonnaiset", r"pulla|korvapuust|croissant|munkki|donitsi|donut|viineri|muffin|kakku|torttu|leivos|brownie|kääretor|pikkuleip|laskiaispul"),
        ("Leivät", r"\bruis|leipä|leivät|limppu|patonki|sämpylä|paahtoleip|bagel|tortilla|pita|rieska|reikäleip|toast|ciabatta|focaccia|hodari|hampurilaissämp|sämpylät"),
    ],
    "Valmisruoat ja pakasteet": [
        ("Jäätelöt", r"jäätelö|jäätelöt|puikko|tuutti|sorbet|magnum|pingviini|ben & jerry|häagen|mehujää|kermajää"),
        ("Pizzat", r"pizza"),
        ("Pakastevihannekset ja -marjat", r"wokkivihann|keittojuurek|pakastevihann|pakastemarj|pakasteherne|herne-maissi|kasvissekoitus|ranskalai|lohkoperun|perunasuikal|marjasekoitus"),
        ("Keitot", r"keitto|keitot|soppa"),
        ("Puurot ja jälkiruoat", r"puuro|tartalet|mämmi|jälkiruo|kiisseli|marenki|juustokakku"),
        ("Taikinat ja pohjat", r"taikina|taikin|pohja"),
        ("Pikaruoat ja välipalat", r"patonki|patongit|hampurilai|burger|hot dog|sandwich|panini|nugget|toast|wrap|burrito|piiras|lämpimäi|pizzapala|pasty|sämpylä"),
        ("Valmisateriat", r"ateria|laatikko|lasagne|lasagnette|pyttipannu|risotto|curry|kebab|lihapull|pihvi|kastike|wok|annos|salaatti|pasta|spagetti|makaroni|perunamuusi|muusi|ruoka|kotiruoka|kaalikääry|tikka|mureke|kiusaus|gratiini|valmisruo|lounas|nuudeli"),
    ],
    "Kuivat, mausteet ja kastikkeet": [
        ("Murot, myslit ja puurot", r"muro|mysli|granola|hiutale|puuro|corn flakes|cheerios|weetabix|aamiai|kaurahiut|chia"),
        ("Pasta, riisi ja nuudelit", r"pasta|spagett|makaroni|penne|fusilli|tagliatel|lasagnelev|riisi|nuudel|couscous|bulgur|kvinoa|quinoa|gnocchi|tortellini|ravioli|perunamuusijauhe|pastat"),
        ("Jauhot ja leivonta", r"jauho|sokeri|leivinjauh|hiiva|vanilli|leivonta|kakkupohj|torttupohj|strösseli|liivate|siirappi|kuorrute|koristerae|marsipaani|leivinpaperi|kaakaojauhe|ruokasooda|maizena"),
        ("Säilykkeet", r"säilyk|tomaattimurs|passata|tomaattipyre|kikherne|papu|pavut|maissi|ananas|persik|hedelmäcocktail|tölkki|kookosmaito|oliivi|kapris|kurkut|kurkku|punajuuri|sardiini|tonnikala"),
        ("Hillot, hunajat ja levitteet", r"hillo|marmeladi|hunaja|nutella|levite|maapähkinävoi|suklaalevite|kiisseli|soose|sose|marjakeitto|hedelmäkeitto"),
        ("Pähkinät, siemenet ja kuivatut hedelmät", r"pähkinä|manteli|cashew|rusina|taateli|luumu|aprikoosi|kuivattu|siemen|pekaani|pistaasi|kuivahedelm|karpalo"),
        ("Kastikkeet ja öljyt", r"kastike|ketsup|ketchup|sinappi|majonee|mayo|salsa|dressing|pesto|soija|öljy|etikka|marinadi|bbq|tabasco|sriracha|relish|kastikkeet|chilikast|tahini|hummus|dippi"),
        ("Mausteet ja liemet", r"mauste|suola|pippuri|chili|kaneli|kardemumma|paprikajauh|curry|liemi|fondi|kuutio|yrtti|mausteet|oregano|basilika|valkosipulijauh|grillimauste|maustesek"),
        ("Maailman maut", r"texmex|tex mex|taco|tortilla|nacho|thai|intia|aasia|kiina|meksik|sushi|wasabi|kimchi|maailman maut"),
    ],
    "Makeiset ja naposteltavat": [
        ("Joulukalenterit ja konvehdit", r"joulukalenteri|konvehti|konvehd|lahjarasia|suklaarasia|praliini|pralin|after eight|mozartkugel|lahjapakkaus"),
        ("Pastillit ja purukumit", r"pastilli|purukum|xylitol|ksylitol|jenkki|läkerol|mentos|tic tac|sisu|pätkis-?|purkka|pastillit"),
        ("Lakritsi ja salmiakki", r"lakrits|lakrit|salmiak|\blaku|tyrkisk|pantteri|apteekki|super salmiakki"),
        ("Suklaa", r"suklaa|marabou|kinder|snickers|twix|\bmars\b|bounty|ritter|lindt|toblerone|daim|geisha|tupla|kismet|maltesers|m&m|milka|dumle|brunberg|kex|kitkat|kit kat|reese|suklaat"),
        ("Sipsit ja naposteltavat", r"sipsi|perunalastu|chips|popcorn|nacho|tortillalastu|pringles|taffel|estrella|lay's|lays|snacks|naksu|pähkinä|cashew|suolapähk|rinkeli|pretzel|kalakeksi|maissinaks|riisisipsi|dippi"),
        ("Patukat", r"patukka|patukat|\bbar\b|välipalapatuk|proteiinipatuk|fazer go|nutri"),
        ("Karkit", r"karkki|karkit|irto|haribo|malaco|candy|kumi|toffee|karamell|allstar|vaahtokarkki|tikkari|hedelmäkarkki|viinikumi|aakkoset|lakupussi|makeis|marmeladi|fazer|cloetta|panda|bubs|karkkipussi"),
    ],
    "Juomat ja kahvi": [
        ("Energia- ja urheilujuomat", r"sport|vitamin well|novelle plus|elektrol|hullu kallo|\bteho\b|energia|energy|red bull|monster|battery|\bed\b|nocco|celsius|urheilujuoma|isotoni|powerade|gatorade|proteiinijuoma|energiajuomat"),
        ("Kahvi", r"kahvi|espresso|cappuccino|latte|kapseli|dolce gusto|nescafe|nescafé|paulig|juhla mokka|presidentti|kulta katriina|löfbergs|lavazza|kahvit"),
        ("Tee ja kaakao", r"jäätee|pussitee|\btee\b|teepuss|chai|rooibos|kaakao|kaakaojuoma|cocoa|teet"),
        ("Oluet, siiderit ja lonkerot", r"heineken|0,0 ?%|olut|oluet|lager|\bipa\b|siideri|lonkero|long drink|\bgin\b|cider|alkoholi|panimo|viini|kuohu|hard seltzer|karhu|lapin kulta|koff|sandels|olvi|aura"),
        ("Mehut, smoothiet ja glögit", r"mehu|smoothie|nektari|juice|tuoremehu|glögi|mehut|marjajuoma"),
        ("Virvoitusjuomat ja vedet", r"limonaad|novelle|limsa|virvoitus|cola|coca|pepsi|fanta|sprite|jaffa|pommac|7up|7 up|mountain dew|limonadi|kivennäis|vesi|vichy|tonic|ginger|hiilihapot|juoma"),
    ],
    "Lemmikit": [
        ("Kissat", r"kissa|kissan|whiskas|sheba|felix|gourmet|kissanhiek|\bcat\b"),
        ("Koirat", r"koira|koiran|pedigree|dentastix|puruluu|purutikk|pururulla|\bdog\b|herkkutank|taste of the wild"),
        ("Herkut ja tarvikkeet", r"makupala|herkku|luu\b|snack|valjaat|tarvike|puru|juustoluu|nartun|talutin|panta"),
        ("Linnut ja pieneläimet", r"lintu|talipallo|jyrsij|kani|marsu|hamsteri|akvaario|kalanruoka|auringonkukansiem"),
    ],
    "Lapset ja lelut": [
        ("Vauvanhoito", r"\d ?kk\b|vaippa|vaipat|libero|pampers|vauva|tutti|tuttipullo|piltti|hedelmäsose|annossose|äidinmaidon|velli|hoitolaukk|vaunu|rattaat|turvaistuin|kosteuspyyhk|harjoitteluhous"),
        ("Lastenvaatteet", r"haalari|body\b|potkupuku|lasten.*(vaate|takki|pipo|suk|saap|kenkä|kengät|housu|paita|pyjama|asu|hanska|lapaset|kerrasto)|lastenvaate|poikien|tyttöjen"),
        ("Pelit ja palapelit", r"palapeli|lautapeli|\bpeli\b|pelit|pelikortit|korttipeli|alias|monopoly|\buno\b|afrikan tähti|kimble|seurapeli"),
        ("Askartelu ja piirtäminen", r"askartel|värityskirja|vahaliitu|liitu|muovailu|tarra|helmi|värikynä|tussi|maalaus|piirtä"),
        ("Lelut", r"lelu|lego|duplo|barbie|nukke|playmobil|brio|pehmo|nalle|hot wheels|paw patrol|ryhmä hau|leikki|figuuri|rata|palikat|auto|traktori|dino|junarata|kauko-ohja|liukuri|pulkka|kelkka"),
    ],
    "Koti, keittiö ja siivous": [
        ("Joulu ja koristeet", r"joulu|tonttu|kuusenkoriste|adventti|kuusiköynn|koriste|valosarja|valoverho|jouluvalo|tähti|kranssi|joulukuus|enkel|nisse|lumihiutale|kimalle|kuusi"),
        ("Kynttilät ja tuoksut", r"kynttilä|tuikku|huonetuoks|tuoksutikk|tuoksukynt|lyhty|bolsius|tuoksuöljy|aromi"),
        ("Valaisimet", r"valaisin|plafondi|kattolamppu|pöytälamppu|lattialamppu|riippuvalaisin|kohdevalo|kattovalo"),
        ("Siivous ja pyykki", r"pesuaine|pesujauhe|pyykki|huuhteluaine|astianpesu|tiski|konetiski|yleispuhd|\bwc\b|wc-|siivous|moppi|harja|sieni|siivousliina|mikrokuitu|omo\b|ariel|fairy|finish|ajax|cif\b|domestos|vanish|comfort|desinfi|tahranpoist|ilmanraikast|perlana|pyykkiteline|pyykkikori|lasinpesu|kalkinpoist|imuripussi|rätti"),
        ("Paperit ja kertakäyttö", r"talouspaperi|wc-paperi|vessapaperi|paperipyyh|lambi|serla|lotus|nenäliina|kertakäyttö|folio|kelmu|leivinpaperi|pakastepussi|roskapussi|jätesäkki|biojätepussi|tulitik|sytytin|servetti|minigrip"),
        ("Tekstiilit", r"pyyhe|pyyhkeet|lakana|pussilakana|tyyny|peitto|peite|matto|verho|viltti|torkkupeit|patja|päiväpeit|kylpytakki|tyynyliina|ovimatto|tyynynpäällinen|sängyn"),
        ("Keittiö ja kattaus", r"kattila|pannu|veitsi|veitset|haarukka|lusikka|aterin|kulho|vuoka|lautanen|lasi\b|lasit|juomalasi|muki|kuppi|tarjotin|pöytäliina|leikkuulauta|termari|rasia|säilytysrasia|purkki|astia|kattaus|keittiö|paistinpann|wok|kauha|lasta|raastin|siivilä|uunipelti|kakkuvuoka|mittasarja|juomapullo|termospullo|kannu"),
        ("Sisustus ja säilytys", r"taulu|kehys|peili|maljakko|sisustus|säilytys|kori|laatikko|hylly|valaisin|kello|tuoli|pöytä|naulakko|henkari|koukku|teline|kaappi|jakkara|rahi|patsas|figuuri|tekokukka|tekokasvi"),
    ],
    "Vaatteet ja kengät": [
        ("Kengät", r"jalkine|tohveli|kenk|kengä|saap|tossu|tennar|lenkkar|sandaal|sneaker|varsikenkä|nilkkuri|crocs|kumisaap"),
        ("Alusvaatteet, sukat ja yöasut", r"alushous|bokser|rintaliiv|sukka|sukat|sukkahous|kerrasto|yöpaita|pyjama|aamutakki|alusasu|stringit|trunk|alusp|hipster|bralette|toppi|aluspaita|yöasu"),
        ("Asusteet", r"pipo|hanska|käsine|lapaset|kaulahuiv|huivi|vyö|lippis|laukku|lompakko|aurinkolasi|koru|korvakoru|kaulakoru|rannekoru|sateenvarjo|kassi|hattu|pannta|panta|tuubihuivi|asuste"),
        ("Lastenvaatteet", r"lasten|vauvan|poikien|tyttöjen|junior|\bkids\b|baby"),
        ("Takit", r"takki|parka|anorakki|toppatakki|toppaliivi|kuoritakki|softshell|untuvatakki|tuulitakki|sadetakki|haalari"),
        ("Naisten vaatteet", r"naisten|mekko|hame|tunika|legging|pusero|neuletakki|bleiseri|naiste"),
        ("Miesten vaatteet", r"miesten|miehen"),
        ("Paidat, neuleet ja housut", r"neule|paita|housut|farkut|college|huppari|t-paita|svetari|pusero"),
    ],
    "Kauneus ja terveys": [
        ("Vitamiinit ja terveys", r"elektrolyyt|bcaa|energy gel|aminohap|ravintolisä|vitamiini|magnesium|kalaöljy|omega|probiootti|maitohappo|lisäravin|proteiini|kreatiini|creatine|urheiluravin|kotitesti|testi|laastari|rakkolaast|ensiapu|kipu|lämpömittari|kondomi|sidetarvik|tukisukka|silmätipat|nenäsuihke|kurkkupastilli|itsehoito|terveyden"),
        ("Tuoksut", r"tuoksu|parfyym|parfum|\bedt\b|\bedp\b|eau de|body mist|after shave|partavesi"),
        ("Hiukset", r"kestoväri|kevytväri|hiusväri|hius|hiukset|shampoo|hoitoaine|sävyte|muotoilu|hairspray|muotoiluvaahto|got2b|syoss|schwarzkopf|gliss|cutrin|elvital|pantene|head & shoulders|kuivashampoo|hiusnaamio|lämpösuoja|kiharru|hiuslakka|taft|hiuspinni|ponnari"),
        ("Meikit ja kynnet", r"meikki|meikit|ripsiväri|huulipuna|huulikiilto|huulikynä|meikkivoide|puuteri|poskipuna|luomiväri|kulmaväri|kulmakynä|eyeliner|rajauskynä|kynsilakka|kynsi|maybelline|max factor|rimmel|essence|mascara|concealer|peitevoide|highlighter|bronzer|tekoripset"),
        ("Ihonhoito", r"kasvo|voide|seerumi|serum|naamio|mask\b|kosteus|puhdistus|aurinko|spf|vartalo|lotion|cream|rasva|käsivoide|huulirasva|huulivoide|huulibalsam|ihonhoito|kuorinta|kasvovesi|misellivesi|silmänympärys|derma|lv\b|nivea|eucerin|cerave|la roche"),
        ("Suihku, hygienia ja parranajo", r"suunhoito|tepe|suihku|saippua|deodorant|antiperspir|\bdeo\b|hammas|suuvesi|hammastahna|hammasharja|hammaslanka|parranajo|höylä|terä|partavaahto|gillette|tamponi|terveyss|\bside\b|ohutside|yöside|pikkuhousunsuoja|vanu|intiimi|käsidesi|kylpyvaah|kylpysuola|kylpyöljy|dove|rexona|wilkinson|venus\b|vuokkoset|libresse|always|colgate|pepsodent|sensodyne|oral-b|parta|ihokarvan|vahaliusk|epilointi|hygienia"),
    ],
    "Urheilu ja vapaa-aika": [
        ("Pyöräily", r"pyörä|pyöräil|polkupyör|rengas|sisärengas|satula|ketju|pumppu|kypärä|venttiili|pinna|vaihde"),
        ("Talviurheilu", r"sukset|suksi|sauvat|luistin|kelkka|pulkka|liukuri|lumilauta|monot|potkukelkka|voitelu|pitovoide|luistelu|hiihto"),
        ("Kuntoilu", r"kahvakuula|käsipaino|jooga|treeni|kuntopyörä|vastuskumi|jumppa|kuntoilu|juoksu|urheilukello|sykemittari|levypaino|leuanveto|hyppynaru|vatsarulla|harjoitus|fitness|gym"),
        ("Retkeily ja kalastus", r"retki|teltta|makuupussi|makuualusta|termos|otsalamppu|onki|vapa|uistin|viehe|kalastus|reppu|puukko|retkikeitin|kuksa|retkituoli|tulisija|kiikari|kompassi|vaellus|riippumatto|kalastaja|pilkki|siima"),
        ("Pallopelit ja pihapelit", r"pallo|maila|frisbee|sulkapallo|pingis|koripallo|jalkapallo|salibandy|tennis|golf|mölkky|kyykkä|trampoliini|petanque"),
        ("Käsityöt", r"lanka|puikot|virkkuu|ompelu|käsityö|neula|kangas|nappi|kirjonta|ompelukone"),
        ("Pelit ja harrasteet", r"\bpeli\b|pelit|lautapeli|kortit|palapeli|pelikortit|tikka|biljardi|rubik|harraste|pienoismalli"),
    ],
    "Elektroniikka ja kodinkoneet": [
        ("Kauneudenhoitolaitteet", r"partakone|kotiparturi|sonicare|hiustenkuiv|suoristus|kiharrin|parranajokone|trimmer|trimmeri|epilaattori|sähköhammas|oral-b|muotoilurauta|ihokarvanpoist|hiustenleikkuu"),
        ("Keittiön pienkoneet", r"vedenkeitin|kahvinkeitin|leivänpaahdin|tehosekoitin|blender|vatkain|airfryer|air fryer|ilmafriteer|mikroaaltou|monitoimikone|sauvasekoitin|vohvelirauta|kahvimylly|espressokone|kahvikone|mehulinko|leipäkone|friteeraus|hitaskeitin|vaaka|grillikone|sous vide"),
        ("Kodinkoneet", r"imuri|pölynimuri|pesukone|kuivausrumpu|jääkaappi|pakastin|liesi|\buuni|astianpesukone|silitysrauta|höyry|ilmanpuhdist|ilmankostut|tuuletin|lämpöpuhallin|patteri|ilmanvaihto"),
        ("Pelaaminen", r"pelikonsoli|playstation|ps5|ps4|xbox|nintendo|switch|ohjain|gaming|pelihiiri|pelikuuloke|pelituoli|\bpeli\b"),
        ("Ääni ja kuva", r"kuulok|kuuloke|nappikuuloke|kaiutin|\btv\b|televisio|soundbar|radio|jbl|kamera|projektori|bluetooth|levysoitin|mikrofoni|vahvistin"),
        ("Puhelimet ja tietokoneet", r"varavirta|puhelin|älypuhelin|tabletti|läppäri|kannettava|tietokone|hiiri|näppäimistö|laturi|kaapeli|usb|hdmi|virtapankki|muistikortti|näyttö|suojakuori|suojakalvo|älykello|reititin|muistitikku|kovalevy|ssd|tulostin|webkamera"),
        ("Valaistus ja paristot", r"lamppu|polttimo|\bled\b|valaisin|otsalamppu|taskulamppu|paristo|akku|jatkojohto|valosarja|pistorasia|ajastin|älypistoke"),
    ],
    "Työkalut, remontti ja autoilu": [
        ("Työvaatteet ja suojaimet", r"työhous|työtakki|työkenk|turvakenk|työkäsine|suojalasi|kuulosuojain|hengityssuoj|työvaate|työpaita|suojakäsine|heijastinliivi|työlapaset"),
        ("Autoilu", r"\bauto|pyyhkijän|tuulilasi|moottoriöljy|jäätymisenesto|lasinpesuneste|jääskrapa|jääskraba|lumiharja|akkulatur|käynnistys|autovaha|autoshampoo|renkaanvaih|rengaspain|lumiketju|hinausköysi|käynnistyskaapel|öljynsuod|auton"),
        ("Sähkötyökalut", r"porakone|\bpora\b|ruuvinväänt|akkuporakone|kulmahiomakone|hiomakone|sirkkeli|pistosaha|kompressori|painepesuri|oksasaha|moottorisaha|lehtipuhallin|ruohonleikkuri|akkutyökalu|työkoneet|kuumailmapuhal|monitoimityökalu"),
        ("Käsityökalut", r"vasara|ruuvimeisseli|ruuvitaltta|pihti|pihdit|saha|vatupassi|avainsarja|ulosvetäjä|taltta|kiintoavain|hylsy|työkalusarja|työkalu|mittanauha|vesivaaka|puukko|kirves|lekka|kuusiokolo|bitsi|terät|teräsarja"),
        ("Maalit, liimat ja tiivisteet", r"maali|pensseli|sivellin|maalitela|\btela\b|teippi|liima|silikoni|tiiviste|vaahto|kitti|hiomapaperi|hiomapap|lakka|petsi|kittaus|wd-40|ruoste|rasvasuihke|voiteluöljy"),
        ("Sähkö ja valaistus", r"jatkojohto|pistorasia|johto|lamppu|valaisin|\bled\b|kaapelikela|työvalo|valonheitin|kytkin|sulake|liitin"),
        ("Kiinnitys ja säilytys", r"nippuside|ruuvi|naula|tulppa|kiinnike|kulmalevy|naulauslevy|koukku|hylly|työkalulaatikko|säilytys|laatikko|lukko|yale|lukitus|riippulukko|kiristysliina|kuormaliina|tikkaat|jakkara|kärry|vaijeri"),
    ],
    "Piha, kukat ja puutarha": [
        ("Hautakynttilät ja ulkotulet", r"hauta|hautakynt|ulkotuli|ulkokynt|tulisoihtu|lyhtykynt"),
        ("Grillaus", r"grilli|hiili|briketti|sytytys|grillaus|kaasugrilli|sytytyspala|sytytysneste|grilliharja|grillausväl"),
        ("Ruukut, multa ja kylvö", r"komposti|ravinne|ruukku|ruukut|multa|lannoite|kylvö|siemenet|kastelukannu|ruukutus|amppeli|parvekelaatikko|kasvualusta|kate"),
        ("Kukat ja kasvit", r"kukka|kukat|kasvi|ruusu|tulppaani|amaryllis|joulutähti|hyasintti|calluna|kanerva|orkidea|kimppu|leikkokukka|viherkasvi|kaktus|kukkasipul|kukkivat|krysanteemi|pelargoni|havu|kuusi"),
        ("Pihatyökalut ja talvi", r"lapio|lumilapio|lumikola|lumityö|harava|letku|kastelu|oksasakset|ruohonleikkuri|trimmeri|kottikärry|kärry|lehtipuhallin|lumilinko|jäänesto|hiekoitus|tikkaat|sahat|kuokka|talikko"),
        ("Pihakalusteet ja valaistus", r"pihakaluste|puutarhakaluste|tuoli|pöytä|aurinkovarjo|ulkovalo|aurinkokenno|aurinkoken|lyhty|terassi|tyyny|riippukeinu|keinu|pihavalo|valosarja|ulkovalosarja|lintulauta|linnunpönt"),
    ],
    "Kirjat ja toimisto": [
        ("Kortit ja lahjapaketointi", r"kortti|kortit|joulukortti|kirjekuor|lahjapaperi|lahjanauha|lahjakassi|lahjapussi|lahjalappu|lahjarasia|tarra|paketointi|kortti miny"),
        ("Askartelu", r"lanka|lankadonitsi|diy|askartel|väri|liitu|muovailu|helmi|kimalle|sivellin|maalisetti|kangasmaali|piirustus|tussi"),
        ("Kirjat ja lehdet", r"ristikko|tai .* -|kirja|kirjat|romaani|keittokirja|lehti|sarjakuva|aku ankka|äänikirja|tietokirja|lastenkirja"),
        ("Toimistotarvikkeet", r"kynä|vihko|paperi|kansio|nitoja|sakset|teippi|lehtiö|muistikirja|kalenteri|laskin|liimapuikko|post-it|mustekas|tulostus|kirjoitus|toimisto|penaali|reppu|viivain|kumi|teroitin|muovitasku|irtolyijy|lyijy"),
    ],
}
SUBCAT_RX = {g: [(name, re.compile(rx)) for name, rx in rules] for g, rules in SUBCATS.items()}


def subcategorize(group, raw_cat, name, use_raw=True):
    """Product family inside a group, or "" when none fits.
    The name is tried first; the store's most specific category only when the store gives a specific one."""
    rules = SUBCAT_RX.get(group)
    if not rules:
        return ""
    texts = [(name or "").lower()]
    if use_raw and raw_cat:
        texts.append(raw_cat.split(" > ")[0].lower())
    for text in texts:
        for sub, rx in rules:
            if rx.search(text + " "):
                return sub
    return ""


# Groups tried for offers that the group rules could not place ("Muut"): the product families are more precise
# than the group rules, so "Kattovalaisin Aneta" still finds "Valaistus" even though no group rule matched.
# Food groups are left out: a non-food name like "Kaminapuhallin" must not land in "Kahvi" by accident.
GUESS_ORDER = ["Työkalut, remontti ja autoilu", "Elektroniikka ja kodinkoneet", "Vaatteet ja kengät", "Kauneus ja terveys",
               "Lapset ja lelut", "Lemmikit", "Urheilu ja vapaa-aika", "Piha, kukat ja puutarha", "Kirjat ja toimisto",
               "Koti, keittiö ja siivous"]


GUESS_FIRST = [
    ("Koti, keittiö ja siivous", "Joulu ja koristeet", re.compile(r"joulu|adventti|tonttu|kuusiköynn|kranssi")),
    ("Koti, keittiö ja siivous", "Valaisimet", re.compile(r"valaisin|plafondi|kattolamppu|pöytälamppu|lattialamppu|kohdevalo")),
    ("Kirjat ja toimisto", "Kortit ja lahjapaketointi", re.compile(r"lahjakassi|lahjapussi|lahjapaperi|sellofaani|pakettitarra|lahjanauha")),
]


def guess_group(name):
    low = (name or "").lower()
    for group, sub, rx in GUESS_FIRST:
        if rx.search(low):
            return group, sub
    for group in GUESS_ORDER:
        sub = subcategorize(group, "", name, use_raw=False)
        if sub:
            return group, sub
    return "Muut", ""
