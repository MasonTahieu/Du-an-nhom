"""Explicit data loading only. No imports of vnstock in the UI/report path."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlparse
import warnings

import pandas as pd
from .storage import Store, symbol

VN_TIME = timezone(timedelta(hours=7))
REPO_URL = "https://github.com/Tumiqa/vn-annual-report-miner"


def completed_session():
    now = datetime.now(VN_TIME)
    day = now.date()
    if now.hour < 16:
        day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.isoformat()


def _vnstock():
    os.environ.setdefault("VNSTOCK_DISABLE_AGENT_SETUP", "1")
    os.environ.setdefault("VNSTOCK_DISABLE_GLOBAL_AGENT", "1")
    os.environ.setdefault("VNSTOCK_AGENT_TARGETS", "none")
    try:
        from vnstock import Market, Reference
        return Market, Reference
    except ImportError as e:
        raise RuntimeError("Chưa cài bộ nạp dữ liệu: chạy python -m pip install -r requirements-market.txt") from e


def fetch_prices(store, tickers, start=None, end=None, *, bootstrap=False):
    Market, _ = _vnstock()
    end = min(end or completed_session(), completed_session())
    old = store.read("prices.parquet")
    results = []
    for value in tickers:
        ticker = symbol(value)
        prev = old.loc[old.symbol == ticker] if not old.empty else pd.DataFrame()
        begin = start or (str((pd.Timestamp(prev.date.max()) - pd.Timedelta(days=10)).date()) if not prev.empty else str((pd.Timestamp(end) - pd.Timedelta(days=365)).date()))
        if pd.Timestamp(begin) > pd.Timestamp(end):
            raise ValueError("Ngày bắt đầu sau ngày kết thúc.")
        market = Market().index(ticker) if ticker == "VNINDEX" else Market().equity(ticker)
        raw = market.ohlcv(start=begin, end=end, source="kbs", count=1000)
        if raw is None or raw.empty:
            raise ValueError(f"{ticker}: nguồn không trả dữ liệu; dữ liệu cũ được giữ.")
        d = raw.rename(columns={"time": "date"}).copy()
        d["date"] = pd.to_datetime(d.date).dt.strftime("%Y-%m-%d")
        d = d.loc[(d.date >= begin) & (d.date <= end)]
        d["symbol"] = ticker
        # KBS equity price is thousands of VND; index stays in points.
        if ticker != "VNINDEX":
            for col in ["open", "high", "low", "close"]:
                d[col] = pd.to_numeric(d[col]) * 1000
        d["price_basis"] = "kbs_provider"
        d["source"] = "KBS via vnstock"
        d["unit"] = "index_points" if ticker == "VNINDEX" else "VND"
        results.append(d[["symbol", "date", "open", "high", "low", "close", "volume", "price_basis", "source", "unit"]])
    incoming = pd.concat(results, ignore_index=True)
    # All requested tickers validated before replacing one consolidated file.
    store.merge_prices(incoming, {"source": "KBS via vnstock 4.x", "source_url": "https://kbbuddywts.kbsec.com.vn",
                        "as_of": incoming.date.max(), "units": "VND; VNINDEX=index_points",
                        "note": "Giá lịch sử do KBS cung cấp có thể được điều chỉnh hồi tố. Mỗi lần nạp tăng dần kiểm tra chồng lấn 10 ngày; sự kiện cổ phiếu cần nạp lại toàn khoảng."}, bootstrap=bootstrap)
    return {"symbols": sorted(incoming.symbol.unique().tolist()), "rows_loaded": len(incoming), "end": end}


def validate_financials(d):
    required = {"symbol", "period", "item_code", "value", "unit", "scope", "source_url"}
    if d.empty or not required <= set(d.columns):
        raise ValueError("BCTC cần symbol,period,item_code,value,unit,scope,source_url.")
    d = d.copy()
    d["symbol"] = d.symbol.map(symbol)
    d["period"] = d.period.astype(str)
    if not d.period.str.fullmatch(r"20\d{2}").all():
        raise ValueError("Bản hiện tại phân tích BCTC theo năm; period phải là năm YYYY.")
    d["value"] = pd.to_numeric(d.value, errors="raise")
    if not d["value"].map(math.isfinite).all() or not d.unit.isin(["VND", "VND/share"]).all():
        raise ValueError("Giá trị thiếu hoặc đơn vị chưa chuẩn hóa về VND / VND/share.")
    per_share = (d.item_code == "eps") | d.item_code.str.contains("tren_co_phieu", na=False)
    if not (d.loc[per_share, "unit"] == "VND/share").all():
        raise ValueError("EPS/chỉ tiêu mỗi cổ phiếu cần đơn vị VND/share.")
    if not d.scope.isin(["consolidated", "separate", "provider_unspecified"]).all():
        raise ValueError("scope phải là consolidated, separate hoặc provider_unspecified.")
    if not d.source_url.map(valid_url).all():
        raise ValueError("BCTC cần URL nguồn hợp lệ.")
    if d.duplicated(["symbol", "period", "item_code"]).any():
        raise ValueError("Trùng chỉ tiêu cùng năm. Chọn một báo cáo/phạm vi nhất quán.")
    if (d.groupby(["symbol", "period"]).scope.nunique() > 1).any():
        raise ValueError("Không trộn BCTC riêng lẻ và hợp nhất trong cùng kỳ.")
    return d


def import_financials(store, csv_path, *, bootstrap=False):
    d = validate_financials(pd.read_csv(csv_path, dtype={"period": str}))
    d["ingestion_origin"] = "manual_csv"
    old = store.read("financials.parquet")
    if not old.empty:
        # Replace whole symbol/year to avoid stale items or mixing report scopes.
        keys = set(zip(d.symbol, d.period))
        old = old.loc[~pd.Series(list(zip(old.symbol, old.period)), index=old.index).isin(keys)]
    merged = pd.concat([old, d], ignore_index=True)
    store.write("financials.parquet", merged, {"source": "CSV do người dùng đối soát", "source_url": "see row source_url",
                "as_of": str(d.period.max()), "units": "VND; EPS=VND/share"}, bootstrap=bootstrap)
    return len(d)


def import_reference(store, repo, tickers, first_year=2022, *, bootstrap=False):
    repo = Path(repo)
    try:
        commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        commit = "unknown; imported from supplied local directory"
    root = repo / "src" / "arminer" / "data" / "bctc_data"
    frames = []
    tickers = [symbol(t) for t in tickers]
    for kind in ["balance_sheet", "income_statement", "cash_flow"]:
        for exchange in ["HSX", "HNX"]:
            p = root / kind / (exchange + ".parquet")
            if p.exists():
                d = pd.read_parquet(p, filters=[("ticker", "in", tickers), ("year", ">=", first_year)])
                if not d.empty:
                    frames.append(d)
    if not frames:
        raise ValueError("Không tìm thấy Parquet hoặc mã được yêu cầu trong repo tham khảo.")
    d = pd.concat(frames, ignore_index=True).rename(columns={"ticker": "symbol", "year": "period"})
    d["period"] = d.period.astype(str)
    d["unit"] = "VND"
    d.loc[d.item_code.str.contains("tren_co_phieu", na=False), "unit"] = "VND/share"
    d["scope"] = "provider_unspecified"
    d["source_url"] = REPO_URL + "/tree/" + (commit if len(commit) == 40 else "main") + "/src/arminer/data/bctc_data"
    d = validate_financials(d)
    old = store.read("financials.parquet")
    if not old.empty:
        keys = set(zip(d.symbol, d.period))
        old = old.loc[~pd.Series(list(zip(old.symbol, old.period)), index=old.index).isin(keys)]
    merged = pd.concat([old, d], ignore_index=True)
    store.write("financials.parquet", merged, {"source": "vn-annual-report-miner bundled annual financials",
                "source_url": REPO_URL, "reference_commit": commit,
                "as_of": str(d.period.max()), "units": "VND; EPS=VND/share",
                "note": "Dữ liệu thứ cấp; phạm vi báo cáo chưa được xác nhận với bản PDF kiểm toán."}, bootstrap=bootstrap)
    return len(d)


def valid_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in ["https", "http"] and bool(parsed.hostname) and not parsed.username


def import_macro(store, path, *, bootstrap=False):
    records = pd.read_csv(path).to_dict("records")
    if not records:
        raise ValueError("Bảng vĩ mô rỗng; hãy nhập ít nhất một chỉ tiêu.")
    required = {"indicator", "label", "value", "unit", "period", "published_at", "source_url", "basis"}
    for row in records:
        if not required <= set(row) or not valid_url(row["source_url"]):
            raise ValueError("Vĩ mô thiếu trường hoặc URL nguồn.")
        row["value"] = float(row["value"])
        if not math.isfinite(row["value"]):
            raise ValueError("Số liệu vĩ mô phải hữu hạn.")
        pd.Timestamp(row["published_at"])
    store.write_json("macro.json", records, {"source": "NSO / SBV / nguồn chính thức do người dùng nhập",
                     "source_url": "see row source_url", "as_of": max(r["published_at"] for r in records)},
                     bootstrap=bootstrap)
    return len(records)


def import_news(store, path, *, bootstrap=False):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("Tin tức cần danh sách JSON không rỗng.")
    for n in records:
        if not isinstance(n, dict) or not {"symbol", "title", "published_at", "url"} <= set(n):
            raise ValueError("Tin thiếu symbol,title,published_at,url.")
        n["symbol"] = symbol(n["symbol"]) if n["symbol"] != "MARKET" else "MARKET"
        if not n.get("title") or not valid_url(n.get("url")) or not n.get("published_at"):
            raise ValueError("Tin cần symbol,title,url,published_at.")
        pd.Timestamp(n["published_at"])
        n.setdefault("summary", "")
        n.setdefault("content_status", "user_reviewed" if n["summary"] else "metadata_only")
    old = store.read_json("news.json", [])
    by_url = {r["url"]: r for r in old + records}
    merged = sorted(by_url.values(), key=lambda n: (n["published_at"], n["url"]), reverse=True)
    store.write_json("news.json", merged, {"source": "Tin nhập tay có URL và ngày công bố", "source_url": "see row url",
                     "as_of": max(n["published_at"][:10] for n in merged)}, bootstrap=bootstrap)
    return len(records)


def fetch_news(store, tickers, limit=5):
    if not 1 <= limit <= 10:
        raise ValueError("Chỉ nạp 1–10 tin mỗi mã trong một lần chạy.")
    _, Reference = _vnstock()
    records = []
    for t in tickers:
        t = symbol(t)
        raw = Reference().company(t).news(source="kbs")
        if raw is None or raw.empty:
            continue
        for row in raw.head(limit).to_dict("records"):
            def pick(*keys):
                return next((row[k] for k in keys if k in row and pd.notna(row[k])), None)
            title = pick("title", "Title", "news_title")
            url = pick("url", "link", "news_url")
            if isinstance(url, str) and url.startswith("/") and not url.startswith("//"):
                # KBS company news currently returns Vietstock article paths.
                url = "https://vietstock.vn" + url
            published = pick("publish_date", "published_at", "date", "time", "publish_time")
            if title and valid_url(url) and published:
                records.append({"symbol": t, "title": str(title), "url": str(url),
                                "published_at": str(pd.Timestamp(published).date()),
                                "summary": "", "content_status": "metadata_only"})
    if not records:
        raise ValueError("Nguồn không trả tin với đủ ngày và URL. Hãy nhập JSON theo mẫu.")
    old = store.read_json("news.json", [])
    by_url = {n["url"]: n for n in old}
    for n in records:
        if n["url"] not in by_url or by_url[n["url"]].get("content_status") == "metadata_only":
            by_url[n["url"]] = n
    merged = list(by_url.values())
    store.write_json("news.json", merged, {"source": "KBS via vnstock (metadata)", "source_url": "https://kbbuddywts.kbsec.com.vn",
                                         "as_of": max(n["published_at"] for n in merged)})
    return len(records)


def seed_local():
    """Explicit copy; never changes the sample and never overwrites existing local files."""
    sample, local = Store("sample"), Store("local")
    local.path.mkdir(parents=True, exist_ok=True)
    for p in sample.path.iterdir():
        if p.is_file() and not (local.path / p.name).exists():
            shutil.copy2(p, local.path / p.name)
    manifest = local.manifest()
    manifest["mode"] = "local"
    from .storage import atomic_json
    atomic_json(local.path / "manifest.json", manifest)
    return str(local.path)


def import_prices(store, csv_path):
    from .storage import validate_prices
    d = validate_prices(pd.read_csv(csv_path))
    if (d.date > completed_session()).any():
        raise ValueError("Chỉ nhập giá của phiên đã hoàn tất.")
    if not {"unit", "source"} <= set(d):
        raise ValueError("CSV giá cần unit và source.")
    expected = d.symbol.map(lambda t: "index_points" if t == "VNINDEX" else "VND")
    if not (d.unit == expected).all():
        raise ValueError("Đơn vị cổ phiếu phải là VND, VNINDEX là index_points.")
    store.merge_prices(d, {"source":"CSV giá đã chuẩn hóa", "source_url":"see row source", "as_of":d.date.max(), "units":"VND; VNINDEX=index_points"})
    return len(d)
