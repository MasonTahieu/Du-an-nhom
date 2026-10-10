# Chạy bản VCB trên máy khác

Bản trình bày: output/pdf/VCB_Bao_cao_2026-10-09.pdf (9 trang).
Dữ liệu thực tế cố định: data/submission, được đưa cùng source lên GitHub; không cần ZIP, API key hay quét lại để xem bản này.
Giá chốt 08/10/2026, BCTC 2022–2025; VCB được đối soát trong phạm vi phụ lục PDF. CTG/MBB chỉ là dữ liệu đối chiếu, chưa đối soát toàn bộ.
Dữ liệu đang cập nhật vẫn ở data/local, không đưa vào Git.

## Máy Windows mới

1. Cài Python 3.11, bật Add Python to PATH.
2. Tải/clone toàn bộ dự án, giữ nguyên assets/fonts và data/submission.
3. Chạy Cai-Dat.cmd một lần để cài thư viện (cần Internet).
4. Chạy Mo-Ung-Dung.cmd, mở http://127.0.0.1:8001.
5. Chọn mã VCB; bấm Xuất báo cáo PDF. Giao diện dùng local, có thể chứa dữ liệu mới hơn bộ cố định.

Sau khi cài thư viện, xem phân tích và xuất PDF chạy offline. Không chạy các CMD nạp 00–05 cho bản nộp.
Các lần mở sau chỉ cần Mo-Ung-Dung.cmd. Nếu trình duyệt còn giao diện cũ, nhấn Ctrl+F5.

Để tái tạo PDF từ đúng bộ cố định `submission`, dùng các lệnh bảo trì trong [README](../README.md#8-bảo-trì-và-tái-tạo-bản-cố-định). Kết quả được ghi tại output/pdf/VCB_Bao_cao_2026-10-09.pdf; không dùng dữ liệu local để mặc nhiên coi là bản cố định.

## Tính tái lập và giới hạn

- manifest.json lưu SHA-256 của các tệp dữ liệu; đầu vào phân tích nằm trong JSON cùng PDF.
- Phiên bản thư viện ở requirements.lock.txt; font tiếng Việt nằm trong assets/fonts.
- Bộ submission chỉ đọc qua ứng dụng; mọi nạp API/CSV tiếp tục ghi vào local.
- Nhận định được gắn dấu kiểm tra đầu vào. Khi giá, BCTC, vĩ mô, tin hoặc nhóm đối chiếu thay đổi, nhận định rà soát cũ không còn được áp dụng.
- Chỉ đối soát giá phiên cuối, các chỉ tiêu trọng yếu VCB 2024–2025, 5 chỉ tiêu NSO và bài IR VCB. Không coi đây là kiểm toán toàn kho.
- BCTN gốc của VCB được đọc qua bản sao tài liệu công bố trên FinancialReports; PDF dẫn URL và trang in 151, 153 (trang tệp 77, 78).
- Không kèm nguyên bài báo hoặc toàn bộ PDF nguồn. Bản nộp giữ số liệu, tóm tắt và URL để đối chiếu.
- Chưa có BCTC quý chuẩn hóa, chưa xác minh toàn bộ điều chỉnh giá, chưa có giá mục tiêu. Không suy P/E từ EPS cũ.
- Source tham khảo BCTC: https://github.com/Tumiqa/vn-annual-report-miner, commit f8cad8d7d4276cd22aee20113fe3214230daf919, giấy phép code MIT. Tham khảo cách dùng Parquet/cache; không sao chép nguyên repo.
- Các nguồn dữ liệu gốc khác được ghi trong research_reviews.json và phụ lục PDF. Phạm vi bộ dữ liệu là phục vụ bài nghiên cứu.

## GitHub

Giữ data/submission, output/pdf, assets, config, vnresearch, static, scripts, các CMD và requirements trong dự án.
Không đưa .env, API key, .venv, logs, tmp hoặc data/local lên Git.
Bộ dữ liệu hiện chỉ hỗ trợ trình bày VCB và đối chiếu CTG/MBB; chế độ local vẫn có danh mục toàn thị trường và các công cụ nạp thủ công.
