"""Explicit user-launched online commands. Importing this module never fetches data."""
import argparse
import json
from datetime import datetime, timezone
from .storage import ROOT, Store, atomic_json, symbol
from .locking import process_lock

def config():
    return json.loads((ROOT/"config/watchlist.json").read_text(encoding="utf-8"))

def _run(kind, tickers=None, *, initial=False, start=None, end=None, refresh=False, dry_run=False, annual_only=False, all_market=False, exchanges=None, limit=None):
    settings = config()
    store = Store("local")
    if kind=="universe":
        if dry_run: return {"kind":kind,"note":"Sẽ lấy danh mục ba sàn khi chạy thật."}
        from .universe import fetch_universe
        return fetch_universe(store)
    all_market = all_market and not tickers
    if all_market:
        from .universe import market_symbols
        selected=market_symbols(store,exchanges)
    else:
        selected=list(dict.fromkeys(symbol(t) for t in (tickers or settings["symbols"])))
    if limit is not None:
        if limit<1: raise ValueError("limit cần lớn hơn 0.")
        selected=selected[:limit]
    if not selected: raise ValueError("Danh sách mã rỗng.")
    if all_market and kind=="context":
        raise ValueError("Tin tức nạp theo mã đang phân tích; dùng --symbols cho nhóm tin.")
    if all_market and kind=="financials" and not annual_only:
        raise ValueError("BCTC toàn danh mục: dùng --annual-only. Quý mới nạp theo --symbols.")
    if kind == "check":
        from .quality import readiness
        return readiness(store)
    if kind == "history":
        from .history import plan, prepare_history
        selected = list(dict.fromkeys(selected+[settings.get("benchmark","VNINDEX")]))
        begin = start or (settings["history_start"] if initial else None)
        if dry_run:
            return plan(store,selected,begin,end,refresh=refresh)
        return prepare_history(store,selected,begin,end,refresh=refresh)
    if dry_run:
        return {"kind":kind,"symbols":selected,"note":"Chỉ xem kế hoạch; chưa gọi nguồn."}
    from .collectors import init_profiles,fetch_annual_reference,fetch_quarters
    init_profiles(store)
    result = {"kind":kind,"symbols":selected,"started_at":datetime.now(timezone.utc).isoformat(),"steps":{},"failed":[]}
    with process_lock(store.path/".pipeline.lock"):
        def step(name, fn):
            print(name,flush=True)
            try:
                value=fn()
                result["steps"][name]=value
                if isinstance(value,dict):
                    result["failed"].extend(value.get("failed",[]))
            except (Exception,SystemExit) as exc:
                result["failed"].append({"step":name,"error":str(exc)[:500]})
            finally:
                atomic_json(store.path/"collection-run.json",result)
        if kind == "financials":
            annual_symbols=list(selected)
            profiles=store.read_json("companies.json",{})
            for t in selected: annual_symbols.extend(profiles.get(t,{}).get("peers",[]))
            annual_symbols=list(dict.fromkeys(annual_symbols))
            catalogue={r["symbol"]:r.get("exchange") for r in store.read_json("universe.json",{}).get("symbols",[])}
            groups={"HSX":[], "HNX":[]}
            for ticker in annual_symbols:
                exchange=catalogue.get(ticker)
                if exchange=="UPCOM":
                    result["failed"].append({"symbol":ticker,"error":"Nguồn BCTC năm chưa hỗ trợ UPCoM."})
                elif exchange in {"HOSE","HSX","HNX"}:
                    groups["HSX" if exchange in {"HOSE","HSX"} else "HNX"].append(ticker)
                else:
                    for group in groups.values(): group.append(ticker)
            for exchange, codes in groups.items():
                if not codes: continue
                step("BCTC năm "+exchange,lambda exchange=exchange,codes=codes:fetch_annual_reference(store,codes,
                     settings["reference_commit"],exchange,settings["first_year"]))
            if not annual_only:
                step("BCTC quý",lambda:fetch_quarters(store,selected))
        elif kind == "context":
            from .evidence import collect_macro,collect_fx,collect_articles
            from .ingest import fetch_news
            sources=json.loads((ROOT/"config/sources.json").read_text(encoding="utf-8"))
            step("Vĩ mô NSO",lambda:collect_macro(store,sources["macro_release"]))
            step("Tỷ giá VCB",lambda:collect_fx(store))
            # Manual command stays bounded to requested symbols and at most 5 articles each.
            step("Danh sách tin",lambda:fetch_news(store,selected,limit=5))
            records=[n for n in sources["articles"] if n["symbol"] in selected]
            records += [n for n in store.read_json("news.json",[]) if n["symbol"] in selected][:5*len(selected)]
            step("Nội dung tin",lambda:collect_articles(store,records,refresh=refresh))
        else:
            raise ValueError("Nhóm nạp không hợp lệ.")
    result["status"]="partial" if result["failed"] else "complete"
    result["finished_at"]=datetime.now(timezone.utc).isoformat()
    atomic_json(store.path/"collection-run.json",result)
    return result

def run(kind, tickers=None, **kwargs):
    if kwargs.get("dry_run") or kind == "check":
        return _run(kind, tickers, **kwargs)
    with process_lock(Store("local").path / ".ingestion.lock"):
        return _run(kind, tickers, **kwargs)


def main():
    p=argparse.ArgumentParser(description="Nạp chủ động vào Parquet/JSON local; không dùng LLM.")
    p.add_argument("kind",choices=["universe","history","financials","context","check"])
    p.add_argument("--symbols",nargs="+")
    p.add_argument("--all-market",action="store_true",help="Dùng danh mục thị trường đã lưu; --symbols ghi đè")
    p.add_argument("--exchanges",nargs="+",choices=["HOSE","HNX","UPCOM"])
    p.add_argument("--limit",type=int,help="Giới hạn số mã để kiểm thử")
    p.add_argument("--initial",action="store_true",help="Lấy từ history_start trong config")
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--refresh",action="store_true",help="Yêu cầu tải lại khoảng/nguồn đã lưu")
    p.add_argument("--dry-run",action="store_true",help="Không gọi nguồn, chỉ in kế hoạch")
    p.add_argument("--annual-only",action="store_true")
    a=p.parse_args()
    try:
        result=run(a.kind,a.symbols,initial=a.initial,start=a.start,end=a.end,
                   refresh=a.refresh,dry_run=a.dry_run,annual_only=a.annual_only,
                   all_market=a.all_market,exchanges=a.exchanges,limit=a.limit)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result.get("status") in {"partial","interrupted","rate_limited"} or result.get("failed"):
            p.exit(1,"Chưa hoàn tất. Dữ liệu đã lưu được giữ; xem lỗi rồi chạy lại.\n")
    except (ValueError,RuntimeError,FileNotFoundError) as exc:
        p.exit(1,str(exc)+"\n")

if __name__=="__main__": main()
