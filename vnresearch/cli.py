from __future__ import annotations
import argparse
import json
from pathlib import Path

from .storage import ROOT, Store, atomic_json, symbol
from .analysis import analyze, valuation
from .ingest import fetch_prices, fetch_news, import_reference, import_financials, import_macro, import_news, import_prices, seed_local


def main():
    parser = argparse.ArgumentParser(description="VN Equity Research — nạp chủ động, phân tích offline")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=8001)
    for command in ["analyze", "report"]:
        p = sub.add_parser(command)
        p.add_argument("symbol")
        p.add_argument("--mode", choices=["sample", "local", "submission"], default="sample")
        p.add_argument("--output", type=Path)
    p = sub.add_parser("prices")
    p.add_argument("symbols", nargs="+")
    p.add_argument("--start")
    p.add_argument("--end")
    p = sub.add_parser("news")
    p.add_argument("symbols", nargs="+")
    p.add_argument("--limit", type=int, default=5)
    p = sub.add_parser("reference")
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--symbols", nargs="+", required=True)
    p.add_argument("--first-year", type=int, default=2022)
    for command in ["import-financials", "import-macro", "import-news", "import-prices"]:
        p = sub.add_parser(command)
        p.add_argument("file", type=Path)
    p = sub.add_parser("verify")
    p.add_argument("--mode", choices=["sample", "local", "submission"], default="sample")
    sub.add_parser("seed-local")
    p = sub.add_parser("repair-financials", help="Chuẩn hóa cache quý offline; tùy chọn nạp nguồn năm thay thế")
    p.add_argument("--symbols", nargs="+")
    p.add_argument("--online", action="store_true")
    p.add_argument("--data-dir", type=Path, help="Thư mục gốc dữ liệu, mặc định data/")
    p = sub.add_parser("valuation")
    p.add_argument("symbol")
    p.add_argument("file", type=Path)
    p = sub.add_parser("company")
    p.add_argument("symbol")
    p.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            import uvicorn
            uvicorn.run("vnresearch.web:app", host="127.0.0.1", port=args.port)
        elif args.command in ["analyze", "report"]:
            result = analyze(Store(args.mode), args.symbol)
            if args.command == "analyze":
                out = args.output or ROOT / "reports" / "generated" / (symbol(args.symbol) + "_" + args.mode + ".json")
                atomic_json(out, result)
            else:
                from .report import build_pdf
                out = args.output or ROOT / "reports" / "generated" / (symbol(args.symbol) + "_" + args.mode + ".pdf")
                build_pdf(result, out)
            print(str(out))
        elif args.command == "prices":
            print(json.dumps(fetch_prices(Store("local"), args.symbols, args.start, args.end), ensure_ascii=False))
        elif args.command == "news":
            print(f"Đã nạp {fetch_news(Store('local'), args.symbols, args.limit)} tin.")
        elif args.command == "reference":
            print(f"Đã nhập {import_reference(Store('local'), args.repo, args.symbols, args.first_year)} chỉ tiêu.")
        elif args.command.startswith("import-"):
            fn = {"import-financials": import_financials, "import-macro": import_macro, "import-news": import_news, "import-prices": import_prices}[args.command]
            print(f"Đã nhập {fn(Store('local'), args.file)} dòng.")
        elif args.command == "repair-financials":
            from .financials import repair_quarter_cache, repair_annual_sources
            from .locking import process_lock
            store = Store("local", args.data_dir)
            if args.online and not args.symbols:
                raise ValueError("Nạp trực tuyến cần --symbols, ví dụ SSI.")
            with process_lock(store.path / ".ingestion.lock"):
                result = {"quarter_cache": repair_quarter_cache(store)}
                if args.online:
                    result["annual"] = repair_annual_sources(store, args.symbols)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result.get("annual", {}).get("failed"):
                parser.exit(1, "Một số năm chưa nạp được; dữ liệu cũ được giữ.\n")
        elif args.command == "seed-local":
            print(seed_local())
        elif args.command == "verify":
            checks = Store(args.mode).verify()
            print(json.dumps(checks, ensure_ascii=False, indent=2))
            if not checks or not all(c["ok"] for c in checks):
                raise ValueError("Bộ dữ liệu rỗng hoặc không khớp dấu kiểm tra.")
        elif args.command in ["valuation", "company"]:
            value = json.loads(args.file.read_text(encoding="utf-8"))
            if args.command == "valuation":
                valuation(value, None)
                name = "valuations.json"
            else:
                if not value.get("name") or value.get("sector") not in ["bank", "technology", "steel", "other"]:
                    raise ValueError("Hồ sơ cần name và sector hợp lệ.")
                name = "companies.json"
            store = Store("local")
            data = store.read_json(name, {})
            data[symbol(args.symbol)] = value
            store.write_json(name, data, {"source": "Người dùng nhập", "source_url": value.get("source_url", "")})
            print("Đã lưu.")
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
