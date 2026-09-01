# -*- coding: utf-8 -*-
"""Universe discovery -- how we decide *which* tickers to pull.

Three sources, all live (no bundled ticker lists to go stale):

1. ``screener``  Yahoo's equity screener, filtered by region / market cap /
   sector. This is what unlocks the 45+ non-US markets: it enumerates the
   actual constituents of each exchange, ranked by market cap.
2. ``custom``    Symbols pasted or uploaded by the user.
3. ``search``    Free-text lookup used by the UI's symbol autocomplete.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, List, Optional

import yfinance as yf

from . import markets

log = logging.getLogger(__name__)

PAGE_SIZE = 100          # Yahoo rejects sizes above 250; 100 keeps latency sane
MAX_UNIVERSE = 5000      # hard ceiling so a stray request can't run forever

SORT_FIELDS = {
    "market_cap": "intradaymarketcap",
    "price": "intradayprice",
    "volume": "dayvolume",
    "pe": "peratio.lasttwelvemonths",
}

SECTORS = [
    "Basic Materials", "Communication Services", "Consumer Cyclical",
    "Consumer Defensive", "Energy", "Financial Services", "Healthcare",
    "Industrials", "Real Estate", "Technology", "Utilities",
]

_screen_lock = threading.Lock()


def _build_query(region: str, min_cap: Optional[float], max_cap: Optional[float],
                 sectors: Optional[List[str]]):
    clauses = [yf.EquityQuery("eq", ["region", region])]
    if min_cap:
        clauses.append(yf.EquityQuery("gt", ["intradaymarketcap", float(min_cap)]))
    if max_cap:
        clauses.append(yf.EquityQuery("lt", ["intradaymarketcap", float(max_cap)]))
    if sectors:
        picked = [s for s in sectors if s in SECTORS]
        if len(picked) == 1:
            clauses.append(yf.EquityQuery("eq", ["sector", picked[0]]))
        elif len(picked) > 1:
            clauses.append(yf.EquityQuery(
                "or", [yf.EquityQuery("eq", ["sector", s]) for s in picked]))
    if len(clauses) == 1:
        # 'and' needs at least two operands; add a no-op market cap floor
        clauses.append(yf.EquityQuery("gt", ["intradaymarketcap", 0]))
    return yf.EquityQuery("and", clauses)


def screen_region(
    region: str,
    limit: int = 100,
    offset: int = 0,
    min_cap: Optional[float] = None,
    max_cap: Optional[float] = None,
    sectors: Optional[List[str]] = None,
    domestic_only: bool = True,
    local_currency_only: bool = False,
    sort_by: str = "market_cap",
    sort_asc: bool = False,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Dict:
    """Enumerate listings on one market.

    ``domestic_only`` drops cross-listings and secondary lines (see
    :func:`_is_primary_local_line`), which otherwise fill the entire top of the
    market-cap ranking on every non-US exchange.
    """
    region = region.lower()
    limit = max(1, min(int(limit), MAX_UNIVERSE))
    query = _build_query(region, min_cap, max_cap, sectors)
    market = markets.BY_REGION.get(region)
    local_currency = market.currency if (local_currency_only and market) else None
    sort_field = SORT_FIELDS.get(sort_by, SORT_FIELDS["market_cap"])

    rows: List[dict] = []
    seen_company: Dict[str, List[int]] = {}   # name prefix -> indices into rows
    total = 0
    cursor = max(0, int(offset))
    # Cross-listings can occupy hundreds of slots before the first local name,
    # so the filtered path scans far deeper than it keeps.
    scan_budget = (limit * 8 + 300) if domestic_only else limit
    scan_budget += cursor
    scanned = 0

    while len(rows) < limit and scanned < scan_budget:
        page = min(PAGE_SIZE, scan_budget - scanned)
        try:
            with _screen_lock:
                resp = yf.screen(query, sortField=sort_field, sortAsc=sort_asc,
                                 size=page, offset=cursor)
        except Exception as exc:  # noqa: BLE001 - Yahoo returns many shapes of failure
            log.warning("screener failed for %s at offset %s: %s", region, cursor, exc)
            break

        quotes = resp.get("quotes") or []
        total = resp.get("total", total) or total
        if not quotes:
            break

        for q in quotes:
            if q.get("quoteType") != "EQUITY":
                continue
            if domestic_only and not _is_primary_local_line(q, local_currency):
                continue
            cur, div = markets.normalize_currency(q.get("currency"))
            price = q.get("regularMarketPrice")
            row = {
                "symbol": q.get("symbol"),
                "name": q.get("shortName") or q.get("longName") or "",
                "long_name": q.get("longName") or "",
                "exchange": q.get("fullExchangeName") or q.get("exchange") or "",
                "region": region,
                "quote_currency": cur,
                "financial_currency": q.get("financialCurrency"),
                # Yahoo reports market cap in the major currency unit even where
                # prices are quoted in pence/cents, so only the price is scaled.
                "market_cap": q.get("marketCap"),
                "trailing_pe": q.get("trailingPE"),
                "price": (price / div) if isinstance(price, (int, float)) else price,
            }

            if domestic_only:
                # LSE and SIX list the same company on several boards (HSBA.L vs
                # HSBAL.XC). Keep the most actively traded line of each company.
                row["_turnover"] = _turnover(q)
                key = _name_prefix(row["name"])
                duplicate_of = next(
                    (i for i in seen_company.get(key, []) if _same_issuer(rows[i], row)), None)
                if duplicate_of is not None:
                    if row["_turnover"] > rows[duplicate_of].get("_turnover", 0.0):
                        rows[duplicate_of] = row
                    continue
                seen_company.setdefault(key, []).append(len(rows))

            rows.append(row)
            if len(rows) >= limit and not domestic_only:
                break
        # When de-duplicating we finish the page even after hitting the limit,
        # so a better line further down (BARC.L after BARCL.XC) can still win.

        cursor += len(quotes)
        scanned += len(quotes)
        if on_progress:
            on_progress(len(rows), limit)
        if len(quotes) < page or cursor >= (total or 0):
            break

    for row in rows:
        row.pop("_turnover", None)
    return {"region": region, "total_available": total, "items": rows[:limit]}


# ------------------------------------------------------- cross-listing filter

# Below this share of market cap changing hands per day, a line is a dormant
# cross-listing rather than the company's real home market. Genuine local
# small caps sit orders of magnitude above it.
DORMANT_TURNOVER_RATIO = 1e-5

# Yahoo tags depositary-receipt boards (Frankfurt's foreign segment) this way.
FOREIGN_MARKET_PREFIXES = ("dr_",)


def _turnover(quote: dict) -> float:
    volume = quote.get("averageDailyVolume3Month") or quote.get("regularMarketVolume") or 0
    price = quote.get("regularMarketPrice") or 0
    try:
        return float(volume) * float(price)
    except (TypeError, ValueError):
        return 0.0


def _is_primary_local_line(quote: dict, local_currency: Optional[str] = None) -> bool:
    """Heuristic: is this the company's own home-market listing?

    Yahoo gives us no domicile field -- its ``region`` is the *caller's* region,
    not the issuer's -- so we lean on observable signals:

    * depositary-receipt market segments are foreign by definition;
    * a cross-listed line barely trades relative to the company's market cap
      (NVDA.SW turns over ~0.0005% of its cap a day, NESN.SW ~0.13%);
    * optionally, the filing currency must match the market's own currency.
      That last one is exact for Germany/Italy/Brazil but too strict for the
      UK, where HSBC and Shell genuinely report in USD -- hence a separate flag.
    """
    if str(quote.get("market", "")).startswith(FOREIGN_MARKET_PREFIXES):
        return False
    cap = quote.get("marketCap")
    if not isinstance(cap, (int, float)) or cap <= 0:
        return False
    if local_currency:
        filing = quote.get("financialCurrency")
        if filing and filing.upper() != local_currency.upper():
            return False
    return (_turnover(quote) / cap) >= DORMANT_TURNOVER_RATIO


def _name_prefix(name: str) -> str:
    """First three letters of the issuer name, ignoring punctuation."""
    letters = [c for c in name.upper() if c.isalpha()]
    return "".join(letters[:3])


def _same_issuer(a: dict, b: dict) -> bool:
    """Two listing lines of one company (HSBA.L vs HSBAL.XC).

    Same leading letters plus market caps within 3% -- Yahoo reports the
    issuer's full cap on every line, so duplicates land almost exactly on top
    of each other while distinct companies do not.
    """
    if _name_prefix(a.get("name", "")) != _name_prefix(b.get("name", "")):
        return False
    ca, cb = a.get("market_cap"), b.get("market_cap")
    if not (isinstance(ca, (int, float)) and isinstance(cb, (int, float))) or not ca or not cb:
        return False
    return abs(ca - cb) / max(ca, cb) <= 0.03


def search_symbols(query: str, limit: int = 12) -> List[dict]:
    """Free-text symbol lookup across every Yahoo-covered exchange."""
    if not query or not query.strip():
        return []
    try:
        quotes = yf.Search(query.strip(), max_results=limit, news_count=0).quotes or []
    except Exception as exc:  # noqa: BLE001
        log.warning("symbol search failed for %r: %s", query, exc)
        return []

    out = []
    for q in quotes:
        symbol = q.get("symbol")
        if not symbol or q.get("quoteType") != "EQUITY":
            continue
        region = markets.suffix_to_region(symbol)
        out.append({
            "symbol": symbol,
            "name": q.get("shortname") or q.get("longname") or "",
            "exchange": q.get("exchDisp") or q.get("exchange") or "",
            "region": region,
            "market": markets.BY_REGION[region].name_zh if region in markets.BY_REGION else "",
        })
    return out


def parse_custom(raw: str) -> List[dict]:
    """Accept comma / whitespace / newline separated tickers, plus CSV paste."""
    if not raw:
        return []
    seen, out = set(), []
    for chunk in raw.replace(",", "\n").replace(";", "\n").replace("\t", "\n").split("\n"):
        sym = chunk.strip().strip('"').strip("'").upper()
        if not sym or sym in seen:
            continue
        # skip obvious CSV headers
        if sym in {"SYMBOL", "TICKER", "CODE", "STOCK_CODE", "YFINANCE_CODE", "股票代码"}:
            continue
        seen.add(sym)
        region = markets.suffix_to_region(sym) or "us"
        out.append({"symbol": sym, "name": "", "exchange": "", "region": region,
                    "quote_currency": None, "market_cap": None, "trailing_pe": None, "price": None})
    return out
