"""Opt-in offline re-mapping of existing quarterly rows (no network access)."""
import json
from .storage import Store
from .financials import repair_quarter_cache
from .quality import readiness


def main():
    store = Store("local")
    if not (store.path / "financial_quarterly.parquet").is_file():
        print("Chưa có data/local/financial_quarterly.parquet. Không có gì cần sửa.")
        return
    result = repair_quarter_cache(store)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print("Đã chuẩn hóa lại từ Parquet đã lưu. Bản cũ nằm trong data/local/backups/quarterly/.")
    checks = [item for item in store.verify() if not item["ok"]]
    if checks:
        raise SystemExit("Có file không khớp manifest: " + str(checks[:5]))
    print("Manifest hợp lệ. Xem giao diện BCTC quý hoặc chạy lệnh kiểm tra dữ liệu.")

if __name__ == "__main__":
    main()
