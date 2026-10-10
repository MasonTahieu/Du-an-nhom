"""Deterministic explanations tied to stored evidence; no external API or model calls."""
import statistics
import pandas as pd

from .financial_policy import accounting_model, required_missing, missing_statements, top_line


def quarterly_rows(frame, ticker, sector="other"):
    """Read-only quarterly coverage; a present quarter is not necessarily complete.

    The source has not established whether income/cash figures are standalone
    quarter values or cumulative YTD, so we never derive YoY/TTM here.
    """
    if frame.empty or "symbol" not in frame or "period" not in frame:
        return []
    d = frame.loc[frame.symbol == ticker]
    if d.empty:
        return []
    # Read-only fallback for old v2 caches. Avoid silently hiding mapped totals
    # just because the user has not yet run the optional offline migration.
    if {"statement", "item_name", "item_code"} <= set(d.columns):
        from .financials import NORMALIZATION_VERSION, resolve_fields
        legacy = ("canonical_field" not in d or
                  d["canonical_field"].fillna("").eq("").all() or
                  ("normalization_version" in d and
                   pd.to_numeric(d["normalization_version"], errors="coerce").fillna(0).lt(NORMALIZATION_VERSION).any()))
        if legacy:
            d, _ = resolve_fields(d)
    result = []
    for period, g in d.groupby("period", sort=True):
        fields = {}
        if "canonical_field" in g:
            named = g.loc[g.canonical_field.fillna("") != ""]
            for field, items in named.groupby("canonical_field"):
                # Conflicting aliases must be resolved by the mapper, not guessed here.
                if len(items) == 1:
                    r = items.iloc[0]
                    fields[field] = {"value": float(r.value), "basis": r.basis,
                                     "scope": r.scope, "item_name": r.item_name,
                                     "source_url": r.source_url}
        present = sorted(set(g.statement.astype(str))) if "statement" in g else []
        absent_reports = missing_statements(present)
        missing_fields = required_missing(fields, sector)
        line_field, _ = top_line(fields, sector)
        result.append({"period": str(period), "fields": fields,
                       "accounting_model": accounting_model(sector),
                       "top_line_field": line_field,
                       "statements_present": present, "missing_statements": absent_reports,
                       "missing_fields": missing_fields,
                       "coverage_status": "partial" if (absent_reports or missing_fields) else "complete",
                       "note": "Tài sản/nợ/vốn tại thời điểm báo cáo. KQKD và dòng tiền theo kỳ nguồn; chưa xác minh riêng quý/lũy kế. Không tính TTM hoặc ROE quý."})
    return result

def latest_macro(records):
    latest={}
    for record in sorted(records,key=lambda r:(str(r.get("published_at","")),str(r.get("retrieved_at","")))):
        r=dict(record)
        if r.get("indicator")=="cpi_yoy" and "bình quân" in r.get("label", "").lower():
            r["indicator"]="cpi_average_yoy"
        latest[r["indicator"]]=r
    return list(latest.values())

def explain_macro(records, sector, fmt):
    latest={}
    for r in sorted(records,key=lambda r:str(r.get("published_at",""))):
        latest[r["indicator"]]=r
    notes=[]
    for key in ["gdp_yoy","cpi_average_yoy","cpi_yoy","iip_yoy","credit_ytd","fdi_disbursed"]:
        r=latest.get(key)
        if not r: continue
        value=float(r["value"])
        evidence=f"{r['label']} {r['period']}: {fmt(value)} {r['unit']} ({r['basis']})."
        if key=="gdp_yoy":
            implication="Nền kinh tế mở rộng, tạo bối cảnh hỗ trợ nhu cầu; chưa đủ để suy ra tăng trưởng của riêng doanh nghiệp." if value>0 else "Hoạt động kinh tế chưa tăng trưởng; cần thận trọng với giả định nhu cầu."
        elif key.startswith("cpi"):
            implication="Cần đối chiếu lãi suất và chi phí đầu vào để đánh giá sức ép lên biên lợi nhuận; một kỳ CPI chưa xác lập xu hướng lạm phát."
        elif key=="credit_ytd":
            implication="Cần so sánh tăng trưởng cho vay của ngân hàng với mức toàn hệ thống và chất lượng tín dụng." if sector=="bank" else "Đây là bối cảnh nguồn vốn toàn nền kinh tế; chưa phản ánh chi phí vay của doanh nghiệp."
        elif key=="iip_yoy":
            implication=(("Sản xuất công nghiệp mở rộng" if value>0 else "Sản xuất công nghiệp thu hẹp")+"; với ngành thép cần kiểm tra thêm sản lượng bán, tồn kho và giá nguyên liệu.") if sector=="steel" else "Chỉ tiêu bổ sung bối cảnh hoạt động sản xuất; cần dữ liệu ngành trực tiếp để kết luận."
        else:
            implication="Giải ngân FDI là bối cảnh đầu tư; chưa chứng minh doanh nghiệp có đơn hàng hoặc doanh thu từ dòng vốn này."
        notes.append({"text":evidence+" "+implication,"source_url":r["source_url"],"period":r["period"]})
    return notes

def explain_peers(peers,ticker,fmt):
    current=next((p for p in peers if p["symbol"]==ticker),None)
    others=[p for p in peers if p["symbol"]!=ticker]
    if not current or not others:
        return ["Chưa có doanh nghiệp đối chiếu cùng kỳ. Cấu hình peers và chạy nạp BCTC để bổ sung."]
    notes=[]
    for field,label in [("roe","ROE"),("roa","ROA")]:
        values=[p[field] for p in others if p.get(field) is not None]
        if values and current.get(field) is not None:
            median=statistics.median(values)
            delta=current[field]-median
            notes.append(f"{label} {current['period']} của {ticker}: {fmt(current[field],'percent')}; trung vị {len(values)} doanh nghiệp đối chiếu: {fmt(median,'percent')}, chênh lệch {fmt(delta*100)} điểm phần trăm.")
    notes.append("Nhóm đối chiếu do người dùng chọn, không đại diện toàn ngành; cần kiểm tra cùng phạm vi báo cáo và năm tài chính.")
    return notes

def conclusion(latest,market,valuation):
    if not latest or market.get("rows",0)<21:
        return "CHƯA ĐỦ DỮ LIỆU — cần BCTC và ít nhất 21 phiên giá để đánh giá đồng thời."
    profit=latest.get("net_income")
    growth=latest.get("profit_growth")
    if profit is not None and profit<0:
        text="CẦN THẬN TRỌNG — doanh nghiệp ghi nhận lỗ trong năm gần nhất."
    elif growth is not None and growth<0:
        text="CẦN THẬN TRỌNG — lợi nhuận năm gần nhất giảm so với năm trước."
    elif growth is not None and growth>0 and (market.get("return_20") or 0)>0:
        text="CÓ ĐIỂM TÍCH CỰC — lợi nhuận năm tăng và giá 20 phiên tăng; cần kiểm tra tính bền vững."
    else:
        text="TIẾP TỤC THEO DÕI — bằng chứng tài chính và diễn biến giá chưa đồng thuận rõ."
    # No target-price or scenario conclusion in the research-only UI/PDF.
    return text
