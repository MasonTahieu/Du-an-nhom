"""Versioned, deterministic financial mapping and explicit provider repair.

No SDK imports or network calls on analysis. Provider inputs are archived so
normalization can be repeated offline with the same version of the source.
"""
import math
import re
import unicodedata
import pandas as pd

NORMALIZATION_VERSION = 3
STATEMENTS = ("balance_sheet", "income_statement", "cash_flow")
PROVIDERS = {"KBS": "https://kbbuddywts.kbsec.com.vn",
             "VCI": "https://trading.vietcap.com.vn"}
RULES = {
 "balance_sheet": {
  "assets": r"^(tong cong tai san|tong tai san)(\s*\(|\s*[:=]|$)",
  "equity": r"^(von chu so huu|tong von chu so huu|von va cac quy)(\s*\(|\s*[:=]|$)",
  "liabilities": r"^(no phai tra|tong no phai tra)(\s*\(|\s*[:=]|$)",
  "current_assets": r"^(tai san ngan han|tong tai san ngan han)(\s*\(|\s*[:=]|$)",
  "current_liabilities": r"^(no ngan han|tong no ngan han)(\s*\(|\s*[:=]|$)",
  "loans": r"^cho vay khach hang(\s*\(|\s*[:=]|$)",
  "deposits": r"^tien gui cua khach hang(\s*\(|\s*[:=]|$)"},
 "income_statement": {
  "revenue": r"^doanh thu thuan(\s|\(|$)|^doanh so thuan",
  "net_income": r"^(loi nhuan (ke toan )?sau thue|lai/?\(?lo\)? thuan sau thue|lai/?lo sau thue)(\s*\(|\s+(thu nhap doanh nghiep|tndn)|$)",
  "parent_income": r"^loi nhuan sau thue (phan bo cho chu so huu|cua co dong (cua )?(cong ty me|ngan hang me))",
  "securities_revenue": r"^(?:(?:cong|tong|tong cong) )?doanh thu hoat dong(\s*\(|\s*[:=]|$)",
  "operating_income": r"^tong thu nhap hoat dong",
  "net_interest_income": r"^thu nhap lai thuan",
  "operating_expense": r"^chi phi hoat dong(\s*\(|\s*[:=]|$)"},
 "cash_flow": {
  "cfo": r"^(?:luu chuyen (?:tien(?: te)? )?(?:thuan|rong)|tien thuan) (?:tu|trong) (?:cac )?hoat dong (?:san xuat )?kinh doanh"}}


def clean_label(value):
    text = unicodedata.normalize("NFKD", str(value).lower().replace("đ", "d"))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"^\s*(?:(?:\d+(?:\.\d+)*|[a-z]+)[.\-)]\s*|[ivx]+\s+)", "", text)
    return re.sub(r"\s+", " ", text).strip()


# VCI CFO: use the FINAL operating cash-flow total, not an intermediate subtotal.
# Other vendor IDs fall back to an unambiguous final-total label.
_CFO_FINAL_IDS = frozenset({
    "net_cash_from_operating_activities",
    "net_cash_inflows_outflows_from_operating_activities",
})
_CFO_NONFINAL_IDS = frozenset({
    "operating_profit_loss_before_changes_in_working_capital",
    "net_cash_flows_from_operating_activities_before_cit",
})


def canonical_field(label, statement, item_code=""):
    text = clean_label(label)
    if statement == "cash_flow":
        # `normalize_statement` stores item_code as cash_flow/<VCI item_id>/<row>.
        pieces = str(item_code).split("/")
        provider_id = pieces[1].lower() if len(pieces) >= 3 and pieces[0] == "cash_flow" else ""
        if provider_id in _CFO_NONFINAL_IDS or "truoc" in text or "before" in text:
            return ""
        if provider_id in _CFO_FINAL_IDS:
            return "cfo"
        return "cfo" if re.search(RULES["cash_flow"]["cfo"], text) else ""
    return next((k for k, pattern in RULES[statement].items()
                 if re.search(pattern, text)), "")


def resolve_fields(frame):
    """One canonical row per statement/period; equal aliases aren't summed.

    Different values remain ambiguous. A parent equity total can be selected
    only when its report code is 400 and assets minus liabilities confirms it.
    """
    d = frame.copy().reset_index(drop=True)
    if d.empty:
        return d, {}
    d["canonical_field"] = [canonical_field(r.item_name, r.statement, getattr(r, "item_code", ""))
                            for r in d.itertuples()]
    diagnostics = {}
    for (ticker, period, statement), g in d.groupby(["symbol", "period", "statement"], sort=True):
        ambiguous, aliases = [], []
        for field, candidates in g.loc[g.canonical_field != ""].groupby("canonical_field"):
            if len(candidates) < 2:
                continue
            values = candidates.value.astype(float).tolist()
            winner = None
            if all(math.isclose(v, values[0], rel_tol=1e-10, abs_tol=.01) for v in values):
                winner = candidates.index[0]
                aliases.append(field)
            elif field == "equity":
                assets = g.loc[g.canonical_field == "assets", "value"].unique()
                liabilities = g.loc[g.canonical_field == "liabilities", "value"].unique()
                totals = candidates.loc[candidates.item_name.str.contains(r"400\s*=", regex=True)]
                if len(totals) == 1 and len(assets) == len(liabilities) == 1 and math.isclose(
                        float(totals.iloc[0].value), float(assets[0]-liabilities[0]), rel_tol=1e-8, abs_tol=1):
                    winner = totals.index[0]
            d.loc[candidates.index, "canonical_field"] = ""
            if winner is not None:
                d.loc[winner, "canonical_field"] = field
            else:
                ambiguous.append(field)
        diagnostics.setdefault(statement, {})[str(period)] = {
            "ambiguous_fields": sorted(ambiguous), "equal_aliases": sorted(aliases),
            "missing_fields": sorted(set(RULES[statement]) - set(d.loc[g.index, "canonical_field"]))}
    return d, diagnostics


def normalize_statement(raw, ticker, statement, *, period="quarter", provider="KBS"):
    from .collectors import utc
    pattern = r"20\d{2}-Q[1-4]" if period == "quarter" else r"20\d{2}"
    cols = [c for c in raw if re.fullmatch(pattern, str(c))]
    if not cols or not {"item", "item_id"} <= set(raw):
        raise ValueError(f"{ticker}/{statement}: cấu trúc BCTC không hợp lệ.")
    rows, skipped = [], []
    for i, record in enumerate(raw.to_dict("records")):
        if record.get("item_id") in {"audit_status", "unit_type"}:
            continue
        label = clean_label(record["item"])
        if "tren co phieu" in label or "per_share" in str(record["item_id"]):
            skipped.append(str(record["item"]))
            continue
        for col in cols:
            value = pd.to_numeric(record.get(col), errors="coerce")
            if pd.isna(value):
                continue
            if not math.isfinite(float(value)):
                raise ValueError("BCTC chứa số không hữu hạn.")
            scope = raw.attrs.get("unit_type", {}).get(str(col), "")
            rows.append({"symbol": ticker, "period": str(col), "statement": statement,
                "item_code": f"{statement}/{record['item_id']}/{i}", "item_name": str(record["item"]),
                "value": float(value), "unit": "VND",
                "scope": "consolidated" if scope == "Hợp nhất" else "separate" if scope == "Riêng lẻ" else "provider_unspecified",
                "basis": "point_in_time" if statement == "balance_sheet" else "annual" if period == "year" else "provider_period_unspecified",
                "audit_status": str(raw.attrs.get("audit_status", {}).get(str(col), "unknown")),
                "source_url": PROVIDERS[provider], "retrieved_at": utc(),
                "normalization_version": NORMALIZATION_VERSION, "ingestion_origin": "provider_auto"})
    if not rows:
        raise ValueError(f"{ticker}/{statement}: BCTC rỗng.")
    d, diagnostics = resolve_fields(pd.DataFrame(rows))
    periods = diagnostics.get(statement, {})
    return d, {"skipped_per_share": skipped,
               "ambiguous_fields": sorted({f for v in periods.values() for f in v["ambiguous_fields"]}),
               "missing_fields": sorted(set(RULES[statement]) - set(d.canonical_field)),
               "periods": periods, "normalization_version": NORMALIZATION_VERSION}


def suspect_years(frame, ticker):
    """Flag large, entirely identical item sets in adjacent report years."""
    if frame.empty:
        return set()
    d = frame.loc[frame.symbol == ticker]
    by_year = {str(y): g.set_index("item_code").value.sort_index() for y, g in d.groupby("period")}
    suspect = set()
    for year in sorted(by_year):
        previous = str(int(year)-1)
        if previous not in by_year:
            continue
        a, b = by_year[previous], by_year[year]
        if len(a) >= 20 and a.index.equals(b.index) and (a.to_numpy() == b.to_numpy()).all():
            suspect.update([previous, year])
    return suspect


def repair_quarter_cache(store):
    """Replay saved normalized rows; never use an incomplete raw download."""
    with store.transaction():
        old = store.read("financial_quarterly.parquet")
        if old.empty or not {"statement", "item_name", "scope"} <= set(old):
            return {"rows": 0, "status": "complete"}
        updated, diagnostics = resolve_fields(old)
        updated["normalization_version"] = NORMALIZATION_VERSION
        if not old.equals(updated):
            meta = dict(store.manifest().get("files", {}).get("financial_quarterly.parquet", {}))
            # Preserve the original source before a versioned, offline re-mapping.
            # No remote API and no change to raw provider JSON.
            backup = f"backups/quarterly/pre-normalization-v{NORMALIZATION_VERSION}.parquet"
            if not (store.path / backup).exists():
                store.write(backup, old, {"source": "Original quarterly Parquet before normalization v3",
                                          "units": "VND", "normalization_version": 2})
            meta["normalization_version"] = NORMALIZATION_VERSION
            store.write("financial_quarterly.parquet", updated, meta)
        return {"rows": len(updated), "status": "complete", "diagnostics": diagnostics}


def provider_statement(ticker, statement, period, provider):
    from .ingest import _vnstock
    _vnstock()
    if provider == "KBS":
        # Reproduced with vnstock 4.0.8: SSI annual values labelled 2022
        # contain 2025 values; quarter columns are shifted as well. Archived
        # KBS rows remain readable, but cannot be used as a trusted replacement.
        raise ValueError("KBS bị lệch nhãn kỳ trong phiên bản SDK đã kiểm tra; dùng VCI hoặc nhập CSV đối soát.")
    from vnstock.explorer.vci.financial import Finance
    return getattr(Finance(ticker, period=period), statement)(period=period, lang="vi")


def repair_annual_sources(store, tickers, *, first_year=2022, through_year=None, fetch=None, delay=7, progress=print):
    """Replace only automatic upstream years with validated full provider years.

    CSV/manual sources are preserved. Missing years and incomplete mappings
    are repaired by VCI without combining provider report statements. KBS
    is excluded until its period alignment has been independently verified.
    """
    import json
    import time
    from .storage import symbol
    from .ingest import validate_financials
    from .collectors import utc, REFERENCE
    from .analysis import financial_rows
    from .peers import map_sector
    from .financial_policy import required_missing
    fetch = fetch or provider_statement
    from datetime import datetime, timezone
    last_year = int(through_year) if through_year is not None else datetime.now(timezone.utc).year - 1
    first_year = int(first_year)
    if not 2000 <= first_year <= last_year <= 2100:
        raise ValueError("Khoảng năm BCTC không hợp lệ.")
    result = {"results": [], "failed": [], "status": "complete"}
    for ticker in dict.fromkeys(symbol(t) for t in tickers):
        old = store.read("financials.parquet")
        profiles = store.read_json("companies.json", {})
        sector = map_sector(ticker, profiles.get(ticker, {}), store.read_json("industry_catalog.json", {}).get("symbols", {}).get(ticker, {}))
        rows = financial_rows(old, ticker, sector)
        suspects = suspect_years(old, ticker)
        def automatic(g):
            if "ingestion_origin" in g and g.ingestion_origin.fillna("").eq("manual_csv").any():
                return False
            return (g.source_url.fillna("").str.startswith(REFERENCE).all() or
                    ("ingestion_origin" in g and g.ingestion_origin.fillna("").eq("provider_auto").all()))
        broken = {r["period"] for r in rows if r["period"] in suspects or bool(required_missing(r, sector))}
        # A duplicated extraction year calls the entire automatically mined
        # series into question, including wrongly selected cash-flow lines.
        if suspects:
            broken.update(str(y) for y, g in old.loc[old.symbol == ticker].groupby("period") if automatic(g))
        missing_years = {str(y) for y in range(int(first_year), last_year+1)} - {r["period"] for r in rows}
        # No need to refresh valid, current stored data during ordinary loads.
        if rows and not broken and not missing_years:
            result["results"].append({"symbol": ticker, "status": "cached", "years": []})
            continue
        protected = set()
        if not old.empty:
            for year in broken:
                g = old.loc[(old.symbol == ticker) & (old.period.astype(str) == year)]
                if not automatic(g):
                    protected.add(year)
        if protected and protected == broken and rows and not missing_years:
            result["failed"].append({"symbol": ticker, "error": "Các năm thiếu dữ liệu thuộc nguồn đã nhập; giữ nguyên, cần bổ sung CSV đối soát: " + ", ".join(sorted(protected))})
            continue
        errors, added, limited = [], [], False
        for provider in ("VCI",):
            progress(f"{ticker}: BCTC năm từ {provider}.")
            try:
                frames = []
                for statement in STATEMENTS:
                    raw = fetch(ticker, statement, "year", provider)
                    if raw is None or raw.empty:
                        raise ValueError(f"{provider}/{statement}: không có dữ liệu.")
                    store.write_json(f"raw/financials/{ticker}/{provider}/year/{statement}.json",
                        {"rows": json.loads(raw.to_json(orient="records", force_ascii=False)), "attrs": raw.attrs, "retrieved_at": utc()},
                        {"source": provider, "source_url": PROVIDERS[provider], "units": "SDK monetary values in VND"})
                    normalized, _ = normalize_statement(raw, ticker, statement, period="year", provider=provider)
                    frames.append(normalized)
                    if delay: time.sleep(delay)
                incoming = pd.concat(frames, ignore_index=True)
                # Canonical codes are the same on every machine/provider. Other
                # provider rows retain stable original IDs for traceability.
                incoming["provider_item_code"] = incoming.item_code
                mapped = incoming.canonical_field != ""
                incoming.loc[mapped, "item_code"] = incoming.loc[mapped, "canonical_field"]
                incoming = validate_financials(incoming)
                duplicated = suspect_years(incoming, ticker)
                validated = financial_rows(incoming, ticker, sector)
                good = {r["period"] for r in validated if first_year <= int(r["period"]) <= last_year and r["period"] not in duplicated
                        and not required_missing(r, sector) and r.get("liabilities") is not None
                        and math.isclose(r["assets"] - r["liabilities"], r["equity"], rel_tol=1e-6, abs_tol=1)}
                good &= {str(y) for y, g in incoming.groupby("period") if set(g.statement) == set(STATEMENTS)}
                with store.transaction():
                    current = store.read("financials.parquet")
                    eligible = set()
                    for year in good:
                        existing = current.loc[(current.symbol == ticker) & (current.period.astype(str) == year)] if not current.empty else current
                        if existing.empty or (year in broken and automatic(existing)):
                            eligible.add(year)
                    if eligible:
                        replaced = current.loc[(current.symbol == ticker) & current.period.astype(str).isin(eligible)] if not current.empty else current
                        if not replaced.empty:
                            store.write(f"backups/annual/{ticker}-{provider}.parquet", replaced, {"source": "Original annual rows before provider repair"})
                        keep = current.loc[~((current.symbol == ticker) & current.period.astype(str).isin(eligible))] if not current.empty else current
                        merged = pd.concat([keep, incoming.loc[incoming.period.isin(eligible)]], ignore_index=True)
                        validate_financials(merged)
                        store.write("financials.parquet", merged, {"source": "Annual financial statements; see source_url per row", "units": "VND", "normalization_version": NORMALIZATION_VERSION,
                            "note": "Nguồn tổng hợp và nguồn dự phòng; giữ dữ liệu nhập thủ công. Chưa đối soát PDF kiểm toán."})
                        added.extend(sorted(eligible))
                remaining = (broken | missing_years) - set(added)
                if added and not remaining:
                    break
                errors.append(f"{provider}: không đủ năm/chỉ tiêu để thay thế {', '.join(sorted(remaining)) or ticker}.")
            except SystemExit:
                limited = True
                errors.append(f"{provider}: giới hạn API; chạy lại sau khi hết hạn mức.")
                break
            except Exception as exc:
                errors.append(f"{provider}: {str(exc)[:300]}")
        result["results"].append({"symbol": ticker, "years": sorted(set(added)), "errors": errors})
        if ((broken | missing_years) - set(added)) or (not rows and not added):
            result["failed"].append({"symbol": ticker, "error": "; ".join(errors) or "Chưa có nguồn đủ chỉ tiêu."})
        if limited:
            result["status"] = "rate_limited"
            break
    if result["status"] != "rate_limited":
        result["status"] = "partial" if result["failed"] else "complete"
    store.write_json("annual-repair-run.json", result, {"source": "Annual provider repair diagnostics"})
    return result
