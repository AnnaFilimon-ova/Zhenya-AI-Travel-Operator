import logging
import time

import httpx

from app.geo import CITY_IATA

log = logging.getLogger(__name__)

AUTOCOMPLETE_URL = "https://autocomplete.travelpayouts.com/places2"
CACHE_TTL = 24 * 3600
CACHE_MAX = 500
_cache: dict[str, tuple[float, str | None]] = {}

WORLD_IATA = {
    "москва": "MOW", "moscow": "MOW",
    "санкт-петербург": "LED", "санкт петербург": "LED", "петербург": "LED", "питер": "LED", "saint petersburg": "LED",
    "сочи": "AER", "sochi": "AER",
    "казань": "KZN", "калининград": "KGD", "екатеринбург": "SVX", "нижний новгород": "GOJ",
    "иркутск": "IKT", "кисловодск": "MRV", "минеральные воды": "MRV",
    "новосибирск": "OVB", "краснодар": "KRR", "самара": "KUF", "уфа": "UFA", "владивосток": "VVO",
    "стамбул": "IST", "istanbul": "IST", "анталья": "AYT", "antalya": "AYT", "анкара": "ESB",
    "бодрум": "BJV", "даламан": "DLM", "измир": "ADB",
    "дубай": "DXB", "dubai": "DXB", "абу-даби": "AUH", "абу даби": "AUH", "шарджа": "SHJ",
    "тбилиси": "TBS", "tbilisi": "TBS", "батуми": "BUS", "batumi": "BUS",
    "ереван": "EVN", "yerevan": "EVN", "баку": "BAK", "baku": "BAK",
    "минск": "MSQ", "алматы": "ALA", "астана": "NQZ", "ташкент": "TAS", "самарканд": "SKD",
    "бишкек": "FRU", "душанбе": "DYU",
    "бангкок": "BKK", "bangkok": "BKK", "пхукет": "HKT", "phuket": "HKT", "паттайя": "BKK",
    "самуи": "USM", "краби": "KBV", "чиангмай": "CNX",
    "ханой": "HAN", "хошимин": "SGN", "хо ши мин": "SGN", "нячанг": "CXR", "дананг": "DAD", "фукуок": "PQC",
    "бали": "DPS", "денпасар": "DPS", "bali": "DPS", "джакарта": "JKT",
    "куала-лумпур": "KUL", "куала лумпур": "KUL", "сингапур": "SIN", "singapore": "SIN",
    "гонконг": "HKG", "hong kong": "HKG", "пекин": "BJS", "beijing": "BJS", "шанхай": "SHA", "shanghai": "SHA",
    "гуанчжоу": "CAN", "шэньчжэнь": "SZX", "санья": "SYX", "харбин": "HRB",
    "токио": "TYO", "tokyo": "TYO", "осака": "OSA", "киото": "OSA", "сеул": "SEL", "seoul": "SEL",
    "дели": "DEL", "мумбаи": "BOM", "гоа": "GOI", "коломбо": "CMB", "мале": "MLE", "мальдивы": "MLE",
    "катманду": "KTM", "тель-авив": "TLV", "тель авив": "TLV", "иерусалим": "TLV",
    "доха": "DOH", "doha": "DOH", "эр-рияд": "RUH", "рияд": "RUH", "джидда": "JED", "маскат": "MCT", "амман": "AMM",
    "каир": "CAI", "cairo": "CAI", "шарм-эль-шейх": "SSH", "шарм эль шейх": "SSH", "хургада": "HRG", "hurghada": "HRG",
    "марракеш": "RAK", "касабланка": "CAS", "тунис": "TUN",
    "париж": "PAR", "paris": "PAR", "лондон": "LON", "london": "LON", "рим": "ROM", "rome": "ROM",
    "милан": "MIL", "венеция": "VCE", "флоренция": "FLR", "неаполь": "NAP",
    "барселона": "BCN", "barcelona": "BCN", "мадрид": "MAD", "madrid": "MAD", "лиссабон": "LIS", "порту": "OPO",
    "берлин": "BER", "berlin": "BER", "мюнхен": "MUC", "франкфурт": "FRA", "гамбург": "HAM",
    "амстердам": "AMS", "amsterdam": "AMS", "брюссель": "BRU", "вена": "VIE", "прага": "PRG", "prague": "PRG",
    "будапешт": "BUD", "варшава": "WAW", "краков": "KRK", "афины": "ATH", "athens": "ATH", "салоники": "SKG",
    "белград": "BEG", "belgrade": "BEG", "подгорица": "TGD", "тиват": "TIV", "сараево": "SJJ", "тирана": "TIA",
    "скопье": "SKP", "загреб": "ZAG", "дубровник": "DBV", "сплит": "SPU", "любляна": "LJU", "братислава": "BTS",
    "цюрих": "ZRH", "женева": "GVA", "копенгаген": "CPH", "стокгольм": "STO", "осло": "OSL", "хельсинки": "HEL",
    "рейкьявик": "REK", "дублин": "DUB", "эдинбург": "EDI", "ларнака": "LCA", "никосия": "NIC", "пафос": "PFO",
    "бухарест": "BUH", "будва": "TIV", "бухара": "BHK",
    "нью-йорк": "NYC", "new york": "NYC", "нью йорк": "NYC", "лос-анджелес": "LAX", "майами": "MIA",
    "сан-франциско": "SFO", "лас-вегас": "LAS", "чикаго": "CHI", "торонто": "YTO", "ванкувер": "YVR",
    "мехико": "MEX", "канкун": "CUN", "гавана": "HAV", "варадеро": "VRA", "пунта-кана": "PUJ", "пунта кана": "PUJ",
    "рио-де-жанейро": "RIO", "буэнос-айрес": "BUE", "сантьяго": "SCL", "лима": "LIM", "богота": "BOG",
    "сидней": "SYD", "мельбурн": "MEL", "окленд": "AKL",
    "маэ": "SEZ", "сейшелы": "SEZ", "маврикий": "MRU", "занзибар": "ZNZ", "найроби": "NBO", "кейптаун": "CPT",
}


def _store(key: str, code: str | None) -> None:
    if len(_cache) >= CACHE_MAX:
        _cache.clear()
    _cache[key] = (time.time(), code)


async def _autocomplete(term: str) -> str | None:
    params = {"term": term, "locale": "ru", "types[]": ["city", "airport"]}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(AUTOCOMPLETE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("IATA autocomplete failed: %s", type(exc).__name__)
        raise
    if not isinstance(data, list):
        return None
    for row in data:
        code = row.get("code") if isinstance(row, dict) else None
        if isinstance(code, str) and len(code) == 3 and code.isalpha():
            return code.upper()
    return None


async def resolve_iata_world(place: str) -> str | None:
    raw = (place or "").strip()
    if not raw:
        return None
    if len(raw) == 3 and raw.isascii() and raw.isalpha():
        return raw.upper()
    if raw in CITY_IATA:
        return CITY_IATA[raw]
    head = raw.split(",")[0].strip().lower()
    for key in (raw.lower(), head):
        if key in WORLD_IATA:
            return WORLD_IATA[key]
    hit = _cache.get(head)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        code = await _autocomplete(head)
    except (httpx.HTTPError, ValueError):
        return None
    _store(head, code)
    return code
