# Nạp dữ liệu theo từng mã

Mở ứng dụng bằng Mo-Ung-Dung.cmd. Xem bộ thực tế cố định không cần nạp lại.

1. Nhập mã ở phần **Nạp dữ liệu theo mã**, ví dụ FPT.
2. Bấm **Nạp / cập nhật mã này**. Chỉ thao tác này mới gọi nguồn.
3. Mặc định nạp BCTC năm của mã và các mã so sánh trong hồ sơ; nạp giá mã đang chọn và VNINDEX.
4. Muốn bổ sung quý, vĩ mô và tin thì đánh dấu lựa chọn bổ sung. Nguồn vĩ mô dùng URL cấu hình hiện có, không tự tìm bản công bố mới nhất.
5. Theo dõi từng bước. Khi kết thúc, ứng dụng chuyển sang local. Nạp một phần vẫn giữ dữ liệu thành công; xem lỗi và nạp lại khi nguồn cho phép.

BCTC năm tái sử dụng 3 file Parquet chung mỗi sàn theo commit; cache dùng chung tại `data/reference/tumiqa/<commit>/` và không tải lại trên các lượt nạp tiếp theo. Giá lần đầu lấy từ history_start trong config/watchlist.json; lần sau cập nhật phần gần nhất theo checkpoint. Không phải realtime. Có thể bấm cập nhật sau phiên mỗi ngày; chưa có lịch tự chạy.

BCTC năm HSX/HNX ưu tiên Tumiqa, dùng VCI bổ sung khi cần; UPCoM thử nguồn VCI nếu có dữ liệu. Mã chưa rõ ngành được ghi nhóm khác, không suy đoán ngành. Một lượt hoàn tất không bảo đảm đủ quý, tin, so sánh, định giá hoặc đã đối soát.

Giữ ứng dụng chạy trong lúc nạp. Khởi động lại không tự tiếp tục tác vụ; bấm nạp lại để dùng phần đã lưu. Chỉ một lượt nạp qua giao diện/CMD cùng lúc. Không cần quét toàn thị trường; các CMD quét toàn thị trường vẫn là tùy chọn.

## Chạy trên máy khác

- data/submission: dữ liệu thật cố định, cần được commit cùng mã nguồn. VCB đã đối soát trong phạm vi ghi ở báo cáo. FPT/HPG và mã so sánh chưa được đối soát độc lập.
- data/sample: dữ liệu demo, không dùng làm bằng chứng đầu tư.
- data/local: dữ liệu tải trên từng máy, bị Git bỏ qua; không tự đồng bộ lên GitHub.
- Máy mới cài thư viện một lần, dùng submission offline; chỉ cần Internet khi nạp mã ngoài bộ cố định.
- Nút nạp luôn ghi local, không thay submission. Dữ liệu thiếu vẫn hiển thị thiếu.
- Không đưa .env, API key hoặc toàn bộ cache lên GitHub.

Không cam kết số giây mỗi mã: phụ thuộc nguồn, giới hạn truy cập, khoảng lịch sử và lựa chọn bổ sung.

## Dùng chung kho BCTC Tumiqa

Bấm nạp mã FPT lần đầu: chương trình tìm ba file BCTC HSX trong cache. Nếu chưa có,
chương trình tải theo `reference_commit` đã ghim. Nạp HPG sau đó không cần tải lại
ba file HSX. Nếu đã từng tải file ở `data/local/raw/reference/...`, chương trình
tái sử dụng nó mà không cần Internet.

Cache HSX/HNX được tự tải khi cần. Quy trình sử dụng web/CMD được tập trung trong [README](../README.md).
**Không cần** chạy bộ quét BCTC năm toàn thị trường. Khi nạp, những mã/năm BCTC
đã có trong `local` được giữ, trừ chuỗi nguồn tự động bị phát hiện thiếu hoặc đáng ngờ và có nguồn VCI thay thế hợp lệ; muốn thay bằng số đã đối soát thì dùng
chức năng nhập CSV. Nạp giá và BCTC quý vẫn là các tác vụ riêng nếu người dùng yêu cầu.

Xem [KHO_BCTC_TUMIQA.md](KHO_BCTC_TUMIQA.md) để hiểu dữ liệu nào lấy được và giới hạn.


BCTC quý mới lấy từ VCI; nguồn năm dự phòng và hướng dẫn máy mới xem [Sửa BCTC và tái lập](SUA_BCTC_VA_TAI_LAP.md). CSV thủ công luôn được giữ khi nạp tự động.
