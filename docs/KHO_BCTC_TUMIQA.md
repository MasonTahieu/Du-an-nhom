# Sử dụng bộ BCTC lịch sử Tumiqa trong StockInsight

## Vị trí và cách vận hành

- **Nguồn:** https://github.com/Tumiqa/vn-annual-report-miner/tree/main/src/arminer/data/bctc_data
- **Phiên bản:** `reference_commit` trong `config/watchlist.json` (ghim SHA 40 ký tự).
- **Dữ liệu:** mỗi sàn HSX/HNX có 3 Parquet: `balance_sheet`, `income_statement`, `cash_flow`.
  Mỗi Parquet chứa nhiều ticker/năm, không phải một file cho một doanh nghiệp.
- **Cache mới:** `data/reference/tumiqa/<commit>/<statement>/<exchange>.parquet`.
- **Dữ liệu đã chuẩn hóa:** `data/local/financials.parquet`, giữ nguyên schema hiện hành.

## Luồng nạp

1. Mở ứng dụng -> nhập một mã 3 ký tự -> bấm **Nạp / cập nhật mã này**.
2. Xác định sàn từ `universe.json` (nếu không rõ, thử HSX rồi HNX).
3. Kiểm tra cache Parquet của đúng commit; nếu có, kiểm tra cấu trúc và SHA-256.
   Nếu cache ở phiên bản StockInsight cũ còn tồn tại, tái sử dụng.
4. Nếu chưa có, tải từ GitHub theo commit, xác minh file Parquet, ghi nguyên tử.
5. Lọc mã, từ `first_year` (mặc định 2022), chuẩn hóa đơn vị, scope, URL nguồn.
6. Chỉ thêm những `(ticker, year)` còn thiếu vào `local`; không ghi đè số liệu
   hiện có, kể cả dữ liệu được đối soát thủ công.
7. Luồng giá, BCTC quý, vĩ mô và tin tức tách riêng, không phụ thuộc kho Tumiqa.

Tải sẵn kho chung (không nhập toàn bộ vào financials):

```powershell
python -m vnresearch.reference_cache --exchange HSX HNX
```

Hoặc trên Windows chạy `08-Chuan-Bi-Kho-BCTC-Tumiqa.cmd` sau khi cài thư viện theo
`Cai-Dat.cmd`. Tải BCTC năm chỉ dùng Python chuẩn và pandas/pyarrow; không yêu cầu vnstock, requests hay Hugging Face token.

## Khi nào vẫn cần mạng?

- Lần đầu lấy BCTC Parquet chưa có trong cache (tải chung theo sàn và loại).
- Cập nhật giá bằng KBS/vnstock và lấy BCTC quý nếu chọn tùy chọn mở rộng.
- Thu thập vĩ mô/tin tức cập nhật từ nguồn tương ứng.

**Không cần mạng:** xem và xuất PDF bằng `data/submission`; truy vấn BCTC tham khảo
đã cache; phân tích local nếu dữ liệu đã đủ. Không có thao tác tự tải khi chỉ chọn
mã hoặc xuất báo cáo.

## Hạn chế và kiểm chứng

- Nguồn lịch sử không bảo đảm đầy đủ mọi mã, năm, UPCoM hay quý 2026.
- `scope = provider_unspecified` cho dữ liệu tham khảo; phải đối soát tài liệu gốc
  trước khi dùng cho kết luận đầu tư/định giá.
- SHA-256 chỉ giúp phát hiện nội dung file cache thay đổi, không chứng minh số liệu đúng.
- Hiện chỉ thêm các **năm chưa có**. Nếu có năm BCTC chưa đủ chỉ tiêu, cần chủ động
  kiểm tra và nhập lại năm đó từ CSV đã đối soát, thay vì trộn số từ nhiều nguồn.
- Không đăng Hugging Face token/API key trong source. Dataset upstream có quyền sở hữu,
  điều kiện tái phân phối riêng cần được kiểm tra trước khi đăng lại dữ liệu lên GitHub.
- Nếu nguồn thay đổi, cập nhật `reference_commit` có kiểm soát và đối chiếu schema;
  chương trình sẽ tạo thư mục cache phiên bản mới nhưng **không tự ghi đè các năm cũ**.
