import json
import socket
import pandas as pd
import pytest
from vnresearch.storage import Store
from vnresearch import history
from vnresearch.collectors import normalize_quarters, fetch_quarters
from vnresearch.insights import quarterly_rows, conclusion, explain_macro
from vnresearch.analysis import fmt

@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def blocked(*a,**k): raise AssertionError("Tests must not download data")
    monkeypatch.setattr(socket.socket,"connect",blocked)

def candle(day,close=10):
    return pd.DataFrame([dict(time=day,open=close,high=close+1,low=close-1,close=close,volume=100)])

def test_history_resumes_after_one_symbol_fails_and_deduplicates(tmp_path,monkeypatch):
    monkeypatch.setattr(history,"completed_session",lambda:"2026-01-09")
    s=Store("local",tmp_path)
    def fetch(t,a,b):
        if t=="FPT": raise ValueError("source down")
        return candle(b)
    r=history.prepare_history(s,["VCB","FPT"],"2026-01-01",retries=0,delay=0,fetch=fetch,progress=lambda _:None)
    assert r["status"]=="partial"
    assert len(s.read("prices.parquet"))==1
    calls=[]
    def recovered(t,a,b):
        calls.append(t);return candle(b)
    r=history.prepare_history(s,["VCB","FPT"],"2026-01-01",delay=0,fetch=recovered,progress=lambda _:None)
    assert calls==["FPT"]
    assert r["status"]=="complete"
    assert s.read("prices.parquet").close.tolist()==[10000,10000]
    r=history.prepare_history(s,["VCB","FPT"],"2026-01-01",delay=0,fetch=recovered,progress=lambda _:None)
    assert r["network_calls"]==0
    assert not s.read("prices.parquet").duplicated(["symbol","date"]).any()

def test_quota_preserves_data_and_leaves_remaining_tasks_pending(tmp_path,monkeypatch):
    monkeypatch.setattr(history,"completed_session",lambda:"2026-01-09")
    s=Store("local",tmp_path)
    def limited(t,a,b): raise SystemExit(1)
    r=history.prepare_history(s,["VCB","FPT"],"2026-01-01",delay=0,fetch=limited,progress=lambda _:None)
    assert r["status"]=="rate_limited"
    assert r["network_calls"]==1
    assert s.read_json("history-progress.json")["checked"]=={}

def test_invalid_prices_never_replace_previous_data(tmp_path,monkeypatch):
    monkeypatch.setattr(history,"completed_session",lambda:"2026-01-09")
    s=Store("local",tmp_path)
    history.prepare_history(s,["VCB"],"2026-01-01",delay=0,fetch=lambda t,a,b:candle(b),progress=lambda _:None)
    before=(s.path/"prices.parquet").read_bytes()
    history.prepare_history(s,["VCB"],"2026-01-01",refresh=True,delay=0,fetch=lambda t,a,b:candle(b,-10),progress=lambda _:None)
    assert before==(s.path/"prices.parquet").read_bytes()

def test_quarter_mapping_uses_net_revenue_and_excludes_scaled_eps():
    raw=pd.DataFrame([
      {"item":"1. Doanh thu bán hàng và cung cấp dịch vụ","item_id":"revenue","2026-Q2":120},
      {"item":"3. Doanh thu thuần về bán hàng và cung cấp dịch vụ","item_id":"revenue","2026-Q2":100},
      {"item":"18. Lợi nhuận sau thuế thu nhập doanh nghiệp","item_id":"net_profit","2026-Q2":20},
      {"item":"19. Lãi cơ bản trên cổ phiếu (VNĐ)","item_id":"earnings_per_share_vnd","2026-Q2":1000000}])
    raw.attrs={"unit_type":{"2026-Q2":"Hợp nhất"}}
    d,notes=normalize_quarters(raw,"FPT","income_statement")
    r=quarterly_rows(d,"FPT")[0]
    assert r["fields"]["revenue"]["value"]==100
    assert r["fields"]["net_income"]["value"]==20
    assert r["fields"]["revenue"]["basis"]=="provider_period_unspecified"
    assert notes["skipped_per_share"]
    assert "eps" not in r["fields"]
    assert "roe" not in r["fields"]

def test_partial_quarter_download_does_not_replace_normalized_financials(tmp_path):
    s=Store("local",tmp_path)
    baseline=pd.DataFrame([{"symbol":"FPT","period":"2025-Q4","value":12}])
    s.write("financial_quarterly.parquet",baseline,{"source":"previous"})
    def partial(t,kind):
        if kind=="income_statement":raise ValueError("failed")
        raw=pd.DataFrame([{"item":"A. TỔNG TÀI SẢN","item_id":"assets","2026-Q2":10}])
        return raw
    r=fetch_quarters(s,["FPT"],delay=0,fetch=partial,progress=lambda _:None)
    assert r["failed"]
    pd.testing.assert_frame_equal(s.read("financial_quarterly.parquet"),baseline)

def test_conclusions_change_with_evidence():
    market={"rows":50,"return_20":.1}
    assert "CÓ ĐIỂM TÍCH CỰC" in conclusion({"net_income":10,"profit_growth":.2},market,{})
    assert "CẦN THẬN TRỌNG" in conclusion({"net_income":-10,"profit_growth":.2},market,{})
    assert "CHƯA ĐỦ" in conclusion({},market,{})

def test_macro_explanation_preserves_period_and_direction():
    base={"indicator":"gdp_yoy","label":"GDP","unit":"%","period":"9M2026","basis":"YoY",
          "published_at":"2026-10-03","source_url":"https://example.com"}
    positive=explain_macro([{**base,"value":8}],"steel",fmt)[0]["text"]
    negative=explain_macro([{**base,"value":-2}],"steel",fmt)[0]["text"]
    assert "9M2026" in positive and "mở rộng" in positive
    assert "chưa tăng trưởng" in negative

def test_manual_dry_run_never_loads_sdk(tmp_path,monkeypatch):
    from vnresearch import manual
    monkeypatch.setattr(manual,"Store",lambda mode:Store(mode,tmp_path))
    from vnresearch import ingest
    monkeypatch.setattr(ingest,"_vnstock",lambda:pytest.fail("SDK import during dry-run"))
    assert manual.run("history",["FPT"],initial=True,dry_run=True)["network_calls"]>0
    assert not (tmp_path/"local").exists()


def test_complete_quarter_collection_archives_mixed_metadata_as_json(tmp_path):
    s=Store("local",tmp_path)
    def provider(t,kind):
        names={"balance_sheet":"A. Tổng tài sản","income_statement":"18. Lợi nhuận sau thuế thu nhập doanh nghiệp","cash_flow":"Lưu chuyển tiền thuần từ hoạt động kinh doanh"}
        raw=pd.DataFrame([{"item":names[kind],"item_id":"numeric","2026-Q2":100.0},
                          {"item":"Kiểm toán","item_id":"audit_status","2026-Q2":"Chưa kiểm toán"}])
        raw.attrs={"unit_type":{"2026-Q2":"Hợp nhất"}}
        return raw
    result=fetch_quarters(s,["FPT"],delay=0,fetch=provider,progress=lambda _:None)
    assert not result["failed"]
    raw=s.read_json("raw/financials/FPT/balance_sheet.json")
    assert raw["rows"][1]["2026-Q2"]=="Chưa kiểm toán"
    rows=quarterly_rows(s.read("financial_quarterly.parquet"),"FPT")
    assert rows[0]["fields"]["assets"]["value"]==100
    assert s.verify() and all(r["ok"] for r in s.verify())


def test_latest_macro_does_not_duplicate_legacy_average_cpi():
    from vnresearch.insights import latest_macro
    records=[{"indicator":"cpi_yoy","label":"CPI bình quân","value":4.5,"published_at":"2026-10-03"},
             {"indicator":"cpi_average_yoy","label":"CPI bình quân","value":4.52,"published_at":"2026-10-03","retrieved_at":"2026-10-09"}]
    result=latest_macro(records)
    assert len(result)==1 and result[0]["value"]==4.52
    assert records[0]["indicator"]=="cpi_yoy"

def test_kbs_quarter_adapter_supports_narrow_wrappers_and_keeps_metadata(tmp_path):
    from vnresearch.collectors import fetch_kbs_quarter
    calls=[]
    class WrappedFinance:
        def __init__(self,ticker,period):
            assert ticker=="VCB" and period=="quarter"
        def result(self,statement,period):
            assert period=="quarter"
            calls.append(statement)
            names={"balance_sheet":"Tổng tài sản",
                   "income_statement":"Lợi nhuận sau thuế",
                   "cash_flow":"Lưu chuyển tiền thuần từ hoạt động kinh doanh"}
            d=pd.DataFrame([{"item":names[statement],"item_id":"amount","2026-Q2":100.0}])
            d.attrs={"unit_type":{"2026-Q2":"Hợp nhất"},"audit_status":{"2026-Q2":"Chưa kiểm toán"}}
            return d
        def balance_sheet(self,period=None,show_log=False):
            return self.result("balance_sheet",period)
        def income_statement(self,period=None,show_log=False):
            return self.result("income_statement",period)
        def cash_flow(self,period=None,show_log=False):
            return self.result("cash_flow",period)
    store=Store("local",tmp_path)
    r=fetch_quarters(store,["VCB"],delay=0,progress=lambda _:None,
        fetch=lambda ticker,statement:fetch_kbs_quarter(WrappedFinance,ticker,statement))
    assert not r["failed"]
    assert calls==["balance_sheet","income_statement","cash_flow"]
    d=store.read("financial_quarterly.parquet")
    assert set(d.scope)=={"consolidated"}
    assert set(d.audit_status)=={"Chưa kiểm toán"}
    assert set(d.canonical_field)=={"assets","net_income","cfo"}
    assert store.read_json("raw/financials/VCB/income_statement.json")["attrs"]["unit_type"]["2026-Q2"]=="Hợp nhất"
