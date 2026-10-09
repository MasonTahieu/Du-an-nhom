"""Non-destructive, offline one-time import of the frozen submission into local.

The UI uses local as its sole active dataset.  The archived sample/submission
modes remain available for regression tests and reproducibility, but no
synthetic sample rows ever enter local.  Existing local data wins on conflicts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from .storage import Store, atomic_json
from .locking import process_lock
import pandas as pd

MARKER = ".unified-submission-v1.json"


def _join_missing_prices(old, baseline):
    if baseline.empty:
        return old, 0, []
    if old.empty:
        return baseline, len(baseline), []
    if not {"symbol", "date", "price_basis"}.issubset(old.columns):
        raise ValueError("Giá local chưa đủ cột symbol/date/price_basis; không tự hợp nhất.")
    skipped = []
    for sym in baseline.symbol.unique():
        a = set(old.loc[old.symbol == sym, "price_basis"].dropna().astype(str))
        b = set(baseline.loc[baseline.symbol == sym, "price_basis"].dropna().astype(str))
        if a and a != b:
            skipped.append(sym)
    accepted = baseline.loc[~baseline.symbol.isin(skipped)]
    existing = set(zip(old.symbol.astype(str), old.date.astype(str)))
    missing = accepted.loc[
        ~pd.Series(list(zip(accepted.symbol.astype(str), accepted.date.astype(str))), index=accepted.index).isin(existing)
    ]
    if missing.empty:
        return old, 0, skipped
    merged = pd.concat([old, missing], ignore_index=True).sort_values(["symbol", "date"])
    return merged, len(missing), skipped


def _join_missing_years(old, baseline):
    if baseline.empty:
        return old, 0
    if old.empty:
        return baseline, len(baseline)
    if not {"symbol", "period"}.issubset(old.columns):
        raise ValueError("BCTC năm local chưa đủ cột symbol/period; không tự hợp nhất.")
    existing = set(zip(old.symbol.astype(str), old.period.astype(str)))
    missing = baseline.loc[
        ~pd.Series(list(zip(baseline.symbol.astype(str), baseline.period.astype(str))), index=baseline.index).isin(existing)
    ]
    if missing.empty:
        return old, 0
    return pd.concat([old, missing], ignore_index=True).sort_values(["symbol", "period"]), len(missing)


def _merge_records(old, baseline, key):
    if not isinstance(old, list) or not isinstance(baseline, list):
        raise ValueError("Dữ liệu cần là danh sách JSON; không tự ghi đè cấu trúc khác.")
    known = {key(row) for row in old}
    extra = []
    for item in baseline:
        k = key(item)
        if k not in known:
            extra.append(item)
            known.add(k)
    return old + extra, len(extra)


def unify_submission_into_local(local: Store | None = None):
    """Safely and idempotently add missing frozen real data into local once.

    No network access. Existing ticker/date prices and ticker/year financials
    are never replaced. Live local news/indicators/profiles take precedence.
    A marker is written only after all datasets have been processed.
    """
    local = local or Store("local")
    if local.mode != "local":
        raise ValueError("Chỉ cho phép hợp nhất vào data/local.")
    baseline = Store("submission", local.base)
    local.path.mkdir(parents=True, exist_ok=True)
    marker = local.path / MARKER
    with process_lock(local.path / ".ingestion.lock", wait=True):
        if marker.exists():
            return {"status": "already_initialized", "message": "Bộ dữ liệu chung đã được chuẩn bị."}
        if not (baseline.path / "prices.parquet").exists() or not (baseline.path / "financials.parquet").exists():
            raise ValueError("Thiếu dữ liệu thực tế đi kèm tại data/submission; hãy tải đủ source GitHub.")

        stats = {}
        merged, added, skipped = _join_missing_prices(local.read("prices.parquet"), baseline.read("prices.parquet"))
        if added:
            local.write("prices.parquet", merged, {"source": "Hợp nhất dữ liệu đã nạp và bản thực tế cố định; ưu tiên local", "source_url": "see row source", "as_of": str(merged.date.max()), "units": "VND; VNINDEX=index_points", "note": "Không ghi đè phiên đã có; bỏ qua mã khác cơ sở điều chỉnh giá."})
        stats["added_price_rows"] = added
        stats["skipped_price_symbols"] = skipped

        merged, added = _join_missing_years(local.read("financials.parquet"), baseline.read("financials.parquet"))
        if added:
            local.write("financials.parquet", merged, {"source": "Hợp nhất BCTC năm local và bản thực tế cố định; ưu tiên local", "source_url": "see row source_url", "as_of": str(merged.period.max()), "units": "VND; EPS=VND/share", "note": "Không ghi đè toàn bộ mã/năm đã có, không trộn BCTC cùng mã/năm khác phạm vi."})
        stats["added_annual_rows"] = added

        # Add profiles absent in local, never replace user edits.
        live_profiles = local.read_json("companies.json", {})
        source_profiles = baseline.read_json("companies.json", {})
        if not isinstance(live_profiles, dict) or not isinstance(source_profiles, dict):
            raise ValueError("Hồ sơ công ty phải là đối tượng JSON.")
        extra = {k: v for k, v in source_profiles.items() if k not in live_profiles}
        if extra:
            local.write_json("companies.json", {**live_profiles, **extra}, {"source": "Hồ sơ local + dữ liệu đã chốt; ưu tiên local"})
        stats["added_profiles"] = len(extra)

        for filename, key in (
            ("news.json", lambda r: (r.get("symbol"), r.get("url"))),
            ("macro.json", lambda r: (r.get("indicator"), r.get("period"), r.get("basis"))),
        ):
            live = local.read_json(filename, [])
            archived = baseline.read_json(filename, [])
            combined, added = _merge_records(live, archived, key)
            if added:
                local.write_json(filename, combined, {"source": "Dữ liệu local + bản thực tế cố định, ưu tiên bản local", "source_url": "see each row", "note": "Bản thực tế cố định được giữ làm lịch sử; kiểm tra kỳ và ngày công bố."})
            stats["added_" + filename.removesuffix(".json")] = added

        live_reviews = local.read_json("research_reviews.json", {})
        archived_reviews = baseline.read_json("research_reviews.json", {})
        if not isinstance(live_reviews, dict) or not isinstance(archived_reviews, dict):
            raise ValueError("Nhận định đã đối soát phải là đối tượng JSON.")
        extra_reviews = {k: v for k, v in archived_reviews.items() if k not in live_reviews}
        if extra_reviews:
            local.write_json("research_reviews.json", {**live_reviews, **extra_reviews}, {"source": "Nhận định phiên chốt; chỉ áp dụng nếu fingerprint của dữ liệu còn khớp"})
        stats["added_reviews"] = len(extra_reviews)

        record = {"schema_version": 1, "status": "complete", "imported_at": datetime.now(timezone.utc).isoformat(), "from": "data/submission", "to": "data/local", **stats}
        atomic_json(marker, record)
        return record
