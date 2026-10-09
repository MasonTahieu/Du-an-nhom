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
    from .newsfeed import relevant_news
    from .analysis import financial_rows
    from .insights import quarterly_rows
    from .peers import map_sector
    news = store.read_json("news.json", [])
    industries = store.read_json("industry_catalog.json", {}).get("symbols", {})
    rows=[]
    for ticker in sorted(symbols-{"VNINDEX"}):
        p=prices.loc[prices.symbol==ticker] if not prices.empty else prices
        f=annual.loc[annual.symbol==ticker] if not annual.empty else annual
        q=quarterly.loc[quarterly.symbol==ticker] if not quarterly.empty else quarterly
        sector = map_sector(ticker, profiles.get(ticker, {}), industries.get(ticker, {}))
        years = financial_rows(f, ticker, sector) if not f.empty and {"item_code", "value"} <= set(f) else []
        quarters = quarterly_rows(q, ticker) if not q.empty and {"statement", "item_name", "scope"} <= set(q) else []
        rows.append({"symbol":ticker,
                     "annual_missing_fields": {r["period"]: missing for r in years
                        if (missing := [k for k in ("assets", "equity", "revenue", "net_income", "cfo") if r.get(k) is None])},
                     "quarter_missing_fields": {r["period"]: r["missing_fields"] for r in quarters if r["missing_fields"]},
                     "financial_quality_issues": sorted({issue for r in years + quarters for issue in r.get("quality_issues", [])}),
                     "price_rows":len(p),"price_end":str(p.date.max()) if not p.empty else None,
                     "annual_periods":sorted(f.period.unique().tolist()) if not f.empty else [],
                     "quarter_periods":sorted(q.period.unique().tolist()) if not q.empty else [],
                     "news_count":sum(relevant_news(n, ticker, profiles.get(ticker, {}).get("sector", "other"))[0] for n in news),
                     "sector":sector})
    checks=store.verify()
    return {"mode":store.mode,"symbols":rows,"macro_count":len(store.read_json("macro.json",[])),
            "checks":checks,"integrity_ok":bool(checks) and all(c["ok"] for c in checks),
            "history":store.read_json("history-run.json",{}),"collection":store.read_json("collection-run.json",{}),
            "note":"Khớp dấu kiểm tra không đồng nghĩa nguồn đã được kiểm toán. Xem kỳ thực tế và trường còn thiếu."}
