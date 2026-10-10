"""Regression tests for every-sector 2022 ratios with offline opening-year data."""
from pathlib import Path
import json
import pandas as pd
import pytest
from vnresearch.storage import Store
from vnresearch.analysis import financial_rows, analyze
from vnresearch.annual_baseline import (
    backfill_from_cache, facts_for_analysis, display_first_year, BASELINE_FILE
)
from vnresearch.quality import readiness


def _fake_parquet(monkeypatch):
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, path, **kw: self.to_pickle(path))
    monkeypatch.setattr(pd, "read_parquet", lambda path, **kw: pd.read_pickle(path))


def _records(ticker, year, sector, k):
    top = ("operating_income" if sector == "bank" else
           "securities_revenue" if sector == "securities" else "revenue")
    return [dict(symbol=ticker, period=str(year), statement=statement,
                 item_code=name, item_name=name, value=value, unit="VND",
                 scope="provider_unspecified", source_url="https://source.test/reference")
            for statement, name, value in (
                ("balance_sheet", "assets", 100*k),
                ("balance_sheet", "equity", 50*k),
                ("balance_sheet", "liabilities", 50*k),
                ("income_statement", top, 75*k),
                ("income_statement", "net_income", 10*k),
                ("cash_flow", "cfo", 8*k))]


@pytest.mark.parametrize("sector", ("bank", "securities", "real_estate", "technology", "steel", "retail", "energy", "oil_gas", "telecom", "other"))
def test_calc_2022_with_opening_year_in_all_sectors(sector, tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    store = Store("local", tmp_path)
    store.write("financials.parquet", pd.DataFrame(_records("ZZZ", 2022, sector, 1.2)), {})
    store.write(BASELINE_FILE, pd.DataFrame(_records("ZZZ", 2021, sector, 1.0)), {})
    combined = facts_for_analysis(store)
    rows = financial_rows(combined, "ZZZ", sector)
    year_2022 = next(r for r in rows if r["period"] == "2022")
    assert year_2022["roa"] == pytest.approx(12/110)
    assert year_2022["roe"] == pytest.approx(12/55)
    assert year_2022["revenue_growth"] == pytest.approx(0.2)
    assert year_2022["net_income"] == 12
    state = readiness(store)
    row = next(r for r in state["symbols"] if r["symbol"] == "ZZZ")
    assert row["annual_periods"] == ["2022"]
    assert "2021" not in row["annual_missing_fields"]
    # The main historic record never receives the synthetic/fake opening year.
    assert set(store.read("financials.parquet").period) == {"2022"}


def test_opening_year_never_replaces_existing_user_annual(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    store = Store("local", tmp_path)
    primary = pd.DataFrame(_records("ZZZ", 2021, "bank", 9) + _records("ZZZ", 2022, "bank", 1.2))
    store.write("financials.parquet", primary, {})
    store.write(BASELINE_FILE, pd.DataFrame(_records("ZZZ", 2021, "bank", 1.0)), {})
    facts = facts_for_analysis(store)
    rows = financial_rows(facts, "ZZZ", "bank")
    assert rows[0]["assets"] == 900.0 and len(facts) == len(primary)


def test_offline_cache_missing_does_not_make_zeros(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    store = Store("local", tmp_path)
    store.write("financials.parquet", pd.DataFrame(_records("ZZZ", 2022, "technology", 1.2)), {})
    before = (store.path / "financials.parquet").read_bytes()
    result = backfill_from_cache(store)
    assert result["status"] == "no_cache_match" and result["added_rows"] == 0
    assert (store.path / "financials.parquet").read_bytes() == before
    assert not (store.path / BASELINE_FILE).exists()


def test_cache_backfill_and_second_run_idempotent(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    store = Store("local", tmp_path)
    annual = pd.DataFrame(_records("ZZZ", 2022, "technology", 1.2))
    store.write("financials.parquet", annual, {})
    # Original public Tumiqa Parquet format but encoded as pickles for this
    # environment, where pyarrow is unavailable. Read path API is the same.
    files = {}
    for statement, field_values in (
        ("balance_sheet", [("bs_tong_tai_san", 100), ("bs_von_chu_so_huu", 50)]),
        ("income_statement", [("is_doanh_thu_thuan", 75), ("is_loi_nhuan_sau_thue", 10)]),
        ("cash_flow", [("cf_luu_chuyen_tien_thuan_tu_hoat_dong_kinh_doanh", 8)]),
    ):
        path = tmp_path / f"{statement}.parquet"
        pd.DataFrame([dict(ticker="ZZZ", year=2021, item_code=code, item_name=code,
                           value=val) for code, val in field_values]).to_pickle(path)
        files[("HSX", statement)] = path
    original = (store.path / "financials.parquet").read_bytes()
    result = backfill_from_cache(store, paths=files)
    assert result["status"] == "complete" and result["added_symbols"] == ["ZZZ"]
    assert result["added_rows"] == 5
    assert set(store.read(BASELINE_FILE).period) == {"2021"}
    assert store.verify() and all(r["ok"] for r in store.verify())
    assert (store.path / "financials.parquet").read_bytes() == original
    again = backfill_from_cache(store, paths=files)
    assert again["status"] == "already_complete" and again["added_rows"] == 0


def test_known_scope_refuses_unknown_reference_mix(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    store = Store("local", tmp_path)
    annual = pd.DataFrame(_records("ZZZ", 2022, "technology", 1.2))
    annual["scope"] = "consolidated"
    store.write("financials.parquet", annual, {})
    files = {}
    for statement in ("balance_sheet", "income_statement", "cash_flow"):
        path = tmp_path / f"{statement}.parquet"
        pd.DataFrame([dict(ticker="ZZZ", year=2021, item_code="bs_tong_tai_san", item_name="Tổng tài sản", value=100)]).to_pickle(path)
        files[("HSX", statement)] = path
    result = backfill_from_cache(store, paths=files)
    assert result["added_rows"] == 0
    assert not (store.path / BASELINE_FILE).exists()


def test_no_baseline_alone_cannot_appear_as_company_facts(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    store = Store("local", tmp_path)
    store.write(BASELINE_FILE, pd.DataFrame(_records("ZZZ", 2021, "bank", 1.0)), {})
    assert facts_for_analysis(store).empty


def test_web_analysis_hides_2021_but_displays_2022_ratios(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    store = Store("local", tmp_path)
    store.write_json("companies.json", {"ZZZ": {"name": "Test technology", "sector": "technology", "peers": []}}, {})
    store.write("financials.parquet", pd.DataFrame(_records("ZZZ", 2022, "technology", 1.2)), {})
    store.write(BASELINE_FILE, pd.DataFrame(_records("ZZZ", 2021, "technology", 1.0)), {})
    answer = analyze(store, "ZZZ")
    assert [r["period"] for r in answer["financials"]] == ["2022"]
    assert answer["financials"][0]["roa"] == pytest.approx(12/110)
    assert answer["financials"][0]["roe"] == pytest.approx(12/55)
    assert answer["financials"][0]["revenue_growth"] == pytest.approx(.2)
    assert "1 năm" in next(r["detail"] for r in answer["coverage"] if r["group"] == "Báo cáo tài chính")


def test_later_consolidated_source_change_disables_unverified_baseline(tmp_path, monkeypatch):
    _fake_parquet(monkeypatch)
    store = Store("local", tmp_path)
    store.write("financials.parquet", pd.DataFrame(_records("ZZZ", 2022, "bank", 1.2)), {})
    store.write(BASELINE_FILE, pd.DataFrame(_records("ZZZ", 2021, "bank", 1.0)), {})
    assert financial_rows(facts_for_analysis(store), "ZZZ", "bank")[-1]["roa"] is not None
    newer = store.read("financials.parquet")
    newer["scope"] = "consolidated"
    store.write("financials.parquet", newer, {})
    assert financial_rows(facts_for_analysis(store), "ZZZ", "bank")[-1]["roa"] is None
