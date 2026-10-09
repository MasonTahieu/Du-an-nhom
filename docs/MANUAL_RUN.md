# Nạp dữ liệu bằng CMD

Mở các file CMD ngay trong thư mục dự án. Đây là thao tác người dùng chủ động chạy; trang web chỉ phân tích dữ liệu đã lưu. Các lệnh nạp và phân tích dùng Python, không dùng token LLM.

## Quét toàn thị trường

Danh mục được lấy từ KBS qua Vnstock, lưu trong data/local/universe.json. Chọn cổ phiếu thường mã 3 ký tự trên HOSE, HNX, UPCoM theo danh mục nguồn, loại ETF, chứng quyền và phái sinh. Không giới hạn 16 mã. Đây không phải danh sách lịch sử đầy đủ của mọi mã từng hủy niêm yết.

Sau khi đã cài thư viện, chạy lần lượt:
1. 00-Nap-Danh-Muc-Thi-Truong.cmd — cập nhật danh mục; bấm Xem phân tích để cập nhật ô chọn trên web.
2. 02-Nap-Lich-Su-Toan-Thi-Truong.cmd — lấy giá từ history_start cho toàn danh mục và VNINDEX.
3. Các ngày sau: 03-Cap-Nhat-Gia-Toan-Thi-Truong.cmd — cập nhật bổ sung sau phiên.

Chạy thử phạm vi nhỏ trong CMD:
~~~bat
02-Nap-Lich-Su-Toan-Thi-Truong.cmd --limit 3 --dry-run
02-Nap-Lich-Su-Toan-Thi-Truong.cmd --limit 3
02-Nap-Lich-Su-Toan-Thi-Truong.cmd --exchanges HOSE
~~~

--dry-run không gọi nguồn nhưng cần danh mục đã lưu. --symbols ghi đè lựa chọn toàn thị trường.
Nếu bị ngắt hoặc chạm hạn mức, chạy lại cùng lệnh sau khi hạn mức phục hồi; dữ liệu đã lưu được giữ. Không mở nhiều đợt quét cùng lúc.
Giá/khối lượng là dữ liệu ngày, lưu Parquet; tiến độ và danh mục lưu JSON trong data/local. Trang web không tự quét.
Danh mục lớn có thể cần nhiều đợt vì hạn mức nguồn. Tệp giá chung được ghi lại sau mỗi lô; tốc độ phụ thuộc dung lượng và ổ đĩa.

Các CMD 02-Nap-Lich-Su-Gia và 03-Cap-Nhat-Gia vẫn dùng nhóm watchlist để nạp thử nhanh.
BCTC và tin tức nạp riêng:
~~~bat
04-Nap-BCTC.cmd --symbols VNM
05-Nap-Vi-Mo-Tin-Tuc.cmd --symbols VNM
04-Nap-BCTC.cmd --all-market --annual-only
~~~
BCTC năm tham khảo chỉ có HSX/HNX; không bảo đảm đủ mọi mã, đặc biệt UPCoM. Quý và tin tùy nguồn hỗ trợ. Danh mục không đồng nghĩa báo cáo đã đủ dữ liệu. Ngành/nhóm đối chiếu cho mã mới cần bổ sung hồ sơ doanh nghiệp để phân tích đúng đặc thù.

## Lần đầu — nhóm mã thử nghiệm

1. Chạy 01-Cai-Bo-Nap.cmd để cài thư viện nạp (cần Internet).
2. Kiểm tra config/watchlist.json: mặc định VCB, FPT, HPG và benchmark VNINDEX. Ngày bắt đầu lịch sử là 2025-01-01. Nhóm so sánh mặc định CTG, ELC, NKG chỉ nạp BCTC năm.
3. Chạy 02-Nap-Lich-Su-Gia.cmd.
4. Chạy 04-Nap-BCTC.cmd.
5. Chạy 05-Nap-Vi-Mo-Tin-Tuc.cmd.
6. Chạy 06-Kiem-Tra-Du-Lieu.cmd; mở Mo-Ung-Dung.cmd, chọn bộ dữ liệu thực tế, bấm Xem phân tích và xuất PDF.

Chạy lần lượt các cửa sổ nạp để tránh dùng chung hạn mức API. Không cần tạo dữ liệu cá nhân từ demo.

## Các lần sau

- Chạy 03-Cap-Nhat-Gia.cmd sau 16:00 khi muốn cập nhật giá. Quét chồng lấn 10 ngày, loại trùng theo mã/ngày. Chạy lại cùng ngày sẽ dùng kết quả đã kiểm tra.
- Khi có sự kiện cổ phiếu khiến nguồn điều chỉnh lịch sử, tải lại toàn khoảng bằng:
  02-Nap-Lich-Su-Gia.cmd --refresh
- BCTC: chạy lại 04 khi có kỳ mới. BCTC năm tham khảo cố định theo reference_commit; muốn bản nguồn mới phải cập nhật commit đã kiểm tra trong config.
- Vĩ mô: cấu hình sources.json hiện trỏ tới báo cáo NSO 9 tháng 2026. Đổi kỳ nguồn và kiểm tra bộ đọc trước khi dùng kỳ khác; không tự coi báo cáo cũ là số mới.
- Tin tức: KBS cung cấp danh sách; trích thêm bài từ URL nguồn. Danh sách bài IR trong sources.json cần cập nhật chủ động. Không đảm bảo bao phủ toàn bộ tin tức.

Có thể giới hạn một mã khi chạy từ CMD:

~~~bat
02-Nap-Lich-Su-Gia.cmd --symbols VCB --start 2025-01-01
04-Nap-BCTC.cmd --symbols VCB
04-Nap-BCTC.cmd --symbols VCB --annual-only
05-Nap-Vi-Mo-Tin-Tuc.cmd --symbols VCB
_python.cmd -m vnresearch.manual history --initial --dry-run
~~~

--dry-run chỉ đọc và in kế hoạch, không gọi API. VNINDEX được thêm vào lịch sử để đối chiếu hiệu suất.

## Khi nguồn lỗi hoặc bị giới hạn

Tiến độ lịch sử nằm ở data/local/history-progress.json; tóm tắt lần chạy ở history-run.json. Các khoảng đã hoàn tất được dùng lại. SDK báo hết hạn mức thì dừng, giữ dữ liệu; đợi ít nhất 60 giây rồi chạy lại cùng CMD. Thời gian nghỉ mặc định giữa các lần gọi là 7 giây. Không có cơ chế vượt hạn mức.

collection-run.json và financial-run.json ghi lỗi nạp BCTC/vĩ mô/tin. Một mã BCTC quý chỉ thay bản chuẩn hóa sau khi cả ba bảng tải và kiểm tra thành công. Kiểm tra cửa sổ lệnh: complete là hoàn tất, partial là vẫn còn nhóm lỗi.

## Dữ liệu và giới hạn

- prices.parquet: giá OHLCV ngày, cổ phiếu VND, chỉ số điểm; chỉ phiên đã đóng. Giá theo cơ sở KBS, chưa xác minh toàn bộ điều chỉnh doanh nghiệp. Chưa có giao dịch từng lệnh, dòng tiền nước ngoài hoặc lịch sử giá trị giao dịch từ nguồn riêng.
- financials.parquet: BCTC năm, VND hoặc VND/cổ phiếu; nguồn repo và commit nằm trong manifest.
- financial_quarterly.parquet: BCTC quý từ KBS. Tài sản/nợ/vốn là tại thời điểm. KQKD/CFO giữ nhãn kỳ nguồn chưa xác minh riêng quý/lũy kế; không cộng TTM hay tính ROE quý. EPS của SDK bị nhân đơn vị nên được giữ trong bản thô, loại khỏi chỉ tiêu sử dụng tự động.
- companies.json: hồ sơ và peers. Với mã mới, thêm hồ sơ/ngành vào config/watchlist.json. Các bộ tiêu chí ngành hiện có: bank, technology, steel, other.
- macro.json, exchange_rates.json, news.json: số liệu và bằng chứng có kỳ, ngày, URL.
- raw/: bản trả về nguồn để đối soát. manifest.json giữ SHA-256 và thông tin thu thập.

Nhận định tài chính, vĩ mô và nhóm so sánh dựa trên số liệu đã lưu. Quan hệ vĩ mô → ngành là diễn giải có điều kiện. Phân loại cơ hội là quy tắc sàng lọc, không phải mô hình dự báo giá. Định giá PE/PB vẫn cần giả định có nguồn trong valuation.json.

## Máy khác và tính tái lập

Source/config/requirements/data/sample được đưa lên Git. data/local được bỏ qua mặc định vì là dữ liệu người dùng nạp. Máy khác chạy CMD để lấy nguồn, nhưng dữ liệu mới có thể khác lần cũ.

Muốn tái lập chính xác một báo cáo: giữ cùng bản source, cấu hình, data/local và manifest, rồi chạy phân tích offline. Có thể chia sẻ thư mục dữ liệu được chọn sau khi kiểm tra quyền chia sẻ của nguồn; không đưa API key hoặc .env lên Git. Không cần ZIP hoặc dịch vụ database.
