# Nguồn dữ liệu và phạm vi

| Nhóm | Nguồn | Lấy / lưu | Giới hạn |
| --- | --- | --- | --- |
| Danh mục / OHLCV | KBS qua vnstock 4.0.9 | Danh mục ba sàn, lịch sử và cập nhật giá theo yêu cầu; cổ phiếu chuẩn hóa VND, VNINDEX giữ điểm; Parquet/JSON | Giá ngày, nguồn có thể sửa giá điều chỉnh |
| BCTC năm | Parquet Tumiqa theo `reference_commit`; VCI bổ sung | Cache chung HOSE/HNX; VCI khi thiếu/nguồn tự động đáng ngờ; UPCoM thử VCI | Có thể thiếu mã, kỳ hoặc chỉ tiêu; không tự điền số thiếu |
| BCTC quý | VCI qua vnstock | Lấy khi yêu cầu nạp quý, chuẩn hóa ba bảng và giữ kỳ/nguồn | Chưa mặc nhiên xác minh quý riêng/lũy kế hoặc suy TTM |
| BCTC nhập tay | Công bố doanh nghiệp / sàn do người dùng đối soát | Nhập CSV năm, giữ dấu `manual_csv` | Không tự thay bằng dữ liệu nạp tự động |
| Vĩ mô | NSO theo URL trong `config/sources.json` | Giữ kỳ/đơn vị/ngày/URL; JSON | Hiện cấu hình báo cáo 9 tháng 2026, không tự tìm kỳ mới |
| Lãi suất | SBV hoặc nguồn người dùng cung cấp | Nhập dữ liệu có kỳ, đơn vị và URL | Không có bộ tự tìm công bố lãi suất mới |
| USD/VND | XML Vietcombank | Lệnh `05` lấy bảng có ngày và loại mua/bán | Phụ thuộc bảng nguồn tại thời điểm lấy |
| Tin tức | CafeF RSS, KBS, URL IR cấu hình hoặc JSON nhập tay | RSS giữ metadata/URL; lệnh `05` lấy thêm tin cho nhóm mã và nội dung từ URL | Phân loại mã/ngành và nội dung tự động chưa mặc nhiên được đối soát |
| Hồ sơ/peers | Cấu hình, danh mục ngành và hồ sơ đã lưu | JSON, gợi ý các mã cùng ngành khi nguồn hỗ trợ | Mã chưa rõ ngành giữ trạng thái chưa xác minh |

Bộ `data/sample/` dùng để kiểm tra cài đặt; bộ `data/submission/` là dữ liệu thực tế cố định. Cả hai không thay cho kho dữ liệu mới do từng máy chủ động nạp. Các bước sử dụng nằm trong [README](../README.md).

## Liên kết

- [Repo tham khảo](https://github.com/Tumiqa/vn-annual-report-miner)
- [Parquet](https://github.com/Tumiqa/vn-annual-report-miner/tree/f8cad8d7d4276cd22aee20113fe3214230daf919/src/arminer/data/bctc_data)
- [NSO 9 tháng 2026](https://www.nso.gov.vn/bai-top/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/)
- [SBV](https://www.sbv.gov.vn)
- [VCB XML tỷ giá](https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx)
- URL từng tin: data/sample/news.json.

## Tham khảo source

data/bctc_data: sáu file dạng dài ticker/year/statement/item_code/item_name/value/source...
financial.py: đọc và chuẩn hóa.
export/financial_excel.py: nhóm mã chỉ tiêu doanh nghiệp/ngân hàng.
news_scraper.py: cách giữ URL/ngày/nội dung và giới hạn tin.
README/catalog: báo cáo theo kỳ, tải batch/PDF là bước nạp, không phải streaming.

Ứng dụng này viết riêng giá EOD, lưu snapshot local/manifest, chỉ số nhất quán, vĩ mô→ngành→cổ phiếu, UI và PDF. Không cần arminer hoặc repo gốc để chạy demo.

Quan hệ vĩ mô→doanh nghiệp là diễn giải định tính. SHA-256 chứng minh file không đổi, không chứng minh nguồn đúng. Phải đối soát dữ liệu trước khi dùng vào bài phân tích hoàn chỉnh.


## Cache chung BCTC lịch sử

Mã nguồn tích hợp `vnresearch/reference_cache.py` để đọc các file Parquet theo
commit cố định trong `config/watchlist.json`. Cache tại `data/reference/tumiqa/`
là bản sao nguồn GitHub đã ghim commit, không phải sản phẩm kiểm toán hoặc dữ liệu
mới nhất. CSV đã nhập thủ công được giữ. Chuỗi năm từ nguồn tự động bị phát hiện thiếu hoặc đáng ngờ chỉ được thay khi có nguồn VCI thay thế hợp lệ, có sao lưu bản cũ.
Không sao chép token Hugging Face từ upstream. Ghi nhận license và phạm vi nguồn ở
`licenses/vn-annual-report-miner-MIT.txt` và `assets/fonts/LICENSE_DEJAVU`.
