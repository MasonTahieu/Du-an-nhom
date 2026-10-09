import pandas as pd
import pytest
from vnresearch.analysis import financial_rows, valuation, analyze, safe_div
from vnresearch.storage import Store
from vnresearch.ingest import validate_financials


def facts(periods):
    return pd.DataFrame([{"symbol":"ABC", "period":str(year), "item_code":key, "value":value}
                         for year, values in periods.items() for key, value in values.items()])


def test_current_ratio_and_average_roe_are_correct():
    d = facts({2024:dict(assets=100,equity=40,net_income=8), 2025:dict(assets=200,equity=60,net_income=10,current_assets=30,current_liabilities=5,liabilities=140)})
    rows=financial_rows(d,"ABC")
    assert rows[0]["roe"] is None
    assert rows[1]["roe"] == .2
    assert rows[1]["roa"] == pytest.approx(10/150)
    assert rows[1]["current_ratio"] == 6  # not total assets / total liabilities


def test_missing_is_distinct_from_zero():
    r=financial_rows(facts({2025:dict(net_income=0,assets=100,equity=50)}),"ABC")[0]
    assert r["net_income"] == 0
    assert r["cfo"] is None
    assert r["roe"] is None
    assert safe_div(1,0) is None


def test_non_contiguous_years_do_not_produce_average_ratios():
    rows=financial_rows(facts({2023:dict(equity=20),2025:dict(equity=40,net_income=10)}),"ABC")
    assert rows[-1]["roe"] is None


def test_bank_avoids_generic_ratios_and_pre_tax_cashflow():
    d=facts({2025:dict(current_assets=30,current_liabilities=5,revenue=100,operating_income=50,operating_expense=-20,net_income=10,
                      cf_luu_chuyen_tien_thuan_tu_hoat_dong_kinh_doanh_truoc_thue_thu_nhap_dn=999)})
    r=financial_rows(d,"ABC","bank")[0]
    assert r["revenue"] == 50
    assert r["current_ratio"] is None
    assert r["net_margin"] is None
    assert r["cfo"] is None
    assert r["cir"] == .4


def test_scenarios_share_one_formula():
    v=valuation(dict(method="PB",per_share=20000,multiple=1.5,as_of="2026-10-08",source_url="https://example.com"),25000)
    base=v["scenarios"][1]
    assert base["target"] == 30000
    assert base["upside"] == .2
    assert not any("probability" in s for s in v["scenarios"])


@pytest.mark.parametrize("value", [-1,0,float("nan"),float("inf")])
def test_bad_valuation_assumptions_rejected(value):
    with pytest.raises(ValueError):
        valuation(dict(method="PE",per_share=value,multiple=10,as_of="2026-10-08",source_url="https://example.com"),100)


def test_no_valuation_is_invented():
    assert not valuation(None,100)["available"]


def test_financial_import_rejects_mixed_scope():
    d=facts({2025:dict(assets=100,equity=50)})
    d["unit"]="VND";d["scope"]=["consolidated","separate"];d["source_url"]="https://example.com"
    with pytest.raises(ValueError,match="trộn"):
        validate_financials(d)


@pytest.mark.parametrize("ticker",["VCB","FPT","HPG"])
def test_real_sample_analysis_is_deterministic_and_complete(ticker):
    a=analyze(Store(),ticker)
    assert a == analyze(Store(),ticker)
    assert a["market"]["rows"] >= 200
    assert a["market"]["date"] == "2026-10-08"
    assert a["financials"][-1]["period"] == "2025"
    assert a["news"] and a["macro"]
    assert not a["valuation"]["available"]
    assert len(a["peers"]) >= 2
    assert all(p["period"] == "2025" for p in a["peers"])


def test_unknown_symbol_has_useful_error():
    with pytest.raises(ValueError,match="Chưa có dữ liệu"):
        analyze(Store(),"ZZZ")
