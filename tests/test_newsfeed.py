"""Offline tests for RSS metadata, tagging, preservation, and user action."""
from __future__ import annotations
import json
import pytest
from vnresearch.storage import Store
from vnresearch import newsfeed, ondemand

FEED = b'''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>CafeF</title>
<item><title>Vietcombank va VietinBank cong bo ket qua kinh doanh</title>
<link>https://cafef.vn/vcb-ctg-20261009.chn?utm_source=test</link>
<description><![CDATA[<p>VCB, CTG cap nhat loi nhuan</p>]]></description>
<pubDate>Fri, 09 Oct 2026 08:30:00 +0700</pubDate></item>
<item><title>Lai suat dieu hanh thay doi</title>
<link>https://cafef.vn/lai-suat-20261009.chn</link><description>Chinh sach tien te</description>
<pubDate>Fri, 09 Oct 2026 08:30:00 +0700</pubDate></item>
<item><title>Malformed external link</title><link>https://evil.example/attack</link>
<pubDate>Fri, 09 Oct 2026 08:30:00 +0700</pubDate></item>
</channel></rss>'''


def test_rss_parse_metadata_urls_and_dates():
    records = newsfeed.parse_feed(FEED)
    assert len(records) == 2
    assert records[0]["url"] == "https://cafef.vn/vcb-ctg-20261009.chn"
    assert records[0]["summary"] == "VCB, CTG cap nhat loi nhuan"
    assert records[0]["published_at"] == "2026-10-09"
    with pytest.raises(ValueError): newsfeed.safe_url("https://cafef.vn.evil.example/rss")
    with pytest.raises(ValueError): newsfeed.safe_url("http://cafef.vn/feed.rss")


def test_ticker_multilabel_sector_and_macro():
    profiles = {"VCB":{"sector":"bank"}, "CTG":{"sector":"bank"}, "HPG":{"sector":"steel"}}
    a = newsfeed.classify("Vietcombank và Vietinbank báo lãi", "", {"sector":"bank"}, profiles)
    assert a["symbols"] == ["CTG", "VCB"]
    assert a["category"] == "company"
    assert a["sectors"] == ["bank"]
    b = newsfeed.classify("Lãi suất điều hành đổi", "NHNN công bố", {"category":"macro"}, profiles)
    assert b["symbols"] == []
    assert b["category"] == "macro"
    assert newsfeed.relevant_news({"category":"sector","sectors":["steel"],"symbols":[]},"HPG","steel") == (False,False,True)
    assert newsfeed.relevant_news({"category":"sector","sectors":["steel"],"symbols":[]},"VCB","bank") == (False,False,False)
    assert newsfeed.relevant_news({"symbol":"VCB","title":"Legacy"},"VCB","bank")[0] is True
    assert not newsfeed.classify("Người mai tham dự", "", {}, profiles)["symbols"]


def test_merge_preserves_prior_review_and_idempotency():
    old = [{"symbol":"VCB", "title":"Review", "url":"https://cafef.vn/vcb-ctg-20261009.chn", "published_at":"2026-10-09", "summary":"Đã đối soát", "content_status":"user_reviewed"}]
    new = [{"symbol":"CTG", "symbols":["CTG"], "sectors":["bank"],"topics":[], "category":"company", "title":"RSS", "url":old[0]["url"], "published_at":"2026-10-09", "summary":"Tin RSS", "content_status":"rss_metadata"}]
    out,added,matched = newsfeed.merge_records(old,new)
    assert (added, matched)==(0,1)
    assert out[0]["summary"] == "Đã đối soát"
    assert out[0]["content_status"] == "user_reviewed"
    assert out[0]["symbols"] == ["CTG", "VCB"]
    out2, added2,_=newsfeed.merge_records(out,new)
    assert added2 == 0 and len(out2)==1


def test_fetch_partial_and_additive_no_parquet(tmp_path, monkeypatch):
    s=Store("local",tmp_path)
    s.write_json("companies.json", {"VCB":{"sector":"bank"},"CTG":{"sector":"bank"}}, {})
    feeds=json.loads((newsfeed.ROOT/"config/news_feeds.json").read_text(encoding="utf-8"))
    assert len(feeds["feeds"])>=4
    def fake(url):
        if url.endswith("tai-chinh-ngan-hang.rss"):raise RuntimeError("blocked by source")
        return FEED
    report=newsfeed.collect_rss_feeds(s,fetch=fake)
    assert report["status"]=="partial"
    assert len(report["failed"])==1
    assert report["unique_fetched"]==2
    records=s.read_json("news.json",[])
    assert len(records)==2
    assert sorted(records[0]["symbols"]) in (["CTG","VCB"], [])
    again=newsfeed.collect_rss_feeds(s,fetch=fake)
    assert again["loaded"]==0
    assert len(s.read_json("news.json",[]))==2


def test_only_user_triggered(monkeypatch,tmp_path):
    s=Store("local",tmp_path)
    calls=[]
    def mock_collect(store):
        calls.append(store.mode)
        return {"status":"complete", "failed":[], "loaded":1}
    monkeypatch.setattr(newsfeed,"collect_rss_feeds",mock_collect)
    monkeypatch.setattr(ondemand,"readiness",lambda s:{"symbols":[],"macro_count":0})
    result=ondemand.load_one(s,"VCB",news_only=True)
    assert calls==["local"]
    assert result["steps"][0]["status"]=="complete"
    assert result["status"]=="complete"
    assert not (s.path/"prices.parquet").exists()


def test_api_news_only_dispatch(monkeypatch):
    from fastapi.testclient import TestClient
    from vnresearch import web
    class FakeJobs:
        def __init__(self): self.calls=[]
        def start(self,ticker,extended=False,news_only=False):
            self.calls.append((ticker,extended,news_only))
            return {"symbol":ticker, "status":"running"}
    jobs=FakeJobs()
    monkeypatch.setattr(web,"_LOAD_JOBS",jobs)
    client=TestClient(web.app)
    r=client.post("/api/load/VND",json={"news_only":True})
    assert r.status_code==202
    assert jobs.calls==[("VND",False,True)]
    assert client.get("/").status_code==200
    assert 'id="loadNewsButton"' in client.get("/").text


def test_analysis_restricts_news_to_correct_company_sector(tmp_path, monkeypatch):
    import pandas as pd
    from vnresearch import storage, analysis
    store=Store("local",tmp_path)
    store.write_json("companies.json",{"VCB":{"name":"VCB","sector":"bank","peers":[]}}, {})
    store.write_json("news.json",[
      {"title":"VCB news", "url":"https://cafef.vn/1.chn", "published_at":"2026-10-09","symbol":"VCB","symbols":["VCB"],"category":"company"},
      {"title":"Other steel sector", "url":"https://cafef.vn/2.chn", "published_at":"2026-10-09","symbol":"MARKET","sectors":["steel"],"category":"sector"},
      {"title":"Bank industry", "url":"https://cafef.vn/3.chn", "published_at":"2026-10-09","symbol":"MARKET","sectors":["bank"],"category":"sector"},
      {"title":"GDP", "url":"https://cafef.vn/4.chn", "published_at":"2026-10-09","symbol":"MARKET","category":"macro"}
    ], {})
    def mock_read(self,name):
        if name=="prices.parquet":
            return pd.DataFrame([{"symbol":"VCB","date":"2026-10-09","open":50000,"high":50000,"low":50000,"close":50000,"volume":1000,"price_basis":"kbs_provider"}])
        return pd.DataFrame()
    monkeypatch.setattr(storage.Store,"read",mock_read)
    r=analysis.analyze(store,"VCB")
    assert [n["title"] for n in r["company_news"]]==["VCB news"]
    assert [n["title"] for n in r["sector_news"]]==["Bank industry"]
    assert [n["title"] for n in r["macro_news"]]==["GDP"]
    assert all(n["title"]!="Other steel sector" for n in r["news"])
    assert r["sector"]["key"]=="bank"


def test_provisional_sector_for_vnd():
    assert newsfeed.sector_for_ticker("VND", {"sector":"other"})=="securities"
    assert newsfeed.sector_for_ticker("VND", {"sector":"bank"})=="bank"
    assert newsfeed.sector_for_ticker("XYZ", {"sector":"other"})=="other"
