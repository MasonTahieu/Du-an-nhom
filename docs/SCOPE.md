# Đối chiếu yêu cầu đề

| Yêu cầu | Đã có | Cần hoàn thiện dữ liệu |
| --- | --- | --- |
| Giá / giao dịch | KBS, OHLCV, biểu đồ và chỉ số | CMD nạp/cập nhật có resume; cần đối soát sự kiện cổ phiếu |
| BCTC | Chuỗi năm, mã/đơn vị, chỉ số | Đối soát PDF, bổ sung mới; có bộ nạp quý và bảng riêng; chưa tính TTM |
| Tin tức | IR mẫu, JSON nội dung có kiểm tra, metadata KBS | Chọn vài tin mới và có ý nghĩa |
| Vĩ mô | Bảng NSO có kỳ/ngày/nguồn | SBV/lãi suất/tỷ giá nếu cần |
| Ngành | bank/technology/steel, peers cùng năm | Chọn peers và chỉ tiêu đặc thù phù hợp |
| Cơ hội cổ phiếu | Nhận định gắn số liệu, sàng lọc theo lợi nhuận/giá, rủi ro; kịch bản có giả định | Hoàn thiện giả định trước khuyến nghị |
| PDF tự động | UI và CLI; 7 phần có bảng/biểu đồ/nguồn | Bổ sung nội dung đã đối soát |
| Mã được chọn | Mã động từ dữ liệu/hồ sơ | Demo 3 mã đầy đủ; chưa nạp thì báo thiếu |
| Độ chính xác | Không thay thiếu bằng 0; công thức/đơn vị rõ; OHLC kiểm tra | Công thức đúng chưa thay thế xác minh nguồn |
| Máy khác chạy | Sample cố định, khóa thư viện, font, kiểm thử offline | Online đổi theo thời gian, cần snapshot |

Không thêm vector database, nhiều dịch vụ, LLM nhiều bước, streaming hoặc OCR toàn thị trường. Đây là khung chạy được, **không phải báo cáo đầu tư đã hoàn tất đối soát**.
