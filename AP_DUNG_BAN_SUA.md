# Bản sửa StockInsight — kho BCTC Tumiqa dùng chung

## Phương án giữ nguyên dự án hiện tại (khuyên dùng)

1. Giải nén **file RAR dự án gốc của bạn** vào thư mục làm việc.
2. Giải nén `stockinsight_tumiqa_patch.zip` **vào đúng thư mục gốc đó**, chọn ghi đè các file mã nguồn/tài liệu trùng tên.
3. Không xóa `data/local`, `data/submission` hoặc `assets/fonts` của dự án gốc.
4. Trên Windows chạy `Cai-Dat.cmd` (nếu máy chưa cài thư viện), rồi `Mo-Ung-Dung.cmd`.
5. Mở web, nhập mã và bấm **Nạp / cập nhật mã này**. BCTC năm được tìm trong kho Tumiqa đã cache, chỉ tải nếu thiếu.
6. Nếu muốn tải sẵn **cả sáu file BCTC HSX/HNX** trước khi nạp mã, chạy `08-Chuan-Bi-Kho-BCTC-Tumiqa.cmd`.

## Source code dạng gọn

Bản `stockinsight_tumiqa_source.zip` có source, dữ liệu `sample`/`submission`, tài liệu và bộ test; không đưa các file tạm, cache local, thư mục Git, nhật ký và font nhị phân vào gói. Khi dùng bản source gọn, hãy lấy `assets/fonts` từ file RAR gốc của bạn trước khi xuất báo cáo PDF. Nếu đang có dữ liệu trong `data/local`, có thể sao chép nguyên thư mục đó từ bản cũ.

## Quy tắc an toàn dữ liệu

- Kho Tumiqa dùng cache ở `data/reference/tumiqa/<commit>` và không ghi đè các kỳ BCTC đã lưu.
- Không chỉnh sửa `data/submission` và `research_reviews.json`.
- BCTC năm không cần quét PDF, không cần Hugging Face token.
- Giá cổ phiếu, VN-Index, BCTC quý, vĩ mô và tin tức vẫn cần nguồn nạp riêng.
- Nếu mạng lỗi, file cache hợp lệ cũ và dữ liệu `local` không bị xóa.
- Các nguồn tham khảo được pin theo commit `config/watchlist.json`; dữ liệu BCTC lịch sử chưa phải dữ liệu đã kiểm toán/đối soát hoàn toàn.

## Kiểm thử

Các bài kiểm thử cache dùng mô phỏng nguồn, không cần Internet. Kiểm tra chạy đầy đủ bằng Python 3.11 và thư viện `pyarrow` theo `requirements.txt`, ví dụ:

```
python -m pip install -r requirements-dev.txt
python -m pytest
python -m vnresearch verify
```
