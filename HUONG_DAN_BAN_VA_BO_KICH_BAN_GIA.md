# Bản vá: bỏ phần lập kịch bản giá trong StockInsight

**Dùng cho:** phiên bản đã cài `stockinsight_research_quy_tac_va_dinh_gia_pe_pb_patch.zip`.

## Thay đổi

- Xóa hai khung giao diện **Lập và lưu kịch bản P/E – P/B** và **Kết quả định giá**.
- Đổi nhãn tab **Định giá & rủi ro** thành **Cơ hội & rủi ro**.
- Giữ mục chỉ số P/E lịch sử để tham khảo, nhưng không tạo bảng giá mục tiêu hay dự phóng từ dữ liệu này.
- Báo cáo PDF chỉ trình bày luận điểm, rủi ro, số liệu P/E lịch sử (khi có) và nguồn. Không đưa kịch bản giá hoặc giá mục tiêu vào PDF.
- Bỏ câu kết luận liên quan đến giá mục tiêu/kịch bản đã nhập.
- Không thay đổi BCTC, giá, tin tức, nhận định nghiên cứu hay cách chọn doanh nghiệp cùng ngành.
- **Không xóa** `data/local/valuations.json` nếu đã lưu trước đây; file này được giữ để bạn có thể khôi phục tính năng trong tương lai, nhưng không xuất hiện ở giao diện và PDF mới.
- API định giá cũ được giữ nhằm tương thích với các phiên bản trước; giao diện hiện tại không gọi chúng.

## Cách áp dụng trên Windows

1. Dừng StockInsight qua `Tat-Ung-Dung.cmd`.
2. Sao lưu thư mục dự án, đặc biệt `data/local`.
3. Giải nén ZIP vào `D:\Dự án 5 chiều` và chọn **Yes to All** khi được hỏi ghi đè.
4. Mở lại bằng `Mo-Ung-Dung.cmd`, sau đó nhấn **Ctrl + F5** trên trình duyệt.
5. Chọn SSI (hoặc một mã khác), mở **Cơ hội & rủi ro** và xuất PDF để kiểm tra.

**Lưu ý:** Các PDF đã tạo từ trước không tự thay đổi; cần xuất lại.
