"""Offline security, provenance and reproducibility checks for the valuation patch."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from vnresearch.valuation_engine import historical_context, validate_input
from vnresearch.analysis import financial_rows, valuation


def annual():
    return pd.DataFrame([
      {"symbol": t, "period": "2025", "item_code":"eps", "value": ep, "unit":"VND/share", "source_url":"https://example.org/2025"}
      for t,ep in {"SSI":1000,"HCM":2000,"VND":1000,"VCI":3000}.items()
    ])


def prices():
    return pd.DataFrame([{"symbol":t,"date":"2026-10-09","close":price,"price_basis":"kbs_provider"}
                        for t,price in {"SSI":24000,"HCM":20000,"VND":13000,"VCI":45000}.items()])


def test_history_metrics_and_peer_median_labeled_indicative():
    rows=[{"symbol":t} for t in ["SSI","HCM","VND","VCI"]]
    d=historical_context(annual(),prices(),"SSI",rows,financial_rows,"securities")
    assert d["historical_eps"] == 1000
    assert d["historical_pe"] == 24
    assert d["peer_pe_count"] == 3
    assert d["peer_pe_median_indicative"] == 13
    assert d["historical_pb"] is None
    assert d["default_method"] == "PB"
    assert any("chưa" in msg.lower() for msg in d["warnings"])


def test_no_false_pb_and_no_multiple_from_too_few_peers():
    d=historical_context(annual(),prices(),"SSI",[{"symbol":"HCM"}],financial_rows,"securities")
    assert d["peer_pe_median_indicative"] is None
    assert d["historical_bvps"] is None


def test_eps_wrong_units_cannot_create_pe():
    a=annual(); a.loc[a.symbol=="SSI", "unit"]="VND"
    d=historical_context(a, prices(), "SSI", [], financial_rows,"securities")
    assert d["historical_pe"] is None
    assert d["historical_eps"] is None


@pytest.mark.parametrize("source",["http://example.org","file:///secret","https://user@example.com","invalid"])
def test_disallow_unsafe_sources(source):
    with pytest.raises(ValueError):
        validate_input(dict(method="PE",basis="historical",per_share=2000,multiple=10,source_url=source,as_of="2026-10-09",reviewed=True))


def test_requires_confirmation_and_method_basis():
    entry=dict(method="PB",basis="historical",per_share=16000,multiple=1.5,source_url="https://example.org/research",as_of="2026-10-09",reviewed=False)
    with pytest.raises(ValueError,match="xác nhận"):
        validate_input(entry)
    entry["reviewed"]=True
    assert validate_input(entry)["per_share"]==16000
    v=valuation(validate_input(entry),24000)
    assert v["basis"]=="historical"
    assert v["scenarios"][1]["target"]==24000
    assert "lịch sử" in v["message"]


def test_saved_reference_price_is_stable():
    saved=dict(method="PE",basis="forecast",per_share=2000,multiple=12,source_url="https://example.org",as_of="2026-10-09",reviewed=True,reference_price=20000)
    v=valuation(saved, saved["reference_price"])
    assert v["scenarios"][1]["upside"]==pytest.approx(.2)


def test_api_preview_does_not_write_and_save_does(monkeypatch):
    import vnresearch.web as web
    class FakeStore:
        def __init__(self):
            self.saved={}
            self.writes=[]
        def read(self,name):
            assert name=="prices.parquet"
            return prices()
        def read_json(self,name,default=None):
            return self.saved.get(name, default)
        def write_json(self,name,data,meta):
            self.saved[name]=data
            self.writes.append((name,meta))
    fake=FakeStore()
    monkeypatch.setattr(web,"Store",lambda mode:fake)
    client=TestClient(web.app)
    payload=dict(method="PE",basis="historical",per_share=1500,multiple=12,source_url="https://example.org/report",as_of="2026-10-09",reviewed=True,note="Kiểm chứng số cổ phiếu")
    bad={**payload,"reviewed":False}
    assert client.post("/api/valuation/SSI",json=bad).status_code==400
    result=client.post("/api/valuation-preview/SSI",json=payload)
    assert result.status_code==200,result.text
    assert not fake.writes
    posted=client.post("/api/valuation/SSI",json=payload)
    assert posted.status_code==200,posted.text
    assert fake.saved["valuations.json"]["SSI"]["reference_price"]==24000
    assert fake.writes[0][0]=="valuations.json"
    assert client.post("/api/valuation/SSI",json=payload,headers={"origin":"https://evil.example"}).status_code==403
