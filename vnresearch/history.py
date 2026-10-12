"""Manual, resumable daily history collection; Parquet is the local data store."""
from datetime import date, datetime, timedelta, timezone
import time
import pandas as pd

from .storage import Store, symbol, atomic_json, validate_prices
from .ingest import completed_session, _vnstock
from .locking import process_lock

SOURCE_URL = "https://kbbuddywts.kbsec.com.vn"
def stamp():
    return datetime.now(timezone.utc).isoformat()

def ranges(begin, end, days=180):
    if not 7 <= days <= 365:
        raise ValueError("Mỗi khoảng quét cần 7–365 ngày.")
    first, last = date.fromisoformat(begin), date.fromisoformat(end)
    if first > last:
        raise ValueError("Ngày bắt đầu sau ngày kết thúc.")
    while first <= last:
        stop = min(first + timedelta(days=days-1), last)
        yield first.isoformat(), stop.isoformat()
        first = stop + timedelta(days=1)

def normalize(raw, ticker, begin, end):
    if raw is None or raw.empty:
        raise ValueError(f"{ticker}: nguồn trả rỗng.")
    d = raw.rename(columns={"time": "date"}).copy()
    d["date"] = pd.to_datetime(d.date).dt.strftime("%Y-%m-%d")
    d = d.loc[(d.date >= begin) & (d.date <= end)].copy()
    if d.empty:
        raise ValueError(f"{ticker}: không có phiên trong khoảng yêu cầu.")
    d["symbol"] = ticker
    if ticker != "VNINDEX":
        for col in ["open", "high", "low", "close"]:
            d[col] = pd.to_numeric(d[col]) * 1000
    d["price_basis"], d["source"] = "kbs_provider", "KBS via vnstock"
    d["unit"] = "index_points" if ticker == "VNINDEX" else "VND"
    d["interval"], d["retrieved_at"] = "1d", stamp()
    return validate_prices(d[["symbol", "date", "open", "high", "low", "close", "volume",
                             "price_basis", "source", "unit", "interval", "retrieved_at"]])

def fetch_chunk(ticker, begin, end):
    Market, _ = _vnstock()
    provider = Market().index(ticker) if ticker == "VNINDEX" else Market().equity(ticker)
    return provider.ohlcv(start=begin, end=end, source="kbs", count=1000)

def plan(store, tickers, start=None, end=None, days=180, *, refresh=False):
    cutoff = min(end or completed_session(), completed_session())
    date.fromisoformat(cutoff)
    checkpoint = store.read_json("history-progress.json", {"chunks": {}, "checked": {}})
    old = store.read("prices.parquet")
    by_symbol = {t:g for t,g in old.groupby("symbol")} if not old.empty else {}
    tasks, reused = [], []
    for ticker in dict.fromkeys(symbol(t) for t in tickers):
        previous = by_symbol.get(ticker,pd.DataFrame())
        present = set(previous.date) if not previous.empty else set()
        begin = start or (
            (pd.Timestamp(previous.date.max())-pd.Timedelta(days=10)).date().isoformat()
            if not previous.empty else (date.fromisoformat(cutoff)-timedelta(days=365)).isoformat())
        if not refresh and not start and checkpoint.get("checked", {}).get(ticker) == cutoff and cutoff in present:
            reused.append(ticker)
            continue
        for a,b in ranges(begin, cutoff, days):
            key = f"{ticker}/{a}/{b}"
            done = checkpoint.get("chunks", {}).get(key, {})
            dates = done.get("dates", [])
            okay = dates and set(dates) <= present and (store.path / done.get("raw_file","missing")).is_file()
            # The last chunk must remain retryable when the source has not returned that session.
            okay = okay and (b != cutoff or cutoff in dates)
            tasks.append({"key": key, "symbol": ticker, "start": a, "end": b,
                          "status": "reused" if okay and not refresh else "pending"})
    return {"cutoff": cutoff, "symbols": list(dict.fromkeys(symbol(t) for t in tickers)),
            "tasks": tasks, "reused_symbols": reused,
            "network_calls": sum(t["status"] == "pending" for t in tasks)}

def prepare_history(store, tickers, start=None, end=None, *, days=180, refresh=False,
                    retries=2, delay=7.0, fetch=None, progress=print):
    store._writable()
    if not 0 <= retries <= 3 or not 0 <= delay <= 30:
        raise ValueError("retries phải 0–3; delay phải 0–30 giây.")
    fetch = fetch or fetch_chunk
    with process_lock(store.path / ".scanner.lock"):
        work = plan(store, tickers, start, end, days, refresh=refresh)
        state = store.read_json("history-progress.json", {"chunks": {}, "checked": {}})
        state.setdefault("chunks", {})
        state.setdefault("checked", {})
        report = {"started_at": stamp(), "finished_at": None, "status": "running",
                  "cutoff": work["cutoff"], "network_calls": 0, "loaded_rows": 0,
                  "reused": len(work["reused_symbols"]), "failed": [],
                  "symbols": list(dict.fromkeys(symbol(t) for t in tickers)), "results": []}
        atomic_json(store.path / "history-run.json", report)
        ticker_failed = set()
        old = store.read("prices.parquet")
        try:
            for index, task in enumerate(work["tasks"], 1):
                ticker, key = task["symbol"], task["key"]
                if task["status"] == "reused":
                    report["reused"] += 1
                    progress(f"{index}/{len(work['tasks'])} {ticker} Dùng lại {task['start']} → {task['end']}")
                    continue
                try:
                    # Retry network retrieval only; validation/writes never re-download a bad batch.
                    for attempt in range(retries+1):
                        try:
                            report["network_calls"] += 1
                            raw = fetch(ticker, task["start"], task["end"])
                            break
                        except SystemExit as exc:
                            raise RuntimeError("API_QUOTA: SDK tạm dừng vì giới hạn truy cập. Chờ 60 giây rồi chạy lại để tiếp tục.") from exc
                        except Exception:
                            if attempt == retries:
                                raise
                            time.sleep(min(30, delay * (2 ** attempt)))
                    incoming = normalize(raw, ticker, task["start"], task["end"])
                    raw_file = f"raw/prices/{ticker}/{task['start']}_{task['end']}.parquet"
                    store.write(raw_file, raw, {"source": "KBS SDK response", "source_url": SOURCE_URL,
                                "symbol": ticker, "requested_start": task["start"], "requested_end": task["end"]})
                    store.merge_prices(incoming, {"source": "KBS via vnstock 4.0.8", "source_url": SOURCE_URL,
                           "as_of": max(work["cutoff"], str(incoming.date.max())), "units": "VND; index_points",
                           "price_basis": "kbs_provider",
                           "note": "Ngày as_of là ngày đã yêu cầu kiểm tra; ngày giá thực tế nằm trên từng dòng. Có chồng lấn 10 ngày khi cập nhật. Chưa xác minh điều chỉnh giá."})
                    state["chunks"][key] = {**task, "status": "complete", "rows": len(incoming),
                                 "dates": incoming.date.tolist(), "raw_file": raw_file, "at": stamp()}
                    report["loaded_rows"] += len(incoming)
                    report["results"].append({"symbol": ticker, "status": "updated", "rows": len(incoming),
                                               "last": str(incoming.date.max())})
                    progress(f"{index}/{len(work['tasks'])} {ticker}: lưu {len(incoming)} phiên, cuối {incoming.date.max()}")
                except Exception as exc:
                    ticker_failed.add(ticker)
                    # Keep last good Parquet. Failure is visible and retryable on next invocation.
                    error = {"symbol": ticker, "start": task["start"], "end": task["end"],
                             "error": str(exc)[:500], "at": stamp()}
                    state["chunks"][key] = {**task, "status": "failed", **error}
                    report["failed"].append(error)
                    progress(f"{index}/{len(work['tasks'])} {ticker}: lỗi {error['error']}")
                    if "API_QUOTA" in str(exc):
                        report["status"] = "rate_limited"
                        atomic_json(store.path / "history-progress.json", state)
                        break
                state["updated_at"] = stamp()
                atomic_json(store.path / "history-progress.json", state)
                atomic_json(store.path / "history-run.json", report)
                if delay:
                    time.sleep(delay)
            old = store.read("prices.parquet")
            for ticker in report["symbols"]:
                tasks = [t for t in work["tasks"] if t["symbol"] == ticker]
                all_done = all(state["chunks"].get(t["key"],{}).get("status") == "complete" for t in tasks)
                latest_present = not old.empty and ((old.symbol == ticker) & (old.date == work["cutoff"])).any()
                if all_done and ticker not in ticker_failed and latest_present:
                    state["checked"][ticker] = work["cutoff"]
                elif not latest_present and state["checked"].get(ticker) == work["cutoff"]:
                    state["checked"].pop(ticker)
            if report["status"] != "rate_limited":
                report["status"] = "partial" if report["failed"] else "complete"
        except KeyboardInterrupt:
            report["status"] = "interrupted"
            progress("Đã dừng. Dữ liệu đã lưu được giữ; chạy lại để tiếp tục.")
        finally:
            report["finished_at"] = stamp()
            old = store.read("prices.parquet")
            atomic_json(store.path / "history-progress.json", state)
            report["coverage"] = [
                {"symbol": t, "rows": len(g), "first": str(g.date.min()), "last": str(g.date.max()),
                 "checked_through": state["checked"].get(t),
                 "latest_session_present": work["cutoff"] in set(g.date)}
                for t,g in old.loc[old.symbol.isin(report["symbols"])].groupby("symbol")] if not old.empty else []
            present = {row["symbol"] for row in report["coverage"] if row["latest_session_present"]}
            report["pending_latest_symbols"] = [t for t in report["symbols"] if t not in present]
            atomic_json(store.path / "history-run.json", report)
        return report
