# -*- coding: utf-8 -*-
"""Market registry.

Each entry maps a Yahoo Finance *region* code (used by the equity screener) to
display metadata, the ticker suffixes Yahoo uses for that market, and the local
trading currency.

`available` reflects whether Yahoo's screener actually returns constituents for
that region -- a handful of regions are listed by the API but return nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class Market:
    region: str          # Yahoo screener region code
    name_en: str
    name_zh: str
    flag: str
    group: str           # continent / bloc used for UI grouping
    currency: str        # local quote currency
    suffixes: List[str]  # Yahoo ticker suffixes ('' means bare ticker)
    exchanges: List[str] # human readable exchange names
    available: bool = True


_M = Market

MARKETS: List[Market] = [
    # ---------------- North America ----------------
    _M("us", "United States", "美国", "🇺🇸", "北美", "USD", ["", ".US"], ["NYSE", "NASDAQ", "NYSE American", "CBOE"]),
    _M("ca", "Canada", "加拿大", "🇨🇦", "北美", "CAD", [".TO", ".V", ".NE", ".CN"], ["TSX", "TSX-V", "NEO", "CSE"]),
    _M("mx", "Mexico", "墨西哥", "🇲🇽", "北美", "MXN", [".MX"], ["BMV"]),

    # ---------------- Greater China ----------------
    _M("cn", "China A-Shares", "中国A股", "🇨🇳", "大中华", "CNY", [".SS", ".SZ"], ["上交所", "深交所"]),
    _M("hk", "Hong Kong", "中国香港", "🇭🇰", "大中华", "HKD", [".HK"], ["HKEX"]),
    _M("tw", "Taiwan", "中国台湾", "🇹🇼", "大中华", "TWD", [".TW", ".TWO"], ["TWSE", "TPEx"]),

    # ---------------- Asia Pacific ----------------
    _M("jp", "Japan", "日本", "🇯🇵", "亚太", "JPY", [".T"], ["Tokyo Stock Exchange"]),
    _M("kr", "South Korea", "韩国", "🇰🇷", "亚太", "KRW", [".KS", ".KQ"], ["KOSPI", "KOSDAQ"]),
    _M("in", "India", "印度", "🇮🇳", "亚太", "INR", [".NS", ".BO"], ["NSE", "BSE"]),
    _M("sg", "Singapore", "新加坡", "🇸🇬", "亚太", "SGD", [".SI"], ["SGX"]),
    _M("au", "Australia", "澳大利亚", "🇦🇺", "亚太", "AUD", [".AX"], ["ASX"]),
    _M("nz", "New Zealand", "新西兰", "🇳🇿", "亚太", "NZD", [".NZ"], ["NZX"]),
    _M("id", "Indonesia", "印度尼西亚", "🇮🇩", "亚太", "IDR", [".JK"], ["IDX"]),
    _M("my", "Malaysia", "马来西亚", "🇲🇾", "亚太", "MYR", [".KL"], ["Bursa Malaysia"]),
    _M("th", "Thailand", "泰国", "🇹🇭", "亚太", "THB", [".BK"], ["SET"]),
    _M("ph", "Philippines", "菲律宾", "🇵🇭", "亚太", "PHP", [".PS"], ["PSE"], available=False),
    _M("vn", "Vietnam", "越南", "🇻🇳", "亚太", "VND", [".VN"], ["HOSE"], available=False),
    _M("pk", "Pakistan", "巴基斯坦", "🇵🇰", "亚太", "PKR", [".KA"], ["PSX"], available=False),
    _M("lk", "Sri Lanka", "斯里兰卡", "🇱🇰", "亚太", "LKR", [".CM"], ["CSE"], available=False),

    # ---------------- Western Europe ----------------
    _M("gb", "United Kingdom", "英国", "🇬🇧", "欧洲", "GBP", [".L", ".IL"], ["LSE", "LSE Intl"]),
    _M("de", "Germany", "德国", "🇩🇪", "欧洲", "EUR", [".DE", ".F", ".BE", ".DU", ".HM", ".HA", ".MU", ".SG"], ["XETRA", "Frankfurt", "Berlin", "Düsseldorf"]),
    _M("fr", "France", "法国", "🇫🇷", "欧洲", "EUR", [".PA"], ["Euronext Paris"]),
    _M("nl", "Netherlands", "荷兰", "🇳🇱", "欧洲", "EUR", [".AS"], ["Euronext Amsterdam"]),
    _M("ch", "Switzerland", "瑞士", "🇨🇭", "欧洲", "CHF", [".SW"], ["SIX Swiss"]),
    _M("it", "Italy", "意大利", "🇮🇹", "欧洲", "EUR", [".MI"], ["Borsa Italiana"]),
    _M("es", "Spain", "西班牙", "🇪🇸", "欧洲", "EUR", [".MC"], ["BME Madrid"]),
    _M("be", "Belgium", "比利时", "🇧🇪", "欧洲", "EUR", [".BR"], ["Euronext Brussels"]),
    _M("at", "Austria", "奥地利", "🇦🇹", "欧洲", "EUR", [".VI"], ["Wiener Börse"]),
    _M("pt", "Portugal", "葡萄牙", "🇵🇹", "欧洲", "EUR", [".LS"], ["Euronext Lisbon"]),
    _M("ie", "Ireland", "爱尔兰", "🇮🇪", "欧洲", "EUR", [".IR"], ["Euronext Dublin"]),
    _M("gr", "Greece", "希腊", "🇬🇷", "欧洲", "EUR", [".AT"], ["ATHEX"]),

    # ---------------- Nordics & Baltics ----------------
    _M("se", "Sweden", "瑞典", "🇸🇪", "北欧", "SEK", [".ST"], ["Nasdaq Stockholm"]),
    _M("no", "Norway", "挪威", "🇳🇴", "北欧", "NOK", [".OL"], ["Oslo Børs"]),
    _M("dk", "Denmark", "丹麦", "🇩🇰", "北欧", "DKK", [".CO"], ["Nasdaq Copenhagen"]),
    _M("fi", "Finland", "芬兰", "🇫🇮", "北欧", "EUR", [".HE"], ["Nasdaq Helsinki"]),
    _M("is", "Iceland", "冰岛", "🇮🇸", "北欧", "ISK", [".IC"], ["Nasdaq Iceland"]),
    _M("ee", "Estonia", "爱沙尼亚", "🇪🇪", "北欧", "EUR", [".TL"], ["Nasdaq Tallinn"]),
    _M("lv", "Latvia", "拉脱维亚", "🇱🇻", "北欧", "EUR", [".RG"], ["Nasdaq Riga"]),
    _M("lt", "Lithuania", "立陶宛", "🇱🇹", "北欧", "EUR", [".VS"], ["Nasdaq Vilnius"]),

    # ---------------- Central & Eastern Europe ----------------
    _M("pl", "Poland", "波兰", "🇵🇱", "中东欧", "PLN", [".WA"], ["GPW Warsaw"]),
    _M("cz", "Czechia", "捷克", "🇨🇿", "中东欧", "CZK", [".PR"], ["Prague SE"]),
    _M("hu", "Hungary", "匈牙利", "🇭🇺", "中东欧", "HUF", [".BD"], ["Budapest SE"]),
    _M("ro", "Romania", "罗马尼亚", "🇷🇴", "中东欧", "RON", [".RO"], ["Bucharest SE"]),
    _M("ru", "Russia", "俄罗斯", "🇷🇺", "中东欧", "RUB", [".ME"], ["MOEX"], available=False),

    # ---------------- Middle East & Africa ----------------
    _M("sa", "Saudi Arabia", "沙特阿拉伯", "🇸🇦", "中东非洲", "SAR", [".SR"], ["Tadawul"]),
    _M("il", "Israel", "以色列", "🇮🇱", "中东非洲", "ILS", [".TA"], ["TASE"]),
    _M("tr", "Türkiye", "土耳其", "🇹🇷", "中东非洲", "TRY", [".IS"], ["Borsa Istanbul"]),
    _M("qa", "Qatar", "卡塔尔", "🇶🇦", "中东非洲", "QAR", [".QA"], ["QSE"]),
    _M("kw", "Kuwait", "科威特", "🇰🇼", "中东非洲", "KWD", [".KW"], ["Boursa Kuwait"]),
    _M("za", "South Africa", "南非", "🇿🇦", "中东非洲", "ZAR", [".JO"], ["JSE"]),
    _M("eg", "Egypt", "埃及", "🇪🇬", "中东非洲", "EGP", [".CA"], ["EGX"], available=False),

    # ---------------- Latin America ----------------
    _M("br", "Brazil", "巴西", "🇧🇷", "拉美", "BRL", [".SA"], ["B3"]),
    _M("cl", "Chile", "智利", "🇨🇱", "拉美", "CLP", [".SN"], ["Santiago SE"]),
    _M("ar", "Argentina", "阿根廷", "🇦🇷", "拉美", "ARS", [".BA"], ["BYMA"]),
    _M("co", "Colombia", "哥伦比亚", "🇨🇴", "拉美", "COP", [".CL"], ["BVC"], available=False),
    _M("pe", "Peru", "秘鲁", "🇵🇪", "拉美", "PEN", [".LM"], ["BVL"], available=False),
    _M("ve", "Venezuela", "委内瑞拉", "🇻🇪", "拉美", "VES", [".CR"], ["BVC"], available=False),
]

BY_REGION: Dict[str, Market] = {m.region: m for m in MARKETS}

GROUP_ORDER = ["北美", "大中华", "亚太", "欧洲", "北欧", "中东欧", "中东非洲", "拉美"]

# Currencies Yahoo quotes in minor units (pence / cents / agorot).
# Financial statements are still reported in the major unit, so this only
# affects quote-derived numbers such as price and market cap.
MINOR_UNIT_CURRENCIES = {"GBp": ("GBP", 100.0), "ZAc": ("ZAR", 100.0), "ILA": ("ILS", 100.0)}


def normalize_currency(code: str | None) -> tuple[str | None, float]:
    """Return (major currency code, divisor) for a Yahoo currency string."""
    if not code:
        return None, 1.0
    if code in MINOR_UNIT_CURRENCIES:
        major, div = MINOR_UNIT_CURRENCIES[code]
        return major, div
    return code.upper(), 1.0


def suffix_to_region(symbol: str) -> str | None:
    """Best-effort reverse lookup: '.DE' -> 'de'. Bare tickers -> 'us'."""
    sym = symbol.strip().upper()
    if "." not in sym:
        return "us"
    dot = "." + sym.rsplit(".", 1)[1]
    for m in MARKETS:
        if dot in [s.upper() for s in m.suffixes if s]:
            return m.region
    return None


def serialize() -> List[dict]:
    return [asdict(m) for m in MARKETS]
