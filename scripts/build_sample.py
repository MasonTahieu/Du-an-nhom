"""Maintainer tool: explicit small refresh, not required to run the packaged demo."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vnresearch.storage import Store
from vnresearch.ingest import import_reference, fetch_prices

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--start", default="2025-10-09")
    parser.add_argument("--end", default="2026-10-08")
    parser.add_argument("--confirm-overwrite", action="store_true")
    args = parser.parse_args()
    store = Store("sample")
    if store.manifest().get("files") and not args.confirm_overwrite:
        parser.error("Demo đã có dữ liệu. Dùng --confirm-overwrite chỉ khi muốn tạo phiên bản demo mới.")
    import json
    seed = Path(__file__).parent / "sample_metadata.json"
    meta = json.loads(seed.read_text(encoding="utf-8"))
    store.write_json("companies.json", meta["companies"], {"source": "Hồ sơ / nhóm so sánh cấu hình thủ công", "source_url": "see row source_url"}, bootstrap=True)
    print("Đang nhập BCTC của nhóm thử nhỏ từ Parquet local...")
    rows = import_reference(store, args.repo, list(meta["companies"]), 2022, bootstrap=True)
    print("BCTC:", rows)
    print("Đang nạp 3 mã và VNINDEX (4 yêu cầu)...")
    print(fetch_prices(store, ["VCB", "FPT", "HPG", "VNINDEX"], args.start, args.end, bootstrap=True))
    store.write_json("macro.json", meta["macro"], {"source":"NSO (số liệu chọn và kiểm tra thủ công)", "source_url": meta["macro"][0]["source_url"], "as_of":"2026-10-03"}, bootstrap=True)
    store.write_json("news.json", meta["news"], {"source":"IR VCB / FPT / Hòa Phát; tóm tắt có kiểm tra", "source_url":"see row url", "as_of":"2026-10-03"}, bootstrap=True)
    store.write_json("valuations.json", {}, {"source":"Chưa nạp giả định định giá", "source_url":""}, bootstrap=True)
    print("Kiểm tra:", store.verify())

if __name__ == "__main__":
    main()
