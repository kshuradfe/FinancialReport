# -*- coding: utf-8 -*-
"""Field catalog.

Every column the app can produce is declared here once, so the API, the CSV
exporter and the UI's field picker all stay in sync.

`rows` lists the yfinance statement row labels to try, in order -- yfinance's
normalised labels drift between company filings, so aliases matter.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field as dc_field
from typing import Callable, Dict, List, Optional


# format hints consumed by the frontend table renderer
FMT_TEXT = "text"
FMT_MONEY = "money"      # value in the statement currency
FMT_NUMBER = "number"
FMT_PERCENT = "percent"  # already expressed 0-100
FMT_RATIO = "ratio"      # e.g. 1.35x


@dataclass(frozen=True)
class Field:
    key: str
    label_zh: str
    label_en: str
    group: str
    source: str                       # identity | quote | balance | income | cashflow | computed
    fmt: str = FMT_MONEY
    rows: tuple = ()                  # yfinance statement row aliases
    info_key: str = ""                # yfinance .info key
    default: bool = True              # selected out of the box
    note_zh: str = ""


GROUPS = [
    {"key": "identity", "label_zh": "标识信息", "label_en": "Identity"},
    {"key": "quote", "label_zh": "估值快照", "label_en": "Valuation snapshot"},
    {"key": "balance", "label_zh": "资产负债表", "label_en": "Balance sheet"},
    {"key": "income", "label_zh": "利润表", "label_en": "Income statement"},
    {"key": "cashflow", "label_zh": "现金流量表", "label_en": "Cash flow"},
    {"key": "computed", "label_zh": "衍生指标", "label_en": "Derived metrics"},
]

F = Field

FIELDS: List[Field] = [
    # ------------------------- identity -------------------------
    F("symbol", "代码", "Symbol", "identity", "identity", FMT_TEXT),
    F("name", "名称", "Name", "identity", "identity", FMT_TEXT),
    F("long_name", "公司全称", "Full name", "identity", "identity", FMT_TEXT, info_key="longName", default=False),
    F("region", "市场", "Market", "identity", "identity", FMT_TEXT),
    F("exchange", "交易所", "Exchange", "identity", "identity", FMT_TEXT),
    F("country", "注册国", "Country", "identity", "identity", FMT_TEXT, info_key="country", default=False),
    F("sector", "板块", "Sector", "identity", "identity", FMT_TEXT, info_key="sector"),
    F("industry", "行业", "Industry", "identity", "identity", FMT_TEXT, info_key="industry", default=False),
    F("currency", "报表货币", "Statement currency", "identity", "identity", FMT_TEXT),
    F("report_date", "报告期", "Report date", "identity", "identity", FMT_TEXT),
    F("period_type", "报告类型", "Period type", "identity", "identity", FMT_TEXT),
    F("fiscal_year", "财年", "Fiscal year", "identity", "identity", FMT_TEXT, default=False),
    F("employees", "员工数", "Employees", "identity", "identity", FMT_NUMBER, info_key="fullTimeEmployees", default=False),
    F("website", "官网", "Website", "identity", "identity", FMT_TEXT, info_key="website", default=False),

    # ------------------------- quote / valuation -------------------------
    F("price", "现价", "Price", "quote", "quote", FMT_NUMBER, info_key="currentPrice", default=False),
    F("market_cap", "市值", "Market cap", "quote", "quote", FMT_MONEY, info_key="marketCap"),
    F("enterprise_value", "企业价值", "Enterprise value", "quote", "quote", FMT_MONEY, info_key="enterpriseValue", default=False),
    F("trailing_pe", "市盈率TTM", "Trailing P/E", "quote", "quote", FMT_RATIO, info_key="trailingPE"),
    F("forward_pe", "预期市盈率", "Forward P/E", "quote", "quote", FMT_RATIO, info_key="forwardPE", default=False),
    F("price_to_book", "市净率", "P/B", "quote", "quote", FMT_RATIO, info_key="priceToBook"),
    F("price_to_sales", "市销率", "P/S", "quote", "quote", FMT_RATIO, info_key="priceToSalesTrailing12Months", default=False),
    F("ev_to_ebitda", "EV/EBITDA", "EV/EBITDA", "quote", "quote", FMT_RATIO, info_key="enterpriseToEbitda", default=False),
    F("ev_to_revenue", "EV/营收", "EV/Revenue", "quote", "quote", FMT_RATIO, info_key="enterpriseToRevenue", default=False),
    F("dividend_yield", "股息率", "Dividend yield", "quote", "quote", FMT_PERCENT, info_key="dividendYield", default=False),
    F("beta", "Beta", "Beta", "quote", "quote", FMT_RATIO, info_key="beta", default=False),
    F("shares_outstanding", "总股本", "Shares outstanding", "quote", "quote", FMT_NUMBER, info_key="sharesOutstanding", default=False),
    F("quote_currency", "行情货币", "Quote currency", "quote", "quote", FMT_TEXT, default=False),
    F("snapshot_date", "快照日期", "Snapshot date", "quote", "quote", FMT_TEXT, default=False),

    # ------------------------- balance sheet -------------------------
    F("balance_cash", "现金及等价物", "Cash & equivalents", "balance", "balance", rows=(
        "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash Financial")),
    F("balance_short_term_investments", "短期投资", "Short-term investments", "balance", "balance", default=False, rows=(
        "Other Short Term Investments", "Available For Sale Securities")),
    F("balance_receivables", "应收账款", "Receivables", "balance", "balance", default=False, rows=(
        "Accounts Receivable", "Receivables", "Gross Accounts Receivable")),
    F("balance_inventory", "存货", "Inventory", "balance", "balance", default=False, rows=("Inventory",)),
    F("balance_current_assets", "流动资产", "Current assets", "balance", "balance", rows=("Current Assets",)),
    F("balance_non_current_assets", "非流动资产", "Non-current assets", "balance", "balance", rows=(
        "Total Non Current Assets",)),
    F("balance_total_assets", "总资产", "Total assets", "balance", "balance", rows=("Total Assets",)),
    F("balance_goodwill", "商誉", "Goodwill", "balance", "balance", default=False, rows=("Goodwill",)),
    F("balance_intangibles", "无形资产", "Intangible assets", "balance", "balance", default=False, rows=(
        "Goodwill And Other Intangible Assets", "Other Intangible Assets")),
    F("balance_current_liabilities", "流动负债", "Current liabilities", "balance", "balance", rows=("Current Liabilities",)),
    F("balance_non_current_liabilities", "非流动负债", "Non-current liabilities", "balance", "balance", rows=(
        "Total Non Current Liabilities Net Minority Interest",)),
    F("balance_total_liabilities", "总负债", "Total liabilities", "balance", "balance", rows=(
        "Total Liabilities Net Minority Interest",)),
    F("balance_total_debt", "有息负债", "Total debt", "balance", "balance", default=False, rows=("Total Debt", "Net Debt")),
    F("balance_equity", "股东权益", "Shareholders' equity", "balance", "balance", rows=(
        "Stockholders Equity", "Total Equity Gross Minority Interest")),
    F("balance_retained_earnings", "留存收益", "Retained earnings", "balance", "balance", default=False, rows=(
        "Retained Earnings",)),
    F("balance_working_capital", "营运资本", "Working capital", "balance", "balance", default=False, rows=("Working Capital",)),

    # ------------------------- income statement -------------------------
    F("income_total_revenue", "营业收入", "Total revenue", "income", "income", rows=("Total Revenue", "Operating Revenue")),
    F("income_cost_of_revenue", "营业成本", "Cost of revenue", "income", "income", rows=("Cost Of Revenue",)),
    F("income_gross_profit", "毛利润", "Gross profit", "income", "income", rows=("Gross Profit",)),
    F("income_rd_expense", "研发费用", "R&D expense", "income", "income", rows=(
        "Research And Development", "Research & Development")),
    F("income_sga_expense", "销售管理费用", "SG&A expense", "income", "income", default=False, rows=(
        "Selling General And Administration", "Selling General And Administrative")),
    F("income_operating_expense", "营业费用", "Operating expense", "income", "income", default=False, rows=("Operating Expense",)),
    F("income_operating_income", "营业利润", "Operating income", "income", "income", rows=("Operating Income", "Total Operating Income As Reported")),
    F("income_ebitda", "EBITDA", "EBITDA", "income", "income", default=False, rows=("EBITDA", "Normalized EBITDA")),
    F("income_ebit", "EBIT", "EBIT", "income", "income", default=False, rows=("EBIT",)),
    F("income_interest_expense", "利息支出", "Interest expense", "income", "income", default=False, rows=(
        "Interest Expense", "Net Interest Income")),
    F("income_pretax_income", "税前利润", "Pretax income", "income", "income", rows=("Pretax Income",)),
    F("income_tax_provision", "所得税", "Tax provision", "income", "income", rows=("Tax Provision",)),
    F("income_net_income", "净利润", "Net income", "income", "income", rows=(
        "Net Income", "Net Income Common Stockholders", "Net Income From Continuing Operation Net Minority Interest")),
    F("income_diluted_eps", "摊薄EPS", "Diluted EPS", "income", "income", FMT_NUMBER, default=False, rows=("Diluted EPS",)),
    F("income_basic_eps", "基本EPS", "Basic EPS", "income", "income", FMT_NUMBER, default=False, rows=("Basic EPS",)),

    # ------------------------- cash flow -------------------------
    F("cashflow_operating", "经营现金流", "Operating cash flow", "cashflow", "cashflow", rows=(
        "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")),
    F("cashflow_investing", "投资现金流", "Investing cash flow", "cashflow", "cashflow", rows=(
        "Investing Cash Flow", "Cash Flow From Continuing Investing Activities")),
    F("cashflow_financing", "筹资现金流", "Financing cash flow", "cashflow", "cashflow", rows=(
        "Financing Cash Flow", "Cash Flow From Continuing Financing Activities")),
    F("cashflow_capex", "资本开支", "Capital expenditure", "cashflow", "cashflow", rows=("Capital Expenditure",)),
    F("cashflow_free_cash_flow", "自由现金流", "Free cash flow", "cashflow", "cashflow", rows=("Free Cash Flow",)),
    F("cashflow_depreciation", "折旧摊销", "D&A", "cashflow", "cashflow", default=False, rows=(
        "Depreciation And Amortization", "Depreciation Amortization Depletion")),
    F("cashflow_stock_comp", "股权激励", "Stock compensation", "cashflow", "cashflow", default=False, rows=(
        "Stock Based Compensation",)),
    F("cashflow_dividends_paid", "分红支出", "Dividends paid", "cashflow", "cashflow", default=False, rows=(
        "Cash Dividends Paid", "Common Stock Dividend Paid")),
    F("cashflow_buyback", "回购支出", "Share buyback", "cashflow", "cashflow", default=False, rows=(
        "Repurchase Of Capital Stock",)),
    F("cashflow_net_change", "现金净变动", "Net change in cash", "cashflow", "cashflow", default=False, rows=(
        "Changes In Cash", "End Cash Position")),

    # ------------------------- computed -------------------------
    F("gross_margin", "毛利率", "Gross margin", "computed", "computed", FMT_PERCENT),
    F("operating_margin", "营业利润率", "Operating margin", "computed", "computed", FMT_PERCENT),
    F("net_margin", "净利率", "Net margin", "computed", "computed", FMT_PERCENT),
    F("rd_ratio", "研发费用率", "R&D intensity", "computed", "computed", FMT_PERCENT),
    F("fcf_margin", "自由现金流率", "FCF margin", "computed", "computed", FMT_PERCENT, default=False),
    F("effective_tax_rate", "实际税率", "Effective tax rate", "computed", "computed", FMT_PERCENT, default=False),
    F("asset_turnover", "资产周转率", "Asset turnover", "computed", "computed", FMT_RATIO),
    F("current_ratio", "流动比率", "Current ratio", "computed", "computed", FMT_RATIO, default=False),
    F("quick_ratio", "速动比率", "Quick ratio", "computed", "computed", FMT_RATIO, default=False),
    F("debt_to_equity", "资产负债率", "Liabilities / equity", "computed", "computed", FMT_RATIO, default=False),
    F("roa", "总资产回报率", "ROA", "computed", "computed", FMT_PERCENT, default=False),
    F("roe", "净资产收益率", "ROE", "computed", "computed", FMT_PERCENT, default=False),
]

BY_KEY: Dict[str, Field] = {f.key: f for f in FIELDS}

# always emitted, regardless of user selection -- without these a row is meaningless
MANDATORY = ["symbol", "name", "region", "report_date", "period_type", "currency"]

DEFAULT_KEYS = [f.key for f in FIELDS if f.default]


def serialize() -> dict:
    return {
        "groups": GROUPS,
        "fields": [
            {
                "key": f.key,
                "label_zh": f.label_zh,
                "label_en": f.label_en,
                "group": f.group,
                "source": f.source,
                "fmt": f.fmt,
                "default": f.default,
                "mandatory": f.key in MANDATORY,
            }
            for f in FIELDS
        ],
        "mandatory": MANDATORY,
    }


# ---------------------------------------------------------------- computations

def _div(a, b, scale=1.0):
    try:
        if a is None or b in (None, 0):
            return None
        return (float(a) / float(b)) * scale
    except (TypeError, ValueError, ZeroDivisionError):
        return None


COMPUTATIONS: Dict[str, Callable[[dict], Optional[float]]] = {
    "gross_margin": lambda r: (
        _div(r.get("income_gross_profit"), r.get("income_total_revenue"), 100)
        if r.get("income_gross_profit") is not None
        else _div(
            (r["income_total_revenue"] - r["income_cost_of_revenue"])
            if r.get("income_total_revenue") is not None and r.get("income_cost_of_revenue") is not None
            else None,
            r.get("income_total_revenue"), 100)
    ),
    "operating_margin": lambda r: _div(r.get("income_operating_income"), r.get("income_total_revenue"), 100),
    "net_margin": lambda r: _div(r.get("income_net_income"), r.get("income_total_revenue"), 100),
    "rd_ratio": lambda r: _div(r.get("income_rd_expense"), r.get("income_total_revenue"), 100),
    "fcf_margin": lambda r: _div(r.get("cashflow_free_cash_flow"), r.get("income_total_revenue"), 100),
    "effective_tax_rate": lambda r: _div(r.get("income_tax_provision"), r.get("income_pretax_income"), 100),
    "asset_turnover": lambda r: _div(r.get("income_total_revenue"), r.get("balance_total_assets")),
    "current_ratio": lambda r: _div(r.get("balance_current_assets"), r.get("balance_current_liabilities")),
    "quick_ratio": lambda r: _div(
        (r["balance_current_assets"] - r["balance_inventory"])
        if r.get("balance_current_assets") is not None and r.get("balance_inventory") is not None
        else None,
        r.get("balance_current_liabilities")),
    "debt_to_equity": lambda r: _div(r.get("balance_total_liabilities"), r.get("balance_equity")),
    "roa": lambda r: _div(r.get("income_net_income"), r.get("balance_total_assets"), 100),
    "roe": lambda r: _div(r.get("income_net_income"), r.get("balance_equity"), 100),
}

# computed metrics that need extra raw fields fetched even if the user hid them
COMPUTE_DEPENDENCIES: Dict[str, List[str]] = {
    "gross_margin": ["income_gross_profit", "income_total_revenue", "income_cost_of_revenue"],
    "operating_margin": ["income_operating_income", "income_total_revenue"],
    "net_margin": ["income_net_income", "income_total_revenue"],
    "rd_ratio": ["income_rd_expense", "income_total_revenue"],
    "fcf_margin": ["cashflow_free_cash_flow", "income_total_revenue"],
    "effective_tax_rate": ["income_tax_provision", "income_pretax_income"],
    "asset_turnover": ["income_total_revenue", "balance_total_assets"],
    "current_ratio": ["balance_current_assets", "balance_current_liabilities"],
    "quick_ratio": ["balance_current_assets", "balance_inventory", "balance_current_liabilities"],
    "debt_to_equity": ["balance_total_liabilities", "balance_equity"],
    "roa": ["income_net_income", "balance_total_assets"],
    "roe": ["income_net_income", "balance_equity"],
}


def expand_selection(keys: List[str]) -> List[str]:
    """Add mandatory columns and hidden dependencies of computed metrics."""
    out = list(dict.fromkeys(MANDATORY + [k for k in keys if k in BY_KEY]))
    for k in list(out):
        for dep in COMPUTE_DEPENDENCIES.get(k, []):
            if dep not in out:
                out.append(dep)
    return out
