import pandas as pd
import pytest
from vnresearch.storage import Store, validate_prices, symbol


def prices(close=100):
    return pd.DataFrame([dict(symbol="VCB", date="2026-10-08", open=100, high=110, low=90, close=close, volume=1000, price_basis="adjusted")])


def test_upsert_is_idempotent_and_refreshes_same_day(tmp_path):
    store = Store("local", tmp_path)
    store.merge_prices(prices(), {})
    store.merge_prices(prices(), {})
    assert len(store.read("prices.parquet")) == 1
    store.merge_prices(prices(105), {})
    assert store.read("prices.parquet").iloc[0].close == 105
    assert all(c["ok"] for c in store.verify())


@pytest.mark.parametrize("field,value", [("close", -1), ("high", 50), ("low", 150), ("volume", -1), ("volume", 1.2), ("high", float("inf"))])
def test_bad_prices_do_not_overwrite_existing_file(tmp_path, field, value):
    store = Store("local", tmp_path)
    store.merge_prices(prices(), {})
    original = (store.path / "prices.parquet").read_bytes()
    d = prices()
    d[field] = value
    with pytest.raises(ValueError):
        store.merge_prices(d, {})
    assert (store.path / "prices.parquet").read_bytes() == original


def test_sample_is_protected(tmp_path):
    with pytest.raises(ValueError, match="demo"):
        Store("sample", tmp_path).merge_prices(prices(), {})


def test_price_basis_cannot_silently_change(tmp_path):
    store = Store("local", tmp_path)
    store.merge_prices(prices(), {})
    d = prices()
    d.price_basis = "raw"
    with pytest.raises(ValueError, match="điều chỉnh"):
        store.merge_prices(d, {})


def test_manifest_detects_corruption(tmp_path):
    store = Store("local", tmp_path)
    store.write_json("news.json", [], {})
    (store.path / "news.json").write_text("[1]", encoding="utf-8")
    assert store.verify()[0]["ok"] is False


@pytest.mark.parametrize("ticker", ["../VCB", "VCB/..", "ABC;pwd", "a" * 20])
def test_symbol_rejects_paths_and_commands(ticker):
    with pytest.raises(ValueError):
        symbol(ticker)
