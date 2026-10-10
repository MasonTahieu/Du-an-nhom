# Nguồn cụ thể

| Nhóm | Nguồn | Lấy / lưu | Giới hạn |
| --- | --- | --- | --- |
| OHLCV | KBS qua vnstock 4.0.8 | Lịch sử từng mã theo yêu cầu; chuẩn hóa VND; Parquet | EOD, nguồn có thể sửa giá điều chỉnh |
| BCTC demo | Parquet vn-annual-report-miner commit f8cad8d... | Lọc 9 mã từ 2022, giữ mã/nguồn; Parquet | Đến 2025, chưa đối soát PDF/phạm vi |
| BCTC thực dùng | Công bố doanh nghiệp / sàn | Đối soát và chuẩn hóa CSV | Hỗ trợ năm; chưa có quý/TTM |
| Vĩ mô | NSO báo cáo 9 tháng 2026 | Số đã đọc, giữ kỳ/đơn vị/ngày/URL; JSON | Công bố 03/10/2026 |
| Lãi suất | SBV | Người dùng nhập khi có nguồn | Demo chưa có |
| USD/VND | VCB XML (gợi ý) | Nhập bảng có ngày/loại mua-bán | Demo chưa có |
| Tin mẫu | IR VCB/FPT/Hòa Phát | Tóm tắt độc lập, ngày/URL; JSON | 1 tin/mã |
| Tin thêm | KBS hoặc JSON nhập tay | Metadata giới hạn 10 tin/mã/lần; nội dung có kiểm tra | Nguồn có thể ít/thiếu |
| Hồ sơ/peers | Cấu hình + trang doanh nghiệp | JSON | Nhóm minh họa, không đại diện ngành |

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
mới nhất. Mã/năm BCTC đã có trong local không bị thay thế trong quá trình nạp tự động.
Không sao chép token Hugging Face từ upstream. Ghi nhận license và phạm vi nguồn ở
`licenses/vn-annual-report-miner-MIT.txt` và `assets/fonts/LICENSE_DEJAVU`.
