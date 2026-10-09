"""Regression coverage for missing SSI metrics and clean-machine ingestion."""
import socket
import pandas as pd
import pytest
from vnresearch.storage import Store
from vnresearch.analysis import financial_rows
from vnresearch.financials import (normalize_statement, resolve_fields, suspect_years,
    repair_annual_sources, repair_quarter_cache, PROVIDERS, NORMALIZATION_VERSION)
from vnresearch.collectors import fetch_quarters, REFERENCE
from vnresearch.insights import quarterly_rows

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*a, **k): raise AssertionError("Unit tests must not use Internet")
    monkeypatch.setattr(socket.socket, "connect", blocked)


def raw(statement, period="year"):
    labels = {
        "balance_sheet": [("A. TỔNG TÀI SẢN", "assets", 100), ("B. VỐN CHỦ SỞ HỮU (400=410+420)", "owners_equity", 40),
            ("I. Vốn chủ sở hữu", "equity", 40), ("Nợ phải trả", "liabilities", 60)],
        "income_statement": [("Doanh thu thuần", "net_sales", 30), ("Cộng doanh thu hoạt động (01->11)", "operating_sales", 35),
            ("XI. LỢI NHUẬN KẾ TOÁN SAU THUẾ TNDN", "net_profit", 8),
            ("11.1. Lợi nhuận sau thuế phân bổ cho chủ sở hữu", "parent_profit", 7),
            ("Lãi cơ bản trên cổ phiếu (VND)", "earnings_per_share", 2000),
            ("Cộng doanh thu hoạt động tài chính (41->44)", "financial_sales", 3)],
        "cash_flow": [("Lưu chuyển thuần từ hoạt động kinh doanh chứng khoán", "net_cash_operating", -2)]}
    periods = ["2024", "2025"] if period == "year" else ["2026-Q1", "2026-Q2"]
    d = pd.DataFrame([{ "item": label, "item_id": code, periods[0]: amount, periods[1]: amount*1.1}
                      for label, code, amount in labels[statement]])
    d.attrs = {"unit_type": {p: "Hợp nhất" for p in periods}, "audit_status": {p: "Kiểm toán" for p in periods}}
    return d


def provider(ticker, statement, period, source):
    assert source == "VCI"
    return raw(statement, period)


def test_securities_mapping_keeps_distinct_profit_and_revenue():
    d, notes = normalize_statement(raw("income_statement", "quarter"), "SSI", "income_statement", provider="VCI")
    fields = quarterly_rows(d, "SSI")[0]["fields"]
    assert fields["net_income"]["value"] == 8
    assert fields["parent_income"]["value"] == 7
    assert fields["revenue"]["value"] == 30
    assert fields["securities_revenue"]["value"] == 35
    assert "eps" not in fields
    assert notes["skipped_per_share"]
    # Retained earnings are a balance, never current-period net income.
    retained = pd.DataFrame([{"item": "7. LNST chưa phân phối", "item_id": "retained", "2026-Q2": 60}])
    d, _ = normalize_statement(retained, "SSI", "balance_sheet")
    assert not d.canonical_field.any()


def test_aliases_resolve_per_period_and_different_values_stay_ambiguous():
    d = raw("balance_sheet", "quarter")
    d.loc[d.item_id == "equity", "2026-Q2"] = 41
    normalized, notes = normalize_statement(d, "SSI", "balance_sheet")
    q = quarterly_rows(normalized, "SSI")
    assert q[0]["fields"]["equity"]["value"] == 40  # Equal aliases, not 80.
    assert q[1]["fields"]["equity"]["value"] == 44  # Assets - liabilities confirms total 400.
    d.loc[d.item_id == "liabilities", "2026-Q2"] = 65
    normalized, notes = normalize_statement(d, "SSI", "balance_sheet")
    assert "equity" in notes["periods"]["2026-Q2"]["ambiguous_fields"]
    assert "equity" not in quarterly_rows(normalized, "SSI")[1]["fields"]


def test_child_balances_are_not_mapped_to_totals():
    d = raw("balance_sheet", "quarter")
    extra = pd.DataFrame([{"item": "Nợ phải trả khác", "item_id": "other", "2026-Q1": 9, "2026-Q2": 10}])
    normalized, _ = normalize_statement(pd.concat([d, extra]), "SSI", "balance_sheet")
    assert quarterly_rows(normalized, "SSI")[0]["fields"]["liabilities"]["value"] == 60


def test_clean_store_downloads_all_statements_and_second_run_is_offline(tmp_path):
    store = Store("local", tmp_path)
    assert not store.path.exists()
    calls = []
    def downloaded(*args):
        calls.append(args)
        return provider(*args)
    result = repair_annual_sources(store, ["SSI"], first_year=2024, through_year=2025, fetch=downloaded, delay=0, progress=lambda _:None)
    assert result["status"] == "complete"
    assert len(calls) == 3
    rows = financial_rows(store.read("financials.parquet"), "SSI", "securities")
    assert [r["period"] for r in rows] == ["2024", "2025"]
    assert rows[0]["revenue"] == 35 and rows[0]["cfo"] == -2
    assert set(store.read("financials.parquet").source_url) == {PROVIDERS["VCI"]}
    assert all(c["ok"] for c in store.verify())
    before = (store.path / "financials.parquet").read_bytes()
    second = repair_annual_sources(store, ["SSI"], first_year=2024, through_year=2025, fetch=lambda *a:pytest.fail("Valid cache must be reused"), delay=0)
    assert second["results"][0]["status"] == "cached"
    assert (store.path / "financials.parquet").read_bytes() == before
    assert not (tmp_path / "sample").exists() and not (tmp_path / "submission").exists()


def test_duplicate_upstream_years_are_replaced_but_manual_year_is_preserved(tmp_path):
    store = Store("local", tmp_path)
    entries = []
    for year in ("2024", "2025"):
        for i in range(30):
            entries.append(dict(symbol="SSI", period=year, item_code=f"bs_item_{i}", item_name="Original", value=float(i), unit="VND",
                                scope="provider_unspecified", source_url=REFERENCE + "/blob/pinned/data"))
    old = pd.DataFrame(entries)
    assert suspect_years(old, "SSI") == {"2024", "2025"}
    # A reviewed third year is never replaced even when an automatic source exists.
    manual = pd.DataFrame([dict(symbol="SSI", period="2023", item_code="revenue", item_name="Manual", value=999., unit="VND",
                               scope="consolidated", source_url="https://example.com/reviewed")])
    store.write("financials.parquet", pd.concat([old, manual]), {})
    result = repair_annual_sources(store, ["SSI"], first_year=2024, through_year=2025, fetch=provider, delay=0, progress=lambda _:None)
    assert result["status"] == "partial"  # Protected 2023 is incomplete.
    assert result["results"][0]["years"] == ["2024", "2025"]
    current = store.read("financials.parquet")
    assert current.loc[current.period == "2023", "value"].tolist() == [999.]
    assert not suspect_years(current, "SSI")
    assert len(store.read("backups/annual/SSI-VCI.parquet")) == 60


def test_failed_provider_preserves_previous_annual_file(tmp_path):
    store = Store("local", tmp_path)
    old = pd.DataFrame([dict(symbol="SSI", period="2025", item_code="assets", item_name="Old", value=100., unit="VND",
                             scope="provider_unspecified", source_url=REFERENCE)])
    store.write("financials.parquet", old, {})
    before = (store.path / "financials.parquet").read_bytes()
    def partial(ticker, statement, period, source):
        if statement == "income_statement": raise ValueError("source down")
        return raw(statement, period)
    result = repair_annual_sources(store, ["SSI"], first_year=2024, through_year=2025, fetch=partial, delay=0, progress=lambda _:None)
    assert result["status"] == "partial"
    assert before == (store.path / "financials.parquet").read_bytes()


def test_repair_cache_is_idempotent_and_reading_never_fetches(tmp_path):
    store = Store("local", tmp_path)
    frames = [normalize_statement(raw(kind, "quarter"), "SSI", kind)[0]
              for kind in ("balance_sheet", "income_statement", "cash_flow")]
    d = pd.concat(frames, ignore_index=True)
    d["canonical_field"] = ""  # Legacy mapping cache.
    store.write("financial_quarterly.parquet", d, {})
    assert quarterly_rows(d, "SSI")[0]["fields"]["net_income"]["value"] == 8
    repair_quarter_cache(store)
    first = (store.path / "financial_quarterly.parquet").read_bytes()
    repair_quarter_cache(store)
    assert first == (store.path / "financial_quarterly.parquet").read_bytes()
    assert set(store.read("financial_quarterly.parquet").normalization_version) == {NORMALIZATION_VERSION}


def test_default_quarter_collector_uses_vci_on_a_clean_machine(tmp_path, monkeypatch):
    from vnresearch import financials
    monkeypatch.setattr(financials, "provider_statement", provider)
    store = Store("local", tmp_path)
    result = fetch_quarters(store, ["SSI"], delay=0, progress=lambda _:None)
    assert result["status"] == "complete" and result["results"][0]["provider"] == "VCI"
    assert all(not r["missing_fields"] for r in quarterly_rows(store.read("financial_quarterly.parquet"), "SSI"))


def test_suspect_years_disable_growth_and_average_balance_ratios():
    d = pd.DataFrame([dict(symbol="SSI", period=y, item_code=code, value=value)
        for y in ("2024", "2025") for code, value in
        list(dict(assets=100, equity=40, net_income=8, revenue=35, cfo=-2).items()) + [(f"detail_{i}", i) for i in range(25)]])
    r = financial_rows(d, "SSI", "securities")
    assert r[-1]["quality_issues"]
    assert r[-1]["profit_growth"] is None and r[-1]["roe"] is None


def test_manual_csv_is_preserved_even_when_source_url_is_tumiqa(tmp_path):
    from vnresearch.ingest import import_financials
    store = Store("local", tmp_path)
    d = pd.DataFrame([dict(symbol="SSI", period=y, item_code="assets", item_name="Đã nhập", value=999., unit="VND",
                          scope="consolidated", source_url=REFERENCE) for y in ("2024", "2025")])
    path = tmp_path / "reviewed.csv"
    d.to_csv(path, index=False)
    import_financials(store, path)
    before = (store.path / "financials.parquet").read_bytes()
    result = repair_annual_sources(store, ["SSI"], first_year=2024, through_year=2025,
        fetch=lambda *a:pytest.fail("Manual source must not be replaced"), delay=0)
    assert result["status"] == "partial"  # Missing metrics are explicit.
    assert before == (store.path / "financials.parquet").read_bytes()


def test_invalid_balance_identity_does_not_replace_old_year(tmp_path):
    store = Store("local", tmp_path)
    old = pd.DataFrame([dict(symbol="SSI", period=y, item_code="assets", item_name="Old", value=100., unit="VND",
                             scope="provider_unspecified", source_url=REFERENCE) for y in ("2024", "2025")])
    store.write("financials.parquet", old, {})
    before = (store.path / "financials.parquet").read_bytes()
    def invalid(*args):
        d = provider(*args)
        if args[1] == "balance_sheet":
            for col in ("2024", "2025"):
                d.loc[d.item_id == "assets", col] = 999
        return d
    result = repair_annual_sources(store, ["SSI"], first_year=2024, through_year=2025, fetch=invalid, delay=0)
    assert result["status"] == "partial"
    assert before == (store.path / "financials.parquet").read_bytes()


def test_manual_pipeline_reports_partial_when_source_omits_cash_flow(tmp_path, monkeypatch):
    from vnresearch import manual, collectors, financials
    store = Store("local", tmp_path)
    monkeypatch.setattr(manual, "Store", lambda _: store)
    monkeypatch.setattr(collectors, "init_profiles", lambda _: None)
    monkeypatch.setattr(collectors, "fetch_annual_reference", lambda *a, **k: {"status": "complete"})
    monkeypatch.setattr(financials, "repair_annual_sources", lambda *a, **k: {"status": "complete"})
    collect = collectors.fetch_quarters
    def missing(ticker, statement):
        d = raw(statement, "quarter")
        if statement == "cash_flow":
            d["item"] = "Nguồn không có dòng tiền kinh doanh cuối cùng"
        return d
    monkeypatch.setattr(collectors, "fetch_quarters", lambda s, ts: collect(s, ts, delay=0, fetch=missing, progress=lambda _:None))
    result = manual.run("financials", ["SSI"])
    assert result["status"] == "partial"
    assert result["steps"]["BCTC quý"]["results"][0]["missing_by_period"] == {"2026-Q1": ["cfo"], "2026-Q2": ["cfo"]}
    assert store.read("financial_quarterly.parquet").shape[0] > 0
