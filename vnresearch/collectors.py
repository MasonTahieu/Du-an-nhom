"""Bounded live sources: pinned annual Parquet, current KBS statements and official releases."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import time

import pandas as pd
from .storage import ROOT, Store, symbol, atomic_json
from .ingest import _vnstock, import_reference, validate_financials
from .locking import process_lock

REFERENCE = "https://github.com/Tumiqa/vn-annual-report-miner"
KBS_URL = "https://kbbuddywts.kbsec.com.vn"
def utc():
    return datetime.now(timezone.utc).isoformat()

def get_http(url, timeout=30):
    import requests
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "VNResearch/0.2"})
    r.raise_for_status()
    return r

def fetch_annual_reference(store, tickers, commit, exchange="HSX", first_year=2022):
    """Query the shared, pinned Tumiqa Parquet dataset; never crawl annual PDFs.

    Cache is reused across every ticker and across subsequent app sessions.
    Existing ticker/year data is preserved (it might have been manually reviewed).
    To deliberately replace a year, use the explicit CSV import workflow.
    """
    from .reference_cache import STATEMENTS, ensure_file
    if not re.fullmatch(r"[a-f0-9]{40}", commit) or exchange not in {"HSX", "HNX"}:
        raise ValueError("Cần commit Git 40 ký tự và sàn HSX/HNX.")
    wanted = list(dict.fromkeys(symbol(t) for t in tickers))
    if not wanted:
        raise ValueError("Danh sách mã BCTC rỗng.")
    first_year = int(first_year)
    if not (2000 <= first_year <= 2100):
        raise ValueError("Năm bắt đầu BCTC không hợp lệ.")

    paths, downloaded = {}, []
    for kind in STATEMENTS:
        paths[kind], was_downloaded = ensure_file(store, commit, exchange, kind)
        if was_downloaded:
            downloaded.append(kind)

    frames = []
    for kind, path in paths.items():
        d = pd.read_parquet(path, filters=[("ticker", "in", wanted), ("year", ">=", first_year)])
        if d.empty:
            continue
        d = d.rename(columns={"ticker": "symbol", "year": "period"})
        d["period"] = d.period.astype(str)
        d["unit"] = "VND"
        d.loc[d.item_code.str.contains("tren_co_phieu", na=False), "unit"] = "VND/share"
        d["scope"] = "provider_unspecified"
        d["source_url"] = REFERENCE + f"/blob/{commit}/src/arminer/data/bctc_data/{kind}/{exchange}.parquet"
        d["retrieved_at"] = utc()
        frames.append(d)
    if not frames:
        raise ValueError("Nguồn BCTC năm không có các mã đã chọn trên " + exchange + ".")
    incoming = validate_financials(pd.concat(frames, ignore_index=True))
    old = store.read("financials.parquet")
    old_keys = set(zip(old.symbol.astype(str), old.period.astype(str))) if not old.empty else set()
    incoming_keys = set(zip(incoming.symbol.astype(str), incoming.period.astype(str)))
    # Do not replace any existing full ticker/year, whether sourced from Tumiqa,
    # CSV imports, or a user-reviewed source. Explicit CSV import can replace it.
    missing = incoming.loc[~pd.Series(list(zip(incoming.symbol, incoming.period)), index=incoming.index).isin(old_keys)]
    added_years = sorted(set(zip(missing.symbol, missing.period)))
    skipped_years = sorted(incoming_keys & old_keys)
    if not missing.empty:
        updated = pd.concat([old, missing], ignore_index=True)
        # Prevent silently introducing duplicates or mixing a report scope.
        validate_financials(updated)
        store.write("financials.parquet", updated,
                    {"source": "vn-annual-report-miner annual Parquet (shared cache)",
                     "source_url": REFERENCE, "reference_commit": commit,
                     "as_of": str(updated.period.max()), "units": "VND; VND/share",
                     "note": "Nguồn thứ cấp, chưa đối soát PDF; không ghi đè mã/năm đã lưu. "
                             "Bản gốc dùng chung trong data/reference/tumiqa theo commit."})
    return {"rows": len(missing), "available_rows": len(incoming),
            "added_years": [{"symbol": t, "year": y} for t, y in added_years],
            "skipped_years": [{"symbol": t, "year": y} for t, y in skipped_years],
            "years": sorted(incoming.period.unique().tolist()), "symbols": wanted,
            "commit": commit, "downloaded_statements": downloaded,
            "source": "shared_tumiqa_cache", "status": "complete"}

def clean_label(value):
    s = unicodedata.normalize("NFKD", str(value).lower().replace("đ", "d"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^\s*(?:[a-z\d]+[.\-)]\s*|[ivx]+\s+)", "", s)
    return re.sub(r"\s+", " ", s).strip()

# Match the Vietnamese statement label, not item_id alone:
# KBS maps gross sales and net sales to the same item_id "revenue".
RULES = {
 "balance_sheet": {
   "assets": r"^(tong cong tai san|tong tai san)(\s|\(|$)",
   "equity": r"^(von chu so huu|tong von chu so huu|von va cac quy)(\s|\(|$)",
   "liabilities": r"^(no phai tra|tong no phai tra)(\s|\(|$)",
   "current_assets": r"^(tai san ngan han|tong tai san ngan han)(\s|\(|$)",
   "current_liabilities": r"^(no ngan han|tong no ngan han)(\s|\(|$)",
   "loans": r"^cho vay khach hang(\s|\(|$)",
   "deposits": r"^tien gui cua khach hang(\s|\(|$)"
 },
 "income_statement": {
   "revenue": r"^doanh thu thuan (ve ban hang|ban hang|ve hoat dong|hoat dong)|^doanh so thuan",
   "net_income": r"^(loi nhuan sau thue|lai/?\(?lo\)? thuan sau thue|lai/?lo sau thue)(\s*\(|\s+thu nhap doanh nghiep|$)",
   "parent_income": r"^loi nhuan sau thue cua co dong (cua cong ty me|cua ngan hang me)",
   "operating_income": r"^tong thu nhap hoat dong",
   "net_interest_income": r"^thu nhap lai thuan",
   "operating_expense": r"^chi phi hoat dong(\s|\(|$)"
 },
 "cash_flow": {
   "cfo": r"^luu chuyen tien thuan (tu|trong) (cac )?hoat dong (san xuat )?kinh doanh(?!.*truoc thue)"
 }
}

def normalize_quarters(raw, ticker, statement):
    cols = [c for c in raw.columns if re.fullmatch(r"20\d{2}-Q[1-4]", str(c))]
    if not cols or not {"item","item_id"} <= set(raw):
        raise ValueError(f"{ticker}/{statement}: cấu trúc BCTC không hợp lệ.")
    rules = RULES[statement]
    matches = {k: [] for k in rules}
    rows, skipped = [], []
    for i,record in enumerate(raw.to_dict("records")):
        if record.get("item_id") in {"audit_status","unit_type"}:
            continue
        label = clean_label(record["item"])
        # The SDK multiplies ALL values by 1000, including EPS originally in VND.
        # Keep those rows only in raw archive pending an explicit source correction.
        if "co phieu" in label or "per_share" in str(record["item_id"]):
            skipped.append(str(record["item"]))
            continue
        canonical = next((k for k,p in rules.items() if re.search(p, label)), None)
        if canonical:
            matches[canonical].append(i)
        for period in cols:
            value = pd.to_numeric(record.get(period), errors="coerce")
            if pd.isna(value):
                continue
            if not __import__("math").isfinite(float(value)):
                raise ValueError("BCTC chứa số không hữu hạn.")
            scope_value = str(raw.attrs.get("unit_type",{}).get(period, ""))
            scope = "consolidated" if scope_value == "Hợp nhất" else "separate" if scope_value == "Riêng lẻ" else "provider_unspecified"
            rows.append({"symbol": ticker, "period": period, "statement": statement,
                         "item_code": f"{statement}/{record['item_id']}/{i}", "item_name": str(record["item"]),
                         "canonical_field": canonical or "", "value": float(value), "unit": "VND", "scope": scope,
                         "basis": "point_in_time" if statement == "balance_sheet" else "provider_period_unspecified",
                         "audit_status": str(raw.attrs.get("audit_status",{}).get(period, "unknown")),
                         "source_url": KBS_URL, "retrieved_at": utc()})
    ambiguous = {k for k,v in matches.items() if len(v)>1}
    for r in rows:
        if r["canonical_field"] in ambiguous:
            r["canonical_field"] = ""
    if not rows:
        raise ValueError(f"{ticker}: BCTC quý rỗng.")
    return pd.DataFrame(rows), {"skipped_per_share": skipped, "ambiguous_fields": sorted(ambiguous),
                               "missing_fields": sorted(k for k,v in matches.items() if not v)}

def fetch_kbs_quarter(finance_factory, ticker, statement):
    # vnai can install narrower wrappers after the first provider call.
    # Keep the public wrapper (and its quota limits), using shared arguments only.
    # KBS defaults retain item/item_id; audit/unit_type are also returned in attrs.
    if statement not in {"balance_sheet", "income_statement", "cash_flow"}:
        raise ValueError("Loại BCTC không hợp lệ.")
    return getattr(finance_factory(ticker, period="quarter"), statement)(period="quarter")

def fetch_quarters(store, tickers, *, delay=7.0, progress=print, fetch=None):
    if fetch is None:
        _vnstock()  # Optional SDK is loaded only for a real user-launched fetch.
        from vnstock.explorer.kbs.financial import Finance
        def fetch(ticker, statement):
            return fetch_kbs_quarter(Finance, ticker, statement)
    result = {"started_at": utc(), "results": [], "failed": []}
    with process_lock(store.path / ".scanner.lock"):
        for ticker in dict.fromkeys(symbol(t) for t in tickers):
            frames, diagnostics = [], {}
            try:
                for statement in ["balance_sheet","income_statement","cash_flow"]:
                    raw = fetch(ticker, statement)
                    if raw is None or raw.empty:
                        raise ValueError(f"{ticker}/{statement}: không có dữ liệu.")
                    # Timestamp archive retains original provider fields and attrs for audit.
                    relative = f"raw/financials/{ticker}/{statement}.json"
                    store.write_json(relative, {"rows":json.loads(raw.to_json(orient="records",force_ascii=False)),
                                                "attrs":raw.attrs,"retrieved_at":utc()},
                                     {"source":"KBS SDK","source_url":KBS_URL,
                                      "sdk_attrs":raw.attrs,"units":"SDK already multiplied by 1000"})
                    normalized, notes = normalize_quarters(raw, ticker, statement)
                    frames.append(normalized)
                    diagnostics[statement] = notes
                    progress(f"{ticker}: đã lấy {statement}, {len(normalized)} chỉ tiêu-kỳ.")
                    if delay: time.sleep(delay)
                incoming = pd.concat(frames, ignore_index=True)
                for period,g in incoming.groupby("period"):
                    if g.scope.nunique() > 1:
                        raise ValueError(f"{ticker}/{period}: phạm vi báo cáo giữa các bảng khác nhau.")
                old = store.read("financial_quarterly.parquet")
                if not old.empty:
                    old = old.loc[~((old.symbol == ticker) & old.period.isin(incoming.period.unique()))]
                store.write("financial_quarterly.parquet", pd.concat([old,incoming],ignore_index=True),
                            {"source": "KBS quarterly financial statements via vnstock 4.0.8",
                             "source_url": KBS_URL, "as_of": incoming.period.max(), "units": "VND",
                             "note": "BS là tại thời điểm; KQKD/CFO chưa xác minh riêng quý hay lũy kế. Không cộng TTM, không tính ROE quý hoặc tự dùng EPS."})
                result["results"].append({"symbol": ticker, "rows": len(incoming), "periods": sorted(incoming.period.unique().tolist()),
                                          "diagnostics": diagnostics})
            except SystemExit:
                result["failed"].append({"symbol":ticker,"error":"Giới hạn API: chờ ít nhất 60 giây và chạy lại."})
                break
            except Exception as exc:
                result["failed"].append({"symbol": ticker, "error": str(exc)[:500]})
                progress(f"{ticker}: {exc}")
            atomic_json(store.path / "financial-run.json", result)
    result["finished_at"] = utc()
    atomic_json(store.path / "financial-run.json", result)
    return result

def init_profiles(store):
    config = json.loads((ROOT / "config/watchlist.json").read_text(encoding="utf-8"))
    profiles = store.read_json("companies.json",{})
    for ticker,info in config["companies"].items():
        profiles.setdefault(ticker,info.copy())
        if not profiles[ticker].get("peers") and info.get("peers"):
            profiles[ticker]["peers"] = info["peers"]
    store.write_json("companies.json",profiles,{"source":"Hồ sơ cấu hình từ trang IR", "source_url":"see per-company source_url"})
    return config
