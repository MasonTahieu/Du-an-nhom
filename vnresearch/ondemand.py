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

def load_one(store, ticker, *, extended=False, progress=lambda message: None):
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

    collectors.init_profiles(store)
    catalogue = {r["symbol"]: r for r in store.read_json("universe.json", {}).get("symbols", [])}
    profiles = store.read_json("companies.json", {})
    if ticker not in profiles:
        profiles[ticker] = {"name": catalogue.get(ticker, {}).get("name", ticker),
                            "sector": "other", "peers": [],
                            "description": "Chưa xác minh phân ngành; cần bổ sung hồ sơ trước khi kết luận ngành."}
        store.write_json("companies.json", profiles, {"source": "Cấu hình và danh mục đã lưu"})
    wanted = list(dict.fromkeys([ticker] + profiles[ticker].get("peers", [])))
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

    prices = store.read("prices.parquet")
    for t in [ticker, cfg.get("benchmark", "VNINDEX")]:
        exists = not prices.empty and bool((prices.symbol == t).any())
        step("Giá " + t, lambda t=t, exists=exists: history.prepare_history(
            store, [t], start=None if exists else cfg["history_start"], delay=7.0, progress=progress))
    if extended:
        step("BCTC quý " + ticker, lambda: collectors.fetch_quarters(store, [ticker]))
        # Reuse bounded manual context pipeline; outer ingestion lock is already held.
        from .manual import _run
        step("Vĩ mô và tin " + ticker, lambda: _run("context", [ticker]))
    coverage = readiness(store)
    result["coverage"] = [r for r in coverage["symbols"] if r["symbol"] in wanted]
    result["macro_count"] = coverage["macro_count"]
    result["status"] = "partial" if result["failed"] else "complete"
    result["note"] = "Hoàn tất các bước đã chọn không có nghĩa báo cáo đã đủ dữ liệu hoặc được đối soát. Xem kỳ, nguồn và phần thiếu."
    return result

class LoadJobs:
    def __init__(self, store_factory=lambda: Store("local"), runner=load_one):
        self.store_factory, self.runner = store_factory, runner
        self.lock = threading.Lock()
        self.job = None

    def current(self):
        with self.lock:
            return deepcopy(self.job)

    def start(self, ticker, extended=False):
        ticker = symbol(ticker)
        if len(ticker) != 3:
            raise ValueError("Nhập mã cổ phiếu gồm 3 ký tự.")
        with self.lock:
            if self.job and self.job["status"] == "running":
                raise RuntimeError("Đang nạp một mã. Chờ hoàn tất trước khi nạp mã tiếp theo.")
            self.job = {"id": uuid.uuid4().hex, "symbol": ticker, "status": "running",
                        "message": "Đang chuẩn bị", "started_at": datetime.now(timezone.utc).isoformat()}
            initial = deepcopy(self.job)
        threading.Thread(target=self._work, args=(ticker, extended), daemon=True).start()
        return initial

    def _work(self, ticker, extended):
        def progress(message):
            with self.lock:
                self.job["message"] = str(message)
        try:
            store = self.store_factory()
            with process_lock(store.path / ".ingestion.lock"):
                result = self.runner(store, ticker, extended=extended, progress=progress)
            with self.lock:
                self.job.update(status=result["status"], result=result, message="Đã kết thúc lượt nạp")
        except (Exception, SystemExit) as exc:
            with self.lock:
                self.job.update(status="failed", message=str(exc)[:500])
