"""Tests for one visible dataset with a non-destructive frozen real-data merge."""
import json
from pathlib import Path
import pandas as pd
import pytest

from vnresearch.storage import Store
from vnresearch.unified import MARKER, unify_submission_into_local


def _fake_parquet(monkeypatch):
    # CI environments without pyarrow: emulate the persistence layer using pickle.
    monkeypatch.setattr(pd, "read_parquet", lambda path, **kwargs: pd.read_pickle(path))
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, path, **kw: self.to_pickle(path))


def _frames():
    cols = ["symbol", "date", "open", "high", "low", "close", "volume", "price_basis", "source", "unit"]
    prices = pd.DataFrame([
        ["VCB", "2026-10-08", 57000, 58000, 56000, 56600, 1000, "kbs_provider", "frozen", "VND"],
        ["FPT", "2026-10-08", 108000, 110000, 106000, 107000, 1000, "kbs_provider", "frozen", "VND"],
        ["VNINDEX", "2026-10-08", 1600, 1700, 1500, 1650, 1000, "kbs_provider", "frozen", "index_points"],
    ], columns=cols)
    financials = pd.DataFrame([
        ["VCB", "2025", "assets", 10.0],
        ["FPT", "2025", "assets", 20.0],
    ], columns=["symbol", "period", "item_code", "value"])
    return prices, financials


def _write_baseline(base):
    sub = Store("submission", base)
    prices, financials = _frames()
    sub.write("prices.parquet", prices, {"source":"test"}, bootstrap=True)
    sub.write("financials.parquet", financials, {"source":"test"}, bootstrap=True)
    sub.write_json("companies.json", {"VCB":{"sector":"bank"},"FPT":{"sector":"technology"}}, {}, bootstrap=True)
    sub.write_json("news.json", [{"symbol":"VCB","url":"https://test/story", "title":"archived"}], {}, bootstrap=True)
    sub.write_json("macro.json", [{"indicator":"gdp", "period":"2026", "basis":"yoy", "value":9}], {}, bootstrap=True)
    sub.write_json("research_reviews.json", {"VCB":{"input_sha256":"unmatched"}}, {}, bootstrap=True)
    return sub


def test_new_machine_gets_real_baseline_no_demo(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    _write_baseline(tmp_path)
    sample = Store("sample", tmp_path)
    sample.write_json("companies.json", {"FAK":{"name":"DEMO"}}, {}, bootstrap=True)
    result = unify_submission_into_local(Store("local",tmp_path))
    local = Store("local", tmp_path)
    assert result["added_price_rows"] == 3
    assert result["added_annual_rows"] == 2
    assert set(local.read("prices.parquet").symbol) == {"VCB", "FPT", "VNINDEX"}
    assert "FAK" not in local.read_json("companies.json")
    assert local.read_json("research_reviews.json")["VCB"]
    assert all(c["ok"] for c in local.verify())
    assert unify_submission_into_local(local)["status"] == "already_initialized"


def test_existing_local_wins_with_missing_rows_added(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    _write_baseline(tmp_path)
    local = Store("local", tmp_path)
    prices, fin = _frames()
    local_prices = prices.iloc[[0]].copy()
    local_prices.loc[local_prices.index[0], "close"] = 59000
    local_prices.loc[local_prices.index[0], "source"] = "manual verified"
    local.write("prices.parquet", local_prices, {})
    local.write("financials.parquet", pd.DataFrame([["VCB","2025","assets",999.0]], columns=fin.columns), {})
    local.write_json("companies.json", {"VCB":{"sector":"manual"}}, {})
    local.write_json("news.json", [{"symbol":"VCB","url":"https://test/story", "title":"user checked"}], {})
    local.write_json("macro.json", [{"indicator":"gdp", "period":"2026", "basis":"yoy", "value":12}], {})
    result = unify_submission_into_local(local)
    merged = local.read("prices.parquet")
    assert len(merged) == 3
    assert merged.loc[merged.symbol=="VCB","close"].iloc[0] == 59000
    assert result["added_price_rows"] == 2
    facts = local.read("financials.parquet")
    assert len(facts) == 2 and facts.loc[facts.symbol=="VCB","value"].iloc[0] == 999
    assert local.read_json("companies.json")["VCB"]["sector"] == "manual"
    assert local.read_json("news.json")[0]["title"] == "user checked"
    assert local.read_json("macro.json")[0]["value"] == 12
    assert all(c["ok"] for c in local.verify())


def test_price_basis_conflicts_skip_ticker(tmp_path,monkeypatch):
    _fake_parquet(monkeypatch)
    _write_baseline(tmp_path)
    local = Store("local",tmp_path)
    prices, _ = _frames()
    old = prices.iloc[[0]].copy()
    old.loc[old.index[0],"price_basis"] = "raw"
    local.write("prices.parquet", old, {})
    result = unify_submission_into_local(local)
    assert result["skipped_price_symbols"] == ["VCB"]
    assert len(local.read("prices.parquet")) == 3
    assert local.read("prices.parquet").loc[lambda d: d.symbol=="VCB", "price_basis"].iloc[0] == "raw"


def test_missing_frozen_data_fails_without_completion_marker(tmp_path,monkeypatch):
    _fake_parquet(monkeypatch)
    local = Store("local", tmp_path)
    with pytest.raises(ValueError,match="Thiếu dữ liệu"):
        unify_submission_into_local(local)
    assert not (local.path / MARKER).exists()


def test_interface_has_single_dataset():
    page=(Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")
    js=(Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert '<input type="hidden" id="mode" value="local">' in page
    assert 'value="sample"' not in page and 'value="submission"' not in page
    assert '/api/initialize-local' in js


def test_http_initialization_endpoint(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    _write_baseline(tmp_path)
    from vnresearch import web, unified
    from fastapi.testclient import TestClient
    monkeypatch.setattr(unified, "Store", lambda mode="local", base=None: Store(mode, tmp_path if base is None else base))
    client = TestClient(web.app)
    first = client.post("/api/initialize-local")
    assert first.status_code == 200
    assert first.json()["added_price_rows"] == 3
    again = client.post("/api/initialize-local")
    assert again.status_code == 200
    assert again.json()["status"] == "already_initialized"
    assert client.post("/api/initialize-local",headers={"origin":"https://attacker.example"}).status_code == 403
