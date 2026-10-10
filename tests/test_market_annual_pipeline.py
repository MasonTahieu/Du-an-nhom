"""Offline regression coverage for the shared web/CMD annual pipeline."""
import socket

import pandas as pd
import pytest

from vnresearch import collectors, financials, manual, upcom_annual
from vnresearch.storage import Store


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not access providers")
    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture
def market(tmp_path, monkeypatch):
    store=Store("local",tmp_path)
    store.write_json("universe.json",{"symbols":[
        {"symbol":"AAA","exchange":"HOSE"},
        {"symbol":"BBB","exchange":"HNX"},
        {"symbol":"CCC","exchange":"UPCOM"},
    ]},{})
    store.write_json("companies.json",{"AAA":{"sector":"technology","peers":["ZZZ"]}},{})
    monkeypatch.setattr(manual,"Store",lambda mode:store)
    monkeypatch.setattr(manual,"config",lambda:{"symbols":["AAA"],"first_year":2024,
        "reference_commit":"a"*40,"history_start":"2025-01-01"})
    monkeypatch.setattr(collectors,"init_profiles",lambda store:None)
    return store


def test_full_market_routes_each_exchange_without_adding_peers(market,monkeypatch):
    calls=[]
    def reference(store,tickers,commit,exchange,first_year):
        calls.append((tickers[0],exchange))
        return {"status":"complete"}
    monkeypatch.setattr(collectors,"fetch_annual_reference",reference)
    monkeypatch.setattr(financials,"repair_annual_sources",lambda *a,**k:{"status":"complete"})
    monkeypatch.setattr(upcom_annual,"fetch_annual_vci",lambda store,ticker,**k:
        calls.append((ticker,"VCI")) or {"status":"complete"})
    result=manual.run("financials",all_market=True,annual_only=True)
    assert calls==[("AAA","HSX"),("BBB","HNX"),("CCC","VCI")]
    assert result["completed_symbols"]==["AAA","BBB","CCC"]
    assert result["pending_symbols"]==[] and result["status"]=="complete"
    assert market.read_json("collection-run.json")["completed_symbols"]==["AAA","BBB","CCC"]


def test_missing_first_source_is_warning_when_vci_succeeds(market,monkeypatch):
    def missing(*a,**k):
        raise ValueError("Tumiqa has no ticker")
    monkeypatch.setattr(collectors,"fetch_annual_reference",missing)
    monkeypatch.setattr(financials,"repair_annual_sources",lambda *a,**k:{"status":"complete"})
    result=manual.run("financials",["AAA"],annual_only=True)
    assert result["status"]=="complete" and result["failed"]==[]
    assert result["warnings"] and "Tumiqa" in result["warnings"][0]["error"]


def test_quota_stops_scan_and_records_remaining_symbols(market,monkeypatch):
    calls=[]
    monkeypatch.setattr(collectors,"fetch_annual_reference",lambda *a,**k:{"status":"complete"})
    def limited(store,tickers,**kwargs):
        calls.extend(tickers)
        return {"status":"rate_limited","failed":[{"symbol":tickers[0],"error":"quota"}]}
    monkeypatch.setattr(financials,"repair_annual_sources",limited)
    result=manual.run("financials",all_market=True,annual_only=True)
    assert calls==["AAA"] and result["status"]=="rate_limited"
    assert result["pending_symbols"]==["BBB","CCC"]
    assert result["failed"][0]["symbol"]=="AAA"
    assert market.read_json("collection-run.json")["status"]=="rate_limited"


def test_bad_ticker_does_not_block_next_ticker(market,monkeypatch):
    monkeypatch.setattr(collectors,"fetch_annual_reference",lambda *a,**k:{"status":"complete"})
    monkeypatch.setattr(financials,"repair_annual_sources",lambda store,tickers,**k:
        {"status":"partial","failed":[{"symbol":"AAA","error":"missing income"}]} if tickers==["AAA"]
        else {"status":"complete"})
    monkeypatch.setattr(upcom_annual,"fetch_annual_vci",lambda *a,**k:{"status":"complete"})
    result=manual.run("financials",all_market=True,annual_only=True)
    assert result["status"]=="partial" and result["completed_symbols"]==["BBB","CCC"]
    assert result["pending_symbols"]==[] and result["failed"][0]["symbol"]=="AAA"


def test_provider_quota_keeps_saved_financials_and_stops_batch(tmp_path):
    store=Store("local",tmp_path)
    saved=pd.DataFrame([dict(symbol="AAA",period="2024",item_code="assets",value=100,
                            unit="VND",scope="consolidated",source_url="https://manual.example/report",
                            ingestion_origin="manual_csv")])
    store.write("financials.parquet",saved,{})
    before=(store.path/"financials.parquet").read_bytes()
    calls=[]
    def limited(ticker,*args):
        calls.append(ticker)
        raise SystemExit(1)
    result=financials.repair_annual_sources(store,["AAA","BBB"],first_year=2024,
        through_year=2025,fetch=limited,delay=0,progress=lambda _:None)
    assert result["status"]=="rate_limited" and calls==["AAA"]
    assert (store.path/"financials.parquet").read_bytes()==before


def test_upcom_reuses_complete_saved_years_without_network(tmp_path):
    store=Store("local",tmp_path)
    rows=[]
    for year in ("2024","2025"):
        for key,value in (("assets",100),("equity",40),("liabilities",60),
                          ("revenue",80),("net_income",10),("cfo",5)):
            rows.append(dict(symbol="CCC",period=year,item_code=key,value=value*(1 if year=="2024" else 1.2),
                unit="VND",scope="consolidated",source_url="https://manual.example/report",
                ingestion_origin="manual_csv"))
    store.write("financials.parquet",pd.DataFrame(rows),{})
    before=(store.path/"financials.parquet").read_bytes()
    result=upcom_annual.fetch_annual_vci(store,"CCC",first_year=2024,
        fetch=lambda *a:pytest.fail("Current valid cache must not fetch"))
    assert result["status"]=="complete" and result["source"]=="local_cache"
    assert result["cached_years"]==["2024","2025"]
    assert (store.path/"financials.parquet").read_bytes()==before


def test_data_check_does_not_depend_on_watchlist(market,monkeypatch):
    settings=manual.config()
    settings["symbols"]=[]
    monkeypatch.setattr(manual,"config",lambda:settings)
    result=manual.run("check")
    assert result["mode"]=="local" and "checks" in result
