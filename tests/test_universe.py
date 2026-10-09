import socket
import pandas as pd
import pytest
from vnresearch.storage import Store
from vnresearch.universe import fetch_universe, market_symbols
from vnresearch import manual, web

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs): raise AssertionError("No downloads in tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)

def source():
    rows=[{"symbol":f"A{i:02d}","exchange":["HSX","HNX","UPCOM"][i%3],"organ_name":f"Company {i}","type":"STOCK"} for i in range(30)]
    return pd.DataFrame(rows+[{"symbol":"ETF","exchange":"HOSE","type":"ETF"},{"symbol":"CVNM01","exchange":"HOSE","type":"CW"}])

def test_catalogue_full_scope_and_failed_refresh_preserves(tmp_path):
    s=Store("local",tmp_path)
    result=fetch_universe(s,fetch=source)
    assert result["symbols"]==30 and result["excluded"]==2
    assert len(market_symbols(s,["HOSE"]))==10
    before=(s.path/"universe.json").read_bytes()
    with pytest.raises(ValueError): fetch_universe(s,fetch=lambda:source().iloc[:1])
    assert (s.path/"universe.json").read_bytes()==before

def test_all_market_dry_run_and_override(tmp_path,monkeypatch):
    s=Store("local",tmp_path)
    fetch_universe(s,fetch=source)
    monkeypatch.setattr(manual,"Store",lambda mode:s)
    result=manual.run("history",all_market=True,dry_run=True,start="2026-01-01",end="2026-01-02")
    assert len({r["symbol"] for r in result["tasks"]})==31
    result=manual.run("history",all_market=True,limit=3,dry_run=True,start="2026-01-01",end="2026-01-02")
    assert len({r["symbol"] for r in result["tasks"]})==4
    assert manual.run("context",["VNM"],all_market=True,dry_run=True)["symbols"]==["VNM"]

def test_status_includes_unloaded_catalogue(tmp_path,monkeypatch):
    s=Store("local",tmp_path)
    fetch_universe(s,fetch=source)
    monkeypatch.setattr(web,"Store",lambda mode:s)
    result=web.status("local")
    assert len(result["symbols"])==30
    assert all(r["has_data"] is False for r in result["symbols"])
    assert {r["exchange"] for r in result["symbols"]}=={"HOSE","HNX","UPCOM"}

