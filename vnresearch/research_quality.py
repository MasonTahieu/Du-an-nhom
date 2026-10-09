"""Conservative, read-only data-quality checks for report inputs.

Never alters the underlying reference Parquet. Flag a near-exact carry-forward as
unverified instead of reporting false flat growth or creating a target price.
"""
from __future__ import annotations

CORE = ("assets", "equity", "net_income")
NUMERIC = ("assets", "equity", "liabilities", "current_assets", "current_liabilities",
           "revenue", "net_income", "parent_income", "cfo", "eps", "net_interest_income",
           "operating_income", "operating_expense", "loans", "deposits", "roe", "roa",
           "revenue_growth", "profit_growth", "net_margin", "current_ratio", "debt_assets", "cir")


def audit_financial_rows(rows, sector):
    """Mutate freshly assembled analysis rows (never stored data)."""
    issues = []
    for index, row in enumerate(rows):
        period = str(row.get("period", ""))
        row.setdefault("quality_status", "unreviewed")
        row.setdefault("quality_notes", [])
        if sector == "securities" and row.get("revenue") == 0 and (row.get("net_income") or 0) > 0:
            row["revenue"] = None
            row["quality_notes"].append("Không xác định được doanh thu/thu nhập hoạt động; giá trị 0 không đủ cơ sở.")
        if index == 0:
            continue
        prev = rows[index - 1]
        if not period.isdigit() or not str(prev.get("period", "")).isdigit() or int(period) != int(prev["period"]) + 1:
            continue
        matching = [k for k in CORE if row.get(k) is not None and prev.get(k) is not None
                    and row[k] == prev[k] and row[k] != 0]
        if len(matching) == len(CORE):
            note = (f"BCTC {period} có tổng tài sản, vốn chủ sở hữu và LNST giống hệt {prev['period']}; "
                    "nghi vấn lặp dữ liệu giữa hai năm, cần đối soát báo cáo gốc.")
            # Avoid using the suspicious year in performance, peer and valuation metrics.
            for key in NUMERIC:
                row[key] = None
            row["quality_status"] = "suspect_duplicate_year"
            row["quality_notes"].append(note)
            issues.append(note)
    # A later year depending on an excluded opening balance also cannot have
    # trustworthy growth / average-asset ROE/ROA, even if its own figures differ.
    for i in range(1, len(rows)):
        if rows[i - 1].get("quality_status") == "suspect_duplicate_year":
            for key in ("revenue_growth", "profit_growth", "roe", "roa"):
                rows[i][key] = None
            rows[i]["quality_notes"].append("Chỉ tiêu tăng trưởng/bình quân cần số liệu năm trước đã đối soát.")
    return issues


def collect_quality(financials, sector, quarterly=None):
    messages = [m for row in financials for m in row.get("quality_notes", [])]
    if sector == "securities":
        if not financials or all(row.get("revenue") is None for row in financials):
            messages.append("Thu nhập hoạt động ngành chứng khoán chưa ánh xạ được từ BCTC năm; không dùng số 0 làm doanh thu.")
    if quarterly:
        messages.append("Số liệu BCTC quý về doanh thu/lợi nhuận/dòng tiền chưa xác minh riêng quý hay lũy kế; không dùng làm TTM.")
    return list(dict.fromkeys(messages))
