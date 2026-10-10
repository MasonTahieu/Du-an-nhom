"""Transparent calculations, evidence and bounded conclusions; no model calls."""
from __future__ import annotations
import math
from datetime import date
import pandas as pd

from .storage import ROOT, Store, symbol
from .financial_policy import accounting_model, required_missing, top_line

FIELDS = {
    "assets": ["bs_tong_tai_san", "bs_tong_cong_tai_san"],
    "equity": ["bs_von_chu_so_huu_4d280b22", "bs_von_chu_so_huu_6cda78ae", "bs_von_chu_so_huu", "bs_tong_von_chu_so_huu", "bs_von_va_cac_quy"],
    "liabilities": ["bs_no_phai_tra", "bs_tong_no_phai_tra"],
    "current_assets": ["bs_tai_san_ngan_han", "bs_tong_tai_san_ngan_han"],
    "current_liabilities": ["bs_no_ngan_han", "bs_tong_no_ngan_han"],
    "revenue": ["is_doanh_so_thuan", "is_doanh_thu_thuan", "is_doanh_thu_thuan_ve_hoat_dong_kinh_doanh"],
    "securities_revenue": ["is_doanh_thu_hoat_dong", "is_cong_doanh_thu_hoat_dong"],
    "net_income": ["is_loi_nhuan_sau_thue_thu_nhap_doanh_nghiep", "is_lai_lo_thuan_sau_thue", "is_loi_nhuan_ke_toan_sau_thue", "is_loi_nhuan_sau_thue"],
    "parent_income": ["is_loi_nhuan_cua_co_dong_cua_cong_ty_me", "is_loi_nhuan_sau_thue_cua_co_dong_cong_ty_me", "is_co_dong_cua_cong_ty_me"],
    "cfo": ["cf_luu_chuyen_tien_thuan_tu_cac_hoat_dong_san_xuat_kinh_doanh", "cf_luu_chuyen_tien_thuan_tu_hoat_dong_kinh_doanh"],
    "eps": ["is_lai_co_ban_tren_co_phieu"],
    "net_interest_income": ["is_thu_nhap_lai_thuan"],
    "operating_income": ["is_tong_thu_nhap_hoat_dong"],
    "operating_expense": ["is_chi_phi_hoat_dong", "is_chi_phi_quan_ly_doanh_nghiep"],
    "loans": ["bs_cho_vay_khach_hang", "bs_cho_vay_khach_hang_2"],
    "deposits": ["bs_tien_gui_cua_khach_hang", "bs_tien_gui_cua_khach_hang_va_cac_to_chuc_tin_dung_khac"],
}
LABELS = {
    "assets": "Tổng tài sản", "equity": "Vốn chủ sở hữu", "revenue": "Doanh thu thuần",
    "net_income": "Lợi nhuận sau thuế", "parent_income": "LN thuộc cổ đông công ty mẹ",
    "cfo": "Dòng tiền kinh doanh", "roe": "ROE", "roa": "ROA",
    "net_margin": "Biên lợi nhuận ròng", "debt_assets": "Nợ phải trả / tài sản",
    "current_ratio": "Thanh toán hiện hành", "revenue_growth": "Tăng doanh thu",
    "profit_growth": "Tăng LNST", "operating_income": "Tổng thu nhập hoạt động",
    "cir": "Chi phí / thu nhập (CIR)", "loans": "Cho vay khách hàng", "deposits": "Tiền gửi khách hàng",
    "net_interest_income": "Thu nhập lãi thuần", "eps": "EPS được công bố",
}
SECTORS = {
    "bank": {
        "label": "Ngân hàng",
        "context": "Tăng trưởng kinh tế hỗ trợ nhu cầu tín dụng. Lạm phát và tỷ giá có thể gây áp lực lên chi phí vốn; tác động cụ thể phụ thuộc cơ cấu tài sản và nguồn vốn từng ngân hàng.",
        "drivers": ["Tăng trưởng tín dụng và huy động", "NIM, CASA và thu nhập ngoài lãi", "Nợ xấu, dự phòng và an toàn vốn"],
        "risks": ["Chất lượng tài sản suy giảm có thể làm tăng dự phòng.", "NIM có thể bị thu hẹp khi chi phí huy động tăng.", "Chưa chuẩn hóa NPL, LLR và CAR từ BCTC: cần kiểm tra báo cáo gốc trước khi kết luận."],
        "checks": ["NIM", "CASA", "NPL", "LLR", "CAR"],
    },
    "technology": {
        "label": "Công nghệ thông tin",
        "context": "Hoạt động kinh tế và sản xuất mở rộng có thể hỗ trợ nhu cầu chuyển đổi số. Đơn hàng xuất khẩu phần mềm còn phụ thuộc ngân sách CNTT toàn cầu; tỷ giá tác động cả doanh thu và chi phí.",
        "drivers": ["Đơn hàng CNTT trong và ngoài nước", "Tỷ trọng dịch vụ có giá trị gia tăng cao", "Chi phí nhân sự và chuyển đổi lợi nhuận thành tiền"],
        "risks": ["Khách hàng trì hoãn ngân sách công nghệ.", "Chi phí nhân sự tăng nhanh hơn doanh thu.", "Đồng tiền thanh toán biến động; cần xem cơ cấu thị trường."],
        "checks": ["Backlog", "Doanh thu thị trường nước ngoài", "Biên lợi nhuận theo mảng"],
    },
    "steel": {
        "label": "Thép",
        "context": "Sản xuất công nghiệp và xây dựng tăng trưởng có thể hỗ trợ nhu cầu thép. Lợi nhuận ngành mang tính chu kỳ và phụ thuộc giá bán, quặng sắt, than luyện cốc và công suất vận hành.",
        "drivers": ["Sản lượng tiêu thụ và công suất", "Chênh lệch giá bán so với nguyên liệu", "Đầu tư công, bất động sản và xuất khẩu"],
        "risks": ["Giá thép giảm hoặc nguyên liệu tăng làm thu hẹp biên lợi nhuận.", "Tồn kho và đầu tư công suất gây áp lực dòng tiền.", "Rào cản thương mại có thể ảnh hưởng xuất khẩu."],
        "checks": ["Sản lượng theo tháng", "Giá thép / nguyên liệu", "Công suất mới"],
    },
    "securities": {
        "label": "Dịch vụ chứng khoán", "context": "Hoạt động môi giới, cho vay ký quỹ và tự doanh chịu ảnh hưởng từ thanh khoản và biến động thị trường.",
        "drivers": ["Thanh khoản và giá trị giao dịch thị trường", "Dư nợ margin và chi phí vốn", "Doanh thu môi giới, tự doanh, tư vấn"],
        "risks": ["Thị trường giảm thanh khoản khiến phí môi giới giảm.", "Rủi ro giá tài sản tự doanh và dư nợ margin."],
        "checks": ["Thị phần môi giới", "Dư nợ margin", "Doanh thu tự doanh", "An toàn vốn"],
    },
    "telecom": {
        "label": "Viễn thông", "context": "Nhu cầu kết nối và hạ tầng mạng hỗ trợ dịch vụ viễn thông, nhưng tác động phụ thuộc khu vực kinh doanh, tỷ giá và đầu tư mạng lưới.",
        "drivers": ["Số thuê bao và doanh thu mỗi thuê bao", "Thị phần và đầu tư hạ tầng mạng", "Tỷ giá tại các thị trường hoạt động"],
        "risks": ["Chi phí đầu tư và khấu hao hạ tầng mạng.", "Rủi ro tỷ giá và pháp lý tại thị trường nước ngoài."],
        "checks": ["Thuê bao", "ARPU", "CAPEX", "Dòng tiền kinh doanh", "Chênh lệch tỷ giá"],
    },
    "real_estate": {
        "label": "Bất động sản", "context": "Phụ thuộc lãi suất, pháp lý dự án, khả năng huy động vốn và khả năng hấp thụ của thị trường.",
        "drivers": ["Lãi suất và tín dụng bất động sản", "Tiến độ pháp lý và bàn giao dự án", "Dòng tiền bán hàng và nợ vay"],
        "risks": ["Chậm pháp lý hoặc bàn giao dự án.", "Áp lực đáo hạn nợ vay và dòng tiền."],
        "checks": ["Backlog", "Hàng tồn kho", "Người mua trả trước", "Nợ vay"],
    },
    "retail": {
        "label": "Bán lẻ", "context": "Tăng trưởng tiêu dùng và thu nhập khả dụng tác động đến nhu cầu; biên lợi nhuận phụ thuộc chi phí và cơ cấu mặt hàng.",
        "drivers": ["Sức mua và tiêu dùng nội địa", "Doanh thu trên cửa hàng", "Biên lợi nhuận gộp và hàng tồn kho"],
        "risks": ["Sức mua yếu làm doanh thu/cửa hàng giảm.", "Áp lực tồn kho và khuyến mãi."],
        "checks": ["SSSG", "Biên gộp", "Vòng quay hàng tồn kho"],
    },
    "energy": {
        "label": "Điện và năng lượng", "context": "Sản lượng điện, chi phí đầu vào, cơ chế giá và tiến độ dự án ảnh hưởng kết quả kinh doanh.",
        "drivers": ["Phụ tải điện", "Giá mua bán điện", "Thủy văn và chi phí nhiên liệu"],
        "risks": ["Biến động thủy văn, nhiên liệu và cơ chế giá."],
        "checks": ["Sản lượng điện", "Giá bán bình quân", "Nợ vay dự án"],
    },
    "oil_gas": {
        "label": "Dầu khí", "context": "Giá dầu, khối lượng thăm dò khai thác và chu kỳ đầu tư ngành quyết định nhu cầu dịch vụ, sản lượng.",
        "drivers": ["Giá dầu và khí", "Chu kỳ dự án upstream", "Hợp đồng và công suất khai thác"],
        "risks": ["Giá năng lượng biến động và dự án đầu tư chậm tiến độ."],
        "checks": ["Giá Brent", "Backlog", "Sản lượng", "Dòng tiền"],
    },
    "other": {
        "label": "Chưa phân loại",
        "context": "Chưa có bộ tiêu chí ngành riêng. Cần bổ sung ngành và nhóm doanh nghiệp so sánh trước khi đưa ra kết luận.",
        "drivers": ["Nhu cầu thị trường", "Biên lợi nhuận", "Dòng tiền và cơ cấu vốn"],
        "risks": ["Chưa có dữ liệu đủ để đánh giá đặc thù ngành."], "checks": ["Phân ngành", "Nhóm so sánh"],
    },
}


def safe_div(a, b):
    if a is None or b is None or not math.isfinite(float(a)) or not math.isfinite(float(b)) or b == 0:
        return None
    return float(a) / float(b)


def fmt(value, kind="number"):
    if value is None:
        return "Chưa có"
    if kind == "percent":
        text = f"{value * 100:,.1f}%"
    elif kind == "billion":
        text = f"{value / 1e9:,.1f}"
    elif kind == "price":
        text = f"{value:,.0f} đ"
    else:
        text = f"{value:,.2f}"
    return text.translate(str.maketrans({",": ".", ".": ","}))


def financial_rows(facts, ticker, sector="other"):
    if facts.empty:
        return []
    d = facts.loc[facts.symbol == ticker]
    rows = []
    # Manual canonical fields and original repository item codes both supported.
    for period in sorted(d.period.unique()):
        p = d.loc[d.period == period]
        values = dict(zip(p.item_code, p.value))
        row = {"period": str(period), "basis": "annual"}
        evidence = {}
        for field, codes in FIELDS.items():
            for code in [field] + codes:
                if code in values and pd.notna(values[code]):
                    row[field] = float(values[code])
                    evidence[field] = code
                    break
            row.setdefault(field, None)
        # Historical Parquet and different SDK versions name some items in
        # different ways. Reuse the strict quarterly mapper as a FALLBACK for
        # missing annual items across all sectors, never summing aliases.
        # Conflicting candidate values remain missing until source review.
        if "item_name" in p:
            from .financials import canonical_field
            by_field = {}
            for record in p.itertuples():
                code = str(record.item_code)
                st = getattr(record, "statement", "")
                if st not in {"balance_sheet", "income_statement", "cash_flow"}:
                    st = ("balance_sheet" if code.startswith("bs_") else
                          "income_statement" if code.startswith("is_") else
                          "cash_flow" if code.startswith("cf_") else "")
                if not st or pd.isna(record.value):
                    continue
                canonical = canonical_field(record.item_name, st, code)
                if canonical and canonical in FIELDS and row.get(canonical) is None:
                    by_field.setdefault(canonical, []).append((code, float(record.value)))
            for field, candidates in by_field.items():
                unique = {value for _, value in candidates}
                if len(unique) == 1:
                    row[field] = next(iter(unique))
                    evidence[field] = "label:" + candidates[0][0]
        # Retain original revenue/TOI lines separately. The generic `revenue`
        # analysis field is the chosen sector-specific top-line metric.
        line_field, line_value = top_line(row, sector)
        row["top_line_field"] = line_field
        row["accounting_model"] = accounting_model(sector)
        row["revenue"] = line_value
        if line_field and line_field != "revenue":
            evidence["revenue"] = evidence.get(line_field, line_field)
        row["evidence"] = evidence
        rows.append(row)
    for i, r in enumerate(rows):
        prev = rows[i-1] if i else {}
        # ROA/ROE need contiguous years and opening balances.
        consecutive = bool(prev) and int(r["period"]) == int(prev["period"]) + 1
        avg_equity = (r["equity"] + prev["equity"]) / 2 if consecutive and r["equity"] is not None and prev["equity"] is not None else None
        avg_assets = (r["assets"] + prev["assets"]) / 2 if consecutive and r["assets"] is not None and prev["assets"] is not None else None
        r["roe"] = safe_div(r["net_income"], avg_equity)
        r["roa"] = safe_div(r["net_income"], avg_assets)
        # Do not compute growth across a sector reclassification or an
        # unsupported change from revenue to TOI/operating revenue.
        comparable = consecutive and r["top_line_field"] == prev.get("top_line_field")
        r["revenue_growth"] = safe_div(r["revenue"] - prev["revenue"], abs(prev["revenue"])) if comparable and r["revenue"] is not None and prev["revenue"] is not None else None
        r["profit_growth"] = safe_div(r["net_income"] - prev["net_income"], abs(prev["net_income"])) if consecutive and r["net_income"] is not None and prev["net_income"] is not None else None
        r["net_margin"] = safe_div(r["net_income"], r["revenue"]) if sector != "bank" else None
        r["current_ratio"] = safe_div(r["current_assets"], r["current_liabilities"]) if sector != "bank" else None
        r["debt_assets"] = safe_div(r["liabilities"], r["assets"])
        r["cir"] = safe_div(abs(r["operating_expense"]), r["operating_income"]) if sector == "bank" and r["operating_expense"] is not None else None
    from .research_quality import audit_financial_rows
    audit_financial_rows(rows, sector)
    return rows


def valuation(assumptions, last_price):
    if not assumptions:
        return {"available": False, "message": "Chưa lưu kịch bản định giá. Xem EPS/P-E lịch sử tham khảo và nhập giả định có nguồn ở biểu mẫu bên dưới."}
    method = assumptions.get("method")
    if method not in ["PE", "PB"]:
        raise ValueError("Phương pháp định giá phải là PE hoặc PB.")
    if not assumptions.get("source_url") or not assumptions.get("as_of"):
        raise ValueError("Giả định cần ngày hiệu lực và URL nguồn.")
    pd.Timestamp(assumptions["as_of"])
    for name in ["per_share", "multiple"]:
        n = assumptions.get(name)
        if not isinstance(n, (float, int)) or isinstance(n, bool) or not math.isfinite(n) or n <= 0:
            raise ValueError("EPS/BVPS và hệ số mục tiêu phải là số dương hữu hạn.")
    scenarios = []
    # Sensitivity, not probabilities or automated recommendations.
    for label, factor in [("Thận trọng", .8), ("Cơ sở", 1), ("Thuận lợi", 1.2)]:
        multiple = assumptions["multiple"] * factor
        target = assumptions["per_share"] * multiple
        scenarios.append({"label": label, "multiple": multiple, "target": target,
                          "upside": safe_div(target - last_price, last_price) if last_price else None})
    basis = assumptions.get("basis", "forecast")
    label = "dự phóng" if basis == "forecast" else "lịch sử đã đối soát"
    warning = []
    if not assumptions.get("reviewed"):
        warning.append("Giả định được nhập từ phiên bản cũ, cần kiểm tra lại nguồn và cơ sở cổ phiếu.")
    return {"available": True, "method": method, "assumptions": assumptions,
            "basis": basis, "warnings": warning, "reference_price": assumptions.get("reference_price", last_price),
            "formula": f"Giá kịch bản = {'EPS' if method=='PE' else 'BVPS'} {label} × {'P/E' if method=='PE' else 'P/B'} mục tiêu",
            "scenarios": scenarios, "message": "Kịch bản theo chỉ tiêu lịch sử đã đối soát, không phải dự báo tương lai." if basis == "historical" else "Kịch bản dự phóng do người dùng kiểm tra và lưu; không gán xác suất, không phải khuyến nghị."}


def analyze(store: Store, ticker: str):
    ticker = symbol(ticker)
    companies = store.read_json("companies.json", {})
    catalogue={r["symbol"]:r for r in store.read_json("universe.json",{}).get("symbols",[])}
    profile = companies.get(ticker, {"name": catalogue.get(ticker,{}).get("name",ticker), "sector": "other", "peers": [], "description": "Chưa có hồ sơ doanh nghiệp."})
    from .peers import map_sector, suggest, compare, explain
    selected_peers = suggest(store, ticker, profiles=companies)
    sector_key = map_sector(ticker, profile, store.read_json("industry_catalog.json", {}).get("symbols", {}).get(ticker, {}))
    inferred_sector = profile.get("sector", "other") in (None, "", "other") and sector_key != "other"
    sector = SECTORS.get(sector_key, SECTORS["other"])
    prices = store.read("prices.parquet")
    p = prices.loc[prices.symbol == ticker].sort_values("date") if not prices.empty else pd.DataFrame()
    from .annual_baseline import facts_for_analysis, display_first_year
    facts = facts_for_analysis(store)
    # Opening-year facts affect the 2022 ratios but are never shown as another
    # reporting year in the UI, PDF or user-facing annual-year summaries.
    financials = [r for r in financial_rows(facts, ticker, sector_key)
                  if int(r["period"]) >= display_first_year()]
    from .insights import quarterly_rows, explain_macro, explain_peers, conclusion, latest_macro
    quarterly = quarterly_rows(store.read("financial_quarterly.parquet"), ticker, sector_key)
    if p.empty and not financials and not quarterly:
        raise ValueError(f"Chưa có dữ liệu cho {ticker}. Hãy nạp giá hoặc BCTC trước.")
    last_price = float(p.iloc[-1].close) if not p.empty else None
    price_date = str(p.iloc[-1].date) if not p.empty else None
    market = {"close": last_price, "date": price_date, "rows": len(p), "return_20": None, "volatility": None,
              "volume_20": None, "ma20": None, "ma50": None, "drawdown": None, "relative_20": None,
              "price_basis": str(p.iloc[-1].price_basis) if not p.empty else None}
    if not p.empty:
        close = p.close.astype(float)
        market["volume_20"] = float(p.tail(20).volume.mean())
        market["return_20"] = float(close.iloc[-1]/close.iloc[-21]-1) if len(close) >= 21 else None
        market["ma20"] = float(close.tail(20).mean()) if len(close) >= 20 else None
        market["ma50"] = float(close.tail(50).mean()) if len(close) >= 50 else None
        market["drawdown"] = float((close / close.cummax() - 1).min())
        market["volatility"] = float(close.pct_change().dropna().std(ddof=1) * math.sqrt(252)) if len(close) >= 21 else None
        bench = prices.loc[prices.symbol == "VNINDEX", ["date", "close"]].rename(columns={"close": "benchmark"})
        aligned = p[["date", "close"]].merge(bench, on="date")
        if len(aligned) >= 21 and str(aligned.iloc[-1].date) == price_date:
            stock_r = float(aligned.close.iloc[-1]/aligned.close.iloc[-21]-1)
            index_r = float(aligned.benchmark.iloc[-1]/aligned.benchmark.iloc[-21]-1)
            market["relative_20"] = stock_r - index_r
    peers = []
    peer_summary = {"period": None, "peer_count": len(selected_peers["peers"]),
                    "peers_with_financials": 0, "medians": {}, "ranks": {},
                    "note": selected_peers["note"], "source": selected_peers["sector_source"],
                    "industry_name": selected_peers.get("industry_name", ""),
                    "valuation_note": "P/B, P/E cần giá, cổ phiếu lưu hành cùng thời điểm và điều chỉnh sự kiện doanh nghiệp."}
    if financials:
        peers, peer_summary = compare(facts, prices, ticker, selected_peers,
                                      financials[-1]["period"], financial_rows, sector_key)
    peer_notes = explain(peers, peer_summary, ticker, fmt)
    latest = financials[-1] if financials else {}
    macro_history = store.read_json("macro.json", [])
    macro = latest_macro(macro_history)
    news_all = store.read_json("news.json", [])
    from .newsfeed import relevant_news
    related = [(n, relevant_news(n, ticker, sector_key)) for n in news_all]
    company_news = [n for n, (is_company, _, _) in related if is_company]
    macro_news = [n for n, (_, is_macro, _) in related if is_macro]
    sector_news = [n for n, (_, _, is_sector) in related if is_sector]
    # Existing PDF renderer and coverage can still read .news; unrelated
    # sector/market headlines are deliberately excluded.
    news = company_news + sector_news + macro_news
    positives, concerns = [], []
    rg, pg = latest.get("revenue_growth"), latest.get("profit_growth")
    if rg is not None:
        (positives if rg > 0 else concerns).append(f"{'Tổng thu nhập hoạt động' if sector_key == 'bank' else 'Doanh thu'} {latest['period']} thay đổi {fmt(rg, 'percent')} so với năm trước.")
    if pg is not None:
        (positives if pg > 0 else concerns).append(f"Lợi nhuận sau thuế {latest['period']} thay đổi {fmt(pg, 'percent')} so với năm trước.")
    if sector_key != "bank" and latest.get("cfo") is not None:
        (positives if latest["cfo"] > 0 else concerns).append(f"Dòng tiền kinh doanh {latest['period']}: {fmt(latest['cfo'], 'billion')} tỷ đồng.")
    if market["return_20"] is not None:
        (positives if market["return_20"] > 0 else concerns).append(f"Giá thay đổi {fmt(market['return_20'], 'percent')} trong 20 phiên; chưa cộng cổ tức tiền mặt.")
    if market["relative_20"] is not None:
        (positives if market["relative_20"] > 0 else concerns).append(f"Chênh lệch hiệu suất so với VN-Index: {fmt(market['relative_20'] * 100)} điểm phần trăm trong 20 phiên chung.")
    critical_financial = required_missing(latest, sector_key) if latest else []
    latest_year_issues = bool(latest.get("quality_issues")) if latest else False
    coverage = [
        {"group": "Giá và giao dịch", "status": "Có" if len(p) else "Thiếu", "detail": f"{len(p)} phiên; cuối kỳ {price_date or 'chưa có'}"},
        {"group": "Báo cáo tài chính", "status": ("Một phần" if financials and (critical_financial or latest_year_issues) else "Có" if financials else "Thiếu"), "detail": f"{len(financials)} năm đã lưu; gần nhất {latest.get('period', 'chưa có')}" + (("; thiếu chỉ tiêu " + ", ".join(critical_financial)) if critical_financial else "") + ("; cần kiểm tra kỳ đáng nghi" if latest_year_issues else "") + "; chưa đối soát PDF kiểm toán"},
        {"group": "Tin tức", "status": "Có" if news else "Thiếu", "detail": f"{len(news)} tin đã lưu; nội dung {', '.join(sorted(set(n.get('content_status', 'chưa trích') for n in news))) or 'chưa nạp'}"},
        {"group": "Vĩ mô", "status": "Có" if macro else "Thiếu", "detail": f"{len(macro)} chỉ tiêu; xem kỳ tham chiếu và ngày công bố"},
        {"group": "So sánh ngành", "status": ("Có" if peer_summary["peers_with_financials"] >= 3 else "Một phần" if peer_summary["peer_count"] else "Thiếu"), "detail": f"{peer_summary['peer_count']} mã ứng viên; {peer_summary['peers_with_financials']} mã có BCTC cùng năm (chưa đồng nghĩa đủ chỉ tiêu/đối soát)"},
    ]
    latest_quarter = quarterly[-1] if quarterly else None
    quarter_gaps = (latest_quarter.get("missing_statements", []) + latest_quarter.get("missing_fields", [])) if latest_quarter else []
    quarter_detail = f"{len(quarterly)} kỳ; gần nhất {latest_quarter['period'] if latest_quarter else 'chưa có'}"
    if quarter_gaps:
        labels = {"balance_sheet": "Cân đối kế toán", "income_statement": "KQKD",
                  "cash_flow": "Lưu chuyển tiền tệ", "cfo": "Dòng tiền kinh doanh",
                  "revenue": "Doanh thu thuần", "operating_income": "Tổng thu nhập hoạt động",
                  "net_income": "LNST", "assets": "Tổng tài sản", "equity": "Vốn chủ sở hữu",
                  "securities_revenue_or_revenue": "Doanh thu hoạt động chứng khoán",
                  "top_line_unclassified": "Doanh thu/thu nhập chính (chưa phân ngành)"}
        quarter_detail += "; thiếu " + ", ".join(dict.fromkeys(labels.get(k, k) for k in quarter_gaps))
    coverage.append({"group": "BCTC quý", "status": "Một phần" if quarter_gaps else "Có" if quarterly else "Thiếu",
                     "detail": quarter_detail + "; chưa xác minh riêng quý/lũy kế"})
    concerns += sector["risks"]
    if latest and price_date and int(latest["period"]) < int(price_date[:4]) and not quarterly:
        concerns.append(f"BCTC mới nhất trong bộ dữ liệu là năm {latest['period']}; chưa có BCTC quý hiện tại.")
    from .valuation_engine import historical_context
    valuation_inputs = historical_context(facts, prices, ticker, peers, financial_rows, sector_key)
    assumptions = store.read_json("valuations.json", {}).get(ticker)
    # The original reference price is preserved for a reproducible scenario.
    # Price changes should never silently rewrite a previously saved upside.
    basis_price = assumptions.get("reference_price") if isinstance(assumptions, dict) else None
    valu = valuation(assumptions, basis_price or last_price)
    valu["inputs"] = valuation_inputs
    if assumptions and basis_price and last_price and abs(last_price - basis_price) > 0.000001:
        valu.setdefault("warnings", []).append("Giá đã thay đổi sau khi lưu giả định; kết quả đang so với giá tham chiếu lúc lưu. Cần lưu lại để cập nhật kịch bản.")
    if quarterly:
        concerns.append("BCTC quý đã lưu riêng; KQKD/dòng tiền cần đối soát cơ sở riêng quý hay lũy kế trước khi cộng TTM.")
    from .research_quality import collect_quality
    data_quality = collect_quality(financials, sector_key, quarterly)
    if data_quality:
        # Never issue a positive investment call from questionable yearly financial rows.
        concerns.extend(data_quality)
    manifest = store.manifest()
    sources = [{"file": name, **meta} for name, meta in manifest.get("files", {}).items() if not name.startswith("raw/")]
    # Stable data cut-off; no current-clock values in an offline analysis.
    as_of = max([x for x in [price_date] + [m.get("published_at") for m in macro] + [n.get("published_at", "")[:10] for n in news] if x], default=latest.get("period", ""))
    result = {"symbol": ticker, "mode": store.mode, "as_of": as_of, "profile": profile,
            "sector": {"key": sector_key, "is_provisional": inferred_sector, **sector}, "market": market,
            "prices": p[["date", "close", "volume"]].to_dict("records") if not p.empty else [],
            "financials": financials, "quarterly_financials": quarterly, "peers": peers, "macro": macro, "news": news, "company_news": company_news, "sector_news": sector_news, "macro_news": macro_news,
            "macro_history": macro_history, "macro_analysis": explain_macro(macro,sector_key,fmt), "peer_analysis": peer_notes, "peer_summary": peer_summary, "peer_selection": selected_peers,
            "exchange_rates":store.read_json("exchange_rates.json",[]),
            "coverage": coverage, "data_quality": data_quality, "opportunity": {"conclusion": conclusion(latest,market,valu),
            "positives": positives or ["Chưa đủ dữ liệu để xác định luận điểm tích cực."],
            "risks": concerns, "next_checks": sector["checks"] + ["Đối soát BCTC gốc", "Kiểm tra sự kiện cổ tức / chia tách", "Cập nhật báo cáo quý và tin công bố"]},
            "valuation": valu, "sources": sources,
            "methodology": ["ROA/ROE = LNST / tài sản hoặc VCSH bình quân đầu-cuối năm; thiếu đầu kỳ thì để trống.",
                            "Thanh toán hiện hành = tài sản ngắn hạn / nợ ngắn hạn; không áp dụng cho ngân hàng.",
                            "Không dùng CFO trước thuế của ngân hàng thay cho CFO cuối cùng.",
                            "Biến động năm hóa dùng 252 phiên; lợi suất giá không bao gồm cổ tức tiền mặt.",
                            "Tin tức là bằng chứng tham khảo, không tự suy ra khuyến nghị từ tiêu đề.",
                            "So sánh cùng năm, trung vị chỉ dùng mã có số liệu; chưa tự tính P/B/P/E khi thiếu cơ sở cổ phiếu lưu hành.",
                            "Báo cáo mô tả bộ dữ liệu hiện có, không phải mô phỏng thông tin đã biết tại một ngày quá khứ."]}

    from .research_rules import compile_research
    result["research"] = compile_research(result, store=store)
    from .review import apply_review
    return apply_review(store,result)
