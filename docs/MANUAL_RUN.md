# Nạp dữ liệu bằng CMD

Quy trình sử dụng và danh sách CMD được tập trung trong [README](../README.md#3-cách-2--quét-toàn-thị-trường-bằng-cmd).

- Nạp từng mã: dùng phần nhập mã trên web.
- Quét toàn danh mục: cập nhật danh mục, nạp lịch sử giá và BCTC năm bằng CMD.
- Sau mỗi phiên: chạy CMD cập nhật giá toàn thị trường.
- Tiến độ giá: `data/local/history-progress.json`, `history-run.json`.
- Kết quả quét BCTC/vĩ mô/tin: `data/local/collection-run.json`.

Cả web và CMD dùng `data/local/`. Chỉ chạy một lượt nạp tại một thời điểm; lỗi nguồn không xóa dữ liệu đã lưu. Tham số bảo trì và công cụ kiểm tra/sửa được giải thích trong README.
