# -*- coding: utf-8 -*-
"""In-process job runner.

A collection run is long (minutes for hundreds of tickers), so the API starts
it in a worker thread and the UI follows along over Server-Sent Events.
Everything lives in memory -- this is a single-user desktop-style tool.
"""

from __future__ import annotations

import itertools
import logging
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from . import fetcher, fields as F, universe

log = logging.getLogger(__name__)

MAX_JOBS_RETAINED = 20

STATUS_QUEUED = "queued"
STATUS_DISCOVERING = "discovering"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"
STATUS_ERROR = "error"
TERMINAL = {STATUS_DONE, STATUS_CANCELLED, STATUS_ERROR}


@dataclass
class Job:
    id: str
    config: dict
    status: str = STATUS_QUEUED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    finished_at: Optional[str] = None
    total: int = 0
    completed: int = 0
    succeeded: int = 0
    failed: int = 0
    rows: List[dict] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)
    logs: List[dict] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    message: str = ""
    _cancel: threading.Event = field(default_factory=threading.Event, repr=False)
    _subscribers: List["queue.Queue"] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ------------------------------------------------------------- events
    def subscribe(self) -> "queue.Queue":
        q: queue.Queue = queue.Queue(maxsize=1000)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: "queue.Queue") -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def emit(self, event: str, payload: dict) -> None:
        message = {"event": event, "data": payload}
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(message)
            except queue.Full:
                pass

    def log_line(self, level: str, text: str) -> None:
        entry = {"t": datetime.now().strftime("%H:%M:%S"), "level": level, "text": text}
        self.logs.append(entry)
        if len(self.logs) > 800:
            del self.logs[:200]
        self.emit("log", entry)

    def progress_payload(self) -> dict:
        return {
            "status": self.status,
            "total": self.total,
            "completed": self.completed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "rows": len(self.rows),
            "message": self.message,
        }

    def summary(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "total": self.total,
            "completed": self.completed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "row_count": len(self.rows),
            "message": self.message,
            "config": self.config,
        }


_jobs: Dict[str, Job] = {}
_jobs_lock = threading.Lock()


def get(job_id: str) -> Optional[Job]:
    with _jobs_lock:
        return _jobs.get(job_id)


def list_jobs() -> List[dict]:
    with _jobs_lock:
        return [j.summary() for j in sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)]


def _register(job: Job) -> None:
    with _jobs_lock:
        _jobs[job.id] = job
        if len(_jobs) > MAX_JOBS_RETAINED:
            stale = sorted(_jobs.values(), key=lambda j: j.created_at)
            for old in stale[: len(_jobs) - MAX_JOBS_RETAINED]:
                if old.status in TERMINAL:
                    _jobs.pop(old.id, None)


def cancel(job_id: str) -> bool:
    job = get(job_id)
    if not job or job.status in TERMINAL:
        return False
    job._cancel.set()
    job.message = "已取消"
    return True


# ------------------------------------------------------------------- runner

def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def start(config: dict) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], config=config)
    job.columns = F.expand_selection(config.get("fields") or F.DEFAULT_KEYS)
    _register(job)
    threading.Thread(target=_run, args=(job,), daemon=True, name=f"job-{job.id}").start()
    return job


def _discover(job: Job) -> List[dict]:
    cfg = job.config
    source = cfg.get("source", "screener")
    items: List[dict] = []

    if source == "custom":
        items = universe.parse_custom(cfg.get("custom_symbols", ""))
        job.log_line("info", f"自定义清单：{len(items)} 个代码")
        return items

    regions = cfg.get("regions") or ["us"]
    per_market = int(cfg.get("limit_per_market", 50))
    offset = int(cfg.get("offset", 0))
    for region in regions:
        if job._cancel.is_set():
            break
        job.message = f"正在检索 {region.upper()} 市场成分股…"
        job.emit("progress", job.progress_payload())
        result = universe.screen_region(
            region=region,
            limit=per_market,
            offset=offset,
            min_cap=cfg.get("min_market_cap"),
            max_cap=cfg.get("max_market_cap"),
            sectors=cfg.get("sectors"),
            domestic_only=bool(cfg.get("domestic_only", True)),
            local_currency_only=bool(cfg.get("local_currency_only", False)),
            sort_by=cfg.get("sort_by", "market_cap"),
            sort_asc=bool(cfg.get("sort_asc", False)),
        )
        found = result["items"]
        items.extend(found)
        job.log_line(
            "info" if found else "warn",
            f"{region.upper()}：命中 {len(found)} 只（该市场共约 {result['total_available']} 只）",
        )

    extra = universe.parse_custom(cfg.get("custom_symbols", ""))
    if extra:
        known = {i["symbol"] for i in items}
        items.extend([e for e in extra if e["symbol"] not in known])
        job.log_line("info", f"追加自定义代码 {len(extra)} 个")

    # de-duplicate, preserve order
    seen, unique = set(), []
    for item in items:
        if item["symbol"] and item["symbol"] not in seen:
            seen.add(item["symbol"])
            unique.append(item)
    return unique


def _run(job: Job) -> None:
    cfg = job.config
    try:
        job.status = STATUS_DISCOVERING
        job.message = "正在构建股票池…"
        job.emit("progress", job.progress_payload())

        candidates = _discover(job)
        if job._cancel.is_set():
            return _finish(job, STATUS_CANCELLED)
        if not candidates:
            job.message = "没有匹配的股票，请放宽筛选条件"
            job.log_line("error", job.message)
            return _finish(job, STATUS_ERROR)

        job.total = len(candidates)
        job.status = STATUS_RUNNING
        job.message = f"开始抓取 {job.total} 只股票的财务数据"
        job.log_line("info", job.message)
        job.emit("universe", {"items": candidates[:2000], "count": len(candidates)})
        job.emit("progress", job.progress_payload())

        selection = job.columns
        period_mode = cfg.get("period_mode", fetcher.PERIOD_AUTO)
        periods = max(1, min(int(cfg.get("periods", 8)), 24))
        date_from = _parse_date(cfg.get("date_from"))
        date_to = _parse_date(cfg.get("date_to"))
        delay = float(cfg.get("request_delay", 0.15))
        workers = max(1, min(int(cfg.get("concurrency", 6)), 16))

        counter = itertools.count(1)

        def work(item: dict) -> None:
            if job._cancel.is_set():
                return
            symbol = item["symbol"]
            try:
                rows = fetcher.fetch_symbol(
                    symbol,
                    selection=selection,
                    period_mode=period_mode,
                    periods=periods,
                    date_from=date_from,
                    date_to=date_to,
                    region_hint=item.get("region"),
                    seed=item,
                )
            except Exception as exc:  # noqa: BLE001
                job.failed += 1
                job.errors.append({"symbol": symbol, "reason": str(exc)[:200]})
                job.log_line("warn", f"{symbol} 失败：{str(exc)[:90]}")
            else:
                job.succeeded += 1
                job.rows.extend(rows)
                ptype = rows[0].get("period_type") if rows else "?"
                job.log_line("ok", f"{symbol} 获取 {len(rows)} 期（{ptype}）")
            finally:
                job.completed = next(counter)
                if job.completed % 2 == 0 or job.completed == job.total:
                    job.message = f"{job.completed}/{job.total}"
                    job.emit("progress", job.progress_payload())
                if delay:
                    time.sleep(delay)

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"fetch-{job.id}") as pool:
            list(pool.map(work, candidates))

        if job._cancel.is_set():
            return _finish(job, STATUS_CANCELLED)

        job.message = f"完成：成功 {job.succeeded}，失败 {job.failed}，共 {len(job.rows)} 行"
        job.log_line("ok", job.message)
        _finish(job, STATUS_DONE)

    except Exception as exc:  # noqa: BLE001
        log.exception("job %s crashed", job.id)
        job.message = f"任务异常：{exc}"
        job.log_line("error", job.message)
        _finish(job, STATUS_ERROR)


def _finish(job: Job, status: str) -> None:
    job.status = status
    job.finished_at = datetime.now().isoformat(timespec="seconds")
    if status == STATUS_CANCELLED and not job.message:
        job.message = "已取消"
    job.emit("progress", job.progress_payload())
    job.emit("done", job.summary())
