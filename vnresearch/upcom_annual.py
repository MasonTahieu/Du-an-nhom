"""VCI annual fallback for UPCoM using the vnstock dependency already present.

No network on import/report generation. Three statements are committed together,
and saved/manual years are NEVER overwritten. Missing/ambiguous data is explicit.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math
import re
import pandas as pd

from .storage import Store, symbol
from .ingest import validate_financials

VCI_URL = "https://trading.vietcap.com.vn"
STATEMENTS = ("balance_sheet", "income_statement", "cash_flow")
# The source's labels are matched conservatively; EPS/share is deliberately ignored.
LABEL_RULES = {
    "balance_sheet": {
        "assets": r"^(tong cong tai san|tong tai san)(\s|\(|$)",
        "liabilities": r"^(tong no phai tra|no phai tra)(\s|\(|$)",
        "equity": r"^(tong von chu so huu|von chu so huu)(\s|\(|$)",
        "current_assets": r"^(tong tai san ngan han|tai san ngan han)(\s|\(|$)",
        "current_liabilities": r"^(tong no ngan han|no ngan han)(\s|\(|$)",
    },
    "income_statement": {
        "revenue": r"^(doanh thu thuan|doanh so thuan)(\s|\(|$)",
        "securities_revenue": r"^doanh thu hoat dong(\s|\(|$)",
        "operating_income": r"^tong thu nhap hoat dong(\s|\(|$)",
        "net_income": r"^(loi nhuan sau thue|loi nhuan ke toan sau thue|lai lo thuan sau thue)(\s|\(|$)",
        "parent_income": r"^loi nhuan sau thue (cua|phan bo cho) (co dong|chu so huu)",
    },
    "cash_flow": {
        "cfo": r"^luu chuyen (tien )?thuan (tu|trong) (cac )?hoat dong (san xuat )?kinh doanh(?!.*truoc thue)"
    }
}


def _fetch(ticker, statement):
    from .ingest import _vnstock
    _vnstock()
    from vnstock.explorer.vci.financial import Finance
    return getattr(Finance(ticker, period="year"), statement)(period="year", lang="vi")


def _normalize(raw, ticker, statement):
    from .newsfeed import fold
    if not isinstance(raw, pd.DataFrame) or raw.empty or not {"item", "item_id"} <= set(raw.columns):
        raise ValueError(f"VCI/{ticker}/{statement}: thiếu trường item/item_id hoặc bảng rỗng.")
    years = [c for c in raw if re.fullmatch(r"20\d{2}", str(c))]
    if not years:
        raise ValueError(f"VCI/{ticker}/{statement}: không có cột năm YYYY (nguồn có thể đổi cấu trúc).")
    records = []
    for row in raw.to_dict("records"):
        label = re.sub(r"\s+", " ", fold(row.get("item", ""))).strip()
        label = re.sub(r"^(?:(?:[ivx]+|[0-9]+(?:\.[0-9]+)*)[.\-)]?\s+)", "", label)
        if "tren co phieu" in label or "per_share" in str(row.get("item_id", "")):
            continue
        matched = [key for key, pat in LABEL_RULES[statement].items() if re.search(pat,label)]
        if "parent_income" in matched and "net_income" in matched:
            matched.remove("net_income")  # Prefer specific attribution over general PAT.
        if len(matched) != 1:
            continue
        for year in years:
            v = pd.to_numeric(row.get(year), errors="coerce")
            if pd.notna(v) and math.isfinite(float(v)):
                scope = raw.attrs.get("unit_type",{}).get(year,"")
                scope = "consolidated" if scope == "Hợp nhất" else "separate" if scope == "Riêng lẻ" else "provider_unspecified"
                records.append({"symbol":ticker,"period":str(year),"item_code":matched[0],
                    "value":float(v),"unit":"VND","scope":scope,"statement":statement,
                    "source_url":VCI_URL,"item_name":str(row.get("item","")),
                    "retrieved_at":datetime.now(timezone.utc).isoformat(),"ingestion_origin":"provider_auto",
                    "audit_status":"unverified"})
    if not records:
        raise ValueError(f"VCI/{ticker}/{statement}: không ánh xạ được chỉ tiêu phù hợp.")
    frame = pd.DataFrame(records)
    # Ambiguous values are not silently picked; reject that year rather than
    # taking an arbitrary income/equity value.
    dup=frame.duplicated(["period","item_code"],keep=False)
    if dup.any():
        ambiguous=set(frame.loc[dup,"period"])
        frame=frame.loc[~frame.period.isin(ambiguous)]
    if frame.empty:
        raise ValueError(f"VCI/{ticker}/{statement}: nhãn chỉ tiêu trùng/không nhất quán.")
    return frame


def fetch_annual_vci(store: Store, ticker, *, first_year=2022, fetch=None):
    """Try all 3 VCI statements; write ONLY complete new years to local.

    Returns status 'partial' with reason when the provider changes its API or
    lacks enough rows; previous financials.parquet is never deleted.
    """
    ticker=symbol(ticker)
    # Valid current saved years are reused on reruns, including manual input.
    from .analysis import financial_rows
    from .financial_policy import required_missing
    from .peers import map_sector
    old=store.read("financials.parquet")
    profile=store.read_json("companies.json",{}).get(ticker,{})
    industry=store.read_json("industry_catalog.json",{}).get("symbols",{}).get(ticker,{})
    sector=map_sector(ticker,profile,industry)
    rows=financial_rows(old,ticker,sector)
    expected={str(year) for year in range(int(first_year),datetime.now(timezone.utc).year)}
    valid={r["period"] for r in rows if not required_missing(r,sector)
           and r.get("liabilities") is not None
           and math.isclose(r["assets"]-r["liabilities"],r["equity"],rel_tol=1e-5,abs_tol=1)}
    if expected and expected <= valid:
        return {"status":"complete", "source":"local_cache", "added_years":[],
                "cached_years":sorted(valid), "available_years":sorted(valid)}
    fetch=fetch or _fetch
    frames=[]
    try:
        for index, statement in enumerate(STATEMENTS):
            if index and fetch is _fetch:
                # Respect typical free SDK limits; tests using an injected
                # fetcher remain instantaneous.
                import time
                time.sleep(5)
            frames.append(_normalize(fetch(ticker,statement),ticker,statement))
    except (Exception,SystemExit) as exc:
        return {"status":"rate_limited" if isinstance(exc,SystemExit) else "partial","failed":[{"symbol":ticker,"error":
            f"VCI chưa cung cấp đủ BCTC năm hoặc đã đổi cấu trúc ({type(exc).__name__}: {exc}). Giữ dữ liệu cũ."}]}
    combined=pd.concat(frames,ignore_index=True)
    good=[]
    for year,g in combined.groupby("period"):
        if int(year)<int(first_year) or set(g.statement)!=set(STATEMENTS) or g.scope.nunique()!=1: continue
        values=dict(zip(g.item_code,g.value))
        required=("assets","liabilities","equity","net_income")
        if not all(k in values for k in required): continue
        if not any(k in values for k in ("revenue","securities_revenue","operating_income")): continue
        if not math.isclose(values["assets"]-values["liabilities"],values["equity"],rel_tol=1e-5,abs_tol=1): continue
        good.append(year)
    if not good:
        return {"status":"partial","failed":[{"symbol":ticker,"error":
            "VCI trả dữ liệu nhưng thiếu bảng/chỉ tiêu hoặc không cân đối được tài sản - nợ - vốn; chưa ghi vào BCTC năm."}]}
    old=store.read("financials.parquet")
    existing=set(old.loc[old.symbol==ticker,"period"].astype(str)) if not old.empty else set()
    insert=combined.loc[combined.period.isin(set(good)-existing)].drop(columns=["statement"])
    if not insert.empty:
        merged=pd.concat([old,validate_financials(insert)],ignore_index=True)
        validate_financials(merged)
        store.write("financials.parquet",merged,{"source":"BCTC năm Tumiqa/VCI theo từng dòng","source_url":VCI_URL,
            "as_of":str(merged.period.max()),"units":"VND", "note":"VCI hỗ trợ UPCoM khi nguồn có dữ liệu; không thay các năm đã lưu. BCTC chưa đối soát PDF kiểm toán."})
    return {"status":"complete","added_years":sorted(set(good)-existing),"available_years":sorted(good),
            "source": "VCI annual via vnstock","cached_years":sorted(existing)}
