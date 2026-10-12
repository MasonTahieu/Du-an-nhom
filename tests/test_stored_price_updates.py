"""Stored-only selection and delayed daily prices, without downloading or editing user data."""
import socket
from pathlib import Path

import pandas as pd
import pytest

from vnresearch import history, manual
from vnresearch.storage import Store


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not download data")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(history, "completed_session", lambda: "2026-10-12")


def candle(day, close=10):
    return pd.DataFrame([dict(time=day, open=close, high=close+1,
                              low=close-1, close=close, volume=100)])


def seed(store, tickers=("VCB", "FPT", "VNINDEX")):
    prices = pd.concat([history.normalize(candle("2026-10-09"), ticker,
                        "2026-10-09", "2026-10-09") for ticker in tickers], ignore_index=True)
    store.merge_prices(prices, {"source": "test"})
    store.write_json("companies.json", {"HPG": {"name": "Profile only"}}, {})
    store.write_json("universe.json", {"symbols": [{"symbol": "AAA", "exchange": "HOSE"}]}, {})
    store.write("financials.parquet", pd.DataFrame([dict(symbol="CTG", value=123)]), {})
    store.write_json("news.json", [{"symbol": "SSI", "title": "News only"}], {})


def snapshot(path):
    return {p.relative_to(path): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def test_stored_dry_run_selects_only_priced_stocks_and_benchmark_without_writes(tmp_path, monkeypatch):
    store = Store("local", tmp_path)
    seed(store)
    monkeypatch.setattr(manual, "Store", lambda mode: store)
    before = snapshot(store.path)
    result = manual.run("history", stored=True, dry_run=True)
    assert result["symbols"] == ["FPT", "VCB", "VNINDEX"]
    assert {t["symbol"] for t in result["tasks"]} == {"FPT", "VCB", "VNINDEX"}
    assert result["cutoff"] == "2026-10-12"
    assert snapshot(store.path) == before


@pytest.mark.parametrize("benchmark_only", [False, True])
def test_stored_empty_stock_list_reports_how_to_load_without_falling_back(tmp_path, monkeypatch, benchmark_only):
    store = Store("local", tmp_path)
    if benchmark_only:
        seed(store, ("VNINDEX",))
    monkeypatch.setattr(manual, "Store", lambda mode: store)
    before = snapshot(store.path)
    with pytest.raises(ValueError, match="Nạp ít nhất một mã trên web"):
        manual.run("history", stored=True, dry_run=True)
    assert snapshot(store.path) == before


@pytest.mark.parametrize("kind,kwargs", [
    ("financials", {}),
    ("history", {"all_market": True}),
    ("history", {"tickers": ["HPG"]}),
    ("history", {"exchanges": ["HOSE"]}),
])
def test_stored_rejects_options_that_would_change_its_scope(tmp_path, monkeypatch, kind, kwargs):
    monkeypatch.setattr(manual, "Store", lambda mode: Store(mode, tmp_path))
    with pytest.raises(ValueError, match="--stored chỉ dùng cập nhật giá đã lưu"):
        manual.run(kind, stored=True, dry_run=True, **kwargs)
    assert not (tmp_path / "local").exists()


def test_stored_update_preserves_history_and_other_datasets_using_existing_price_flow(tmp_path, monkeypatch):
    store = Store("local", tmp_path)
    seed(store)
    monkeypatch.setattr(manual, "Store", lambda mode: store)
    before = snapshot(store.path)
    prior_prices = store.read("prices.parquet")
    calls = []
    prepare = history.prepare_history
    def fetch(ticker, start, end):
        calls.append((ticker, start, end))
        return candle(end, 12)
    def update(store, tickers, start, end, **kwargs):
        return prepare(store, tickers, start, end, fetch=fetch, delay=0, **kwargs)
    monkeypatch.setattr(history, "prepare_history", update)
    result = manual.run("history", stored=True)
    assert result["status"] == "complete"
    assert result["pending_latest_symbols"] == []
    assert [t for t, _, _ in calls] == ["FPT", "VCB", "VNINDEX"]
    assert {(start, end) for _, start, end in calls} == {("2026-09-29", "2026-10-12")}
    prices = store.read("prices.parquet")
    pd.testing.assert_frame_equal(prices.loc[prices.date == "2026-10-09"].reset_index(drop=True),
                                  prior_prices.reset_index(drop=True))
    assert len(prices) == 6 and not prices.duplicated(["symbol", "date"]).any()
    latest = prices.loc[prices.date == "2026-10-12"].set_index("symbol")
    assert latest.loc["FPT", "close"] == 12000
    assert latest.loc["VNINDEX", "close"] == 12
    assert set(prices.price_basis) == {"kbs_provider"}
    for name in ("companies.json", "universe.json", "financials.parquet", "news.json"):
        assert (store.path / name).read_bytes() == before[Path(name)]
    assert all(row["ok"] for row in store.verify())


def test_delayed_latest_session_is_retryable_and_successful_session_is_reused(tmp_path):
    store = Store("local", tmp_path)
    seed(store, ("FPT",))
    result = history.prepare_history(store, ["FPT"], fetch=lambda *a: candle("2026-10-09"),
                                     delay=0, progress=lambda _: None)
    assert result["pending_latest_symbols"] == ["FPT"]
    assert result["coverage"][0]["last"] == "2026-10-09"
    assert "FPT" not in store.read_json("history-progress.json")["checked"]
    calls = []
    def ready(*args):
        calls.append(args)
        return candle("2026-10-12")
    result = history.prepare_history(store, ["FPT"], fetch=ready, delay=0, progress=lambda _: None)
    assert len(calls) == 1
    assert result["pending_latest_symbols"] == []
    assert store.read_json("history-progress.json")["checked"]["FPT"] == "2026-10-12"
    assert set(store.read("prices.parquet").date) == {"2026-10-09", "2026-10-12"}
    result = history.prepare_history(store, ["FPT"], fetch=ready, delay=0, progress=lambda _: None)
    assert len(calls) == 1 and result["network_calls"] == 0


def test_legacy_checked_date_and_completed_chunk_cannot_hide_a_missing_session(tmp_path):
    store = Store("local", tmp_path)
    seed(store, ("FPT",))
    task = history.plan(store, ["FPT"])["tasks"][0]
    raw_file = "raw/prices/FPT/legacy.parquet"
    store.write(raw_file, candle("2026-10-09"), {})
    store.write_json("history-progress.json", {
        "checked": {"FPT": "2026-10-12"},
        "chunks": {task["key"]: {**task, "status": "complete", "dates": ["2026-10-09"],
                                 "raw_file": raw_file}},
    }, {})
    result = history.plan(store, ["FPT"])
    assert result["reused_symbols"] == []
    assert result["tasks"][0]["status"] == "pending"
    result = history.prepare_history(store, ["FPT"], fetch=lambda *a: candle("2026-10-09"),
                                     delay=0, progress=lambda _: None)
    assert result["network_calls"] == 1 and result["pending_latest_symbols"] == ["FPT"]
    assert "FPT" not in store.read_json("history-progress.json")["checked"]


def test_incomplete_last_chunk_retries_without_redownloading_earlier_history(tmp_path):
    store = Store("local", tmp_path)
    def delayed(ticker, start, end):
        return candle("2026-10-09" if end == "2026-10-12" else end)
    result = history.prepare_history(store, ["FPT"], "2026-01-01", fetch=delayed,
                                     delay=0, progress=lambda _: None)
    assert result["network_calls"] == 2 and result["pending_latest_symbols"] == ["FPT"]
    calls = []
    def ready(ticker, start, end):
        calls.append(end)
        return candle(end)
    result = history.prepare_history(store, ["FPT"], "2026-01-01", fetch=ready,
                                     delay=0, progress=lambda _: None)
    assert calls == ["2026-10-12"] and result["reused"] == 1
    assert result["pending_latest_symbols"] == []
