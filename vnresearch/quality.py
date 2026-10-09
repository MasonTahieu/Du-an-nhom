"""Read-only data readiness; never contacts providers."""
from .storage import Store

def readiness(store):
    prices=store.read("prices.parquet")
    annual=store.read("financials.parquet")
    quarterly=store.read("financial_quarterly.parquet")
    profiles=store.read_json("companies.json",{})
    symbols=set(profiles)
    for frame in [prices,annual,quarterly]:
        if not frame.empty: symbols.update(frame.symbol)
    rows=[]
    for ticker in sorted(symbols-{"VNINDEX"}):
        p=prices.loc[prices.symbol==ticker] if not prices.empty else prices
        f=annual.loc[annual.symbol==ticker] if not annual.empty else annual
        q=quarterly.loc[quarterly.symbol==ticker] if not quarterly.empty else quarterly
        rows.append({"symbol":ticker,"price_rows":len(p),"price_end":str(p.date.max()) if not p.empty else None,
                     "annual_periods":sorted(f.period.unique().tolist()) if not f.empty else [],
                     "quarter_periods":sorted(q.period.unique().tolist()) if not q.empty else [],
                     "news_count":sum(n.get("symbol")==ticker for n in store.read_json("news.json",[])),
                     "sector":profiles.get(ticker,{}).get("sector","other")})
    checks=store.verify()
    return {"mode":store.mode,"symbols":rows,"macro_count":len(store.read_json("macro.json",[])),
            "checks":checks,"integrity_ok":bool(checks) and all(c["ok"] for c in checks),
            "history":store.read_json("history-run.json",{}),"collection":store.read_json("collection-run.json",{}),
            "note":"Khớp dấu kiểm tra không đồng nghĩa nguồn đã được kiểm toán. Xem kỳ thực tế và trường còn thiếu."}
