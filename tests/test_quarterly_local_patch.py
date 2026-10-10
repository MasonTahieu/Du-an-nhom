"""Regressions for StockInsight local quarterly mapping/status, no external services."""
import json

import pandas as pd
import pytest

from vnresearch.collectors import fetch_quarters
from vnresearch.financials import NORMALIZATION_VERSION, normalize_statement, resolve_fields, repair_quarter_cache
from vnresearch.insights import quarterly_rows
from vnresearch.quality import readiness
from vnresearch.storage import Store


@pytest.fixture
def fake_parquet(monkeypatch):
    """Only for running these tests in minimal environments without pyarrow."""
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, path, **kw: self.to_pickle(path))
    monkeypatch.setattr(pd, "read_parquet", lambda path, **kw: pd.read_pickle(path))


def _raw(statement, symbol="NLG", missing_cfo=False):
    periods = ["2026-Q1", "2026-Q2"]
    if statement == "balance_sheet":
        pairs = [("Tổng tài sản", "total_assets", 100), ("Vốn chủ sở hữu", "owners_equity", 40)]
    elif statement == "income_statement":
        pairs = [("Doanh thu thuần", "net_sales", 60), ("Lợi nhuận kế toán sau thuế", "net_profit", 8)]
    elif symbol == "NAB":
        pairs = [("Lưu chuyển tiền thuần từ hoạt động kinh doanh trước những thay đổi về tài sản và vốn lưu động",
                  "operating_profit_loss_before_changes_in_working_capital", 100),
                 ("Lưu chuyển tiền thuần từ các hoạt động sản xuất kinh doanh", "net_cash_from_operating_activities", 25),
                 ("Lưu chuyển tiền thuần từ hoạt động kinh doanh trước thuế thu nhập DN",
                  "net_cash_flows_from_operating_activities_before_cit", 45)]
    else:
        pairs = [("Lợi nhuận/(lỗ) từ hoạt động kinh doanh trước những thay đổi vốn lưu động",
                  "operating_profit_loss_before_changes_in_working_capital", 100),
                 ("Lưu chuyển tiền tệ ròng từ các hoạt động sản xuất kinh doanh" if not missing_cfo else "Dòng khác",
                  "net_cash_inflows_outflows_from_operating_activities" if not missing_cfo else "unrelated_item", -25)]
    d = pd.DataFrame([{"item":label, "item_id":code, periods[0]:v, periods[1]:v * 2}
                      for label, code, v in pairs])
    d.attrs = {"unit_type":{p:"Hợp nhất" for p in periods}}
    return d


def test_real_cfo_ids_are_final_and_not_subtotals():
    for ticker,expected in [("NLG",-50),("DRI",-50),("NAB",50)]:
        d, diag = normalize_statement(_raw("cash_flow", ticker), ticker, "cash_flow", provider="VCI")
        assert not diag["ambiguous_fields"]
        result = quarterly_rows(d,ticker, "bank" if ticker=="NAB" else "other")
        assert result[-1]["fields"]["cfo"]["value"] == expected
        assert d.loc[d.item_code.str.contains("before"),"canonical_field"].eq("").all()


def test_sector_specific_coverage_and_missing_report():
    def collect(symbol):
        parts = [normalize_statement(_raw(statement, symbol), symbol, statement, provider="VCI")[0]
                 for statement in ("balance_sheet", "income_statement", "cash_flow")]
        return pd.concat(parts,ignore_index=True)
    nonbank=quarterly_rows(collect("NLG"), "NLG", "real_estate")
    assert nonbank[-1]["missing_fields"] == [] and nonbank[-1]["missing_statements"] == []
    assert "operating_income" not in nonbank[-1]["missing_fields"]
    bank=quarterly_rows(collect("NAB"), "NAB", "bank")
    assert "operating_income" in bank[-1]["missing_fields"]
    assert "revenue" not in bank[-1]["missing_fields"]
    without_cash=collect("NLG").loc[lambda d:~((d.period=="2026-Q2") & (d.statement=="cash_flow"))]
    latest=quarterly_rows(without_cash,"NLG")[-1]
    assert latest["missing_statements"] == ["cash_flow"]
    assert latest["coverage_status"] == "partial"


def test_quarter_fetch_records_real_missing_not_keyerror_and_verifies_manifest(tmp_path, fake_parquet):
    store=Store("local",tmp_path)
    store.write_json("companies.json",{"NLG":{"sector":"real_estate"}}, {})
    response=fetch_quarters(store,["NLG"],fetch=lambda ticker,statement:_raw(statement,ticker),
                            delay=0,progress=lambda _:None)
    assert response["status"] == "complete"
    assert response["execution_status"] == response["quality_status"] == "complete"
    assert response["results"][0]["missing_by_period"] == {}
    assert not response["failed"]
    assert all(r["ok"] for r in store.verify())
    rows=readiness(store)["symbols"]
    nlg=next(x for x in rows if x["symbol"]=="NLG")
    assert nlg["quarter_missing_fields"] == {}


def test_partial_is_data_quality_not_failed_download(tmp_path, fake_parquet):
    store=Store("local",tmp_path)
    response=fetch_quarters(store,["NLG"],fetch=lambda t,s:_raw(s,t,missing_cfo=(s=="cash_flow")),
                            delay=0,progress=lambda _:None)
    assert response["status"] == "partial" and response["execution_status"] == "complete"
    assert response["quality_status"] == "partial" and response["failed"] == []
    assert response["results"][0]["missing_by_period"] == {"2026-Q1":["cfo"], "2026-Q2":["cfo"]}
    assert not store.read("financial_quarterly.parquet").empty


def test_offline_remap_backups_and_idempotency(tmp_path,fake_parquet):
    store=Store("local",tmp_path)
    frames=[normalize_statement(_raw(kind, "NAB"),"NAB",kind,provider="VCI")[0]
            for kind in ("balance_sheet", "income_statement", "cash_flow")]
    old=pd.concat(frames,ignore_index=True)
    old.loc[old.canonical_field=="cfo","canonical_field"]=""  # corrupt old mapping
    old["normalization_version"]=2
    store.write("financial_quarterly.parquet",old,{"source":"legacy"})
    # The read-only fallback already exposes CFO; persisted v2 rows still need repair.
    assert store.read("financial_quarterly.parquet").loc[lambda d: d.item_code.str.contains("net_cash_from_operating_activities"),"canonical_field"].eq("").all()
    out=repair_quarter_cache(store)
    assert out["status"]=="complete"
    assert quarterly_rows(store.read("financial_quarterly.parquet"),"NAB","bank")[-1]["fields"]["cfo"]["value"]==50
    backup=store.read(f"backups/quarterly/pre-normalization-v{NORMALIZATION_VERSION}.parquet")
    assert backup.equals(old)
    before=(store.path/"financial_quarterly.parquet").read_bytes()
    repair_quarter_cache(store)
    assert before==(store.path/"financial_quarterly.parquet").read_bytes()
    assert all(r["ok"] for r in store.verify())
