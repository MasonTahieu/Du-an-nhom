"""User-triggered ingestion. No network on import, selection or analysis."""
from copy import deepcopy
from datetime import datetime, timezone
import threading
import uuid

from .storage import Store, symbol, atomic_json
from .locking import process_lock
from . import collectors, history
from .manual import config
from .quality import readiness

def load_one(store, ticker, *, extended=False, news_only=False, progress=lambda message: None):
    ticker = symbol(ticker)
    cfg = config()
    result = {"symbol": ticker, "steps": [], "failed": [], "warnings": [], "optional_failed": []}
    def explain_error(exc):
        if isinstance(exc, KeyError):
            return ("Thiếu trường trong dữ liệu/API: " + repr(str(exc)) +
                    ". Nguồn hoặc cache đã đổi cấu trúc; dữ liệu cũ không bị xóa.")
        return f"{type(exc).__name__}: {str(exc)}"
    def step(label, action, *, scope="primary"):
        """Keep optional peer/industry/reference failures separate from the main ticker."""
        progress(label)
        try:
            value = action()
            failed = value.get("failed", []) if isinstance(value, dict) else []
            state = value.get("status", "complete") if isinstance(value, dict) else "complete"
            quality_only = (state == "partial" and isinstance(value, dict)
                            and value.get("execution_status") == "complete"
                            and value.get("quality_status") == "partial" and not failed)
            if quality_only:
                for row in value.get("results", []):
                    gaps = [f"{period}: {', '.join(keys)}"
                            for key in ("missing_statements_by_period", "missing_by_period")
                            for period, keys in row.get(key, {}).items() if keys]
                    if gaps:
                        result["warnings"].append({"step": label, "message": row.get("symbol", ticker)
                                                   + " đã lưu nguồn, nhưng chưa đầy đủ: " + "; ".join(gaps)})
            elif failed or state in {"partial", "rate_limited", "interrupted"}:
                issue = {"step": label, "scope": scope, "error": str(failed or state)[:500]}
                if scope == "primary":
                    result["failed"].append(issue)
                else:
                    result["optional_failed"].append(issue)
                    result["warnings"].append({"step": label, "message": "Nguồn bổ sung/đối chiếu chưa hoàn tất: " + issue["error"]})
            result["steps"].append({"name": label, "scope": scope, "status": "partial" if failed else state})
            return value
        except (Exception, SystemExit) as exc:
            issue = {"step": label, "scope": scope, "error": explain_error(exc)[:500]}
            if scope == "primary":
                result["failed"].append(issue)
            else:
                result["optional_failed"].append(issue)
                result["warnings"].append({"step": label, "message": "Nguồn bổ sung/đối chiếu chưa hoàn tất: " + issue["error"]})
            result["steps"].append({"name": label, "scope": scope, "status": "failed"})

    if news_only:
        from .newsfeed import collect_rss_feeds
        step("Tin RSS CafeF · tự phân loại ngành và doanh nghiệp", lambda: collect_rss_feeds(store))
        try:
            result["coverage"] = [r for r in readiness(store)["symbols"] if r["symbol"] == ticker]
        except (Exception, SystemExit) as exc:
            result["coverage"] = []
            result["failed"].append({"step":"Đọc thống kê bộ dữ liệu đã lưu", "error":explain_error(exc)[:500]})
        result["macro_count"] = len(store.read_json("macro.json", []))
        result["execution_status"] = "partial" if result["failed"] else "complete"
        result["quality_status"] = "unreviewed"
        result["status"] = result["execution_status"]
        result["note"] = "RSS chỉ có tiêu đề, tóm tắt và URL; ngành/mã được gắn theo quy tắc, chưa đối soát."
        return result

    collectors.init_profiles(store)
    catalogue = {r["symbol"]: r for r in store.read_json("universe.json", {}).get("symbols", [])}
    profiles = store.read_json("companies.json", {})
    if ticker not in profiles:
        profiles[ticker] = {"name": catalogue.get(ticker, {}).get("name", ticker),
                            "sector": "other", "peers": [],
                            "description": "Chưa xác minh phân ngành; cần bổ sung hồ sơ trước khi kết luận ngành."}
        store.write_json("companies.json", profiles, {"source": "Cấu hình và danh mục đã lưu"})
    from .peers import suggest, refresh_industry_catalog, map_sector
    # One optional industry lookup per week; never blocks the ticker's own data.
    # It is only triggered by explicit "Nạp/cập nhật mã", not by reading charts.
    if not store.read_json("industry_catalog.json", {}).get("symbols", {}).get(ticker):
        from .newsfeed import sector_for_ticker
        if sector_for_ticker(ticker, profiles[ticker]) == "other":
            step("Tra cứu phân ngành ICB (nếu nguồn hỗ trợ)", lambda: refresh_industry_catalog(store), scope="optional")
    try:
        selection = suggest(store, ticker, profiles=profiles)
    except (Exception, SystemExit) as exc:
        result["optional_failed"].append({"step": "Chọn nhóm cùng ngành", "scope": "optional", "error": explain_error(exc)[:500]})
        result["warnings"].append({"step": "Chọn nhóm cùng ngành", "message": explain_error(exc)[:500]})
        selection = {"peers": [], "candidates": [], "sector": "other", "sector_source": "Không lấy được phân ngành",
                     "note": "Đã giữ lại dữ liệu mã chính; không tự ghép nhóm ngành khi lỗi."}
    wanted = list(dict.fromkeys([ticker] + selection["peers"]))
    result["peer_selection"] = selection
    for t in wanted:
        def annual_step(label, action, *, scope="primary", t=t):
            return step(label, action, scope=scope if t == ticker else "optional")
        collectors.fetch_annual_for_symbol(store, t, cfg, step=annual_step, progress=progress)

    prices = store.read("prices.parquet")
    for t in [ticker, cfg.get("benchmark", "VNINDEX")]:
        exists = not prices.empty and bool((prices.symbol == t).any())
        step("Giá " + t, lambda t=t, exists=exists: history.prepare_history(
            store, [t], start=None if exists else cfg["history_start"], delay=7.0, progress=progress),
            scope="primary" if t == ticker else "optional")
    if extended:
        step("BCTC quý " + ticker, lambda: collectors.fetch_quarters(store, [ticker]))
        # Reuse bounded manual context pipeline; outer ingestion lock is already held.
        from .manual import _run
        step("Vĩ mô và tin " + ticker, lambda: _run("context", [ticker], include_rss=False), scope="optional")
        from .newsfeed import collect_rss_feeds
        step("Tin RSS CafeF · ngành và cổ phiếu", lambda: collect_rss_feeds(store), scope="optional")
    try:
        coverage = readiness(store)
        result["coverage"] = [r for r in coverage["symbols"] if r["symbol"] in wanted]
        result["macro_count"] = coverage["macro_count"]
        primary = next((r for r in result["coverage"] if r["symbol"] == ticker), {})
        annual_missing = primary.get("annual_missing_fields", {})
        q_missing = primary.get("quarter_missing_fields", {})
        q_reports = primary.get("quarter_missing_statements", {})
        years = primary.get("annual_periods", [])
        quarters = primary.get("quarter_periods", [])
        quality_gaps = []
        for year in years:
            if annual_missing.get(year):
                quality_gaps.append("BCTC năm " + str(year) + ": " + ", ".join(annual_missing[year]))
        if extended:
            for period in quarters:
                if q_missing.get(period) or q_reports.get(period):
                    quality_gaps.append("BCTC quý " + str(period) + ": " +
                                        ", ".join(q_reports.get(period, []) + q_missing.get(period, [])))
        if quality_gaps:
            result["warnings"].append({"step": "Kiểm tra chỉ tiêu mã chính",
                                       "message": "; ".join(quality_gaps[:8]) +
                                       (f"; và {len(quality_gaps)-8} kỳ khác" if len(quality_gaps) > 8 else "")})
        result["quality_status"] = "partial" if quality_gaps else "complete"
    except (Exception, SystemExit) as exc:
        # A read-only coverage/SDK schema exception should not turn an otherwise
        # successful import into the unhelpful job-level 'missing-fields'.
        result["coverage"] = []
        result["macro_count"] = len(store.read_json("macro.json", []))
        result["optional_failed"].append({"step":"Đọc thống kê bộ dữ liệu đã lưu", "error":explain_error(exc)[:500]})
        result["warnings"].append({"step":"Đọc thống kê bộ dữ liệu đã lưu", "message":explain_error(exc)[:500]})
        result["quality_status"] = "unverified"
    result["execution_status"] = "partial" if result["failed"] else "complete"
    result["status"] = "partial" if result["failed"] or result.get("quality_status") == "partial" else "complete"
    result["note"] = "Đã đề xuất "+str(len(selection["peers"]))+" mã cùng ngành. "+selection["note"]+" Hoàn tất nạp không có nghĩa dữ liệu đã được đối soát."
    return result

class LoadJobs:
    def __init__(self, store_factory=lambda: Store("local"), runner=load_one):
        self.store_factory, self.runner = store_factory, runner
        self.lock = threading.Lock()
        self.job = None

    def current(self):
        with self.lock:
            return deepcopy(self.job)

    def start(self, ticker, extended=False, news_only=False):
        ticker = symbol(ticker)
        if len(ticker) != 3:
            raise ValueError("Nhập mã cổ phiếu gồm 3 ký tự.")
        with self.lock:
            if self.job and self.job["status"] == "running":
                raise RuntimeError("Đang nạp một mã. Chờ hoàn tất trước khi nạp mã tiếp theo.")
            self.job = {"id": uuid.uuid4().hex, "symbol": ticker, "status": "running",
                        "message": "Đang chuẩn bị", "started_at": datetime.now(timezone.utc).isoformat()}
            initial = deepcopy(self.job)
        threading.Thread(target=self._work, args=(ticker, extended, news_only), daemon=True).start()
        return initial

    def _work(self, ticker, extended, news_only=False):
        def progress(message):
            with self.lock:
                self.job["message"] = str(message)
        try:
            store = self.store_factory()
            with process_lock(store.path / ".ingestion.lock"):
                kwargs = {"extended": extended, "progress": progress}
                if news_only:
                    kwargs["news_only"] = True
                result = self.runner(store, ticker, **kwargs)
            with self.lock:
                self.job.update(status=result["status"], result=result, message="Đã kết thúc lượt nạp")
        except (Exception, SystemExit) as exc:
            with self.lock:
                self.job.update(status="failed", message=("Lỗi "+type(exc).__name__+": "+str(exc))[:500])
        finally:
            # Keep one result per job instead of overwriting financial-run.json.
            # Diagnostic logging must never turn a successful import into failed.
            try:
                with self.lock:
                    snapshot = deepcopy(self.job)
                store = locals().get("store")
                if store is not None:
                    path = store.path / "logs" / "ingestion" / ticker / (snapshot["id"] + ".json")
                    atomic_json(path, snapshot)
            except (OSError, ValueError, TypeError, KeyError):
                pass
