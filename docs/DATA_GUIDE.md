> Quy trình nạp trên web và CMD: xem [README](../README.md). Tài liệu này mô tả quy cách dữ liệu nhập thủ công.

# Nạp dữ liệu thủ công

Nạp vào **local**. Bộ demo có sẵn để chạy ứng dụng và xuất PDF; không cần nạp toàn thị trường.

## Giá và khối lượng

~~~text
python -m vnresearch prices VCB FPT HPG VNINDEX --start YYYY-MM-DD --end YYYY-MM-DD
~~~

Vnstock 4.0.8: Market().equity("VCB").ohlcv(..., source="kbs", count=1000); chỉ số dùng Market().index("VNINDEX").

- Giá cổ phiếu KBS là nghìn VND: nhân 1.000 thành VND trước lưu.
- VNINDEX giữ đơn vị điểm. Khối lượng là số cổ phiếu.
- Chạy sau 16:00, tối đa một lần/ngày. Không có streaming/scheduler.
- Phiên hôm nay chưa hoàn tất bị loại. Ngày nghỉ/lễ dựa các dòng nguồn thực tế trả.
- Có chồng lấn 10 ngày; loại trùng symbol/date. Sự kiện cổ phiếu có thể yêu cầu nạp lại toàn khoảng.
- Không trộn khác cơ sở điều chỉnh. Nguồn lỗi/OHLC lỗi thì giữ dữ liệu cũ.
- Phạm vi nguồn trả có thể ngắn hơn yêu cầu; kiểm tra số phiên trong ứng dụng.
- CSV ngoài API: dùng mẫu templates/prices.csv và lệnh import-prices; chuẩn hóa VND/cơ sở giá trước nhập.

## BCTC năm

**Từ Parquet tham khảo:**

~~~text
python -m vnresearch reference --repo "PATH/vn-annual-report-miner" --symbols VCB FPT HPG --first-year 2022
~~~

Đọc 6 file ở src/arminer/data/bctc_data, lọc mã/năm, giữ item_code/item_name/source_file/source_sheet/statement/exchange. Không quét PDF, không gọi LLM. Phạm vi chưa đối soát ghi provider_unspecified.

**CSV đã kiểm tra:**

~~~csv
symbol,period,item_code,value,unit,scope,source_url
~~~

period = năm YYYY. **Không trộn số quý hoặc lũy kế vào chuỗi năm.** BCTC quý có mô hình chuẩn hóa riêng từ nguồn VCI; mẫu CSV này chỉ dùng cho BCTC năm. Chưa tự tính TTM quý.

| item_code ngắn | Nội dung | Đơn vị |
| --- | --- | --- |
| assets | Tổng tài sản | VND |
| equity | Tổng VCSH | VND |
| liabilities | Nợ phải trả | VND |
| current_assets | Tài sản ngắn hạn | VND |
| current_liabilities | Nợ ngắn hạn | VND |
| revenue | Doanh thu thuần | VND |
| net_income | Tổng LNST | VND |
| parent_income | LNST cổ đông công ty mẹ | VND |
| cfo | Dòng tiền kinh doanh cuối cùng | VND |
| eps | EPS công bố | VND/share |
| operating_income | Tổng thu nhập hoạt động ngân hàng | VND |
| operating_expense | Chi phí hoạt động ngân hàng | VND |
| net_interest_income | Thu nhập lãi thuần | VND |
| loans | Cho vay khách hàng | VND |
| deposits | Tiền gửi khách hàng | VND |

Mã gốc của repo cũng dùng được. scope = consolidated/separate/provider_unspecified; không trộn phạm vi trong cùng mã/năm. source_url trỏ báo cáo gốc. Nên thêm published_at, source_file và ghi chú đối soát. Số “triệu đồng” phải nhân 1.000.000 trước nhập.

Thiếu dữ liệu thì bỏ dòng, không điền 0. Số 0 có thật được giữ. Nạp năm liền trước để tính ROA/ROE bình quân.

~~~text
python -m vnresearch import-financials financials.csv
~~~

Một mã/năm mới thay toàn bộ mã/năm cũ: nhập đủ các chỉ tiêu muốn giữ. Có thể nhập qua giao diện.

## Vĩ mô

Ưu tiên NSO (GDP/CPI/IIP/FDI), SBV (chính sách/lãi suất), VCB (tỷ giá tham khảo). Chưa có số đã kiểm tra thì để thiếu.

~~~csv
indicator,label,value,unit,period,basis,published_at,source_url
~~~

Tỷ lệ phần trăm: value=4.52, unit=%, không dùng 0.0452. basis phân biệt YoY/MoM/so cuối năm/giá trị lũy kế. period là kỳ của số liệu; published_at là ngày nguồn công bố. Không nhầm chỉ số USD NSO với tỷ giá USD/VND.

~~~text
python -m vnresearch import-macro macro.csv
~~~

Thay toàn bộ bảng; nhập đủ dòng cần giữ. Có thể nạp qua giao diện.

## Tin tức

~~~text
python -m vnresearch news VCB --limit 5
~~~

Lệnh này chỉ lấy metadata KBS; nguồn có thể ít tin hoặc đổi schema. Nội dung đã đọc nhập như sau:

~~~json
[
  {
    "symbol": "VCB",
    "title": "Tiêu đề ngắn theo nội dung nguồn",
    "published_at": "2026-08-17",
    "url": "https://www.vietcombank.com.vn/...",
    "summary": "Tóm tắt đã kiểm tra; phân biệt kết quả thực tế và kế hoạch.",
    "content_status": "user_reviewed"
  }
]
~~~

Tin chung dùng symbol=MARKET. URL trùng được cập nhật. Không gán tin tốt/xấu chỉ từ tiêu đề.

~~~text
python -m vnresearch import-news news.json
~~~

Có thể nạp bằng giao diện. Tham khảo news_scraper.py của repo gốc nếu muốn mở rộng CafeF/Vietstock/IR; khung này không crawl rộng hoặc đóng gói toàn bài báo trong Git.

## Hồ sơ và định giá

~~~text
python -m vnresearch company VNM company.json
python -m vnresearch valuation VCB valuation.json
~~~

Mẫu ở templates. Ngành: bank/technology/steel/other; nhập các mã peers rồi nạp BCTC của chúng.

Định giá: method=PE/PB; per_share=EPS/BVPS dự phóng VND/cp đã kiểm tra chia tách; multiple=hệ số mục tiêu có lý do; as_of/source_url bắt buộc. Giá cơ sở = per_share × multiple. Nhạy cảm hệ số 0,8×/1,2×, không gán xác suất.

**Số trong valuation.json template chỉ minh họa schema, không phải định giá VCB.** Demo không chứa giả định giá mục tiêu.

## Tái lập

Source + data/sample + font + requirements đủ chạy demo. Không cần nguồn online sau cài đặt.

Dữ liệu cá nhân ở data/local, được bỏ qua Git. Có thể sao chép riêng kèm manifest. Không đưa key vào chat/source/Git. Nếu dịch vụ yêu cầu key, dùng biến môi trường hoặc .env đã được bỏ qua Git.

CSV số dùng dấu chấm thập phân và không dùng dấu phân cách hàng nghìn. Không chạy hai thao tác nạp cùng một file đồng thời.
