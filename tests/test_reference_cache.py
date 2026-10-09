"""Offline tests for shared Tumiqa Parquet caching and non-destructive imports."""
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from vnresearch.storage import Store
from vnresearch import collectors, reference_cache

COMMIT = "f8cad8d7d4276cd22aee20113fe3214230daf919"
FAKE_PARQUET = b"PAR1" + b"test-contents" * 4 + b"PAR1"


def _fake_read_parquet(path, columns=None, filters=None):
    if columns is not None:
        return pd.DataFrame(columns=list(columns))
    kind = next(k for k in reference_cache.STATEMENTS if k in str(path))
    ticker = "FPT"
    if filters and (ticker not in filters[0][2]):
        return pd.DataFrame(columns=["ticker", "year", "item_code", "item_name", "value"])
    return pd.DataFrame([dict(ticker=ticker, year=2025, item_code=f"{kind}_item",
                              item_name=kind, value=100.0)])


def test_shared_cache_download_once_for_multiple_symbols(tmp_path, monkeypatch):
    store = Store("local", tmp_path)
    monkeypatch.setattr(reference_cache.pd, "read_parquet", _fake_read_parquet)
    calls = []
    def fetch(url, timeout):
        calls.append(url)
        return SimpleNamespace(content=FAKE_PARQUET)
    for kind in reference_cache.STATEMENTS:
        _, downloaded = reference_cache.ensure_file(store, COMMIT, "HSX", kind, getter=fetch)
        assert downloaded
    for kind in reference_cache.STATEMENTS:
        path, downloaded = reference_cache.ensure_file(store, COMMIT, "HSX", kind, getter=fetch)
        assert path.is_file() and not downloaded
        assert path.with_suffix(".sha256").exists()
    assert len(calls) == 3


def test_bad_download_does_not_replace_cache(tmp_path, monkeypatch):
    store = Store("local", tmp_path)
    monkeypatch.setattr(reference_cache.pd, "read_parquet", _fake_read_parquet)
    ref = reference_cache
    path, _ = ref.ensure_file(store, COMMIT, "HSX", "cash_flow",
                              getter=lambda *_: SimpleNamespace(content=FAKE_PARQUET))
    before = path.read_bytes()
    path.with_suffix(".sha256").write_text("0" * 64)
    with pytest.raises(ValueError, match="không phải Parquet"):
        ref.ensure_file(store, COMMIT, "HSX", "cash_flow",
                        getter=lambda *_: SimpleNamespace(content=b"<html>unavailable</html>"))
    assert path.read_bytes() == before


def test_migrate_old_reference_cache_without_internet(tmp_path, monkeypatch):
    store = Store("local", tmp_path)
    monkeypatch.setattr(reference_cache.pd, "read_parquet", _fake_read_parquet)
    legacy = store.path / "raw" / "reference" / COMMIT / "src/arminer/data/bctc_data/income_statement/HSX.parquet"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(FAKE_PARQUET)
    path, downloaded = reference_cache.ensure_file(store, COMMIT, "HSX", "income_statement",
                                    getter=lambda *_: pytest.fail("Should reuse local copy"))
    assert not downloaded and path.read_bytes() == FAKE_PARQUET


def test_tumiqa_import_reuses_cache_and_preserves_existing_year(tmp_path, monkeypatch):
    store = Store("local", tmp_path)
    monkeypatch.setattr(collectors.pd, "read_parquet", _fake_read_parquet)
    monkeypatch.setattr(reference_cache.pd, "read_parquet", _fake_read_parquet)
    requests = []
    monkeypatch.setattr(reference_cache, "_http_download", lambda url, timeout: (
        requests.append(url) or FAKE_PARQUET))
    saved = pd.DataFrame()
    saved_writes = []
    def read(name):
        return saved.copy()
    def write(name, frame, metadata):
        nonlocal saved
        saved = frame.copy()
        saved_writes.append(metadata)
    monkeypatch.setattr(store, "read", read)
    monkeypatch.setattr(store, "write", write)
    first = collectors.fetch_annual_reference(store, ["FPT"], COMMIT, "HSX", 2022)
    assert first["rows"] == 3
    assert len(saved) == 3
    assert len(requests) == 3
    second = collectors.fetch_annual_reference(store, ["FPT"], COMMIT, "HSX", 2022)
    assert second["rows"] == 0
    assert second["skipped_years"] == [{"symbol": "FPT", "year": "2025"}]
    assert len(requests) == 3
    assert len(saved_writes) == 1


def test_existing_reviewed_values_never_overwritten(tmp_path, monkeypatch):
    store = Store("local", tmp_path)
    monkeypatch.setattr(collectors.pd, "read_parquet", _fake_read_parquet)
    monkeypatch.setattr(reference_cache.pd, "read_parquet", _fake_read_parquet)
    monkeypatch.setattr(reference_cache, "_http_download", lambda *_: FAKE_PARQUET)
    reviewed = pd.DataFrame([dict(symbol="FPT", period="2025", item_code="verified_revenue",
                                  item_name="Doanh thu đối soát", value=999.0, unit="VND",
                                  scope="consolidated", source_url="https://example.com/source")])
    monkeypatch.setattr(store, "read", lambda _: reviewed)
    monkeypatch.setattr(store, "write", lambda *a, **k: pytest.fail("Do not overwrite reviewed year"))
    result = collectors.fetch_annual_reference(store, ["FPT"], COMMIT, "HSX", 2022)
    assert result["rows"] == 0
    assert len(result["skipped_years"]) == 1
