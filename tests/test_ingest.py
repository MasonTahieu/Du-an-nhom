import pandas as pd
import pytest
from datetime import datetime, timezone
from vnresearch.storage import Store
import vnresearch.ingest as ingest


@pytest.mark.parametrize("utc_time,expected", [
    ("2026-10-09T08:29:59", "2026-10-08"),
    ("2026-10-09T08:30:00", "2026-10-09"),
    ("2026-10-09T09:00:00", "2026-10-09"),
    ("2026-10-10T08:29:00", "2026-10-09"),
    ("2026-10-10T08:30:00", "2026-10-09"),
    ("2026-10-11T08:30:00", "2026-10-09"),
    ("2026-10-12T08:29:59", "2026-10-09"),
    ("2026-10-12T08:30:00", "2026-10-12"),
])
def test_completed_session_uses_1530_vietnam_time_and_skips_weekends(monkeypatch, utc_time, expected):
    instant = datetime.fromisoformat(utc_time).replace(tzinfo=timezone.utc)
    class Clock:
        @staticmethod
        def now(tz):
            return instant.astimezone(tz)
    monkeypatch.setattr(ingest, "datetime", Clock)
    assert ingest.completed_session() == expected


class PriceDomain:
    def __init__(self,ticker): self.ticker=ticker
    def ohlcv(self,**kwargs):
        if self.ticker=="ERR":
            raise ValueError("source failure")
        return pd.DataFrame([
            dict(time="2026-10-08",open=100,high=110,low=90,close=105,volume=1000),
            dict(time="2026-10-09",open=100,high=110,low=90,close=105,volume=1000)
        ])
class Market:
    def equity(self,ticker): return PriceDomain(ticker)
    def index(self,ticker): return PriceDomain(ticker)


def test_source_unit_conversion_and_incomplete_day_filter(tmp_path,monkeypatch):
    monkeypatch.setattr(ingest,"_vnstock",lambda:(Market,None))
    monkeypatch.setattr(ingest,"completed_session",lambda:"2026-10-08")
    store=Store("local",tmp_path)
    ingest.fetch_prices(store,["VCB","VNINDEX"],"2026-10-01","2026-10-09")
    d=store.read("prices.parquet")
    assert len(d)==2
    assert d.date.max()=="2026-10-08"
    assert d.loc[d.symbol=="VCB","close"].iloc[0]==105000
    assert d.loc[d.symbol=="VNINDEX","close"].iloc[0]==105
    assert set(d.price_basis)=={"kbs_provider"}


def test_partial_source_failure_keeps_previous_prices(tmp_path,monkeypatch):
    monkeypatch.setattr(ingest,"_vnstock",lambda:(Market,None))
    monkeypatch.setattr(ingest,"completed_session",lambda:"2026-10-08")
    store=Store("local",tmp_path)
    ingest.fetch_prices(store,["VCB"],"2026-10-01")
    before=(store.path/"prices.parquet").read_bytes()
    with pytest.raises(ValueError):
        ingest.fetch_prices(store,["VCB","ERR"],"2026-10-01")
    assert (store.path/"prices.parquet").read_bytes()==before


def test_kbs_relative_news_url_is_normalized_without_inventing_content(tmp_path,monkeypatch):
    class Company:
        def news(self,**kwargs):
            return pd.DataFrame([dict(title="Tin nguồn",url="/2026/09/article.htm",publish_time="2026-09-10T09:10:25")])
    class Reference:
        def company(self,ticker):return Company()
    monkeypatch.setattr(ingest,"_vnstock",lambda:(None,Reference))
    store=Store("local",tmp_path)
    assert ingest.fetch_news(store,["VCB"],2)==1
    news=store.read_json("news.json")[0]
    assert news["url"]=="https://vietstock.vn/2026/09/article.htm"
    assert news["summary"]==""
    assert news["content_status"]=="metadata_only"


def test_seed_does_not_overwrite_personal_files(tmp_path,monkeypatch):
    sample,local=Store("sample",tmp_path),Store("local",tmp_path)
    sample.write_json("news.json",[{"title":"demo"}],{},bootstrap=True)
    local.write_json("news.json",[{"title":"personal"}],{})
    monkeypatch.setattr(ingest,"Store",lambda mode:Store(mode,tmp_path))
    ingest.seed_local()
    assert local.read_json("news.json")==[{"title":"personal"}]
    assert sample.read_json("news.json")==[{"title":"demo"}]


def test_eps_unit_must_be_per_share():
    d=pd.DataFrame([dict(symbol="VCB",period="2025",item_code="eps",value=3000,unit="VND",scope="consolidated",source_url="https://example.com")])
    with pytest.raises(ValueError,match="VND/share"):
        ingest.validate_financials(d)
