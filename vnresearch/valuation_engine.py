"""Auditable valuation inputs and historical multiples; never manufacture forecasts.

Read-only analytics use stored snapshots, not network access. Peer P/E is indicative
until per-share corporate actions and financial statement comparability are checked.
"""
from __future__ import annotations
from datetime import date
from statistics import median
import math
from urllib.parse import urlparse


def positive(value):
    try:
        x = float(value)
        return x if math.isfinite(x) and x > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def validate_input(payload):
    if not isinstance(payload, dict):
        raise ValueError("Giả định định giá phải là một đối tượng JSON.")
    kind = payload.get("method")
    if kind not in ("PE", "PB"):
        raise ValueError("Chọn phương pháp P/E hoặc P/B.")
    basis = payload.get("basis")
    if basis not in ("historical", "forecast"):
        raise ValueError("Cần ghi rõ dùng chỉ tiêu lịch sử hay dự phóng.")
    per_share = positive(payload.get("per_share"))
    multiple = positive(payload.get("multiple"))
    if per_share is None or multiple is None or multiple > 1000 or per_share > 1e9:
        raise ValueError("EPS/BVPS và hệ số phải là số dương hợp lệ, trong phạm vi cho phép.")
    source_url = str(payload.get("source_url") or "").strip()
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or len(source_url) > 1000:
        raise ValueError("Cần URL nguồn HTTPS hợp lệ của giả định.")
    date_text = str(payload.get("as_of") or "")
    try:
        dt = date.fromisoformat(date_text)
    except ValueError as exc:
        raise ValueError("Ngày của giả định phải theo YYYY-MM-DD.") from exc
    if dt.year < 2000 or dt > date.today():
        raise ValueError("Ngày nguồn không hợp lệ hoặc nằm trong tương lai.")
    if payload.get("reviewed") is not True:
        raise ValueError("Bạn cần xác nhận đã kiểm tra EPS/BVPS, số cổ phiếu và nguồn dữ liệu.")
    note = str(payload.get("note") or "").strip()
    if len(note) > 1200:
        raise ValueError("Ghi chú quá dài.")
    return {"method": kind, "basis": basis, "per_share": per_share,
            "multiple": multiple, "as_of": dt.isoformat(), "source_url": source_url,
            "reviewed": True, "note": note}


def latest_price(prices, ticker):
    if prices.empty or "symbol" not in prices:
        return None
    d = prices.loc[prices.symbol == ticker].sort_values("date")
    if d.empty:
        return None
    r = d.iloc[-1]
    amount = positive(r.close)
    return {"price": amount, "date": str(r.date), "price_basis": str(r.get("price_basis", ""))} if amount else None


def _eps_row(financials, ticker, financial_rows, sector, period):
    records = financial_rows(financials, ticker, sector)
    return next((r for r in reversed(records) if r.get("period") == period), None)


def historical_context(financials, prices, ticker, peers, financial_rows, sector):
    """Indicative P/E only: no peer P/B without verified BVPS and share counts."""
    rows = financial_rows(financials, ticker, sector)
    latest = rows[-1] if rows else None
    last = latest_price(prices, ticker)
    period = latest["period"] if latest else None
    eps = positive(latest.get("eps")) if latest else None
    eps_source = None
    if eps and not financials.empty and "item_code" in financials.columns:
        code = latest.get("evidence", {}).get("eps")
        matches = financials.loc[(financials.symbol == ticker) &
                                  (financials.period.astype(str) == period) &
                                  (financials.item_code == code)] if code else financials.iloc[0:0]
        if not matches.empty:
            r = matches.iloc[0]
            if r.get("unit") != "VND/share":
                eps = None
            else:
                eps_source = str(r.get("source_url", ""))
    else:
        eps = None
    warnings = []
    if not last:
        warnings.append("Chưa có giá đóng cửa để tính hệ số định giá.")
    if not eps:
        warnings.append("Chưa có EPS dương được công bố với đơn vị VND/cổ phiếu.")
    if eps:
        warnings.append("EPS năm chưa được xác minh điều chỉnh theo các sự kiện cổ phiếu đến ngày giá.")
        if last and period and int(last["date"][:4]) > int(period) + 1:
            warnings.append("BCTC năm quá cũ so với phiên giá hiện có.")
    if last and last["price_basis"] == "kbs_provider":
        warnings.append("Cơ sở điều chỉnh giá KBS chưa được đối soát với EPS của kỳ BCTC.")
    relative = []
    candidate_tickers = [x.get("symbol") for x in peers if x.get("symbol") != ticker]
    for p in candidate_tickers:
        if not period:
            break
        row = _eps_row(financials, p, financial_rows, sector, period)
        px = latest_price(prices, p)
        val = positive(row.get("eps")) if row else None
        if px and last and val and abs((date.fromisoformat(px["date"]) - date.fromisoformat(last["date"])).days) <= 7:
            # Require VND/share provenance, not an arbitrary numeric EPS.
            evidence = row.get("evidence",{}).get("eps")
            matched = financials.loc[(financials.symbol == p) & (financials.period.astype(str)==period) &
                                      (financials.item_code==evidence)] if evidence else financials.iloc[0:0]
            if not matched.empty and matched.iloc[0].get("unit") == "VND/share":
                relative.append({"symbol":p, "pe":px["price"]/val, "price_date":px["date"], "eps_year":period})
    reference = float(median([p["pe"] for p in relative])) if len(relative) >= 3 else None
    if len(relative) < 3:
        warnings.append("Thiếu giá và EPS cùng kỳ của tối thiểu 3 đối thủ để tính trung vị P/E tham khảo.")
    return {
        "year": period, "historical_eps": eps, "eps_source_url": eps_source,
        "historical_pe": last["price"]/eps if last and eps else None,
        "price": last["price"] if last else None,
        "price_date": last["date"] if last else None,
        "price_basis": last["price_basis"] if last else None,
        "historical_bvps": None, "historical_pb": None,
        "peer_pe": relative, "peer_pe_median_indicative": reference,
        "peer_pe_count": len(relative), "default_method": "PB" if sector in ("bank", "securities") else "PE",
        "warnings": warnings,
        "note": "P/E lịch sử chỉ để tham khảo; không tự chuyển thành dự phóng hay giá mục tiêu. P/B cần BVPS được xác minh."
    }
