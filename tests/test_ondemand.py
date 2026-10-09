import threading
import pytest
from vnresearch.storage import Store
from vnresearch import ondemand
from vnresearch.locking import process_lock

@pytest.fixture(autouse=True)
def isolated_annual_repair(monkeypatch):
    from vnresearch import financials, peers
    monkeypatch.setattr(peers, "suggest", lambda *a, **k: {"peers": [], "note": "", "sector_source": "test"})
    monkeypatch.setattr(peers, "refresh_industry_catalog", lambda *a, **k: {})
    monkeypatch.setattr(financials, "repair_annual_sources", lambda *a, **k: {"status": "complete"})


def test_unknown_exchange_falls_back_and_history_partial_is_not_success(tmp_path, monkeypatch):
    s=Store("local",tmp_path)
    monkeypatch.setattr(ondemand.collectors,"init_profiles",lambda store: None)
    calls=[]
    def annual(store, tickers, commit, exchange, year):
        calls.append(exchange)
        if exchange=="HSX": raise ValueError("Không có BCTC")
        return {"rows":1}
    monkeypatch.setattr(ondemand.collectors,"fetch_annual_reference",annual)
    monkeypatch.setattr(ondemand.history,"prepare_history",lambda *a,**k: {"status":"rate_limited","failed":[]})
    r=ondemand.load_one(s,"ABC")
    assert calls==["HSX","HNX"]
    assert r["status"]=="partial"
    assert s.read_json("companies.json")["ABC"]["sector"]=="other"

def test_upcom_annual_unavailable_does_not_block_prices(tmp_path, monkeypatch):
    s=Store("local",tmp_path)
    s.write_json("universe.json",{"symbols":[{"symbol":"ABC","exchange":"UPCOM"}]}, {})
    monkeypatch.setattr(ondemand.collectors,"init_profiles",lambda store: None)
    monkeypatch.setattr(ondemand.collectors,"fetch_annual_reference",lambda *a,**k: pytest.fail("Must not fetch UPCoM annual"))
    calls=[]
    def price(store, tickers, **kwargs):
        calls.extend(tickers)
        return {"status":"complete"}
    monkeypatch.setattr(ondemand.history,"prepare_history",price)
    r=ondemand.load_one(s,"ABC")
    assert calls==["ABC","VNINDEX"]
    assert r["status"]=="partial"

def test_one_background_job_and_cross_process_lock(tmp_path):
    entered, release=threading.Event(),threading.Event()
    def runner(*a,**kw):
        entered.set()
        assert release.wait(3)
        return {"status":"complete"}
    jobs=ondemand.LoadJobs(lambda:Store("local",tmp_path),runner)
    jobs.start("FPT")
    assert entered.wait(3)
    try:
        with pytest.raises(RuntimeError):jobs.start("HPG")
        with pytest.raises(RuntimeError):
            with process_lock(tmp_path/"local"/".ingestion.lock"):pass
    finally:release.set()

def test_load_api_does_not_start_on_read(monkeypatch):
    from fastapi.testclient import TestClient
    from vnresearch import web
    class Jobs:
        def current(self):return None
        def start(self,ticker,extended):
            return {"symbol":ticker,"extended":extended}
    monkeypatch.setattr(web,"_LOAD_JOBS",Jobs())
    client=TestClient(web.app)
    assert client.get("/api/load-status").json()=={"job":None}
    assert client.post("/api/load/FPT",json={"extended":False}).status_code==202
