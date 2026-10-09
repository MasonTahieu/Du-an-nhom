"""Deterministic analysis checks: no AI, no invented news or duplicated annual facts."""
import json
from pathlib import Path
import pandas as pd
from vnresearch.analysis import financial_rows, analyze
from vnresearch.storage import Store
from vnresearch.research_rules import compile_research


def fake_analysis(symbol="SSI"):
    base = {
        "symbol":symbol, "sector":{"key":"securities", "label":"Dịch vụ chứng khoán"},
        "market":{"return_20":-0.064,"date":"2026-10-09"}, "financials":[],
        "peer_summary":{"peers_with_financials":0}, "peer_analysis":[], "data_quality":[], "macro":[],
        "company_news":[], "sector_news":[], "macro_news":[],
    }
    return base


def test_repeated_2024_2025_blocked_without_modifying_source():
    data=[]
    for year in ("2024","2025"):
        for name,val in (("assets",73507),("equity",26826),("net_income",2845),("revenue",0)):
            data.append({"symbol":"SSI","period":year,"item_code":name,"value":val})
    raw = pd.DataFrame(data)
    rows=financial_rows(raw,"SSI","securities")
    assert rows[-1]["quality_status"] == "suspect_duplicate_year"
    assert rows[-1]["profit_growth"] is None
    assert rows[-1]["roe"] is None
    assert rows[-1]["net_income"] is None
    assert rows[0]["revenue"] is None
    assert len(raw)==8 and raw.loc[(raw.period=="2025") & (raw.item_code=="net_income"),"value"].iloc[0] == 2845


def test_rss_metadata_only_does_not_become_verified_fact_and_filter_macro():
    d=fake_analysis()
    d["macro_news"]=[
        {"category":"macro","url":"https://cafef.vn/housing","title":"Xã An Khánh: nhà ở xã hội", "summary":"Nhà xưởng vi phạm","published_at":"2026-10-09","content_status":"rss_metadata"},
        {"category":"macro","url":"https://cafef.vn/rate","title":"Lãi suất tăng trên thị trường", "summary":"Lãi suất thị trường có biến động", "published_at":"2026-10-08","content_status":"rss_metadata"},
    ]
    d["sector_news"]=[
        {"category":"sector","url":"https://cafef.vn/liquidity","title":"Thanh khoản thị trường chứng khoán thay đổi", "summary":"Giá trị giao dịch cần quan sát", "published_at":"2026-10-08", "sectors":["securities"],"content_status":"rss_metadata"},
        {"category":"sector","url":"https://cafef.vn/other","title":"Rồng Việt thay đổi hội đồng quản trị", "summary":"Cổ đông VDS", "published_at":"2026-10-09", "sectors":["securities"],"symbols":["VDS"],"content_status":"rss_metadata"},
    ]
    result=compile_research(d)
    urls=[x["url"] for x in result["references"]]
    assert "https://cafef.vn/housing" not in urls
    assert "https://cafef.vn/other" not in urls
    assert "https://cafef.vn/rate" in urls
    assert "https://cafef.vn/liquidity" in urls
    assert len(result["news_theses"])==2
    assert "có thể" in result["news_theses"][0]["text"]
    assert "chưa" in result["news_theses"][0]["text"]


def test_only_cached_article_body_keywords_used_no_fetch(tmp_path):
    store=Store("local",tmp_path)
    store.write_json("raw/news/ssi.json",{
        "url":"https://publisher.vn/ssi", "text":"Phần nội dung bài báo đề cập tới thanh khoản, dư nợ margin. "*10
    },{"source":"test"})
    d=fake_analysis()
    d["company_news"]=[{
       "title":"SSI cập nhật hoạt động môi giới","summary":"Tin doanh nghiệp", "url":"https://publisher.vn/ssi",
       "published_at":"2026-10-09","symbol":"SSI","body_file":"raw/news/ssi.json",
       "content_status":"extracted_unreviewed"
    }]
    result=compile_research(d,store)
    assert len(result["news_theses"])==1
    assert "Văn bản đã lưu" in result["news_theses"][0]["text"]
    assert "chưa được đối soát" in result["news_theses"][0]["text"]


def test_analysis_and_pdf_with_repeated_year_and_headlines(monkeypatch,tmp_path):
    import vnresearch.storage as storage
    import vnresearch.analysis as a
    from vnresearch.report import build_pdf
    data=[]
    for sym in ("SSI", "HCM"):
        for year in ("2024", "2025"):
            values={"assets":73507.,"equity":26826.,"net_income":2845.,"revenue":0.} if sym=="SSI" else {
                   "assets":(50000. if year=="2024" else 52000.),"equity":(20000. if year=="2024" else 23000.),
                   "net_income":(1500. if year=="2024" else 2100.),"revenue":4300.}
            for name,val in values.items():
                data.append({"symbol":sym,"period":year,"item_code":name,"value":val,"source_url":"https://example.org","unit":"VND"})
    financials=pd.DataFrame(data)
    px=pd.DataFrame([{"symbol":"SSI","date":f"2026-09-{i:02d}","close":20000.+i,"volume":1000.,"price_basis":"kbs_provider"} for i in range(1,29)])
    monkeypatch.setattr(storage.Store,"read",lambda self,name: {"financials.parquet":financials,"prices.parquet":px}.get(name,pd.DataFrame()))
    store=Store("local",tmp_path)
    store.write_json("companies.json",{"SSI":{"name":"CTCP Chứng khoán SSI","sector":"securities","peers":[]}}, {})
    store.write_json("news.json",[
      {"category":"macro","url":"https://cafef.vn/housing","title":"Xã An Khánh nhà ở xã hội", "summary":"Nhà xưởng", "published_at":"2026-10-09","content_status":"rss_metadata"},
      {"category":"company","url":"https://cafef.vn/ssi","title":"Chứng khoán SSI công bố kế hoạch hoạt động", "summary":"Tình hình margin và thanh khoản", "published_at":"2026-10-08","symbols":["SSI"],"content_status":"rss_metadata"},
    ],{})
    got=a.analyze(store,"SSI")
    assert got["financials"][-1]["net_income"] is None
    assert got["data_quality"]
    assert len(got["research"]["references"])==1
    assert got["research"]["references"][0]["url"]=="https://cafef.vn/ssi"
    assert got["valuation"]["available"] is False
    json.dumps(got,allow_nan=False,ensure_ascii=False)
    dest=tmp_path/"ssi_research.pdf"
    build_pdf(got,dest)
    assert dest.exists() and dest.stat().st_size > 10000
    import fitz
    document=fitz.open(dest)
    all_text="\n".join(p.get_text() for p in document)
    assert "Sự kiện và luận điểm" in all_text
    assert "Cảnh báo chất lượng BCTC" in all_text
    assert "https://cafef.vn/ssi" in all_text
    assert "https://cafef.vn/housing" not in all_text
    assert "Định giá và kịch bản" not in all_text
    assert "Giá theo giả định" not in all_text
    assert "Kịch bản" not in all_text
    assert all_text.find("https://cafef.vn/ssi") > all_text.find("Cơ hội và rủi ro")
