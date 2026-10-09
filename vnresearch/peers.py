"""Cautious, local-first peer discovery. No network while viewing a stock or creating PDFs.

A user-triggered load may refresh vnstock Community industry data. Curated
stock-to-sector mappings provide a conservative offline fallback. Candidate
selection does not manufacture missing financial statements or price multiples.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re
import statistics
import unicodedata

import pandas as pd
from .storage import ROOT, Store, symbol

INDUSTRY_FILE = "industry_catalog.json"
PREFERRED = {
    "securities": ["HCM", "VND", "VCI", "BSI", "VIX", "SSI", "MBS", "SHS", "CTS", "DSE", "BVS", "AGR", "ORS", "APG"],
    "bank": ["VCB", "CTG", "BID", "MBB", "TCB", "ACB", "VPB", "STB", "TPB", "LPB", "MSB"],
    "steel": ["HPG", "HSG", "NKG"],
    "technology": ["FPT", "ELC"],
    "real_estate": ["VHM", "NLG", "KDH", "VIC"],
    "retail": ["MWG", "FRT", "PNJ"],
    "energy": ["POW", "REE", "PC1"],
    "oil_gas": ["GAS", "PVS", "PVD"],
    "telecom": ["FOX", "MFS", "TTN", "CTR", "VGI"],
}
URL = "https://vnstocks.com/docs/vnstock/tra-cuu-thong-tin-tham-chieu-reference"


def _fold(value):
    s = unicodedata.normalize("NFKD", str(value or "").lower().replace("đ", "d"))
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def map_sector(ticker, profile=None, industry=None):
    from .newsfeed import sector_for_ticker
    existing = sector_for_ticker(ticker, profile)
    if existing != "other":
        return existing
    label = _fold((industry or {}).get("industry_name", ""))
    # Conservative matches for the finance subsectors; others remain unknown.
    if "chung khoan" in label or "securities" in label or "investment services" in label:
        return "securities"
    if "ngan hang" in label or "banks" in label or "banking" in label:
        return "bank"
    if "san xuat thep" in label or "steel" in label:
        return "steel"
    if any(term in label for term in ("vien thong", "telecommunication", "telecom", "wireless", "mobile telecom", "internet service")):
        return "telecom"
    return "other"


def normalize_industry(raw):
    """Accept common vnstock industry table column variants, keeping most detailed ICB row."""
    if raw is None or not isinstance(raw, pd.DataFrame) or raw.empty:
        raise ValueError("Nguồn ICB trả bảng rỗng.")
    aliases = {
        "symbol": ("symbol", "ticker", "stock_code", "stock_symbol"),
        "industry_code": ("icb_code4", "icb_code", "industry_code", "icb_code3"),
        "industry_name": ("icb_name4", "icb_name", "industry_name", "industry"),
        "industry_level": ("icb_level", "level"),
    }
    def pick(row, keys):
        return next((row[k] for k in keys if k in row and pd.notna(row[k]) and str(row[k]).strip()), None)
    result = {}
    for record in raw.to_dict("records"):
        t = str(pick(record, aliases["symbol"]) or "").upper().strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9]{2}", t):
            continue
        code = str(pick(record, aliases["industry_code"]) or "").strip()
        name = str(pick(record, aliases["industry_name"]) or "").strip()
        level = pick(record, aliases["industry_level"])
        try: level = int(level) if level is not None else (4 if len(code) >= 4 else 0)
        except (TypeError, ValueError): level = 0
        if not code and not name:
            continue
        if code.lower() in {"nan", "none"}: code = ""
        candidate = {"industry_code": code, "industry_name": name, "industry_level": level}
        current = result.get(t)
        if current is None or (level, len(code)) > (current["industry_level"], len(current["industry_code"])):
            result[t] = candidate
    if not result:
        raise ValueError("Nguồn ICB thiếu mã cổ phiếu hoặc cột phân ngành.")
    return result


def refresh_industry_catalog(store: Store, *, fetch=None, max_age_days=7):
    """Only called during explicit ticker ingestion; failures keep existing cache."""
    old = store.read_json(INDUSTRY_FILE, {})
    last = old.get("retrieved_at", "")
    if isinstance(old.get("symbols"), dict) and old["symbols"] and last:
        try:
            if datetime.now(timezone.utc) - datetime.fromisoformat(last.replace("Z", "+00:00")) < timedelta(days=max_age_days):
                return {"status": "complete", "cached": True, "symbols": len(old["symbols"])}
        except ValueError:
            pass
    try:
        if fetch is None:
            from .ingest import _vnstock
            _, Reference = _vnstock()
            # Documented in the Community edition; no paid vnstock_data required.
            fetch = lambda: Reference().equity.list_by_industry()
        rows = normalize_industry(fetch())
        if len(rows) < 3:
            raise ValueError("Danh mục ICB quá ít mã; không ghi đè cache trước đó.")
        store.write_json(INDUSTRY_FILE, {"symbols": rows, "source_url": URL,
                         "source": "vnstock Reference.equity.list_by_industry (Community)",
                         "retrieved_at": datetime.now(timezone.utc).isoformat()},
                         {"source": "vnstock Community ICB metadata", "source_url": URL})
        return {"status": "complete", "cached": False, "symbols": len(rows)}
    except (Exception, SystemExit) as exc:
        # A missing/blocked source should not block prices or annual reports.
        return {"status": "partial", "failed": [{"error": str(exc)[:220]}],
                "cached": bool(old.get("symbols")), "note": "Không lấy được ICB; dùng phân ngành đã lưu hoặc danh sách tham khảo."}


def suggest(store: Store, ticker, *, profiles=None, limit=5):
    """Deterministically choose up to five same-sector peers; never infer by RSS headlines."""
    ticker = symbol(ticker)
    profiles = profiles if profiles is not None else store.read_json("companies.json", {})
    profile = profiles.get(ticker, {})
    cached = store.read_json(INDUSTRY_FILE, {}).get("symbols", {})
    ref = json.loads((ROOT / "config/company_sectors.json").read_text(encoding="utf-8"))["symbols"]
    universe = {r.get("symbol") for r in store.read_json("universe.json", {}).get("symbols", [])}
    icb = cached.get(ticker, {})
    sector = map_sector(ticker, profile, icb)
    code = icb.get("industry_code", "")
    sector_source = "ICB đã lưu" if code else "hồ sơ/ánh xạ tham khảo"
    if sector == "other" and not code and not profile.get("peers"):
        return {"sector": sector, "sector_source": "Chưa có phân ngành đáng tin cậy",
                "industry_name": "", "industry_code": "", "candidates": [], "peers": [],
                "note": "Không tự ghép đối thủ: chưa biết phân ngành; hãy nạp lại mã khi có ICB hoặc cấu hình ngành."}
    # Base candidate pool is the local ICB map, verified local profiles, and
    # explicit curated map; do not infer peers merely from article mentions.
    candidates = set(cached) | set(ref) | set(profiles)
    ranked = []
    preferred = PREFERRED.get(sector, [])
    catalogue = {r.get("symbol"):r.get("exchange") for r in store.read_json("universe.json", {}).get("symbols", [])}
    original = [symbol(t) for t in profile.get("peers", []) if isinstance(t, str) and re.fullmatch(r"[A-Z][A-Z0-9]{2}", t.upper())]
    for t in candidates | set(original):
        if t == ticker or not re.fullmatch(r"[A-Z][A-Z0-9]{2}", t): continue
        cinfo = cached.get(t, {})
        ccode = cinfo.get("industry_code", "")
        t_sector = map_sector(t, profiles.get(t), cinfo)
        exact_icb = bool(code and ccode and code == ccode)
        if code:
            # Same detailed ICB always wins. For telecom only, supplement the
            # often fragmented ICB categories with explicit curated peers;
            # mark them provisional, never report as exact industry matches.
            if not exact_icb and not (sector == "telecom" and t_sector == "telecom"):
                continue
        elif sector == "other" or t_sector != sector:
            continue
        # Do not exclude UPCoM: the candidate list is not a promise of annual
        # financial coverage. Annuals are checked separately by the loader.
        # exact ICB > explicit peer > same curated sector; do not mistake a list
        # of industry candidates for a verified business-model match.
        score = (3 if exact_icb else 2 if t in original else 1)
        ranked.append(((-score, original.index(t) if t in original else 999, preferred.index(t) if t in preferred else 999, t), t,
                       "ICB cùng mã ngành" if exact_icb else "Được cấu hình" if t in original else "Ngành tham khảo (khác phân ngành chi tiết)" if code else "Ngành tham khảo"))
    ranked.sort(key=lambda x:x[0])
    selected = [{"symbol":t,"reason":reason} for _,t,reason in ranked[:max(0,min(5,int(limit)))]]
    return {"sector":sector,"sector_source":sector_source,"industry_name":icb.get("industry_name", ""),
            "industry_code":code,"candidates":selected,"peers":[r["symbol"] for r in selected],
            "note": ("Chỉ có " + str(len(selected)) + " mã ứng viên phù hợp đã biết; không thêm mã khác ngành." if len(selected)<3 else
                     "Đây là danh sách ứng viên theo ngành; các mô hình kinh doanh và BCTC cần được đối soát riêng.")}


def compare(facts, prices, ticker, selected, year, financial_rows, sector):
    """Build comparable annual rows, with missing candidates explicit and medians computed only from real values."""
    entries = [ticker] + [x for x in selected.get("peers", []) if x != ticker]
    label = {r["symbol"]:r["reason"] for r in selected.get("candidates", [])}
    out = []
    for t in entries:
        rows = financial_rows(facts, t, sector)
        row = next((r for r in rows if r["period"] == year), None)
        keys = ["revenue", "net_income", "assets", "equity", "roe", "roa", "profit_growth", "revenue_growth", "net_margin", "debt_assets", "cir"]
        rec = {"symbol":t,"period":year,"basis":"annual", "reason":label.get(t,"Đang phân tích"),
               **{k:row.get(k) if row else None for k in keys},
               "financial_available":row is not None,"price_available":False,"pb":None,"pe":None}
        if not prices.empty and "symbol" in prices.columns and (prices.symbol==t).any():
            rec["price_available"] = True
        # P/B and P/E intentionally blank. Share-count at *the same date* and
        # adjustments must be audited before computing market cap / BVPS.
        out.append(rec)
    medians={}
    for key in ["roe","roa","profit_growth","revenue_growth","net_margin","debt_assets"]:
        values = [r[key] for r in out[1:] if r[key] is not None]
        medians[key] = float(statistics.median(values)) if values else None
    ranks={}
    for key in ["roe","roa","profit_growth"]:
        values = [r for r in out if r.get(key) is not None]
        sorted_ = sorted(values, key=lambda r:(-r[key],r["symbol"]))
        ranks[key] = next((i+1 for i,r in enumerate(sorted_) if r["symbol"]==ticker),None)
    return out, {"period":year, "peer_count":len(out)-1,
                 "peers_with_financials":sum(r["financial_available"] for r in out[1:]),
                 "medians":medians,"ranks":ranks,
                 "note":selected.get("note", ""),"source":selected.get("sector_source", ""),
                 "industry_name":selected.get("industry_name", ""),
                 "valuation_note":"P/B và P/E chưa tự tính: cần số cổ phiếu lưu hành cùng thời điểm, kiểm tra chia tách/phát hành và giá so sánh tương ứng."}


def explain(result, summary, ticker, fmt):
    if not result:
        return ["Chưa có mã cùng ngành được xác minh; cần bổ sung phân ngành trước khi so sánh."]
    notes=[f"Đề xuất {summary['peer_count']} mã đối chiếu, có {summary['peers_with_financials']} mã đủ BCTC năm {summary['period']}. {summary['note']}"]
    first = result[0]
    for key,label in [("roe","ROE"),("roa","ROA"),("profit_growth","Tăng trưởng LNST")]:
        value,median=first.get(key),summary["medians"].get(key)
        if value is not None and median is not None:
            delta = (value-median)*100
            rank=summary["ranks"].get(key)
            notes.append(f"{label} {ticker}: {fmt(value,'percent')}; trung vị nhóm {fmt(median,'percent')}; chênh lệch {fmt(delta)} điểm %."+
                         (f" Xếp thứ {rank}/{1+sum(r.get(key) is not None for r in result[1:])} trong các mã đủ chỉ tiêu." if rank else ""))
    if len(notes)==1:
        notes.append("Chưa đủ dữ liệu cùng kỳ để tính trung vị ROE/ROA hoặc tăng trưởng lợi nhuận. Không suy ra chỉ số giả.")
    notes.append(summary["valuation_note"])
    return notes
