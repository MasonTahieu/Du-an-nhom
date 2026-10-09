import json
import shutil
import socket
import pytest
from vnresearch.storage import Store,ROOT
from vnresearch.analysis import analyze

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*a,**kw): raise AssertionError("Snapshot must work offline")
    monkeypatch.setattr(socket.socket,"connect",blocked)

def copied(tmp_path):
    shutil.copytree(ROOT/"data/submission",tmp_path/"submission")
    return Store("submission",tmp_path)

def test_snapshot_replays_and_has_audited_values(tmp_path):
    s=copied(tmp_path)
    assert all(r["ok"] for r in s.verify())
    d=analyze(s,"VCB")
    assert d["market"]["close"]==56600 and d["market"]["date"]=="2026-10-08"
    assert d["financials"][-1]["net_income"]==35197940000000
    assert d["financials"][-1]["roe"]==pytest.approx(.1673033541860492)
    assert "review" in d and len(d["review"]["audit"])==9
    assert d["news"][0]["content_status"]=="source_reviewed_summary"
    assert not d["valuation"]["available"]

def test_submission_rejects_user_writes(tmp_path):
    s=copied(tmp_path)
    with pytest.raises(ValueError): s.write_json("news.json",[],{})

def test_changed_inputs_disable_review(tmp_path):
    s=copied(tmp_path)
    frame=s.read("prices.parquet")
    frame.loc[(frame.symbol=="VCB")&(frame.date=="2026-10-08"),"close"]=56700
    s.write("prices.parquet",frame,{},bootstrap=True)
    d=analyze(s,"VCB")
    assert "review" not in d
    assert "thay đổi" in d["review_status"]

@pytest.mark.parametrize("ticker",["FPT","HPG"])
def test_added_real_snapshots_offline(tmp_path,ticker):
    d=analyze(copied(tmp_path),ticker)
    assert len(d["prices"])==437
    assert len(d["financials"])==4
    assert "review" not in d
