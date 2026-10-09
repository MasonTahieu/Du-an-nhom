# Sửa biểu đồ giá và khối lượng theo phiên giao dịch

**Vấn đề:** biểu đồ PDF cũ dùng ngày lịch trên trục X (`ax.plot(dates,...)` / `ax.bar(dates,...)`). Điều này tạo các khoảng trống cho thứ Bảy, Chủ nhật và ngày nghỉ, mặc dù dữ liệu chỉ gồm những phiên thật. Không có bằng chứng rằng ứng dụng đang chủ động chèn nến giả vào dữ liệu.

**Đã sửa:**

- `vnresearch/report.py`: giá và khối lượng trên PDF đều dùng vị trí phiên 0, 1, 2... trên trục X. Ngày thực vẫn xuất hiện ở nhãn trục. Các cột khối lượng sử dụng chiều rộng 0.85 phiên, cách đều nhau.
- `static/app.js`: trục X của Web đã dùng vị trí phiên; nay biểu đồ khối lượng dùng cột đứng thay vì đường và vùng tô, giúp thống nhất cách hiển thị với PDF.
- `tests/test_trading_session_charts.py`: kiểm tra thứ Sáu 02/10/2026 và thứ Hai 05/10/2026 nằm liền kề, dữ liệu trục X và ngày không bị thay đổi; kiểm tra một phiên duy nhất.

**Không thay đổi:** các tệp `data/`, các chỉ tiêu MA20/MA50, lợi suất, biến động, các nhận định đã đối soát và cơ chế nạp dữ liệu. `data/submission/` giữ nguyên.

## Áp dụng trên Windows

1. Dừng ứng dụng bằng `Tat-Ung-Dung.cmd` hoặc Ctrl+C trong cửa sổ CMD/PowerShell đang chạy.
2. Sao lưu dự án đang hoạt động.
3. Giải nén `stockinsight_chart_patch.zip` vào thư mục gốc (nơi có `Mo-Ung-Dung.cmd`); cho phép ghi đè các file cùng tên.
4. Chạy lại `Mo-Ung-Dung.cmd`, nhấn Ctrl+F5 trên trình duyệt để tải lại JavaScript.
5. Xuất lại PDF (file PDF đã xuất từ bản cũ sẽ **không tự thay đổi**).

Bạn **không cần nạp lại dữ liệu giá** chỉ để sửa vấn đề khoảng cách trên biểu đồ.

Nếu sau khi sửa vẫn có ngày nghỉ hiển thị như một dòng dữ liệu có giá/khối lượng, cần kiểm tra trực tiếp `prices.parquet` và dữ liệu trả về từ API, thay vì tự xóa ngày từ nguồn.
