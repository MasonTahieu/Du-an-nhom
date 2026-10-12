"""PDF source links preserve the complete URI even when text wraps."""
import hashlib
import json
import socket

from pypdf import PdfReader

from vnresearch.analysis import analyze
from vnresearch.report import build_pdf
from vnresearch.storage import Store


def test_full_source_links_wrap_safely_without_network_or_changing_inputs(tmp_path, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("PDF source links must not fetch articles")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    data = analyze(Store(), "VCB")
    article = (
        "https://cafef.vn/bidv-agribank-vietcombank-vietinbank-se-chan-giao-dich-"
        "nhan-chuyen-tien-neu-su-dung-loat-thiet-bi-sau-188261011082643966.chn"
        "?utm_source=PDF&note=%22A%26B%22#references"
    )
    original_source = "https://publisher.example/financials?year=2025&scope=consolidated"
    macro_source = "https://publisher.example/macro?period=9M2026&type=official"
    audited_source = "https://publisher.example/audit?file=report&section=finance"
    data["research"]["references"] = [{
        "id": 1, "title": 'CafeF: "Ngân hàng & doanh nghiệp" <nguồn>',
        "url": article, "published_at": "2026-10-12",
        "status": "rss_metadata", "category": "company",
    }]
    data["sources"][0]["source_url"] = original_source
    data["sources"].append({"file": "manual.csv", "source": "Nhập tay", "source_url": "see row source_url"})
    data["macro"][0]["source_url"] = macro_source
    data["review"] = {
        "macro_to_bank": [], "bank_to_company": [], "audit": [],
        "limitations": "Nguồn minh họa cho kiểm thử hyperlink.",
        "reviewed_at": "2026-10-12", "cutoff": "2026-10-09",
        "sources": [{"id": "S1", "title": "Báo cáo đối chiếu", "url": audited_source}],
    }
    before = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False)
    first, second = tmp_path / "first.pdf", tmp_path / "second.pdf"
    build_pdf(data, first)
    build_pdf(data, second)
    reader = PdfReader(first)
    targets = []
    for page in reader.pages:
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            action = annotation.get("/A")
            if annotation.get("/Subtype") == "/Link" and action and action.get("/S") == "/URI":
                targets.append(str(action["/URI"]))

    # A long URL has more than one clickable rectangle, all with the same full URI.
    assert targets.count(article) >= 2
    assert {article, original_source, macro_source, audited_source} <= set(targets)
    assert "see row source_url" not in targets
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Mở nguồn:" in text
    assert 'Ngân hàng & doanh nghiệp' in text and "<nguồn>" in text
    assert json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False) == before
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
