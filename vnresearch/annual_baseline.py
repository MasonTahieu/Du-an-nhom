"""Offline opening-year annual facts for ROA, ROE and annual growth.

Historical baseline is an independent, verified local Parquet file. It never
replaces user-reviewed annual financials, and is never presented as an extra
annual reporting year. Reading charts/reports performs NO network or writes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .storage import ROOT, Store, symbol, atomic_json

BASELINE_FILE = "annual_baseline.parquet"
KINDS = ("balance_sheet", "income_statement", "cash_flow")
EXCHANGES = ("HSX", "HNX")
REQUIRED = {"ticker", "year", "item_code", "item_name", "value"}


def display_first_year():
    """Keep the report's original year range, despite an extra opening year."""
    try:
        conf = json.loads((ROOT / "config" / "watchlist.json").read_text(encoding="utf-8"))
        year = int(conf.get("first_year", 2022))
        return year if 2001 <= year <= 2100 else 2022
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 2022


def facts_for_analysis(store: Store, annual: pd.DataFrame | None = None):
    """Append baseline years only when the main annual file has no such year.

    Keep verified/manual annual rows authoritative and never mix two statement
    scopes within the same ticker/year. The caller does not persist this merge.
    """
    annual = store.read("financials.parquet") if annual is None else annual
    baseline = store.read(BASELINE_FILE)
    if baseline.empty:
        return annual
    if annual.empty:
        return baseline.iloc[0:0].copy()  # Baseline alone is NOT company coverage.
    existing = set(zip(annual.symbol.astype(str), annual.period.astype(str)))
    additions = baseline.loc[
        ~pd.Series(list(zip(baseline.symbol.astype(str), baseline.period.astype(str))), index=baseline.index).isin(existing)
    ]
    if additions.empty:
        return annual
    # A later VCI/manual refresh might replace the following year with a
    # clearly consolidated/separate report. An unspecified Tumiqa baseline
    # then cannot be silently used as a comparable opening balance.
    if "scope" in annual.columns:
        incompatible = set()
        for ticker, year in set(zip(additions.symbol.astype(str), additions.period.astype(str))):
            next_year = str(int(year) + 1)
            later = annual.loc[(annual.symbol.astype(str) == ticker) & (annual.period.astype(str) == next_year)]
            if set(later.scope.dropna().astype(str)) & {"consolidated", "separate"}:
                incompatible.add((ticker, year))
        if incompatible:
            key = pd.Series(list(zip(additions.symbol.astype(str), additions.period.astype(str))), index=additions.index)
            additions = additions.loc[~key.isin(incompatible)]
    if additions.empty:
        return annual
    return pd.concat([annual, additions], ignore_index=True)


def _cache_candidates(store, commit, exchange, kind):
    relative = Path(kind) / f"{exchange}.parquet"
    return (
        store.base / "reference" / "tumiqa" / commit / relative,
        store.path / "raw" / "reference" / commit / "src" / "arminer" / "data" / "bctc_data" / relative,
    )


def _parse_source_rows(path, *, year, kind, exchange, commit):
    # Indexed Parquet filtering avoids loading full market data into memory.
    raw = pd.read_parquet(path, filters=[("year", "==", int(year))])
    if raw.empty:
        return pd.DataFrame()
    if not REQUIRED.issubset(raw.columns):
        raise ValueError(f"{path}: thiếu cột {_format_missing(REQUIRED - set(raw.columns))}")
    raw = raw.loc[raw.year.astype(str).eq(str(year))].copy()
    if raw.empty:
        return pd.DataFrame()
    raw = raw.rename(columns={"ticker": "symbol", "year": "period"})
    raw["period"] = raw.period.astype(str)
    raw["symbol"] = raw.symbol.astype(str).str.upper()
    raw["statement"] = kind
    raw["scope"] = "provider_unspecified"
    raw["source_url"] = ("https://github.com/Tumiqa/vn-annual-report-miner/blob/" + commit +
                         f"/src/arminer/data/bctc_data/{kind}/{exchange}.parquet")
    raw["unit"] = "VND"
    raw.loc[raw.item_code.astype(str).str.contains("tren_co_phieu", na=False), "unit"] = "VND/share"
    raw["ingestion_origin"] = "tumiqa_opening_year_cache"
    raw["audit_status"] = "unverified"
    raw["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    raw["cache_exchange"] = exchange
    return raw


def _format_missing(values):
    return ", ".join(sorted(map(str, values)))


def backfill_from_cache(store: Store | None = None, *, year: int | None = None,
                        symbols=None, paths=None, dry_run: bool = False):
    """Backfill ONLY existing local companies' opening-year facts from local cache.

    No network; no changes to financials.parquet, sample or submission.
    Supports callers supplying { (exchange,kind): pathlib.Path } from freshly
    cached reference statements after annual data is committed.
    """
    store = store or Store("local")
    if store.mode != "local":
        raise ValueError("Chỉ được bổ sung dữ liệu nền vào data/local.")
    year = int(year) if year is not None else display_first_year() - 1
    if year < 2000 or year > 2099:
        raise ValueError("Năm dữ liệu nền không hợp lệ.")
    annual = store.read("financials.parquet")
    if annual.empty:
        return {"status": "no_annual_data", "year": str(year), "added_symbols": [], "added_rows": 0,
                "warnings": ["Chưa có dữ liệu BCTC năm trong local; chưa tạo dữ liệu nền."], "no_network": True}
    targets = set(annual.loc[annual.period.astype(str).eq(str(year + 1)), "symbol"].astype(str))
    if symbols is not None:
        targets &= {symbol(t) for t in symbols}
    if not targets:
        return {"status": "no_targets", "year": str(year), "added_symbols": [], "added_rows": 0,
                "warnings": ["Không có mã được chọn với năm báo cáo liền sau dữ liệu nền."], "no_network": True}

    existing_baseline = store.read(BASELINE_FILE)
    existing = set(zip(annual.symbol.astype(str), annual.period.astype(str)))
    if not existing_baseline.empty:
        existing |= set(zip(existing_baseline.symbol.astype(str), existing_baseline.period.astype(str)))
    pending = {t for t in targets if (t, str(year)) not in existing}
    if not pending:
        return {"status": "already_complete", "year": str(year), "cache_files": 0,
                "added_symbols": [], "added_rows": 0, "missing_symbols": [],
                "warnings": [], "no_network": True, "unchanged_financials": True}
    warnings, loaded = [], []
    commit = json.loads((ROOT / "config" / "watchlist.json").read_text(encoding="utf-8"))["reference_commit"]
    paths = paths or {}
    seen_files = 0
    for exchange in EXCHANGES:
        for kind in KINDS:
            path = paths.get((exchange, kind))
            if path is None:
                path = next((p for p in _cache_candidates(store, commit, exchange, kind) if p.is_file()), None)
            if path is None:
                continue
            path = Path(path)
            # For pre-existing shared cache, check persisted digest when present.
            digest_path = path.with_suffix(".sha256")
            if digest_path.exists():
                import hashlib
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != digest_path.read_text(encoding="ascii").strip():
                    warnings.append(f"Bỏ qua cache sai SHA256: {path}")
                    continue
            try:
                frame = _parse_source_rows(path, year=year, kind=kind, exchange=exchange, commit=commit)
            except (OSError, ValueError, ImportError, KeyError) as exc:
                warnings.append(f"Không đọc được {exchange}/{kind}: {type(exc).__name__}: {exc}")
                continue
            seen_files += 1
            if not frame.empty:
                loaded.append(frame.loc[frame.symbol.isin(pending)].copy())
    loaded = [f for f in loaded if not f.empty]
    if not loaded:
        warnings.append("Không tìm thấy dữ liệu nền cho các mã cần bổ sung trong cache HSX/HNX có sẵn.")
        return {"status": "no_cache_match", "year": str(year), "cache_files": seen_files,
                "added_symbols": [], "added_rows": 0, "missing_symbols": sorted(pending),
                "warnings": warnings, "no_network": True}

    candidate = pd.concat(loaded, ignore_index=True)
    eligible = []
    for ticker, data in candidate.groupby("symbol"):
        exchanges = set(data.cache_exchange)
        # A ticker must not silently use unrelated HSX/HNX history.
        if len(exchanges) != 1:
            warnings.append(f"{ticker}: cache năm {year} có ở nhiều sàn; chưa xác định nguồn đúng.")
            continue
        next_rows = annual.loc[(annual.symbol == ticker) & annual.period.astype(str).eq(str(year + 1))]
        scopes = set(next_rows.scope.dropna().astype(str)) if "scope" in next_rows else set()
        if any(s in {"consolidated", "separate"} for s in scopes):
            # Reference cache has unspecified consolidation; don't imply it
            # can be compared to a verified consolidated/separate statement.
            warnings.append(f"{ticker}: năm {year+1} có phạm vi hợp nhất/riêng xác định, "
                            f"nhưng nguồn {year} chưa rõ phạm vi; cần đối soát trước khi ghép.")
            continue
        # Critical opening balance and top-line must resolve without ambiguity.
        from .analysis import financial_rows
        from .peers import map_sector
        profiles = store.read_json("companies.json", {})
        industries = store.read_json("industry_catalog.json", {}).get("symbols", {})
        sector = map_sector(ticker, profiles.get(ticker, {}), industries.get(ticker, {}))
        row = financial_rows(data, ticker, sector)
        if not row or any(row[0].get(f) is None for f in ("assets", "equity", "revenue")):
            warnings.append(f"{ticker}: cache năm {year} thiếu tài sản, vốn chủ hoặc chỉ tiêu doanh thu phù hợp ngành.")
            continue
        eligible.append(data.drop(columns=["cache_exchange"]))

    if not eligible:
        return {"status": "no_comparable_baseline", "year": str(year), "cache_files": seen_files,
                "added_symbols": [], "added_rows": 0, "missing_symbols": sorted(pending),
                "warnings": warnings, "no_network": True}
    additions = pd.concat(eligible, ignore_index=True)
    from .ingest import validate_financials
    additions = validate_financials(additions)
    added_symbols = sorted(set(additions.symbol))
    summary = {"status": "preview" if dry_run else "complete", "year": str(year),
               "cache_files": seen_files, "added_symbols": added_symbols, "added_rows": int(len(additions)),
               "missing_symbols": sorted(pending - set(added_symbols)), "warnings": warnings,
               "no_network": True, "unchanged_financials": True}
    if not dry_run:
        with store.transaction():
            current_annual = store.read("financials.parquet")
            current_baseline = store.read(BASELINE_FILE)
            current_existing = set(zip(current_annual.symbol.astype(str), current_annual.period.astype(str)))
            if not current_baseline.empty:
                current_existing |= set(zip(current_baseline.symbol.astype(str), current_baseline.period.astype(str)))
            insert = additions.loc[~pd.Series(list(zip(additions.symbol, additions.period)), index=additions.index).isin(current_existing)]
            if not insert.empty:
                combined = pd.concat([current_baseline, insert], ignore_index=True)
                validate_financials(combined)
                store.write(BASELINE_FILE, combined, {
                    "source": "Lịch sử BCTC năm Tumiqa cache - chỉ dùng làm dữ liệu nền",
                    "source_url": "https://github.com/Tumiqa/vn-annual-report-miner",
                    "as_of": str(year), "units": "VND; VND/share",
                    "note": "Nguồn thứ cấp, scope chưa đối soát PDF; không thay thế financials.parquet."
                })
            summary["added_rows"] = int(len(insert))
            summary["added_symbols"] = sorted(set(insert.symbol)) if not insert.empty else []
        report_path = store.path / "logs" / f"annual_baseline_{year}_report.json"
        atomic_json(report_path, {"generated_at": datetime.now(timezone.utc).isoformat(), **summary})
    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bổ sung năm nền từ cache Tumiqa đã có (không dùng Internet).")
    parser.add_argument("--dry-run", action="store_true", help="Xem trước mà không ghi dữ liệu")
    args = parser.parse_args()
    summary = backfill_from_cache(dry_run=args.dry_run)
    print(f"Năm nền: {summary['year']}; thêm {len(summary['added_symbols'])} mã, {summary['added_rows']} dòng.")
    if summary.get("missing_symbols"):
        print("Chưa có năm nền / chưa đồng nhất phạm vi:", ", ".join(summary["missing_symbols"]))
    for warning in summary["warnings"][:30]:
        print(" -", warning)
    print("Không gọi Internet. Giữ nguyên financials.parquet, sample/submission.")
    if not args.dry_run and summary["status"] == "complete":
        print("Chi tiết: data/local/logs/annual_baseline_" + summary['year'] + "_report.json")


if __name__ == "__main__":
    main()
