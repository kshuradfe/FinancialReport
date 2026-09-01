# -*- coding: utf-8 -*-
"""Result export in the formats the old scripts produced, plus xlsx/json."""

from __future__ import annotations

import io
import json
from typing import List, Sequence

import pandas as pd

from . import fields as F


def _frame(rows: List[dict], columns: Sequence[str], lang: str) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=list(columns))
    if lang == "zh":
        df.columns = [F.BY_KEY[c].label_zh if c in F.BY_KEY else c for c in df.columns]
    elif lang == "en":
        df.columns = [F.BY_KEY[c].label_en if c in F.BY_KEY else c for c in df.columns]
    return df


def to_csv(rows: List[dict], columns: Sequence[str], lang: str = "key") -> bytes:
    # utf-8-sig keeps Excel on Windows happy with Chinese headers
    return _frame(rows, columns, lang).to_csv(index=False).encode("utf-8-sig")


def to_json(rows: List[dict], columns: Sequence[str], lang: str = "key") -> bytes:
    payload = [{k: r.get(k) for k in columns} for r in rows]
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def to_xlsx(rows: List[dict], columns: Sequence[str], lang: str = "key") -> bytes:
    buffer = io.BytesIO()
    df = _frame(rows, columns, lang)
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="financials")
        sheet = writer.sheets["financials"]
        for idx, name in enumerate(df.columns, start=1):
            width = min(max(12, len(str(name)) + 4), 40)
            sheet.column_dimensions[sheet.cell(row=1, column=idx).column_letter].width = width
        sheet.freeze_panes = "A2"
    return buffer.getvalue()


RENDERERS = {"csv": to_csv, "json": to_json, "xlsx": to_xlsx}

MEDIA_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "json": "application/json; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
