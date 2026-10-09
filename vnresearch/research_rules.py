"""Deterministic investment-research prose from STORED evidence only.

No model, no network, no hidden external assumptions. A news article's metadata
supports a *reported topic*, never verified causal or financial conclusions.
Citations point to the exact selected stored URLs with their review state.
"""
from __future__ import annotations

import re
from pathlib import Path
from .newsfeed import fold
from .analysis import fmt

# Specific to each industry's business model. Conditional, not forecast claims.
IMPACTS = {
    "securities": {
        "liquidity": ("Thanh khoản thị trường", "Thanh khoản thay đổi có thể ảnh hưởng phí môi giới và nhu cầu vay ký quỹ; chưa thể suy ra mức tăng/giảm doanh thu SSI.", "Giá trị giao dịch toàn thị trường, thị phần môi giới và dư nợ margin."),
        "rate": ("Chi phí vốn", "Mặt bằng lãi suất thay đổi có thể tác động đến chi phí tài trợ cho vay ký quỹ và hiệu quả tự doanh.", "Lãi vay thực tế, nợ vay và lãi thuần từ cho vay ký quỹ."),
        "foreign": ("Dòng vốn và cấu trúc thị trường", "Biến động dòng vốn và hoạt động của nhà đầu tư có thể tác động thanh khoản, nhưng không trực tiếp xác nhận lợi nhuận của doanh nghiệp.", "Giao dịch thực tế trên sở và cơ cấu doanh thu SSI."),
        "capital": ("Thay đổi vốn cổ phần", "Thay đổi vốn có thể mở rộng năng lực kinh doanh nhưng cũng làm thay đổi EPS/BVPS và hiệu quả sử dụng vốn.", "Nghị quyết phát hành, số cổ phiếu sau sự kiện và mục đích sử dụng vốn."),
    },
    "bank": {
        "rate": ("Lãi suất và NIM", "Biến động lãi suất có thể làm thay đổi chênh lệch thu nhập lãi và chi phí huy động.", "NIM, CASA, lãi suất huy động và chất lượng tín dụng của ngân hàng."),
        "credit": ("Tín dụng", "Tăng trưởng tín dụng hỗ trợ quy mô tài sản sinh lãi nếu chất lượng khoản vay không suy giảm.", "Tăng trưởng dư nợ, nợ xấu, dự phòng và hệ số an toàn vốn."),
    },
    "steel": {
        "commodity": ("Giá nguyên liệu", "Giá nguyên liệu biến động có thể làm thay đổi biên lợi nhuận ngành thép, tùy tồn kho và thời điểm bán hàng.", "Giá quặng/than, giá bán thành phẩm, sản lượng và hàng tồn kho."),
        "investment": ("Đầu tư xây dựng", "Nhu cầu xây dựng hoặc đầu tư công thay đổi có thể ảnh hưởng tiêu thụ thép nhưng chưa phản ánh trực tiếp lợi nhuận.", "Sản lượng tiêu thụ, giá bán và công suất sử dụng."),
    },
    "technology": {
        "technology": ("Đơn hàng công nghệ", "Nhu cầu dịch vụ CNTT có thể ảnh hưởng tăng trưởng doanh thu, phụ thuộc thời điểm ghi nhận hợp đồng.", "Backlog, doanh thu thị trường nước ngoài và biên lợi nhuận."),
    },
    "real_estate": {"investment": ("Nhu cầu và pháp lý", "Hoạt động đầu tư và tín dụng có thể tác động sức mua và tiến độ triển khai dự án.", "Tiến độ bàn giao, pháp lý dự án và dòng tiền bán hàng.")},
    "retail": {"consumption": ("Sức mua", "Tiêu dùng thay đổi có thể ảnh hưởng doanh thu trên cửa hàng và biên lợi nhuận.", "Doanh số cùng cửa hàng, tồn kho và biên lợi nhuận gộp.")},
}
KEYWORDS = {
    "liquidity": ("thanh khoan", "vn-index", "vnindex", "gia tri giao dich", "moi gioi", "margin", "thi truong chung khoan", "krx"),
    "rate": ("lai suat", "chi phi von", "tien te", "huy dong"),
    "foreign": ("khoi ngoai", "nang hang", "von ngoai", "ftse", "dong von", "ban rong", "mua rong"),
    "capital": ("phat hanh", "tang von", "chia co phieu", "thuong co phieu", "co tuc"),
    "credit": ("tin dung", "no xau", "cho vay"),
    "commodity": ("quang sat", "than luyen coc", "gia thep", "ton thep"),
    "investment": ("dau tu cong", "ha tang", "xay dung", "du an"),
    "technology": ("phan mem", "chuyen doi so", "ai", "hop dong", "cntt", "cong nghe"),
    "consumption": ("ban le", "tieu dung", "suc mua", "cua hang"),
}
# Broad macro feed categories alone are *not* sufficient evidence of relevance.
GENERAL_MACRO = ("gdp", "cpi", "lam phat", "lai suat", "ty gia", "fdi", "dau tu cong", "kinh te vi mo", "tang truong tin dung", "chinh sach tien te", "vn-index", "thanh khoan", "nang hang", "von ngoai")
RELEVANT_MARKET = {"securities": ("vn-index", "thanh khoan", "khoi ngoai", "thi truong chung khoan", "nang hang", "lai suat", "dau tu"),
                  "bank": ("lai suat", "tin dung", "ngan hang", "ty gia", "nha bang"),
                  "steel": ("thep", "quang sat", "dau tu cong", "xay dung"),
                  "technology": ("cong nghe", "cntt", "phan mem", "chuyen doi so"),
                  "retail": ("tieu dung", "ban le", "suc mua"),
                  "real_estate": ("bat dong san", "nha o", "tien te", "dau tu cong"),
                  "energy": ("dien", "nang luong", "dau", "gia dien"),
                  "oil_gas": ("gia dau", "dau khi", "nang luong")}


def _has(text, words):
    return any(re.search(r"(?<![\w])" + re.escape(w) + r"(?![\w])", text) for w in words)


def _tokens(item):
    return fold(str(item.get("title") or "") + " " + str(item.get("summary") or ""))


def _theme(news, sector):
    text = _tokens(news)
    for tag in IMPACTS.get(sector, {}):
        if _has(text, KEYWORDS.get(tag, ())):
            return tag
    return None


def _score(news, ticker, sector, category):
    text = _tokens(news)
    if not news.get("url", "").startswith("https://") or not news.get("published_at"):
        return -1
    symbols = news.get("symbols") if isinstance(news.get("symbols"), list) else [news.get("symbol")]
    symbols = [v for v in symbols if v and v != "MARKET"]
    # A story about one other company is not automatically relevant to SSI.
    if category != "company" and symbols and ticker not in symbols:
        return -1
    if category == "company":
        return 15 if ticker in symbols else -1
    sector_tags = news.get("sectors") or []
    if category == "sector" and sector not in sector_tags:
        return -1
    theme = _theme(news, sector)
    if category == "macro":
        if not _has(text, GENERAL_MACRO):
            return -1
        # Economy-wide indicators that are orthogonal to the issuer shouldn't flood the report.
        allowed = RELEVANT_MARKET.get(sector, ())
        if not _has(text, allowed):
            return -1
    if category == "sector" and not (theme or _has(text, RELEVANT_MARKET.get(sector, ()))):
        return -1
    score = (4 if theme else 0) + (3 if news.get("content_status") in ("user_reviewed", "source_reviewed_summary") else 0)
    return score + (1 if news.get("content_status") == "extracted_unreviewed" else 0)


def _choose(data, limit=4):
    ticker, sector = data["symbol"], data["sector"]["key"]
    buckets = (("company", data.get("company_news", []), 2),
               ("sector", data.get("sector_news", []), 2),
               ("macro", data.get("macro_news", []), 1))
    out, seen = [], set()
    for category, items, cap in buckets:
        choices = []
        for news in items:
            score = _score(news, ticker, sector, category)
            if score >= 0:
                choices.append((score, str(news.get("published_at", "")), news))
        # Specificity is more important than mere recency, but dates break ties.
        for _, _, item in sorted(choices, key=lambda x: (x[0], x[1]), reverse=True):
            url = item.get("url")
            if url in seen: continue
            seen.add(url)
            out.append((category, item))
            cap -= 1
            if cap <= 0 or len(out) >= limit: break
        if len(out) >= limit: break
    return out


def _with_cached_body(news, store):
    """Only use an existing *publisher* extraction; no network, no scraping."""
    name = news.get("body_file")
    if not name or store is None or not isinstance(name, str):
        return ""
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts or not name.startswith("raw/news/") or rel.suffix != ".json":
        return ""
    try:
        payload = store.read_json(name, {})
        if payload.get("url") != news.get("url"):
            return ""
        value = str(payload.get("text", ""))
        return value[:10000] if len(value) >= 100 else ""
    except (OSError, ValueError, TypeError):
        return ""


def _news_thesis(category, news, ticker, sector, source_id, store):
    theme = _theme(news, sector)
    impact = IMPACTS.get(sector, {}).get(theme)
    title = str(news.get("title") or "").strip()[:200]
    published = news.get("published_at") or "không rõ"
    if impact:
        heading, effect, followup = impact
    else:
        heading = "Diễn biến tại doanh nghiệp" if category == "company" else "Bối cảnh ngành"
        effect = "Thông tin có thể liên quan đến hoạt động doanh nghiệp, nhưng chưa đủ bằng chứng xác định tác động tới lợi nhuận."
        followup = "Báo cáo công bố chính thức và các chỉ tiêu hoạt động có liên quan."
    status = news.get("content_status", "rss_metadata")
    body_text = _with_cached_body(news, store)
    if status == "rss_metadata":
        evidence_type = "bản tin RSS (chỉ có tiêu đề/tóm tắt)"
    elif body_text:
        evidence_type = "bài báo đã trích xuất nội dung nhưng chưa đối soát" if status != "user_reviewed" else "bài báo đã được đánh dấu đối soát"
    else:
        evidence_type = "bản tin đã lưu chưa có văn bản nguồn kiểm tra được"
    # Read the existing source body for *topic confirmation* when available;
    # we do not copy its paragraphs or treat unverified assertions as facts.
    body_topics = []
    topic_names = {"liquidity":"thanh khoản", "rate":"lãi suất", "foreign":"dòng vốn",
                   "capital":"thay đổi vốn", "credit":"tín dụng", "commodity":"nguyên liệu",
                   "investment":"đầu tư", "technology":"công nghệ", "consumption":"tiêu dùng"}
    if body_text:
        normalized = fold(body_text)
        body_topics = [topic_names[label] for label, tokens in KEYWORDS.items() if _has(normalized, tokens)]
    body_note = (" Văn bản đã lưu có nhắc tới các nhóm vấn đề: " + ", ".join(body_topics[:2]) +
                 "; nội dung này chưa được đối soát với công bố gốc.") if body_topics else ""
    s = (f"Theo {evidence_type} ngày {published}, nguồn đăng tin «{title}» [{source_id}]. "
         f"{effect}{body_note} Cần đối chiếu: {followup}")
    return {"heading": heading, "text": s, "sources": [source_id], "status": status}


def _financial_analysis(data):
    annual = data.get("financials", [])
    if not annual:
        return ["Chưa có BCTC năm để đánh giá hiệu quả kinh doanh."]
    latest = annual[-1]
    notes = []
    if latest.get("quality_status") == "suspect_duplicate_year":
        notes.append("Kỳ " + latest["period"] + " bị tạm loại khỏi nhận định tăng trưởng: ba chỉ tiêu tài sản, vốn chủ và lợi nhuận trùng chính xác kỳ trước. Cần đối soát báo cáo gốc.")
        return notes
    for name, key in (("lợi nhuận sau thuế", "profit_growth"), ("doanh thu/thu nhập hoạt động", "revenue_growth")):
        value = latest.get(key)
        if value is not None:
            notes.append(f"{name.capitalize()} năm {latest['period']} {'tăng' if value > 0 else 'giảm' if value < 0 else 'không thay đổi theo số liệu lưu'} "
                         f"{fmt(abs(value), 'percent')} so với năm trước; đây là biến động lịch sử, không phải dự phóng.")
    if latest.get("roe") is not None:
        notes.append(f"ROE năm {latest['period']} đạt {fmt(latest['roe'], 'percent')} theo vốn chủ sở hữu bình quân. Chỉ tiêu cần đối soát phạm vi hợp nhất và lợi nhuận sử dụng.")
    if latest.get("revenue") is None and data["sector"]["key"] == "securities":
        notes.append("Chưa xác định được doanh thu/thu nhập hoạt động của công ty chứng khoán từ bảng mã nguồn: không ghi bằng 0 và không suy diễn biên lợi nhuận.")
    if not notes:
        notes.append("BCTC đã lưu chưa đủ chỉ tiêu cùng kỳ để lập nhận định tăng trưởng đáng tin cậy.")
    return notes[:4]


def _macro_notes(data):
    sector = data["sector"]["key"]
    records = {r.get("indicator"):r for r in data.get("macro", [])}
    order = {"bank": ("credit_ytd", "cpi_average_yoy", "gdp_yoy"),
             "securities": ("credit_ytd", "cpi_average_yoy"),
             "steel": ("iip_yoy", "fdi_disbursed"),
             "technology": ("gdp_yoy", "fdi_disbursed"),
             "real_estate": ("credit_ytd", "gdp_yoy"),
             "retail": ("cpi_average_yoy", "gdp_yoy")}.get(sector, ("gdp_yoy",))
    output = []
    for key in order:
        r = records.get(key)
        if not r or not isinstance(r.get("value"), (int,float)):
            continue
        basis = str(r.get("basis", ""))
        output.append(f"{r['label']} kỳ {r.get('period','?')} là {fmt(r['value'])} {r.get('unit','')} ({basis}). "
                      f"Đây là bối cảnh; chưa chứng minh mức thay đổi của doanh thu hoặc lợi nhuận riêng {data['symbol']}.")
    return output or ["Không đủ dữ liệu vĩ mô có liên quan trực tiếp đến phân ngành để lượng hóa tác động."]


def compile_research(data, store=None):
    """Produce the SAME data-backed prose for web and PDF, deterministically."""
    refs, news = [], []
    for category, item in _choose(data):
        id_ = len(refs) + 1
        refs.append({"id": id_, "title": str(item.get("title") or "")[:200],
                     "url": item["url"], "published_at": item.get("published_at", ""),
                     "status": item.get("content_status", "rss_metadata"), "category": category})
        news.append(_news_thesis(category, item, data["symbol"], data["sector"]["key"], id_, store))
    market = data.get("market", {})
    executive = []
    quality = data.get("data_quality") or []
    if quality:
        executive.append("Cảnh báo dữ liệu: một số kỳ/chỉ tiêu chưa đạt điều kiện đối soát; chưa thể sử dụng chúng để đánh giá tăng trưởng hoặc mức giá hợp lý.")
    if market.get("return_20") is not None:
        executive.append(f"Giá {data['symbol']} biến động {fmt(market['return_20'], 'percent')} trong 20 phiên; "
                         "phải đối chiếu xu hướng lợi nhuận và diễn biến thị trường thay vì suy ra khuyến nghị chỉ từ giá.")
    financial_notes = _financial_analysis(data)
    if not quality and data.get("financials") and data["financials"][-1].get("profit_growth") is not None:
        executive.append(financial_notes[0])
    if news:
        executive.append("Thông tin thị trường/doanh nghiệp được xem xét dưới góc độ tác động có điều kiện; các dẫn nguồn bên dưới chưa tự động được coi là sự kiện đã kiểm toán.")
    if not executive:
        executive.append("Chưa đủ bằng chứng đáng tin cậy để hình thành luận điểm đầu tư cho kỳ hiện tại.")
    peer_summary = data.get("peer_summary", {})
    peer_notes = data.get("peer_analysis", [])
    sector_analysis = [str(x) for x in peer_notes[:3]]
    if peer_summary.get("peers_with_financials",0) == 0:
        sector_analysis = ["Nhóm ứng viên cùng ngành đã được đề xuất nhưng chưa có BCTC cùng kỳ; không thể xếp hạng đối thủ hoặc suy ra hệ số định giá."]
    return {"executive": executive[:4], "macro": _macro_notes(data),
            "financial": financial_notes, "industry": sector_analysis,
            "news_theses": news, "references": refs,
            "quality_warnings": quality,
            "method": "Mẫu câu và quy tắc cố định, không dùng AI; tin chưa đối soát không được biến thành khuyến nghị."}
