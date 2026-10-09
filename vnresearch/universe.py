"""User-launched market catalogue; import and UI never contact sources."""
from datetime import datetime, timezone
import re
import pandas as pd
from .ingest import _vnstock
from .storage import symbol
EXCHANGES={"HOSE":"HOSE","HSX":"HOSE","HNX":"HNX","UPCOM":"UPCOM"}
NON_STOCK={"ETF","CW","WARRANT","BOND","FUTURE","FUTURES","DERIVATIVE","INDEX"}
def normalize_universe(raw):
    if raw is None or raw.empty or not {"symbol","exchange"}<=set(raw):
        raise ValueError("Nguồn danh mục thiếu symbol/exchange hoặc trả rỗng; danh mục cũ được giữ.")
    records,excluded=[],[]
    for r in raw.to_dict("records"):
        code=str(r.get("symbol","")).strip().upper()
        exchange=EXCHANGES.get(str(r.get("exchange","")).strip().upper())
        kind=str(r.get("type","")).strip().upper()
        # Ordinary Vietnamese equities use three-character identifiers, including A32.
        if not exchange or kind in NON_STOCK or not re.fullmatch(r"[A-Z][A-Z0-9]{2}",code):
            excluded.append({"symbol":code,"type":kind,"exchange":str(r.get("exchange",""))});continue
        name=r.get("organ_name",r.get("name",code))
        records.append({"symbol":symbol(code),"name":str(name) if pd.notna(name) else code,"exchange":exchange,"type":"stock"})
    records=list({r["symbol"]:r for r in records}.values())
    if {r["exchange"] for r in records}!={"HOSE","HNX","UPCOM"}:
        raise ValueError("Nguồn chưa có đủ HOSE/HNX/UPCOM; giữ danh mục cũ.")
    return sorted(records,key=lambda r:(r["exchange"],r["symbol"])),excluded
def fetch_universe(store,fetch=None):
    store._writable()
    if fetch is None:
        _,Reference=_vnstock()
        fetch=lambda:Reference().equity.list_by_exchange(source="kbs")
    try: raw=fetch()
    except SystemExit as exc:
        raise RuntimeError("SDK dừng vì giới hạn truy cập; chờ 60 giây rồi chạy lại.") from exc
    records,excluded=normalize_universe(raw)
    payload={"symbols":records,"retrieved_at":datetime.now(timezone.utc).isoformat(),
             "source":"KBS via vnstock","source_url":"https://kbbuddywts.kbsec.com.vn","excluded":excluded,
             "note":"Cổ phiếu thường 3 ký tự trên ba sàn theo danh mục nguồn; không gồm ETF/CW/phái sinh."}
    store.write_json("universe.json",payload,{"source":payload["source"],"source_url":payload["source_url"],
                                           "as_of":payload["retrieved_at"][:10],"rows":len(records)})
    return {"status":"complete","symbols":len(records),
            "exchanges":{e:sum(r["exchange"]==e for r in records) for e in ["HOSE","HNX","UPCOM"]},"excluded":len(excluded)}
def market_symbols(store,exchanges=None):
    records=store.read_json("universe.json",{}).get("symbols",[])
    if not records: raise ValueError("Chạy 00-Nap-Danh-Muc-Thi-Truong.cmd để nạp danh mục trước.")
    wanted={str(e).upper() for e in (exchanges or ["HOSE","HNX","UPCOM"])}
    if not wanted<={"HOSE","HNX","UPCOM"}: raise ValueError("Chọn sàn HOSE, HNX hoặc UPCOM.")
    return [r["symbol"] for r in records if r["exchange"] in wanted]
