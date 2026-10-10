# Sửa BCTC thiếu chỉ tiêu và nạp dữ liệu trên máy mới

Bản sửa ngày 09/10/2026 được kiểm tra với Python 3.11, `vnstock==4.0.8`, `vnai==2.6.1`. Các phiên bản SDK này được ghim trong `requirements-market.txt`; bộ thư viện ứng dụng được ghim trong `requirements.lock.txt`.

## Nguyên nhân và hành vi sau sửa

- Tên “Doanh thu thuần”, “Lợi nhuận kế toán sau thuế TNDN”, “Lợi nhuận sau thuế phân bổ cho chủ sở hữu” chưa được nhận diện đầy đủ. Bộ chuẩn hóa chung nay phân biệt LNST tổng, lợi nhuận thuộc chủ sở hữu và doanh thu hoạt động chứng khoán; không lấy doanh thu tài chính làm doanh thu chính, không lấy LNST chưa phân phối làm LNST trong kỳ.
- Khi cùng chỉ tiêu xuất hiện hai lần, bản cũ xóa mọi kết quả. Bản mới xử lý từng kỳ: hai giá trị bằng nhau chọn một dòng, không cộng; giá trị khác nhau để “Cần đối soát”. Tổng vốn mã 400 chỉ được ưu tiên khi phương trình tài sản trừ nợ xác nhận giá trị.
- Kho năm SSI cũ có 2024–2025 trùng toàn bộ 344 chỉ tiêu và một số dòng tiền được trích sai. Khi phát hiện cả bộ chỉ tiêu trùng giữa hai năm liền kề, ứng dụng cảnh báo và không tính ROA/ROE từ bình quân hoặc tăng trưởng giữa hai năm đó. Lần nạp tiếp theo kiểm tra lại chuỗi năm từ nguồn tự động bằng VCI; không thay dữ liệu CSV đã nhập.
- Thử trực tiếp KBS với SDK 4.0.8 cho SSI cho thấy sai nhãn kỳ: tổng tài sản 2025 bị gắn vào 2022; các quý cũng lệch. Vì vậy BCTC năm dự phòng và BCTC quý mới dùng **VCI**. Cache KBS cũ có cảnh báo cần nạp lại; chuẩn hóa offline chỉ sửa tên chỉ tiêu, không sửa niên độ bằng suy đoán.
- Với công ty chứng khoán, bảng dùng nhãn **Doanh thu hoạt động**. Doanh thu thuần được giữ riêng nếu nguồn có; không thay mọi số 0 bằng doanh thu hoạt động. Giá trị 0 hợp lệ vẫn được giữ.

## Máy mới tải source từ GitHub

Quy trình cài đặt, nạp từng mã trên web và quét toàn thị trường bằng CMD được tập trung trong [README](../README.md). `Cai-Dat.cmd` cài đầy đủ thư viện ứng dụng và bộ nạp; không cần trình cài bổ sung.

Web và CMD quét BCTC năm dùng chung cách chọn nguồn: Tumiqa cho HSX/HNX, VCI bổ sung khi thiếu; UPCoM thử VCI nếu nguồn có dữ liệu. Dữ liệu `local` và cache được tạo trên máy mới, không cần sao chép cache tác giả. Nguồn trực tuyến vẫn cần Internet, quyền truy cập SDK và hạn mức phù hợp.

## Kiểm tra và sửa cache đã có

- `06-Kiem-Tra-Du-Lieu.cmd`: chỉ kiểm tra dữ liệu đã lưu.
- `09-Kiem-Tra-Va-Sua-BCTC-Toan-Nganh.cmd`: chuẩn hóa lại quý từ cache và lưu báo cáo thiếu dữ liệu toàn ngành, không gọi mạng.
- `10-Bo-Sung-Du-Lieu-Nen-2021.cmd`: bổ sung năm nền từ cache có sẵn; không sửa BCTC chính.

Kiểm thử nạp năm/quý vào thư mục trống, giữ dữ liệu thủ công, tái sử dụng cache và bảo toàn bản cũ khi nguồn lỗi nằm trong `tests/`. Các kiểm thử dùng nguồn mô phỏng; không thay cho kiểm tra API thực hoặc chạy trên một máy vật lý thứ hai.

Nạp lại quý qua giao diện hoặc lệnh `manual financials` để thay các kỳ KBS bằng VCI. Dữ liệu gốc, đơn vị, tên chỉ tiêu, URL nguồn và metadata SDK được lưu tại `data/local/raw/financials/`. Dòng chuẩn hóa có `normalization_version`, `ingestion_origin`, và nguồn theo từng dòng; năm từ SDK giữ cả mã chỉ tiêu nguồn `provider_item_code`. Manifest ghi SHA-256. Khi thay năm/quý, các dòng cũ được sao lưu trong `data/local/backups/`; lỗi tải một trong ba bảng không thay dữ liệu đang dùng.

CSV nhập qua giao diện/lệnh được đánh dấu `manual_csv` và không tự thay thế. Khi nguồn không có kỳ hoặc giá trị, ứng dụng giữ trạng thái thiếu, không điền 0 và không ghép ba bảng khác nhà cung cấp/phạm vi trong cùng kỳ. Trường hợp đã nhập CSV thiếu chỉ tiêu cần nhập lại file năm đầy đủ.

## Phạm vi tính tái lập

- Cùng phiên bản source và cùng dữ liệu gốc cho cùng cách chọn chỉ tiêu và cùng kết quả tính toán. Bộ chuẩn hóa có phiên bản; đọc phân tích không gọi mạng.
- Kho Tumiqa được ghim theo commit. VCI là nguồn trực tuyến có thể điều chỉnh số liệu theo thời gian; các lần tải vào ngày khác không được cam kết giống từng byte. Để đối chiếu một lần nạp, lưu dữ liệu gốc và manifest cùng snapshot phân tích.
- Quyền cộng đồng SDK hiện giới hạn tối đa bốn kỳ mỗi yêu cầu. Nguồn năm ghim có thể bổ sung lịch sử, nhưng không đảm bảo mọi mã/mọi năm. Thiếu lịch sử hoặc nguồn lỗi vẫn được báo thiếu/partial; có thể nhập CSV đã đối soát làm phương án thay thế.
- VCI không cung cấp rõ phạm vi hợp nhất/riêng lẻ trong định dạng SDK đang dùng; dữ liệu ghi `provider_unspecified`. KQKD/CFO quý giữ cơ sở `provider_period_unspecified`; chưa cộng TTM hay tính ROE quý.
- Việc khớp SHA-256 xác nhận file không đổi, không xác nhận mọi chỉ tiêu đã được đối soát BCTC kiểm toán. SSI 2025 đã đối chiếu các số tổng quan với [tài liệu công bố của SSI](https://www.ssi.com.vn/upload/files/IR/5_20260104_SSI_Cac_Bao_cao_va_To_trinh_AGM2026%281%29.pdf); không coi đây là kiểm toán toàn bộ năm/quý.
