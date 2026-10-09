"""Unicode Vietnamese PDF with explicit evidence, calculations and coverage."""
from __future__ import annotations
from functools import partial
from io import BytesIO
from pathlib import Path
from datetime import date
import threading
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

from .storage import ROOT
from .analysis import fmt, LABELS

_LOCK = threading.RLock()
BLUE = colors.HexColor("#125b86")
DARK = colors.HexColor("#17324d")
LIGHT = colors.HexColor("#edf5fa")
GRAY = colors.HexColor("#526579")


def chart(data, kind):
    fig, ax = plt.subplots(figsize=(8.7, 2.8), dpi=150)
    fig.patch.set_facecolor("white")
    if kind in ("price", "volume"):
        # Day-based matplotlib axes include weekends and public holidays as gaps.
        # Use the ordinal position of each *observed* trading session instead.
        # Dates remain unchanged in the stored series and in axis labels.
        rows = sorted(data["prices"], key=lambda row: row["date"])
        sessions = list(range(len(rows)))
        dates = [date.fromisoformat(row["date"]) for row in rows]
        if kind == "price":
            close = [row["close"] / 1000 for row in rows]
            ax.plot(sessions, close, color="#125b86", linewidth=1.6)
            ax.fill_between(sessions, close, min(close) * .98, color="#d5e9f5", alpha=.5)
            ax.set_ylabel("Nghìn đồng / cổ phiếu", fontsize=9)
        else:
            ax.bar(sessions, [row["volume"] / 1e6 for row in rows], color="#79a8c2", width=.85)
            ax.set_ylabel("Triệu cổ phiếu", fontsize=9)

        if dates:
            count = min(7, len(dates))
            ticks = ([0] if count == 1 else
                     [round(i * (len(dates) - 1) / (count - 1)) for i in range(count)])
            long_range = (dates[-1] - dates[0]).days > 180
            labels = [dates[i].strftime("%Y-%m" if long_range else "%d/%m/%y") for i in ticks]
            ax.set_xticks(ticks, labels)
            ax.set_xlim(-.5, len(rows) - .5)
        ax.set_xlabel("Phiên giao dịch (không gồm ngày nghỉ)", fontsize=8)
    else:
        rows = data["financials"]
        x = list(range(len(rows)))
        ax.bar([i-.18 for i in x], [(r.get("revenue") if r.get("revenue") is not None else float("nan"))/1e9 for r in rows], .36, color="#125b86", label="Thu nhập hoạt động" if data["sector"]["key"] == "bank" else "Doanh thu")
        ax.bar([i+.18 for i in x], [(r.get("net_income") if r.get("net_income") is not None else float("nan"))/1e9 for r in rows], .36, color="#54b1ab", label="LNST")
        ax.set_xticks(x, [r["period"] for r in rows])
        ax.set_ylabel("Tỷ đồng", fontsize=9)
        ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=.15)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=17.5*cm, height=5.6*cm)


def build_pdf(data, output):
    with _LOCK:
        return _build_pdf(data, output)


def _build_pdf(data, output):
    fonts = ROOT / "assets" / "fonts"
    if "Research" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Research", str(fonts / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("Research-Bold", str(fonts / "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily("Research", normal="Research", bold="Research-Bold", italic="Research", boldItalic="Research-Bold")
    styles = getSampleStyleSheet()
    body = ParagraphStyle("ResearchBody", fontName="Research", fontSize=9, leading=14, textColor=DARK, spaceAfter=7)
    small = ParagraphStyle("ResearchSmall", parent=body, fontSize=7.5, leading=11, textColor=GRAY)
    h1 = ParagraphStyle("ResearchH1", parent=body, fontName="Research-Bold", fontSize=19, leading=25, textColor=BLUE, spaceAfter=12)
    h2 = ParagraphStyle("ResearchH2", parent=body, fontName="Research-Bold", fontSize=11, leading=16, textColor=BLUE, spaceBefore=6, spaceAfter=8)
    title = ParagraphStyle("ResearchTitle", parent=h1, fontSize=29, leading=34)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=(21*cm, 29.7*cm),
                            topMargin=2*cm, bottomMargin=1.7*cm, leftMargin=1.7*cm, rightMargin=1.7*cm,
                            title=f"Báo cáo phân tích {data['symbol']}", author="VN Equity Research", invariant=1)
    story = []
    def p(text, style=body):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)
    def add(text, style=body):
        story.append(p(text, style))
    def bullet(items):
        for text in items:
            add("• " + text)
    def table(headers, rows, widths=None):
        header_style = ParagraphStyle("WhiteHeader", parent=small, textColor=colors.white, fontName="Research-Bold")
        cells = [[p(v, header_style) for v in headers]] + [[p(v, small) for v in r] for r in rows]
        t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BLUE), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT]),
            ("VALIGN", (0,0), (-1,-1), "TOP"), ("TOPPADDING", (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("LINEBELOW", (0,0), (-1,0), .5, BLUE),
        ]))
        # Paragraphs override table text color: use explicit white header style.
        for cell in cells[0]:
            cell.style = ParagraphStyle("WhiteHeader", parent=small, textColor=colors.white, fontName="Research-Bold")
        story.append(t)
        story.append(Spacer(1, .18*cm))
    def chapter(number, name):
        # Major analytical parts have page starts; compact supplementary sections
        # flow naturally to avoid pages with little content.
        if number in (2, 3, 4, 6):
            story.append(PageBreak())
        elif number > 1:
            story.append(Spacer(1, .4*cm))
        add(f"0{number} / {name.upper()}", h1)
    review = data.get("review")
    research = data.get("research", {})
    m, sector, latest = data["market"], data["sector"], data["financials"][-1] if data["financials"] else {}
    chapter(1, "Tổng quan đầu tư")
    add(data["symbol"], title)
    add(data["profile"]["name"], h2)
    add(sector["label"] + "  |  " + ("Bộ dữ liệu demo cố định" if data["mode"] == "sample" else "Dữ liệu thực tế cố định · 09/10/2026" if data["mode"]=="submission" else "Bộ dữ liệu cá nhân"), small)
    table(["Giá cuối phiên", "Ngày giá", "BCTC năm", "20 phiên"],
          [[fmt(m["close"], "price"), m["date"] or "Chưa có", latest.get("period", "Chưa có"), fmt(m["return_20"], "percent")]], [4.4*cm]*4)
    add("Tóm tắt từ bằng chứng đang có", h2)
    bullet(research.get("executive") or [data["opportunity"]["conclusion"]])
    add(data["profile"].get("description", "Chưa có mô tả."))
    add("Luận điểm từ dữ liệu đã lưu", h2)
    bullet(research.get("financial", [])[:2])
    add("Rủi ro cần chú ý", h2)
    bullet(data["opportunity"]["risks"][:3])
    add("Phạm vi đánh giá", h2)
    add(f"Dữ liệu trong báo cáo có ngày và kỳ tham chiếu khác nhau. Giá kết thúc ở {m['date'] or 'chưa có'}; BCTC đến năm {latest.get('period', 'chưa có')}. Bộ demo không tự cập nhật. Các nhận định ngành là diễn giải định tính, chưa phải mô hình dự báo.")
    add("Nhận định do quy tắc cố định tạo từ dữ liệu đã lưu; không sử dụng AI và không thay thế việc đối soát nguồn gốc.", small)
    chapter(2, "Vĩ mô và tác động tới ngành")
    if data["macro"]:
        table(["Chỉ tiêu", "Giá trị", "Kỳ / cơ sở so sánh", "Công bố"],
              [[r["label"], f"{fmt(r['value'])} {r['unit']}", str(r["period"]) + "\n" + r["basis"], r["published_at"]] for r in data["macro"]],
              [5*cm,3*cm,6.8*cm,2.8*cm])
    else:
        add("Chưa nạp dữ liệu vĩ mô. Không đưa số liệu ước đoán vào báo cáo.")
    add("Liên hệ vĩ mô → ngành ngân hàng" if review else "Nhận định từ số liệu đã lưu", h2)
    if review:
        bullet(review["macro_to_bank"])
        add("Nguồn S3 được liệt kê trong phụ lục đối soát. Tác động tới lợi nhuận là diễn giải có điều kiện, chưa phải dự báo định lượng.",small)
    else:
        bullet(research.get("macro", []) or [r["text"] for r in data.get("macro_analysis",[])])
        add("Cơ chế liên hệ với ngành: " + sector["context"])
        add("Các yếu tố cần giám sát: " + "; ".join(sector["drivers"]), small)
    chapter(3, "Giá và giao dịch")
    if data["prices"]:
        story.append(chart(data, "price"))
        story.append(chart(data, "volume"))
    table(["Thước đo", "Kết quả", "Cách hiểu"], [
        ["MA20 / MA50", fmt(m["ma20"], "price") + " / " + fmt(m["ma50"], "price"), "Trung bình 20 / 50 phiên, đủ số phiên mới tính"],
        ["Khối lượng TB", fmt(m["volume_20"]), "Trung bình tối đa 20 phiên cuối"],
        ["Biến động năm hóa", fmt(m["volatility"], "percent"), "Độ lệch chuẩn lợi suất ngày × căn(252)"],
        ["Sụt giảm lớn nhất", fmt(m["drawdown"], "percent"), "So với đỉnh tích lũy trong khoảng đã lưu"],
        ["So với VN-Index", fmt(m["relative_20"], "percent"), "Chênh lệch điểm phần trăm qua 20 phiên có ngày chung"],
    ], [5*cm,4.5*cm,8.1*cm])
    add("Nguồn KBS qua vnstock; cổ phiếu chuẩn hóa về VND, chỉ số giữ đơn vị điểm. Đây là dữ liệu lịch sử/EOD, không phải luồng realtime. Lợi suất không bao gồm cổ tức tiền mặt; cơ sở điều chỉnh chưa được xác minh; lịch sử có thể được sửa hồi tố.", small)
    chapter(4, "Doanh nghiệp và tài chính")
    rows = data["financials"]
    if rows:
        headers = ["Chỉ tiêu"] + [r["period"] for r in rows]
        fields = ["assets", "equity", "operating_income" if sector["key"] == "bank" else "revenue", "net_income",
                  "roe", "roa", "cir" if sector["key"] == "bank" else "net_margin",
                  "debt_assets"] + ([] if sector["key"] == "bank" else ["cfo", "current_ratio"])
        table(headers, [[LABELS[field]] + [fmt(r.get(field), "percent" if field in ["roe", "roa", "net_margin", "debt_assets", "cir"] else "number" if field == "current_ratio" else "billion") for r in rows] for field in fields],
              [5.6*cm] + [12*cm/len(rows)]*len(rows))
        add("Đơn vị số tiền: tỷ đồng. Tỷ lệ: %. Thanh toán hiện hành: lần. “Chưa có” không phải bằng 0.", small)
        story.append(chart(data, "financial"))
        add("Diễn giải kết quả tài chính", h2)
        bullet(research.get("financial", []))
        if research.get("quality_warnings"):
            add("Cảnh báo chất lượng BCTC", h2)
            bullet(research["quality_warnings"][:5])
    else:
        add("Chưa có BCTC trong bộ dữ liệu.")
    quarters = data.get("quarterly_financials",[])
    if quarters:
        add("BCTC quý theo nguồn",h2)
        qfields=[("assets","Tổng tài sản"),("equity","Vốn chủ sở hữu"),
                 ("operating_income" if sector["key"]=="bank" else "revenue","Thu nhập hoạt động" if sector["key"]=="bank" else "Doanh thu thuần"),
                 ("net_income","LNST"),("cfo","Dòng tiền kinh doanh")]
        selected=quarters[-4:]
        table(["Chỉ tiêu"]+[r["period"] for r in selected],
              [[label]+[fmt(r["fields"].get(key,{}).get("value"),"billion") for r in selected] for key,label in qfields],
              [5.6*cm]+[12*cm/len(selected)]*len(selected))
        add("Đơn vị: tỷ đồng. "+quarters[-1]["note"],small)
    add("Phạm vi đối soát số liệu", h2)
    if review:
        add(review["limitations"],small)
    else:
        add("BCTC năm lấy từ Parquet tham khảo hoặc file được nhập; báo cáo quý có nguồn riêng. Phạm vi hợp nhất/riêng lẻ chưa được xác minh bằng báo cáo kiểm toán; năm báo cáo không đồng nghĩa với ngày công bố. Không ghép EPS lịch sử với giá hiện tại để tự suy ra P/E khi chưa kiểm tra chia tách và cổ tức cổ phiếu.", small)
    chapter(5, "Phân tích ngành và tin tức")
    if review:
        add("Từ ngành ngân hàng đến VCB",h2)
        bullet(review["bank_to_company"])
    add("Nhận định nhóm đối chiếu",h2)
    bullet(research.get("industry", []) or data.get("peer_analysis", []))
    add("Doanh nghiệp so sánh cùng kỳ", h2)
    summary = data.get("peer_summary", {})
    if data["peers"]:
        add(f"Năm so sánh: {summary.get('period') or 'chưa có'}. Nhóm {summary.get('peer_count', 0)} đối thủ đề xuất, "
            f"{summary.get('peers_with_financials', 0)} đối thủ có BCTC cùng kỳ. "
            f"Nguồn ngành: {summary.get('source','hồ sơ tham khảo')}.", small)
        table(["Mã", "Năm", "DT/TOI (tỷ)", "LNST (tỷ)", "Tăng LN", "ROE", "ROA"],
              [[r["symbol"], r["period"], fmt(r.get("revenue"), "billion"),
                fmt(r.get("net_income"), "billion"), fmt(r.get("profit_growth"), "percent"),
                fmt(r.get("roe"), "percent"), fmt(r.get("roa"), "percent")] for r in data["peers"]],
              [1.5*cm,1.6*cm,3.0*cm,3.0*cm,2.9*cm,2.8*cm,2.8*cm])
        med = summary.get("medians", {})
        if med:
            add("Trung vị chỉ lấy từ các đối thủ có số liệu hợp lệ: ROE " + fmt(med.get("roe"), "percent") +
                "; ROA " + fmt(med.get("roa"), "percent") +
                "; tăng LNST " + fmt(med.get("profit_growth"), "percent") + ".", small)
        add(summary.get("valuation_note", "P/B, P/E cần nguồn và cơ sở cổ phiếu lưu hành đồng nhất."), small)
    else:
        add("Chưa có BCTC của doanh nghiệp đang phân tích để lập bảng cùng kỳ.")
    add("Nhóm doanh nghiệp được tự đề xuất theo ICB/cấu hình tham khảo; cần kiểm tra sự tương đồng mô hình kinh doanh, phạm vi BCTC và kỳ số liệu. Không coi trung vị là giá trị hợp lý của doanh nghiệp.", small)
    add("Sự kiện và luận điểm từ nguồn tin được chọn", h2)
    selected = research.get("news_theses", [])
    if selected:
        for item in selected:
            add(item["heading"], h2)
            add(item["text"])
        add("Tin RSS chỉ phản ánh tiêu đề/tóm tắt do nguồn đăng; tác động phân tích luôn ở dạng điều kiện và phải đối chiếu với dữ liệu công bố.", small)
    else:
        add("Chưa có bản tin đủ liên quan và phù hợp nguồn để đưa thành luận điểm. Không chèn tin chung chỉ để đủ nội dung.")
    chapter(6, "Cơ hội và rủi ro")
    add("Tổng hợp luận điểm từ dữ liệu có thể kiểm tra", h2)
    bullet(research.get("executive", []) or [data["opportunity"]["conclusion"]])
    # Only historical context is displayed. Saved valuation scenarios are intentionally
    # ignored; neither target prices nor scenario multiples belong in this report.
    ctx = data.get("valuation", {}).get("inputs", {})
    if ctx:
        add("Chỉ số P/E lịch sử tham khảo", h2)
        table(["Chỉ tiêu", "Dữ liệu"], [
            ["Giá lưu / ngày", fmt(ctx.get("price"), "price") + " / " + str(ctx.get("price_date") or "chưa có")],
            ["EPS năm " + str(ctx.get("year") or ""), fmt(ctx.get("historical_eps"), "price")],
            ["P/E lịch sử (chưa đối soát chia tách)", fmt(ctx.get("historical_pe")) + " lần" if ctx.get("historical_pe") is not None else "Chưa có"],
            ["P/E trung vị đối thủ (ít nhất 3 mã)", fmt(ctx.get("peer_pe_median_indicative")) + " lần" if ctx.get("peer_pe_median_indicative") is not None else "Chưa đủ dữ liệu"],
        ], [8.7*cm, 8.9*cm])
        add("Chỉ số lịch sử chỉ để tham khảo, không phải giá mục tiêu hay khuyến nghị. EPS và giá cần đối chiếu sự kiện cổ phiếu trước khi sử dụng.", small)
        for warning in ctx.get("warnings", [])[:3]:
            add("Lưu ý dữ liệu: " + warning, small)
    add("Rủi ro", h2)
    bullet(data["opportunity"]["risks"][:6])
    add("Điều kiện cần kiểm tra thêm", h2)
    add("; ".join(data["opportunity"]["next_checks"]))
    chapter(7, "Dữ liệu, phương pháp và nguồn")
    table(["Nhóm", "Trạng thái", "Phạm vi"], [[r["group"],r["status"],r["detail"]] for r in data["coverage"]], [4.2*cm,2*cm,11.4*cm])
    add("Quy tắc tính toán", h2)
    bullet(data["methodology"])
    add("Tài liệu và bài báo được tham chiếu trong phần nhận định", h2)
    if research.get("references"):
        for ref in research["references"]:
            add(f"[{ref['id']}] {ref['title']} | {ref['published_at']} | {ref['status']}", small)
            add(ref["url"], small)
    else:
        add("Không chọn được bài báo phù hợp. Các chỉ tiêu tài chính và giá có nguồn lưu trữ riêng.", small)
    add("Nguồn dữ liệu gốc và dấu vết thu thập", h2)
    for s in data["sources"]:
        if s.get("file") == "valuations.json":
            continue  # Historical valuation scenario files stay on disk, not in report
        add(s.get("source", s["file"]) + "  |  " + s["file"], small)
        add(s.get("source_url", "") + "  |  Kỳ: " + str(s.get("as_of", "ghi theo dòng")), small)
    if data["macro"]:
        add("Vĩ mô: " + data["macro"][0]["source_url"], small)
    add("Dấu kiểm tra SHA-256 và ngày thu thập nằm trong manifest.json đi cùng bộ dữ liệu. Tái lập bằng cùng bộ dữ liệu, cấu hình và phiên bản source; không gọi API trong lúc lập báo cáo.", small)

    if review:
        chapter(8,"Đối soát và bằng chứng")
        add("Ngày rà soát: "+review["reviewed_at"]+". "+review["cutoff"],small)
        table(["Chỉ tiêu / kỳ","Giá trị","Kết quả / vị trí nguồn"],
              [[r["metric"]+"\n"+r["period"],r["value"],r["status"]+"\n"+r["source"]+": "+r["location"]] for r in review["audit"]],
              [4.4*cm,3.5*cm,9.7*cm])
        add(review["limitations"],small)
        story.append(PageBreak())
        add("Nguồn đối chiếu",h1)
        for source in review["sources"]:
            add(source["id"]+" / "+source["title"],h2)
            add(source["url"],small)
        add("ROE sử dụng LNST hợp nhất gồm lợi ích không kiểm soát và tổng VCSH cùng phạm vi. Đơn vị gốc BCTN là triệu VND; chia 1.000 để trình bày tỷ VND. Không đồng nhất ROE này với mọi cách tính bình quân của bên cung cấp.",body)
        add("Bộ dữ liệu nộp được giữ cố định và có SHA-256. Phân tích và xuất PDF chạy offline sau khi cài thư viện. Nhận định đã rà soát tự ngừng áp dụng khi các đầu vào liên quan thay đổi.",body)

    def footer(canvas, document):
        canvas.saveState()
        width, height = document.pagesize
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(.6)
        canvas.line(1.7*cm, height-1.45*cm, width-1.7*cm, height-1.45*cm)
        canvas.setFont("Research-Bold", 8)
        canvas.setFillColor(BLUE)
        canvas.drawString(1.7*cm, height-1.17*cm, "VN EQUITY RESEARCH")
        canvas.setFont("Research", 7)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(width-1.7*cm, height-1.17*cm, data["symbol"] + " / " + data["mode"])
        canvas.drawString(1.7*cm, 1*cm, "Phân tích từ dữ liệu đã lưu • Xem kỳ tham chiếu và giới hạn dữ liệu")
        canvas.drawRightString(width-1.7*cm, 1*cm, str(document.page))
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer, canvasmaker=partial(Canvas, invariant=1))
    return output
