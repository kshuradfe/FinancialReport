# -*- coding: utf-8 -*-
"""FinScope API.

Run with:  python -m uvicorn backend.app.main:app --reload --port 8787
"""

from __future__ import annotations

import json
import logging
import os
import queue
import time
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import export, fields as F, jobs, markets, universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("peewee").setLevel(logging.ERROR)

app = FastAPI(title="FinScope API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------- models

class UniversePreviewRequest(BaseModel):
    regions: List[str] = Field(default_factory=lambda: ["us"])
    limit_per_market: int = 20
    offset: int = 0
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    sectors: Optional[List[str]] = None
    domestic_only: bool = True
    local_currency_only: bool = False
    sort_by: str = "market_cap"
    sort_asc: bool = False


class JobRequest(BaseModel):
    source: str = "screener"                     # screener | custom
    regions: List[str] = Field(default_factory=lambda: ["us"])
    limit_per_market: int = 50
    offset: int = 0
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    sectors: Optional[List[str]] = None
    domestic_only: bool = True
    local_currency_only: bool = False
    sort_by: str = "market_cap"
    sort_asc: bool = False
    custom_symbols: str = ""

    fields: List[str] = Field(default_factory=lambda: list(F.DEFAULT_KEYS))
    period_mode: str = "auto"                    # auto | quarterly | annual
    periods: int = 8
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    concurrency: int = 6
    request_delay: float = 0.15


# ---------------------------------------------------------------------- meta

@app.get("/api/meta")
def meta():
    return {
        "markets": markets.serialize(),
        "group_order": markets.GROUP_ORDER,
        "fields": F.serialize(),
        "sectors": universe.SECTORS,
        "sort_options": [
            {"key": "market_cap", "label_zh": "市值", "label_en": "Market cap"},
            {"key": "volume", "label_zh": "成交量", "label_en": "Volume"},
            {"key": "price", "label_zh": "股价", "label_en": "Price"},
            {"key": "pe", "label_zh": "市盈率", "label_en": "P/E"},
        ],
        "period_modes": [
            {"key": "auto", "label_zh": "自动（季报优先，回退年报）", "label_en": "Auto"},
            {"key": "quarterly", "label_zh": "仅季报", "label_en": "Quarterly only"},
            {"key": "annual", "label_zh": "仅年报", "label_en": "Annual only"},
        ],
        "max_universe": universe.MAX_UNIVERSE,
    }


@app.get("/api/search")
def search(q: str = Query(..., min_length=1), limit: int = 12):
    return {"items": universe.search_symbols(q, limit=limit)}


@app.post("/api/universe/preview")
def universe_preview(req: UniversePreviewRequest):
    regions = [r for r in req.regions if r in markets.BY_REGION] or ["us"]
    items, totals = [], {}
    for region in regions[:8]:
        result = universe.screen_region(
            region=region,
            limit=min(req.limit_per_market, 60),
            offset=req.offset,
            min_cap=req.min_market_cap,
            max_cap=req.max_market_cap,
            sectors=req.sectors,
            domestic_only=req.domestic_only,
            local_currency_only=req.local_currency_only,
            sort_by=req.sort_by,
            sort_asc=req.sort_asc,
        )
        totals[region] = result["total_available"]
        items.extend(result["items"])
    return {"items": items, "totals": totals, "count": len(items)}


# ---------------------------------------------------------------------- jobs

@app.post("/api/jobs")
def create_job(req: JobRequest):
    cfg = req.model_dump()
    if cfg["source"] == "screener":
        cfg["regions"] = [r for r in cfg["regions"] if r in markets.BY_REGION]
        if not cfg["regions"] and not cfg["custom_symbols"].strip():
            raise HTTPException(400, "请至少选择一个市场，或填写自定义股票代码")
    elif not cfg["custom_symbols"].strip():
        raise HTTPException(400, "自定义模式下请填写股票代码")
    job = jobs.start(cfg)
    return job.summary()


@app.get("/api/jobs")
def list_jobs():
    return {"items": jobs.list_jobs()}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    payload = job.summary()
    payload["columns"] = job.columns
    payload["logs"] = job.logs[-200:]
    payload["errors"] = job.errors[:200]
    return payload


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    if not jobs.cancel(job_id):
        raise HTTPException(409, "任务已结束或不存在")
    return {"ok": True}


@app.get("/api/jobs/{job_id}/rows")
def job_rows(job_id: str, offset: int = 0, limit: int = 200,
             sort: Optional[str] = None, desc: bool = True, q: Optional[str] = None):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")

    rows = job.rows
    if q:
        needle = q.strip().lower()
        rows = [r for r in rows
                if needle in str(r.get("symbol", "")).lower()
                or needle in str(r.get("name", "")).lower()]
    if sort and sort in job.columns:
        def key(row):
            value = row.get(sort)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return (0, float(value), "")
            return (1, 0.0, str(value).lower())
        present = [r for r in rows if r.get(sort) is not None]
        missing = [r for r in rows if r.get(sort) is None]
        rows = sorted(present, key=key, reverse=bool(desc)) + missing  # blanks always last

    total = len(rows)
    window = rows[offset: offset + max(1, min(limit, 1000))]
    return {"columns": job.columns, "rows": window, "total": total, "offset": offset}


@app.get("/api/jobs/{job_id}/export")
def export_job(job_id: str, format: str = "csv", lang: str = "zh"):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if format not in export.RENDERERS:
        raise HTTPException(400, "不支持的导出格式")
    if not job.rows:
        raise HTTPException(409, "该任务还没有数据")

    payload = export.RENDERERS[format](job.rows, job.columns, lang)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"finscope_{job_id}_{stamp}.{format}"
    return Response(
        content=payload,
        media_type=export.MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/jobs/{job_id}/events")
def job_events(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")

    def stream():
        q = job.subscribe()
        try:
            yield _sse("progress", job.progress_payload())
            for entry in job.logs[-40:]:
                yield _sse("log", entry)
            last_ping = time.time()
            while True:
                try:
                    message = q.get(timeout=1.0)
                except queue.Empty:
                    if job.status in jobs.TERMINAL:
                        yield _sse("done", job.summary())
                        break
                    if time.time() - last_ping > 15:
                        last_ping = time.time()
                        yield ": ping\n\n"
                    continue
                yield _sse(message["event"], message["data"])
                if message["event"] == "done":
                    break
        finally:
            job.unsubscribe(q)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.now().isoformat(timespec="seconds")}


# ------------------------------------------------------ static build (optional)

_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="app")
