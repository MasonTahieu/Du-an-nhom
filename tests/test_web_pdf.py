import hashlib
import socket
from pathlib import Path
from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest

from vnresearch.web import app
from vnresearch.storage import Store
from vnresearch.analysis import analyze
from vnresearch.report import build_pdf


def test_pages_and_analysis_work_without_network(monkeypatch):
    original_connect = socket.socket.connect
    def blocked(sock, address):
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        raise AssertionError("Offline operation attempted external network access")
    monkeypatch.setattr(socket.socket,"connect",blocked)
    client=TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    status=client.get("/api/status").json()
    assert status["verified"]
    for ticker in ["VCB","FPT","HPG"]:
        r=client.get("/api/analysis/"+ticker)
        assert r.status_code == 200
        assert r.json()["symbol"] == ticker
    assert client.get("/api/analysis/ZZZ").status_code == 400
    assert client.get("/api/status?mode=bad").status_code == 400
    assert client.get("/api/template/not-allowed").status_code == 404


def test_pdf_contains_required_sections_vietnamese_and_is_stable(tmp_path,monkeypatch):
    def blocked(*args,**kwargs):
        raise AssertionError("PDF attempted network")
    monkeypatch.setattr(socket.socket,"connect",blocked)
    data=analyze(Store(),"VCB")
    a,b=tmp_path/"a.pdf",tmp_path/"b.pdf"
    build_pdf(data,a);build_pdf(data,b)
    pdf=PdfReader(a)
    text="\n".join(p.extract_text() for p in pdf.pages)
    assert 7 <= len(pdf.pages) <= 9
    for phrase in ["TỔNG QUAN ĐẦU TƯ","VĨ MÔ","GIÁ VÀ GIAO DỊCH","TÀI CHÍNH","TIN TỨC","ĐỊNH GIÁ","PHƯƠNG PHÁP","Lợi nhuận"]:
        assert phrase in text
    assert hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()


def test_wrong_origin_cannot_modify_data():
    client=TestClient(app)
    assert client.post("/api/seed-local",headers={"origin":"https://unrelated.example"}).status_code == 403


def test_invalid_news_is_400_and_does_not_write(tmp_path,monkeypatch):
    import vnresearch.web as web
    monkeypatch.setattr(web,"Store",lambda mode="sample":Store(mode,tmp_path))
    client=TestClient(app)
    r=client.post("/api/import",json={"kind":"news","content":"[{}]"})
    assert r.status_code == 400
    assert not (tmp_path/"local"/"news.json").exists()
