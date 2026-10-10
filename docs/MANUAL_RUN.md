# CMD và công cụ bảo trì

Quy trình tải source, cài đặt và hai cách nạp dữ liệu nằm trong [README](../README.md#2-nạp-dữ-liệu). Tài liệu này dành cho các thao tác nâng cao; không cần chạy toàn bộ để sử dụng ứng dụng.

## 1. Chạy CMD với tham số

Mở PowerShell trong thư mục dự án, chạy tên file với tiền tố `.\`. `--symbols` ưu tiên hơn lựa chọn toàn thị trường; `--limit` giới hạn số mã và `--exchanges` lọc sàn trong danh mục đã lưu.

```powershell
# Xem trước kế hoạch, không gọi nguồn hoặc ghi dữ liệu.
.\02-Nap-Lich-Su-Toan-Thi-Truong.cmd --limit 3 --dry-run
.\04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd --limit 3 --dry-run

# Lọc sàn hoặc chọn nhóm mã.
.\02-Nap-Lich-Su-Toan-Thi-Truong.cmd --exchanges HOSE
.\03-Cap-Nhat-Gia-Toan-Thi-Truong.cmd --symbols FPT HPG
.\04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd --symbols SSI NLG
.\05-Nap-Vi-Mo-Tin-Tuc.cmd --symbols SSI NLG

# Lấy lịch sử từ ngày khác cấu hình.
.\02-Nap-Lich-Su-Toan-Thi-Truong.cmd --symbols FPT --start 2024-01-01
```

Lệnh dùng toàn danh mục cần chạy `00-Nap-Danh-Muc-Thi-Truong.cmd` trước. Tham số `--refresh` yêu cầu tải lại khoảng/nguồn thay vì chỉ dùng checkpoint; kiểm tra cơ sở điều chỉnh giá trước khi chủ động tải lại lịch sử.

Các mặc định ở `config/watchlist.json`: `history_start=2025-01-01`, `first_year=2022`, nhóm tin `VCB, FPT, HPG`. Lệnh `03` cập nhật vùng gần giá cuối đã lưu, chồng lấn 10 ngày; chưa có lịch sử cho một mã thì dùng khoảng mặc định một năm. Muốn dựng từ ngày cấu hình, dùng `02`.

## 2. Tiến độ và kiểm tra dữ liệu

- Giá: `data/local/history-progress.json`, `history-run.json`.
- BCTC/vĩ mô/tin: `data/local/collection-run.json`.
- Kiểm tra độ đầy đủ và tính toàn vẹn: `06-Kiem-Tra-Du-Lieu.cmd`.

Chạy lại để tiếp tục theo dữ liệu/checkpoint đã lưu và thử lại phần lỗi. Lượt quét BCTC dừng khi nguồn hết hạn mức; không mặc định hoàn tất trong một lần. `04` chỉ quét BCTC năm; BCTC quý mới nạp theo mã trên web. `05` lấy tin cho nhóm cấu hình hoặc `--symbols`, không quét tin từng mã của toàn thị trường.

## 3. Sửa cache và bổ sung năm nền

| Công cụ | Tác dụng |
|---|---|
| `09-Kiem-Tra-Va-Sua-BCTC-Toan-Nganh.cmd` | Chuẩn hóa lại ánh xạ BCTC quý đã lưu, sao lưu bản cũ và ghi báo cáo thiếu dữ liệu toàn ngành; không gọi mạng |
| `10-Bo-Sung-Du-Lieu-Nen-2021.cmd` | Bổ sung năm nền từ cache có sẵn, lưu riêng để hỗ trợ ROA/ROE/tăng trưởng năm đầu; không ghi đè BCTC chính |

Năm nền là `first_year - 1`, hiện là 2021. Xem trước bằng:

```powershell
.\10-Bo-Sung-Du-Lieu-Nen-2021.cmd --dry-run
```

Hai công cụ này không thay cho việc tải BCTC mới. Chi tiết chuẩn hóa, giữ CSV thủ công và sao lưu: [Sửa BCTC và tái lập](SUA_BCTC_VA_TAI_LAP.md).

## 4. Tùy chọn cài đặt và kiểm thử

```powershell
# Chỉ cài/kiểm tra phần ứng dụng; bỏ qua bộ nạp online trong lần này.
.\Cai-Dat.cmd -Offline

# Cài đầy đủ và thêm thư viện dành cho kiểm thử.
.\Cai-Dat.cmd -Dev
.\_python.cmd -m pytest
```

`-Offline` vẫn cần Internet để tải thư viện khi cài lần đầu. Chạy lại `Cai-Dat.cmd` không kèm tùy chọn để cài/kiểm tra đầy đủ bộ nạp. Không kết hợp `-Offline` với `-Market`.

Bộ cài dùng `.venv` trong dự án. Khi chuyển source sang thư mục hoặc máy khác, chạy bộ cài để tạo môi trường tại nơi mới, không sao chép `.venv` cũ. Môi trường ở thư mục người dùng từ bản cũ được giữ nguyên.

Trên macOS/Linux, `sh scripts/setup.sh` hỗ trợ `--offline` và `--dev`; kích hoạt `.venv/bin/activate` trước khi chạy Python của dự án.

## 5. Tái tạo bản cố định

Các lệnh sau đọc bộ `submission`, không dùng kho local để mặc nhiên coi là bản cố định:

```powershell
.\_python.cmd -m vnresearch verify --mode submission
if ($LASTEXITCODE -eq 0) {
    .\_python.cmd -m vnresearch report VCB --mode submission --output output/pdf/VCB_Bao_cao_2026-10-09.pdf
}

# Tải sẵn cache Tumiqa nếu chủ động cần; đây là thao tác có gọi mạng.
.\_python.cmd -m vnresearch.reference_cache --exchange HSX HNX
```

Phạm vi đối soát và cách xem bản đóng gói: [Bản VCB cố định](CHAY_BAN_NOP.md). Công cụ dựng dữ liệu mẫu và xuất PDF mẫu nằm trong `scripts/`; bộ kiểm thử nằm trong `tests/`.
