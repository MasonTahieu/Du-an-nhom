"""User-triggered ingestion. No network on import, selection or analysis."""
from copy import deepcopy
from datetime import datetime, timezone
import threading
import uuid

from .storage import Store, symbol
from .locking import process_lock
from . import collectors, history
from .manual import config
from .quality import readiness

def load_one(store, ticker, *, extended=False, news_only=False, progress=lambda message: None):
    ticker = symbol(ticker)
    cfg = config()
    result = {"symbol": ticker, "steps": [], "failed": []}
    def step(label, action):
        progress(label)
        try:
            value = action()
            failed = value.get("failed", []) if isinstance(value, dict) else []
            state = value.get("status", "complete") if isinstance(value, dict) else "complete"
            if failed or state in {"partial", "rate_limited", "interrupted"}:
                result["failed"].append({"step": label, "error": str(failed or state)[:500]})
            result["steps"].append({"name": label, "status": "partial" if failed else state})
        except (Exception, SystemExit) as exc:
            result["failed"].append({"step": label, "error": str(exc)[:500]})
            result["steps"].append({"name": label, "status": "failed"})

    if news_only:
        from .newsfeed import collect_rss_feeds
        step("Tin RSS CafeF · tự phân loại ngành và doanh nghiệp", lambda: collect_rss_feeds(store))
        result["coverage"] = [r for r in readiness(store)["symbols"] if r["symbol"] == ticker]
        result["macro_count"] = len(store.read_json("macro.json", []))
        result["status"] = "partial" if result["failed"] else "complete"
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
            step("Tra cứu phân ngành ICB (nếu nguồn hỗ trợ)", lambda: refresh_industry_catalog(store))
    selection = suggest(store, ticker, profiles=profiles)
    wanted = list(dict.fromkeys([ticker] + selection["peers"]))
    result["peer_selection"] = selection
    for t in wanted:
        exchange = catalogue.get(t, {}).get("exchange")
        exchanges = {"HOSE": ["HSX"], "HSX": ["HSX"], "HNX": ["HNX"], "UPCOM": []}.get(exchange, ["HSX", "HNX"])
        if not exchanges:
            result["failed"].append({"step": "BCTC năm " + t, "error": "Nguồn năm chưa hỗ trợ UPCoM."})
            continue
        def annual(t=t, exchanges=exchanges):
            errors = []
            for ex in exchanges:
                try:
                    return collectors.fetch_annual_reference(store, [t], cfg["reference_commit"],
                                                              ex, cfg["first_year"])
                except ValueError as exc:
                    errors.append(str(exc))
            raise ValueError("; ".join(errors))
        step("BCTC năm " + t + " · dùng cache nếu có", annual)
        from .financials import repair_annual_sources
        step("Kiểm tra / bổ sung BCTC năm " + t,
             lambda t=t: repair_annual_sources(store, [t], first_year=cfg["first_year"], progress=progress))

    prices = store.read("prices.parquet")
    for t in [ticker, cfg.get("benchmark", "VNINDEX")]:
        exists = not prices.empty and bool((prices.symbol == t).any())
        step("Giá " + t, lambda t=t, exists=exists: history.prepare_history(
            store, [t], start=None if exists else cfg["history_start"], delay=7.0, progress=progress))
    if extended:
        step("BCTC quý " + ticker, lambda: collectors.fetch_quarters(store, [ticker]))
        # Reuse bounded manual context pipeline; outer ingestion lock is already held.
        from .manual import _run
        step("Vĩ mô và tin " + ticker, lambda: _run("context", [ticker], include_rss=False))
        from .newsfeed import collect_rss_feeds
        step("Tin RSS CafeF · ngành và cổ phiếu", lambda: collect_rss_feeds(store))
    coverage = readiness(store)
    result["coverage"] = [r for r in coverage["symbols"] if r["symbol"] in wanted]
    result["macro_count"] = coverage["macro_count"]
    result["status"] = "partial" if result["failed"] else "complete"
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
                self.job.update(status="failed", message=str(exc)[:500])
