# -*- coding: utf-8 -*-
"""Per-ticker financial statement extraction.

Fixes the two bugs that made the original scripts fail outside the US:

1. Quarterly statements were required. Most European, Australian and Japanese
   issuers report semi-annually, so ``quarterly_income_stmt`` comes back empty
   and the old code bailed out. We now fall back to annual statements whenever
   the quarterly set is empty -- not just when it raises.
2. Currency and exchange were guessed from substrings of the ticker
   (``'L' in code`` matched AAPL and stamped it GBP). We now read the currency
   Yahoo reports for the filing itself.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence

import pandas as pd
import yfinance as yf

from . import fields as F
from . import markets

log = logging.getLogger(__name__)

PERIOD_AUTO = "auto"
PERIOD_QUARTERLY = "quarterly"
PERIOD_ANNUAL = "annual"


class FetchError(Exception):
    pass


def _clean(value):
    """Normalise numpy/NaN/inf into JSON-safe primitives."""
    if value is None:
        return None
    if isinstance(value, (str, bool)):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int,)):
        return int(value)
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _row_value(frame: Optional[pd.DataFrame], aliases: Sequence[str], column) -> Optional[float]:
    if frame is None or frame.empty or column not in frame.columns:
        return None
    for alias in aliases:
        if alias in frame.index:
            val = frame.loc[alias, column]
            if isinstance(val, pd.Series):      # duplicated index labels
                val = val.iloc[0]
            cleaned = _clean(val)
            if cleaned is not None:
                return cleaned
    return None


def _statement(ticker: yf.Ticker, kind: str, quarterly: bool) -> pd.DataFrame:
    getter = {
        ("income", True): "quarterly_income_stmt",
        ("income", False): "income_stmt",
        ("balance", True): "quarterly_balance_sheet",
        ("balance", False): "balance_sheet",
        ("cashflow", True): "quarterly_cashflow",
        ("cashflow", False): "cashflow",
    }[(kind, quarterly)]
    try:
        frame = getattr(ticker, getter)
    except Exception as exc:  # noqa: BLE001
        log.debug("%s unavailable: %s", getter, exc)
        return pd.DataFrame()
    return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()


def _needed_statements(selection: Sequence[str]) -> set:
    return {F.BY_KEY[k].source for k in selection
            if k in F.BY_KEY and F.BY_KEY[k].source in {"balance", "income", "cashflow"}}


def _needs_info(selection: Sequence[str]) -> bool:
    return any(
        k in F.BY_KEY and (F.BY_KEY[k].source == "quote" or
                           (F.BY_KEY[k].source == "identity" and F.BY_KEY[k].info_key))
        for k in selection
    )


def _period_columns(frames: Dict[str, pd.DataFrame], limit: int,
                    date_from: Optional[date], date_to: Optional[date]) -> List:
    seen = {}
    for frame in frames.values():
        if frame is None or frame.empty:
            continue
        for col in frame.columns:
            try:
                key = pd.Timestamp(col).normalize()
            except Exception:  # noqa: BLE001
                continue
            seen[key] = col
    cols = sorted(seen.keys(), reverse=True)
    if date_from:
        cols = [c for c in cols if c.date() >= date_from]
    if date_to:
        cols = [c for c in cols if c.date() <= date_to]
    return [seen[c] for c in cols[:limit]]


def fetch_symbol(
    symbol: str,
    selection: Sequence[str],
    period_mode: str = PERIOD_AUTO,
    periods: int = 8,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    region_hint: Optional[str] = None,
    seed: Optional[dict] = None,
    retries: int = 2,
) -> List[dict]:
    """Return one record per reporting period for ``symbol``."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise FetchError("empty symbol")

    seed = seed or {}
    last_exc: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            return _fetch_once(symbol, selection, period_mode, periods,
                               date_from, date_to, region_hint, seed)
        except FetchError:
            raise
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
    raise FetchError(f"{type(last_exc).__name__}: {last_exc}")


def _fetch_once(symbol, selection, period_mode, periods, date_from, date_to,
                region_hint, seed) -> List[dict]:
    ticker = yf.Ticker(symbol)

    info: dict = {}
    if _needs_info(selection):
        try:
            info = ticker.info or {}
        except Exception as exc:  # noqa: BLE001
            log.debug("info unavailable for %s: %s", symbol, exc)
            info = {}

    wanted = _needed_statements(selection)
    frames: Dict[str, pd.DataFrame] = {}
    used_quarterly = False

    if wanted:
        # The income statement is the anchor: many non-US issuers publish a
        # quarterly balance sheet but only half-year or annual P&L. Mixing the
        # two would line up balance-sheet dates against blank revenue, so the
        # whole record set follows whichever basis the income statement has.
        anchor = next((k for k in ("income", "balance", "cashflow") if k in wanted))
        if period_mode in (PERIOD_AUTO, PERIOD_QUARTERLY):
            frames = {k: _statement(ticker, k, True) for k in wanted}
            used_quarterly = not (frames[anchor] is None or frames[anchor].empty)
        # --- the fix: an empty quarterly set falls through to annual ---
        if not used_quarterly and period_mode in (PERIOD_AUTO, PERIOD_ANNUAL):
            frames = {k: _statement(ticker, k, False) for k in wanted}
            used_quarterly = False
        if all(f is None or f.empty for f in frames.values()):
            raise FetchError("no statement data returned")

    columns = _period_columns(frames, periods, date_from, date_to) if frames else []

    # currency: statements use financialCurrency; quotes use currency
    fin_currency = info.get("financialCurrency") or seed.get("financial_currency")
    quote_currency_raw = info.get("currency") or seed.get("quote_currency")
    quote_currency, quote_divisor = markets.normalize_currency(quote_currency_raw)
    if not fin_currency:
        region = region_hint or markets.suffix_to_region(symbol)
        fin_currency = markets.BY_REGION[region].currency if region in markets.BY_REGION else quote_currency

    region = (region_hint or markets.suffix_to_region(symbol) or "us")
    market = markets.BY_REGION.get(region)

    base = {
        "symbol": symbol,
        "name": info.get("shortName") or seed.get("name") or symbol,
        "long_name": info.get("longName") or seed.get("long_name") or "",
        "region": market.name_zh if market else region,
        "exchange": info.get("fullExchangeName") or info.get("exchange") or seed.get("exchange") or "",
        "currency": fin_currency,
        "quote_currency": quote_currency,
        "snapshot_date": date.today().isoformat(),
    }
    for key in selection:
        f = F.BY_KEY.get(key)
        if f and f.source == "identity" and f.info_key:
            base[key] = _clean(info.get(f.info_key))
        elif f and f.source == "quote" and f.info_key:
            raw = _clean(info.get(f.info_key))
            if raw is None:
                # Yahoo omits .info for some exchanges (Shanghai, NSE); the
                # screener already handed us these numbers, so reuse them.
                raw = _clean(seed.get({"market_cap": "market_cap",
                                       "trailing_pe": "trailing_pe",
                                       "price": "price"}.get(key, "")))
            # Yahoo quotes GBp/ZAc/ILA prices in minor units but still reports
            # market cap in the major unit, so only the price needs scaling.
            if raw is not None and quote_divisor != 1.0 and key == "price":
                raw = raw / quote_divisor
            if key == "dividend_yield" and raw is not None and raw < 1:
                raw = raw * 100  # yfinance flips between 0.023 and 2.3 across versions
            base[key] = raw

    if not columns:
        # snapshot-only request (no statement fields selected)
        record = dict(base)
        record["report_date"] = date.today().isoformat()
        record["period_type"] = "S"
        record["fiscal_year"] = None
        _apply_computed(record, selection)
        return [_project(record, selection)]

    records: List[dict] = []
    for col in columns:
        stamp = pd.Timestamp(col)
        record = dict(base)
        record["report_date"] = stamp.strftime("%Y-%m-%d")
        record["period_type"] = "Q" if used_quarterly else "A"
        record["fiscal_year"] = str(stamp.year)

        for key in selection:
            f = F.BY_KEY.get(key)
            if not f or f.source not in {"balance", "income", "cashflow"}:
                continue
            record[key] = _row_value(frames.get(f.source), f.rows, col)

        # derive non-current buckets when the vendor omits the subtotal
        if record.get("balance_non_current_assets") is None:
            ta, ca = record.get("balance_total_assets"), record.get("balance_current_assets")
            record["balance_non_current_assets"] = (ta - ca) if ta is not None and ca is not None else None
        if record.get("balance_non_current_liabilities") is None:
            tl, cl = record.get("balance_total_liabilities"), record.get("balance_current_liabilities")
            record["balance_non_current_liabilities"] = (tl - cl) if tl is not None and cl is not None else None
        if record.get("income_gross_profit") is None:
            rev, cost = record.get("income_total_revenue"), record.get("income_cost_of_revenue")
            record["income_gross_profit"] = (rev - cost) if rev is not None and cost is not None else None
        if record.get("cashflow_free_cash_flow") is None:
            ocf, capex = record.get("cashflow_operating"), record.get("cashflow_capex")
            record["cashflow_free_cash_flow"] = (ocf + capex) if ocf is not None and capex is not None else None

        _apply_computed(record, selection)
        records.append(_project(record, selection))

    return records


def _apply_computed(record: dict, selection: Sequence[str]) -> None:
    for key in selection:
        f = F.BY_KEY.get(key)
        if f and f.source == "computed":
            try:
                record[key] = _clean(F.COMPUTATIONS[key](record))
            except Exception:  # noqa: BLE001
                record[key] = None


def _project(record: dict, selection: Sequence[str]) -> dict:
    return {k: _clean(record.get(k)) for k in selection}
