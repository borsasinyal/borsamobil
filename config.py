"""
Borsa Sinyal Uygulaması - Ayarlar
TÜM BIST HİSSELERİ
"""

# TÜM BIST hisseleri (Tüm pazarlar: Yıldız, Ana, Alt, Yakın İzleme)
TUM_BIST = [
    "A1CAP", "ACSEL", "ADEL", "ADESE", "ADGYO", "AEFES", "AFYON", "AGESA",
    "AGHOL", "AGROT", "AHGAZ", "AKBNK", "AKCNS", "AKENR", "AKFGY", "AKFYE",
    "AKGRT", "AKMGY", "AKSA", "AKSEN", "AKSGY", "AKSUE", "AKYHO", "ALARK",
    "ALBRK", "ALCAR", "ALCTL", "ALFAS", "ALGYO", "ALKA", "ALKIM", "ALKLC",
    "ALMAD", "ALTNY", "ALVES", "ANELE", "ANGEN", "ANHYT", "ANSGR", "ARASE",
    "ARCLK", "ARDYZ", "ARENA", "ARMGD", "ARSAN", "ARTMS", "ARZUM", "ASELS",
    "ASGYO", "ASTOR", "ASUZU", "ATAGY", "ATAKP", "ATATP", "ATEKS", "ATLAS",
    "ATSYH", "AVGYO", "AVHOL", "AVOD", "AVPGY", "AVTUR", "AYCES", "AYDEM",
    "AYEN", "AYES", "AYGAZ", "AZTEK", "BAGFS", "BAHKM", "BAKAB", "BALAT",
    "BANVT", "BARMA", "BASCM", "BASGZ", "BAYRK", "BEGYO", "BERA", "BEYAZ",
    "BFREN", "BIENY", "BIGCH", "BIMAS", "BINBN", "BINHO", "BIOEN", "BIZIM",
    "BJKAS", "BLCYT", "BMSCH", "BMSTL", "BNTAS", "BOBET", "BORLS", "BORSK",
    "BOSSA", "BRISA", "BRKO", "BRKSN", "BRKVY", "BRLSM", "BRMEN", "BRSAN",
    "BRYAT", "BSOKE", "BTCIM", "BUCIM", "BULGS", "BURCE", "BURVA", "BVSAN",
    "BYDNR", "CANTE", "CASA", "CATES", "CCOLA", "CELHA", "CEMAS", "CEMTS",
    "CEOEM", "CIMSA", "CLEBI", "CMBTN", "CMENT", "CONSE", "COSMO", "CRDFA",
    "CRFSA", "CUSAN", "CVKMD", "CWENE", "DAGHL", "DAGI", "DAPGM", "DARDL",
    "DCTTR", "DENGE", "DERHL", "DERIM", "DESA", "DESPC", "DEVA", "DGATE",
    "DGGYO", "DGNMO", "DIRIT", "DITAS", "DMSAS", "DNISI", "DOAS", "DOBUR",
    "DOCO", "DOFER", "DOGUB", "DOHOL", "DOKTA", "DURDO", "DYOBY", "DZGYO",
    "EBEBK", "ECILC", "ECZYT", "EDATA", "EDIP", "EFORC", "EGEEN", "EGEPO",
    "EGGUB", "EGPRO", "EGSER", "EKGYO", "EKIZ", "EKOS", "EKSUN", "ELITE",
    "EMKEL", "EMNIS", "ENERY", "ENJSA", "ENKAI", "ENSRI", "ENTRA", "EPLAS",
    "ERBOS", "ERCB", "EREGL", "ERSU", "ESCAR", "ESCOM", "ESEN", "ETILR",
    "ETYAT", "EUHOL", "EUKYO", "EUPWR", "EUREN", "EUYO", "EYGYO", "FADE",
    "FENER", "FLAP", "FMIZP", "FONET", "FORMT", "FORTE", "FRIGO", "FROTO",
    "FZLGY", "GARAN", "GARFA", "GEDIK", "GEDZA", "GENIL", "GENTS", "GEREL",
    "GESAN", "GIPTA", "GLBMD", "GLCVY", "GLRYH", "GLYHO", "GMTAS", "GOKNR",
    "GOLTS", "GOODY", "GOZDE", "GRNYO", "GRSEL", "GRTHO", "GSDDE", "GSDHO",
    "GSRAY", "GUBRF", "GUNDG", "GWIND", "GZNMI", "HALKB", "HATEK", "HATSN",
    "HDFGS", "HEDEF", "HEKTS", "HKTM", "HLGYO", "HOROZ", "HRKET", "HTTBT",
    "HUBVC", "HUNER", "HURGZ", "ICBCT", "ICUGS", "IDGYO", "IEYHO", "IHAAS",
    "IHEVA", "IHGZT", "IHLAS", "IHLGM", "IHYAY", "IMASM", "INDES", "INFO",
    "INGRM", "INTEK", "INTEM", "INVEO", "INVES", "IPEKE", "ISATR", "ISBIR",
    "ISBTR", "ISCTR", "ISDMR", "ISFIN", "ISGSY", "ISGYO", "ISKPL", "ISMEN",
    "ISSEN", "ISYAT", "IZENR", "IZFAS", "IZINV", "IZMDC", "JANTS", "KAPLM",
    "KAREL", "KARSN", "KARTN", "KARYE", "KATMR", "KAYSE", "KBORU", "KCAER",
    "KCHOL", "KENT", "KERVN", "KERVT", "KFEIN", "KGYO", "KIMMR", "KLGYO",
    "KLKIM", "KLMSN", "KLNMA", "KLRHO", "KLSER", "KLSYN", "KMPUR", "KNFRT",
    "KOCMT", "KONKA", "KONTR", "KONYA", "KOPOL", "KORDS", "KOTON", "KOZAA",
    "KOZAL", "KRDMA", "KRDMB", "KRDMD", "KRGYO", "KRONT", "KRPLS", "KRSTL",
    "KRTEK", "KRVGD", "KSTUR", "KTLEV", "KTSKR", "KUTPO", "KUVVA", "KUYAS",
    "KZBGY", "KZGYO", "LIDER", "LIDFA", "LILAK", "LINK", "LKMNH", "LMKDC",
    "LOGO", "LRSHO", "LUKSK", "LYDHO", "MAALT", "MACKO", "MAGEN", "MAKIM",
    "MAKTK", "MANAS", "MARBL", "MARKA", "MARTI", "MAVI", "MEDTR", "MEGAP",
    "MEGMT", "MEKAG", "MEPET", "MERCN", "MERIT", "MERKO", "METRO", "METUR",
    "MGROS", "MHRGY", "MIATK", "MIPAZ", "MMCAS", "MNDRS", "MNDTR", "MOBTL",
    "MOGAN", "MPARK", "MRGYO", "MRSHL", "MSGYO", "MTRKS", "MTRYO", "MZHLD",
    "NATEN", "NETAS", "NIBAS", "NTGAZ", "NTHOL", "NUGYO", "NUHCM", "OBAMS",
    "OBASE", "ODAS", "ODINE", "OFSYM", "ONCSM", "ONRYT", "ORCAY", "ORGE",
    "ORMA", "OSMEN", "OSTIM", "OTKAR", "OTOKC", "OTTO", "OYAKC", "OYAYO",
    "OYLUM", "OYYAT", "OZATD", "OZGYO", "OZKGY", "OZRDN", "OZSUB", "OZYSR",
    "PAGYO", "PAMEL", "PAPIL", "PARSN", "PASEU", "PATEK", "PCILT", "PEHOL",
    "PEKGY", "PENGD", "PENTA", "PETKM", "PETUN", "PGSUS", "PINSU", "PKART",
    "PKENT", "PLTUR", "PNLSN", "PNSUT", "POLHO", "POLTK", "PRDGS", "PRKAB",
    "PRKME", "PRZMA", "PSDTC", "PSGYO", "QNBFB", "QNBFL", "QUAGR", "RALYH",
    "RAYSG", "REEDR", "RGYAS", "RNPOL", "RODRG", "RTALB", "RUBNS", "RYGYO",
    "RYSAS", "SAFKR", "SAHOL", "SAMAT", "SANEL", "SANFM", "SANKO", "SARKY",
    "SASA", "SAYAS", "SDTTR", "SEGYO", "SEKFK", "SEKUR", "SELEC", "SELGD",
    "SELVA", "SERNT", "SERVE", "SEYKM", "SILVR", "SISE", "SKBNK", "SKTAS",
    "SKYLP", "SKYMD", "SMART", "SMRTG", "SNGYO", "SNICA", "SNKRN", "SODSN",
    "SOKE", "SOKM", "SONME", "SRVGY", "SUMAS", "SUNTK", "SURGY", "SUWEN",
    "TABGD", "TARKM", "TATEN", "TATGD", "TAVHL", "TBORG", "TCELL", "TCKRC",
    "TDGYO", "TEKTU", "TERA", "TETMT", "TEZOL", "TGSAS", "THYAO", "TKFEN",
    "TKNSA", "TLMAN", "TMPOL", "TMSN", "TNZTP", "TOASO", "TRCAS", "TRGYO",
    "TRILC", "TSGYO", "TSKB", "TSPOR", "TTKOM", "TTRAK", "TUCLK", "TUKAS",
    "TUPRS", "TUREX", "TURGG", "TURSG", "UFUK", "ULAS", "ULKER", "ULUFA",
    "ULUSE", "ULUUN", "UMPAS", "UNLU", "USAK", "VAKBN", "VAKFN", "VAKKO",
    "VANGD", "VBTYZ", "VERTU", "VERUS", "VESBE", "VESTL", "VKFYO", "VKGYO",
    "VKING", "VRGYO", "YAPRK", "YATAS", "YAYLA", "YBTAS", "YEOTK", "YESIL",
    "YGGYO", "YGYO", "YKBNK", "YKSLN", "YONGA", "YUNSA", "YYAPI", "YYLGD",
    "ZEDUR", "ZOREN", "ZRGYO"
]

# Yahoo Finance için .IS uzantısı eklenmiş liste
BIST_SYMBOLS = [f"{symbol}.IS" for symbol in TUM_BIST]

# Bilgi
print(f"📊 Toplam {len(TUM_BIST)} BIST hissesi yüklendi")

# Veritabanı ayarları
DATABASE_NAME = "borsa_sinyal.db"

# Tarama ayarları
SCAN_INTERVAL_MINUTES = 15  # Her 15 dakikada bir tarama
HISTORICAL_DAYS = 365  # 1 yıllık geçmiş veri

# Sinyal eşik değerleri
RSI_OVERSOLD = 30      # Aşırı satım
RSI_OVERBOUGHT = 70    # Aşırı alım
MIN_SIGNAL_SCORE = 65  # Minimum sinyal skoru (0-100)

# Borsa saatleri (Türkiye)
MARKET_OPEN_HOUR = 10
MARKET_CLOSE_HOUR = 18


# Telegram (bulutta environment variable'dan, yerelde direkt)
import os
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8979052471:AAExZQmB5KTJpuIsMBnN-c4o1Rlx02V10Ro')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '982314149')