"""Smoke tests for the research-only StockInsight report and front end."""
from pathlib import Path
from vnresearch.insights import conclusion

ROOT = Path(__file__).resolve().parents[1]

def test_frontend_has_no_scenario_form_or_result():
    app = (ROOT/'static/app.js').read_text(encoding='utf-8')
    nav = (ROOT/'static/index.html').read_text(encoding='utf-8')
    assert 'Lập và lưu kịch bản P/E' not in app
    assert 'Kết quả định giá' not in app
    assert 'valuationForm' not in app
    assert 'Chỉ số P/E lịch sử tham khảo' in app
    assert '◇ Cơ hội & rủi ro' in nav

def test_conclusion_never_mentions_price_scenarios():
    market = {'rows':30, 'return_20':0.05}
    latest = {'net_income':100,'profit_growth':0.04}
    for v in ({'available':False},{'available':True,'scenarios':[{'target':1234}]}):
        t=conclusion(latest,market,v)
        assert 'kịch bản' not in t and 'giả định' not in t

def test_pdf_source_does_not_render_saved_scenarios():
    report = (ROOT/'vnresearch/report.py').read_text(encoding='utf-8')
    assert 'chapter(6, "Cơ hội và rủi ro")' in report
    assert 'v["scenarios"]' not in report
    assert 'Giá theo giả định' not in report

def test_pdf_ignores_previously_saved_price_targets(tmp_path, monkeypatch):
    import pandas as pd
    import fitz
    from vnresearch import storage
    from vnresearch.analysis import analyze
    from vnresearch.report import build_pdf

    rows=[]
    for sym in ("SSI", "HCM"):
        for year in ("2024", "2025"):
            vals={"assets":80000000000000.0,"equity":30000000000000.0,
                  "net_income":3000000000000.0,"eps":2000.0} if year == "2024" else {
                  "assets":90000000000000.0,"equity":35000000000000.0,
                  "net_income":3500000000000.0,"eps":2200.0}
            for key,val in vals.items():
                rows.append({"symbol":sym,"period":year,"item_code":key,"value":val,"scope":"consolidated","unit":"VND"})
    fs=pd.DataFrame(rows)
    days=pd.bdate_range("2026-08-01",periods=50)
    px=pd.DataFrame([{"symbol":s,"date":day.strftime('%Y-%m-%d'),"close":20000.0 + idx * 10,
                      "volume":1000000.0,"price_basis":"kbs_provider"}
                     for idx,day in enumerate(days) for s in ("SSI","HCM","VNINDEX")])
    monkeypatch.setattr(storage.Store, "read", lambda self, name: {
        "financials.parquet":fs,"prices.parquet":px}.get(name,pd.DataFrame()))
    store=storage.Store("local",tmp_path)
    store.write_json("companies.json",{"SSI":{"name":"SSI","sector":"securities","peers":["HCM"]}}, {})
    store.write_json("valuations.json",{"SSI":{"method":"PE","basis":"forecast",
        "per_share":1000000.0,"multiple":50.0,"as_of":"2026-10-09",
        "source_url":"https://example.org/reviewed","reviewed":True,"reference_price":20000.0}}, {})
    data=analyze(store,"SSI")
    assert data["valuation"]["available"]
    assert data["valuation"]["scenarios"]
    target=data["valuation"]["scenarios"][1]["target"]
    path=tmp_path/"report.pdf"
    build_pdf(data,path)
    with fitz.open(path) as doc:
        text="\n".join(p.get_text() for p in doc)
    assert "CƠ HỘI VÀ RỦI RO" in text
    assert "Kết quả định giá" not in text
    assert "Định giá và kịch bản" not in text
    assert "Giá mục tiêu" not in text
    assert "Giá theo giả định" not in text
    assert "Giá kịch bản" not in text
    assert "50.000.000" not in text  # Previously saved PE scenario must not render
    assert "Chỉ số P/E lịch sử tham khảo" in text
    assert "Lưu ý dữ liệu" in text or "lịch sử chỉ để tham khảo" in text
