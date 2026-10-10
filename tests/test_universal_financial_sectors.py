"""All ticker/sector cases use the same rules and do not require Internet."""
import pandas as pd
import pytest
from vnresearch.financial_policy import accounting_model, required_missing, top_line
from vnresearch.financials import normalize_statement, canonical_field
from vnresearch.analysis import financial_rows
from vnresearch.insights import quarterly_rows
from vnresearch.peers import map_sector

SECTORS = ("bank", "securities", "technology", "steel", "real_estate", "retail",
           "energy", "oil_gas", "telecom", "other")

@pytest.mark.parametrize("sector", SECTORS)
def test_topline_model_for_each_sector(sector):
    base = {"assets":100.0, "equity":50.0, "net_income":10.0, "cfo":0.0}
    assert required_missing(base, sector)  # Has no top-line yet, zero CFO is VALID
    value = "operating_income" if sector == "bank" else "securities_revenue" if sector == "securities" else "revenue"
    base[value] = 80.0
    assert required_missing(base, sector) == []
    assert top_line(base, sector)[0] == value
    assert accounting_model(sector) in {"bank","securities","nonfinancial","unclassified"}
    if sector != "bank":
        assert "operating_income" not in required_missing(base,sector)

@pytest.mark.parametrize("sector", SECTORS)
def test_annual_growth_does_not_require_unrelated_sector_fields(sector):
    name = "operating_income" if sector == "bank" else "securities_revenue" if sector == "securities" else "revenue"
    records=[]
    for y,k in (("2024",1.0),("2025",1.2)):
        for field,value in (("assets",100.0*k),("equity",60.0*k),
                            ("net_income",9.0*k),("cfo",0.0),(name,75.0*k)):
            records.append({"symbol":"ZZZ","period":y,"item_code":field,"value":value})
    rows=financial_rows(pd.DataFrame(records),"ZZZ",sector)
    assert len(rows)==2
    assert required_missing(rows[-1],sector)==[]
    assert rows[-1]["revenue_growth"]==pytest.approx(.2)

@pytest.mark.parametrize("sector", SECTORS)
def test_quarter_present_missing_and_unclassified(sector):
    name = "operating_income" if sector == "bank" else "securities_revenue" if sector == "securities" else "revenue"
    records = [dict(symbol="ZZZ",period="2026-Q2",statement=statement,
                    canonical_field=field,item_name=field,item_code=field,value=float(v),
                    scope="consolidated",basis="provider_period_unspecified",source_url="https://example.com")
               for statement,field,v in (("balance_sheet","assets",200),("balance_sheet","equity",90),
                                          ("income_statement",name,80),("income_statement","net_income",10),
                                          ("cash_flow","cfo",0))]
    q = quarterly_rows(pd.DataFrame(records),"ZZZ",sector)[0]
    assert q["missing_fields"] == []
    assert q["missing_statements"] == []
    assert q["coverage_status"] == "complete"
    assert q["top_line_field"] == name
    without = pd.DataFrame(records[:-1])
    q = quarterly_rows(without,"ZZZ",sector)[0]
    assert q["coverage_status"] == "partial" and q["missing_statements"] == ["cash_flow"]
    assert "cfo" in q["missing_fields"]

@pytest.mark.parametrize("label,sector", [
    ("Ngân hàng thương mại","bank"),
    ("Dịch vụ chứng khoán","securities"),
    ("Phát triển bất động sản","real_estate"),
    ("Dịch vụ bán lẻ","retail"),
    ("Phần mềm và công nghệ thông tin","technology"),
    ("Sản xuất thép","steel"),
    ("Dầu khí","oil_gas"),
    ("Sản xuất điện","energy"),
    ("Dịch vụ viễn thông","telecom"),
])
def test_icb_fallback_for_all_supported_sectors(label,sector):
    assert map_sector("ZZZ",{}, {"industry_name":label})==sector


def test_cfo_cannot_match_working_capital_subtotals():
    bad = "Lưu chuyển tiền thuần từ hoạt động kinh doanh trước những thay đổi vốn lưu động"
    assert canonical_field(bad,"cash_flow") == ""
    good = "Lưu chuyển tiền tệ ròng từ các hoạt động sản xuất kinh doanh"
    assert canonical_field(good,"cash_flow") == "cfo"


def test_annual_label_fallback_without_guessing_conflicting_aliases():
    rows = pd.DataFrame([
        dict(symbol="ZZZ",period="2025",statement="balance_sheet",item_code="unknown_assets", item_name="Tổng tài sản",value=110),
        dict(symbol="ZZZ",period="2025",statement="balance_sheet",item_code="unknown_equity", item_name="Vốn chủ sở hữu",value=40),
        dict(symbol="ZZZ",period="2025",statement="income_statement",item_code="unknown_rev", item_name="Doanh thu thuần",value=120),
        dict(symbol="ZZZ",period="2025",statement="income_statement",item_code="unknown_profit", item_name="Lợi nhuận sau thuế",value=10),
        dict(symbol="ZZZ",period="2025",statement="cash_flow",item_code="unknown_cfo", item_name="Lưu chuyển tiền tệ ròng từ hoạt động kinh doanh",value=-5),
    ])
    r=financial_rows(rows,"ZZZ","real_estate")[0]
    assert required_missing(r,"real_estate")==[] and r["cfo"]==-5
    rows=pd.concat([rows,pd.DataFrame([dict(symbol="ZZZ",period="2025",statement="income_statement",item_code="another_rev",item_name="Doanh thu thuần",value=250)])],ignore_index=True)
    r=financial_rows(rows,"ZZZ","real_estate")[0]
    assert r["revenue"] is None  # Can't choose between inconsistent aliases


def test_source_fallback_success_does_not_mislabel_ticker_partial(monkeypatch,tmp_path):
    from vnresearch import ondemand, financials, peers
    from vnresearch.storage import Store
    monkeypatch.setattr(ondemand.collectors,"init_profiles",lambda *_:None)
    monkeypatch.setattr(peers,"suggest",lambda *a,**k:{"peers":[],"note":"","sector":"bank"})
    monkeypatch.setattr(ondemand.collectors,"fetch_annual_reference",lambda *a,**k: (_ for _ in ()).throw(ValueError("no Tumiqa file")))
    monkeypatch.setattr(financials,"repair_annual_sources",lambda *a,**k:{"status":"complete", "results":[{"symbol":"AAA","years":["2025"]}],"failed":[]})
    monkeypatch.setattr(ondemand.history,"prepare_history",lambda *a,**k:{"status":"complete"})
    monkeypatch.setattr(ondemand,"readiness",lambda *a,**k:{"symbols":[{"symbol":"AAA","annual_periods":["2025"],"annual_missing_fields":{},"quarter_periods":[],"quarter_missing_fields":{},"quarter_missing_statements":{}}],"macro_count":0})
    result=ondemand.load_one(Store("local",tmp_path),"AAA")
    assert result["status"]=="complete" and result["execution_status"]=="complete"
    assert result["optional_failed"] and not result["failed"]
    assert any("Tumiqa" in issue["error"] for issue in result["optional_failed"])


def test_all_annual_periods_checked_not_only_latest(monkeypatch,tmp_path):
    from vnresearch import ondemand, financials, peers
    from vnresearch.storage import Store
    monkeypatch.setattr(ondemand.collectors,"init_profiles",lambda *_:None)
    monkeypatch.setattr(peers,"suggest",lambda *a,**k:{"peers":[],"note":"","sector":"retail"})
    monkeypatch.setattr(ondemand.collectors,"fetch_annual_reference",lambda *a,**k:{"status":"complete"})
    monkeypatch.setattr(financials,"repair_annual_sources",lambda *a,**k:{"status":"complete"})
    monkeypatch.setattr(ondemand.history,"prepare_history",lambda *a,**k:{"status":"complete"})
    monkeypatch.setattr(ondemand,"readiness",lambda *a,**k:{"symbols":[{"symbol":"AAA","annual_periods":["2024","2025"],"annual_missing_fields":{"2024":["cfo"]},"quarter_periods":[],"quarter_missing_fields":{},"quarter_missing_statements":{}}],"macro_count":0})
    result=ondemand.load_one(Store("local",tmp_path),"AAA")
    assert result["status"]=="partial" and result["execution_status"]=="complete"
    assert result["quality_status"]=="partial" and result["failed"]==[]
    assert "2024" in result["warnings"][-1]["message"]


def test_offline_full_sector_audit_creates_report_without_touching_reference_data(tmp_path,monkeypatch):
    from vnresearch.storage import Store
    from vnresearch.universal_repair import run
    monkeypatch.setattr(pd.DataFrame,"to_parquet",lambda self,path,**kw:self.to_pickle(path))
    monkeypatch.setattr(pd,"read_parquet",lambda path,**kw:pd.read_pickle(path))
    store=Store("local",tmp_path)
    store.write_json("companies.json",{"FPT":{"sector":"technology"},
                                      "VCB":{"sector":"bank"}}, {})
    store.write("financials.parquet",pd.DataFrame([
        dict(symbol="FPT",period="2025",item_code="assets",value=100),
        dict(symbol="FPT",period="2025",item_code="equity",value=50),
        dict(symbol="FPT",period="2025",item_code="net_income",value=10),
        dict(symbol="FPT",period="2025",item_code="revenue",value=80),
        dict(symbol="VCB",period="2025",item_code="operating_income",value=150),
    ]), {"source":"unit test"})
    before=(store.path/"financials.parquet").read_bytes()
    output, report=run(store)
    assert output.is_file()
    assert (store.path/"financials.parquet").read_bytes()==before
    assert report["integrity_ok"] and len(report["symbols"])==2
    fpt=next(r for r in report["symbols"] if r["symbol"]=="FPT")
    vcb=next(r for r in report["symbols"] if r["symbol"]=="VCB")
    assert fpt["annual_missing_fields"]["2025"]==["cfo"]
    assert "operating_income" not in fpt["annual_missing_fields"]["2025"]
    assert "operating_income" not in vcb["annual_missing_fields"]["2025"]
    assert not (tmp_path/"submission").exists() and not (tmp_path/"sample").exists()
