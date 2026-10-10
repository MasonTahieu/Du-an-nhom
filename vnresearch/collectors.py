"""Bounded live sources: pinned annual Parquet, VCI statements and official releases."""
from datetime import datetime, timezone
import json
import re
import time

import pandas as pd
from .storage import ROOT, Store, symbol, atomic_json
from .ingest import validate_financials
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
    # Cache is already available: add the preceding year as calculation-only
    # context without touching the primary financials.parquet history.
    # This never makes a separate network request or fails the annual import.
    baseline = {"status": "not_checked"}
    try:
        from .annual_baseline import backfill_from_cache
        baseline = backfill_from_cache(
            store, year=int(first_year) - 1, symbols=wanted,
            paths={(exchange, kind): path for kind, path in paths.items()})
    except (OSError, ValueError, ImportError, KeyError) as exc:
        baseline = {"status": "warning", "message": f"Không bổ sung năm nền: {exc}"}
    return {"rows": len(missing), "available_rows": len(incoming),
            "added_years": [{"symbol": t, "year": y} for t, y in added_years],
            "skipped_years": [{"symbol": t, "year": y} for t, y in skipped_years],
            "years": sorted(incoming.period.unique().tolist()), "symbols": wanted,
            "commit": commit, "downloaded_statements": downloaded,
            "source": "shared_tumiqa_cache", "baseline": baseline, "status": "complete"}


def fetch_annual_for_symbol(store, ticker, settings, *, step, progress=print):
    """Shared web/CMD source routing; step records optional and primary outcomes."""
    ticker = symbol(ticker)
    catalogue = {r["symbol"]: r.get("exchange")
                 for r in store.read_json("universe.json", {}).get("symbols", [])}
    exchange = catalogue.get(ticker)
    if exchange == "UPCOM":
        from .upcom_annual import fetch_annual_vci
        return step("BCTC năm " + ticker + " · VCI (UPCoM, nếu có)",
                    lambda: fetch_annual_vci(store, ticker, first_year=settings["first_year"]))
    exchanges = {"HOSE": ["HSX"], "HSX": ["HSX"], "HNX": ["HNX"]}.get(
        exchange, ["HSX", "HNX"])
    def reference():
        errors = []
        for ex in exchanges:
            try:
                return fetch_annual_reference(store, [ticker], settings["reference_commit"],
                                              ex, settings["first_year"])
            except ValueError as exc:
                errors.append(str(exc))
        raise ValueError("; ".join(errors))
    # Failure of the first source remains a warning when VCI can fill the data.
    step("BCTC năm " + ticker + " · dùng cache nếu có", reference, scope="optional")
    from .financials import repair_annual_sources
    return step("Đối soát / bổ sung BCTC năm " + ticker + " qua VCI khi cần",
                lambda: repair_annual_sources(store, [ticker],
                    first_year=settings["first_year"], progress=progress))

# Shared mapping is versioned and can be replayed from saved provider data.
from .financials import clean_label, RULES, normalize_statement

def normalize_quarters(raw, ticker, statement):
    return normalize_statement(raw, ticker, statement)


def fetch_kbs_quarter(finance_factory, ticker, statement):
    # vnai can install narrower wrappers after the first provider call.
    # Keep the public wrapper (and its quota limits), using shared arguments only.
    # KBS defaults retain item/item_id; audit/unit_type are also returned in attrs.
    if statement not in {"balance_sheet", "income_statement", "cash_flow"}:
        raise ValueError("Loại BCTC không hợp lệ.")
    return getattr(finance_factory(ticker, period="quarter"), statement)(period="quarter")

def fetch_quarters(store, tickers, *, delay=7.0, progress=print, fetch=None):
    from .financials import (STATEMENTS, PROVIDERS, provider_statement,
                             repair_quarter_cache, normalize_statement)
    from .insights import quarterly_rows
    from .peers import map_sector
    repair_quarter_cache(store)
    providers = ["KBS"] if fetch is not None else ["VCI"]
    result = {"started_at": utc(), "results": [], "failed": []}
    with process_lock(store.path / ".scanner.lock"):
        for ticker in dict.fromkeys(symbol(t) for t in tickers):
            errors, success, limited = [], False, False
            for provider in providers:
                frames, diagnostics = [], {}
                try:
                    for statement in STATEMENTS:
                        raw = fetch(ticker, statement) if fetch else provider_statement(ticker, statement, "quarter", provider)
                        if raw is None or raw.empty:
                            raise ValueError(f"{ticker}/{statement}: không có dữ liệu.")
                        relative = f"raw/financials/{ticker}/{statement}.json" if provider == "KBS" else f"raw/financials/{ticker}/{provider}/quarter/{statement}.json"
                        store.write_json(relative, {"rows": json.loads(raw.to_json(orient="records", force_ascii=False)),
                            "attrs": raw.attrs, "retrieved_at": utc()},
                            {"source": provider + " SDK", "source_url": PROVIDERS[provider], "units": "SDK monetary values in VND"})
                        normalized, notes = normalize_statement(raw, ticker, statement, provider=provider)
                        frames.append(normalized)
                        diagnostics[statement] = notes
                        progress(f"{ticker}: đã lấy {statement} từ {provider}, {len(normalized)} chỉ tiêu-kỳ.")
                        if delay: time.sleep(delay)
                    incoming = pd.concat(frames, ignore_index=True)
                    for period, g in incoming.groupby("period"):
                        if g.scope.nunique() > 1:
                            raise ValueError(f"{ticker}/{period}: phạm vi báo cáo giữa các bảng khác nhau.")
                    # Commit only after all three requests succeed. Preserve a
                    # cached cash-flow period absent from the incoming source.
                    with store.transaction():
                        old = store.read("financial_quarterly.parquet")
                        if not old.empty:
                            if not {"statement", "scope"} <= set(old):
                                raise ValueError("Cache quý chưa đủ cấu trúc; giữ bản cũ.")
                            keys = set(zip(incoming.period, incoming.statement))
                            old_keys = pd.Series(list(zip(old.period, old.statement)), index=old.index)
                            retained = old.loc[(old.symbol == ticker) & old.period.isin(incoming.period.unique()) & ~old_keys.isin(keys)]
                            combined = pd.concat([retained, incoming], ignore_index=True)
                            if any(g.scope.nunique() > 1 or g.source_url.nunique() > 1 for _, g in combined.groupby("period")):
                                raise ValueError("Không ghép các bảng khác nguồn/phạm vi trong cùng kỳ.")
                            replaced = old.loc[(old.symbol == ticker) & old_keys.isin(keys)]
                            if not replaced.empty:
                                store.write(f"backups/quarterly/{ticker}.parquet", replaced,
                                            {"source": "Original quarterly rows before provider update"})
                            old = old.loc[~((old.symbol == ticker) & old_keys.isin(keys))]
                        store.write("financial_quarterly.parquet", pd.concat([old, incoming], ignore_index=True),
                            {"source": "Quarterly statements; see source_url per row", "source_url": PROVIDERS[provider],
                             "normalization_version": 3, "as_of": incoming.period.max(), "units": "VND",
                             "note": "BS tại thời điểm; KQKD/CFO chưa xác minh riêng quý hay lũy kế. Không tính TTM hoặc ROE quý."})
                    profiles = store.read_json("companies.json", {})
                    industry = store.read_json("industry_catalog.json", {}).get("symbols", {})
                    sector = map_sector(ticker, profiles.get(ticker, {}), industry.get(ticker, {}))
                    coverage = quarterly_rows(incoming, ticker, sector)
                    result["results"].append({"symbol": ticker, "provider": provider, "rows": len(incoming),
                        "periods": sorted(incoming.period.unique().tolist()), "diagnostics": diagnostics,
                        "missing_by_period": {r["period"]: r["missing_fields"] for r in coverage if r["missing_fields"]},
                        "missing_statements_by_period": {r["period"]: r["missing_statements"] for r in coverage if r["missing_statements"]},
                        "fallback_errors": errors})
                    success = True
                    break
                except SystemExit:
                    errors.append("Giới hạn API: chờ hết hạn mức rồi chạy lại.")
                    limited = True
                    break
                except Exception as exc:
                    errors.append(provider + ": " + str(exc)[:300])
                    progress(f"{ticker}: {errors[-1]}")
            if not success:
                result["failed"].append({"symbol": ticker, "error": "; ".join(errors)})
            if limited: break
    # Network/download execution and semantic data completeness are independent.
    result["execution_status"] = "partial" if result["failed"] else "complete"
    result["quality_status"] = "partial" if any(
        r.get("missing_by_period") or r.get("missing_statements_by_period")
        for r in result["results"]) else "complete"
    result["status"] = "partial" if (result["execution_status"] == "partial" or
                                    result["quality_status"] == "partial") else "complete"
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
