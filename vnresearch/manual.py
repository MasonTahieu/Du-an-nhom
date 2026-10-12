"""Explicit user-launched online commands. Importing this module never fetches data."""
import argparse
import json
from datetime import datetime, timezone
from .storage import ROOT, Store, atomic_json, symbol
from .locking import process_lock

def config():
    return json.loads((ROOT/"config/watchlist.json").read_text(encoding="utf-8"))

def _run(kind, tickers=None, *, initial=False, start=None, end=None, refresh=False, dry_run=False, annual_only=False, all_market=False, stored=False, exchanges=None, limit=None, include_rss=True):
    if stored and (kind != "history" or tickers or all_market or exchanges):
        raise ValueError("--stored chỉ dùng cập nhật giá đã lưu; không kết hợp --symbols, --all-market hoặc --exchanges.")
    settings = config()
    store = Store("local")
    if kind=="universe":
        if dry_run: return {"kind":kind,"note":"Sẽ lấy danh mục ba sàn khi chạy thật."}
        from .universe import fetch_universe
        return fetch_universe(store)
    if kind == "check":
        from .quality import readiness
        return readiness(store)
    all_market = all_market and not tickers
    if stored:
        prices = store.read("prices.parquet")
        benchmarks = {"VNINDEX", settings.get("benchmark", "VNINDEX")}
        selected = sorted({symbol(t) for t in prices["symbol"].dropna()} - benchmarks) if not prices.empty else []
        if not selected:
            raise ValueError("Chưa có mã cổ phiếu nào có dữ liệu giá trên máy. Nạp ít nhất một mã trên web trước.")
    elif all_market:
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
    if kind == "history":
        from .history import plan, prepare_history
        selected = list(dict.fromkeys(selected+[settings.get("benchmark","VNINDEX")]))
        begin = start or (settings["history_start"] if initial else None)
        if dry_run:
            return plan(store,selected,begin,end,refresh=refresh)
        if stored:
            print(f"Cập nhật giá {len(selected)} mã (gồm chỉ số đối chiếu): " + ", ".join(selected), flush=True)
        return prepare_history(store,selected,begin,end,refresh=refresh)
    if dry_run:
        return {"kind":kind,"symbols":selected,"note":"Chỉ xem kế hoạch; chưa gọi nguồn."}
    from .collectors import init_profiles,fetch_annual_for_symbol,fetch_quarters
    init_profiles(store)
    result = {"kind":kind,"symbols":selected,"started_at":datetime.now(timezone.utc).isoformat(),"steps":{},"failed":[],"warnings":[]}
    with process_lock(store.path/".pipeline.lock"):
        def step(name, fn, *, scope="primary"):
            print(name,flush=True)
            try:
                value=fn()
                result["steps"][name]=value
                if isinstance(value,dict):
                    failures = value.get("failed", [])
                    if value.get("status") in {"partial", "rate_limited", "interrupted"} and not failures:
                        failures = [{"step": name, "error": "Nguồn chưa đủ chỉ tiêu/kỳ; xem kết quả bước nạp."}]
                    target = "warnings" if scope == "optional" else "failed"
                    result[target].extend(failures)
                return value
            except (Exception,SystemExit) as exc:
                issue={"step":name,"error":str(exc)[:500]}
                target="warnings" if scope == "optional" else "failed"
                result[target].append(issue)
                value={"status":"rate_limited" if isinstance(exc,SystemExit) else "partial", "failed":[issue]}
                result["steps"][name]=value
                return value
            finally:
                atomic_json(store.path/"collection-run.json",result)
        if kind == "financials":
            annual_symbols=list(selected)
            # A full-market scan covers exactly its selected catalogue/filter.
            # Per-ticker CLI use retains optional comparison companies.
            if not all_market:
                profiles=store.read_json("companies.json",{})
                for t in selected: annual_symbols.extend(profiles.get(t,{}).get("peers",[]))
                annual_symbols=list(dict.fromkeys(annual_symbols))
            result["completed_symbols"]=[]
            result["pending_symbols"]=list(annual_symbols)
            result["total_symbols"]=len(annual_symbols)
            result["status"]="running"
            try:
                for index,ticker in enumerate(annual_symbols,1):
                    print(f"{index}/{len(annual_symbols)} · BCTC năm {ticker}",flush=True)
                    failures_before=len(result["failed"])
                    def annual_step(name, fn, *, scope="primary", ticker=ticker):
                        value=step(name,fn,scope=scope)
                        for issue in result["failed"][failures_before:]:
                            issue.setdefault("symbol",ticker)
                        return value
                    value=fetch_annual_for_symbol(store,ticker,settings,step=annual_step)
                    result["pending_symbols"].remove(ticker)
                    if len(result["failed"])==failures_before:
                        result["completed_symbols"].append(ticker)
                    print(f"{index}/{len(annual_symbols)} · {ticker}: " +
                          ("hoàn tất" if len(result["failed"])==failures_before else "chưa đầy đủ; xem lỗi"),flush=True)
                    atomic_json(store.path/"collection-run.json",result)
                    if isinstance(value,dict) and value.get("status")=="rate_limited":
                        result["status"]="rate_limited"
                        break
                if not annual_only and result["status"]!="rate_limited":
                    step("BCTC quý",lambda:fetch_quarters(store,selected))
            except KeyboardInterrupt:
                result["status"]="interrupted"
                print("Đã dừng. Dữ liệu đã lưu được giữ; chạy lại để tiếp tục.",flush=True)
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
            if include_rss:
                from .newsfeed import collect_rss_feeds
                step("Tin RSS CafeF",lambda:collect_rss_feeds(store))
        else:
            raise ValueError("Nhóm nạp không hợp lệ.")
    if result.get("status") not in {"rate_limited","interrupted"}:
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
    p.add_argument("--stored",action="store_true",help="Cập nhật giá các mã đã có lịch sử giá local và chỉ số đối chiếu")
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
                   all_market=a.all_market,stored=a.stored,exchanges=a.exchanges,limit=a.limit)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if a.kind == "history" and not a.dry_run:
            missing = result.get("pending_latest_symbols", [])
            print(f"Ngày giá yêu cầu: {result['cutoff']} (mốc 15:30 giờ Việt Nam).")
            if missing:
                latest = {row["symbol"]: row["last"] for row in result.get("coverage", [])}
                print("Chưa có dữ liệu phiên yêu cầu: " + ", ".join(
                    f"{ticker} (giá cuối: {latest.get(ticker, 'chưa có')})" for ticker in missing))
                print("Nguồn có thể chưa cập nhật hoặc mã không có giao dịch. Dữ liệu đã lưu được giữ; chạy lại để kiểm tra.")
        if result.get("status") in {"partial","interrupted","rate_limited"} or result.get("failed"):
            p.exit(1,"Chưa hoàn tất. Dữ liệu đã lưu được giữ; xem lỗi rồi chạy lại.\n")
    except (ValueError,RuntimeError,FileNotFoundError) as exc:
        p.exit(1,str(exc)+"\n")

if __name__=="__main__": main()
