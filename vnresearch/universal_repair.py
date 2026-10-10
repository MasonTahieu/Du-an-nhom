"""Offline, all-ticker normalization plus an auditable completeness report.

This does NOT fetch data, infer missing values or change annual/price data.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .storage import Store, atomic_json
from .financials import repair_quarter_cache
from .quality import readiness


def run(store=None):
    store = store or Store("local")
    source = store.path / "financial_quarterly.parquet"
    before = {"rows": 0, "status": "skipped"}
    if source.is_file():
        before = repair_quarter_cache(store)
    state = readiness(store)
    out = []
    for ticker in state["symbols"]:
        annual_gaps = ticker.get("annual_missing_fields", {})
        q_gaps = ticker.get("quarter_missing_fields", {})
        report_gaps = ticker.get("quarter_missing_statements", {})
        out.append({
            "symbol": ticker["symbol"], "sector": ticker.get("sector", "other"),
            "accounting_model": ticker.get("accounting_model", "unclassified"),
            "annual_periods": ticker.get("annual_periods", []),
            "annual_missing_fields": annual_gaps,
            "quarter_periods": ticker.get("quarter_periods", []),
            "quarter_missing_fields": q_gaps,
            "quarter_missing_statements": report_gaps,
            "price_rows": ticker.get("price_rows", 0),
            "price_end": ticker.get("price_end"),
            "coverage_status": "partial" if annual_gaps or q_gaps or report_gaps else (
                "available" if ticker.get("annual_periods") or ticker.get("quarter_periods") else "no_financials"),
        })
    bad = [item for item in state.get("checks", []) if not item.get("ok")]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "data/local", "no_network": True,
        "quarterly_remap_rows": before.get("rows", 0),
        "integrity_ok": len(bad) == 0, "integrity_errors": bad[:20],
        "symbols": out,
        "note": "Bao phủ số liệu theo cấu trúc; không thay thế xác nhận BCTC kiểm toán, quý riêng/lũy kế hoặc kiểm tra API trực tuyến.",
    }
    destination = store.path / "logs" / "financial_coverage_all_sectors.json"
    atomic_json(destination, report)
    return destination, report


def main():
    path, report = run()
    print("Đã kiểm tra", len(report["symbols"]), "mã trên data/local.")
    print("Đã ánh xạ lại", report["quarterly_remap_rows"], "dòng BCTC quý (nếu có).")
    for ticker in report["symbols"]:
        if ticker["coverage_status"] == "partial":
            years = list(ticker["annual_missing_fields"])
            quarters = list(set(ticker["quarter_missing_fields"]) | set(ticker["quarter_missing_statements"]))
            print(ticker["symbol"], "- thiếu năm:", ",".join(years) or "không", "- thiếu quý:", ",".join(sorted(quarters)) or "không")
    print("Báo cáo:", path)
    if not report["integrity_ok"]:
        raise SystemExit("Có file dữ liệu không khớp manifest; hãy kiểm tra integrity_errors trong báo cáo. Không nên nạp đè.")

if __name__ == "__main__":
    main()
