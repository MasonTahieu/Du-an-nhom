# StockInsight — VN Equity Research

Ứng dụng nghiên cứu cổ phiếu Việt Nam: nạp giá và báo cáo tài chính (BCTC), xem phân tích trên web, xuất PDF tiếng Việt. Dữ liệu chỉ được cập nhật khi bạn chủ động nạp bằng web hoặc CMD.

## 1. Tải source và chạy dự án

1. Mở [repo GitHub](https://github.com/MasonTahieu/Du-an-nhom), chọn **Code → Download ZIP** và giải nén toàn bộ. Mở thư mục có `Cai-Dat.cmd` và `Mo-Ung-Dung.cmd`; không chạy trực tiếp trong ZIP.
2. Cài **Python 3.11, 64-bit**, bật **Add Python to PATH**. Nếu vừa cài Python, đóng và mở lại cửa sổ lệnh.
3. Nhấp đúp **`Cai-Dat.cmd`** khi có Internet. Bộ cài tự tạo `.venv` trong dự án và cài thư viện ứng dụng cùng bộ nạp dữ liệu. Chỉ mở ứng dụng sau khi thấy **San sang. Chay Mo-Ung-Dung.cmd de mo giao dien.**
4. Nhấp đúp **`Mo-Ung-Dung.cmd`**. Nếu trình duyệt không tự mở, truy cập [http://127.0.0.1:8001](http://127.0.0.1:8001).

Các lần sau chỉ cần `Mo-Ung-Dung.cmd`. Dừng ứng dụng bằng **`Tat-Ung-Dung.cmd`**; đóng tab trình duyệt chưa dừng server.

<details>
<summary>Tải bằng Git hoặc chạy trên macOS/Linux</summary>

Nếu đã cài Git, có thể tải bằng:

```powershell
git clone https://github.com/MasonTahieu/Du-an-nhom.git
cd Du-an-nhom
```

Trên macOS/Linux, cần Python 3.11 rồi chạy trong thư mục dự án:

```sh
sh scripts/setup.sh
. .venv/bin/activate
python -m vnresearch serve --port 8001
```

Sau đó mở http://127.0.0.1:8001. Nhấn Ctrl+C trong cửa sổ chạy server để dừng.

</details>

**Máy mới chưa có kho dữ liệu thị trường của máy khác.** Source có dữ liệu mẫu và một bộ thực tế cố định để tham khảo; cài đặt và mở ứng dụng không tự tải dữ liệu mới. Chọn một trong hai cách nạp dưới đây.

## 2. Nạp dữ liệu

### Cách A — Nạp từng cổ phiếu trên web

Phù hợp khi nghiên cứu một vài mã, không cần quét toàn thị trường.

1. Vào **Tổng quan đầu tư**, mở khung **Nạp dữ liệu theo mã**, nhập mã như FPT, VCB hoặc SSI.
2. Mặc định nạp BCTC năm của mã và nhóm đối chiếu, giá của mã và VNINDEX. Nếu cần thêm quý, vĩ mô và tin tức, tích **Bổ sung BCTC quý, vĩ mô và tin tức (lâu hơn)**.
3. Bấm **Nạp / cập nhật mã này**, đợi kết quả từng bước và xem lỗi/cảnh báo nếu có. Dùng lại nút này khi cần bổ sung hoặc cập nhật.

Chỉ cần tin RSS thì bấm **Cập nhật tin CafeF theo ngành / mã**; thao tác này không tải lại giá/BCTC. Giữ ứng dụng chạy trong lúc nạp. Chọn doanh nghiệp hoặc mở trang phân tích chỉ đọc dữ liệu đã lưu.

### Cách B — Quét toàn thị trường bằng CMD

Cài xong thư viện rồi nhấp đúp các file trong bảng. Đợi một lượt kết thúc trước khi chạy lượt tiếp theo; không nạp đồng thời trên web và CMD.

| File | Khi dùng |
|---|---|
| `00-Nap-Danh-Muc-Thi-Truong.cmd` | Lấy/làm mới danh mục cổ phiếu HOSE, HNX, UPCoM |
| `02-Nap-Lich-Su-Toan-Thi-Truong.cmd` | Dựng lịch sử giá toàn danh mục và VNINDEX; mặc định từ 01/01/2025 |
| `03-Cap-Nhat-Gia-Toan-Thi-Truong.cmd` | Cập nhật giá sau phiên, khi nguồn đã công bố dữ liệu; nên chạy sau 16:00 giờ Việt Nam |
| `04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd` | Nạp/bổ sung BCTC năm toàn danh mục; mặc định từ 2022 |
| `05-Nap-Vi-Mo-Tin-Tuc.cmd` | Lấy vĩ mô, tỷ giá, RSS và tin cho nhóm mã cấu hình; mặc định VCB, FPT, HPG |
| `06-Kiem-Tra-Du-Lieu.cmd` | Kiểm tra dữ liệu đã lưu, không nạp hoặc sửa dữ liệu |

**Lần đầu dựng kho:** `00 → 02 → 04 → 06`. **Cập nhật sau mỗi phiên:** chạy `03`; chạy `04` khi cần BCTC năm mới và `05` khi cần bối cảnh/tin.

`04` chỉ quét BCTC năm; quý mới nạp theo mã trên web. `05` không quét tin cho từng mã của toàn thị trường. Ngày bắt đầu và nhóm mã mặc định nằm trong `config/watchlist.json`.

Quét toàn thị trường có thể cần nhiều lượt do hạn mức nguồn. Chạy lại để dùng phần đã lưu và bổ sung phần thiếu. Xem [tham số CMD và công cụ bảo trì](docs/MANUAL_RUN.md) nếu cần giới hạn mã, sàn hoặc khoảng thời gian.

## 3. Xem phân tích và xuất PDF

Sau khi nạp, chọn doanh nghiệp rồi bấm **Xem phân tích**. Nếu nạp bằng CMD khi web đang mở, tải lại trang để làm mới danh sách.

- Mở các trang giá, tài chính, so sánh, vĩ mô và cơ hội/rủi ro để xem dữ liệu.
- Vào **Dữ liệu & hướng dẫn → Kiểm tra dữ liệu đã lưu** để kiểm tra ngày giá cuối, năm/quý BCTC và phần còn thiếu.
- Bấm **Xuất báo cáo PDF**. PDF và JSON phân tích được lưu tại `reports/generated/`.

Khi đã có dữ liệu phù hợp trên máy, xem phân tích và xuất PDF có thể chạy offline. Việc tải dữ liệu mới cần Internet và quyền truy cập nguồn. Có mã trong danh mục hoặc quét xong không đồng nghĩa mọi kỳ/chỉ tiêu đã đầy đủ.

## 4. Nguồn và cách lấy dữ liệu

| Dữ liệu | Nguồn và cách lấy |
|---|---|
| Danh mục cổ phiếu | KBS qua `vnstock`, lấy danh mục ba sàn khi chạy `00` |
| Giá và VNINDEX | KBS qua `vnstock`; lấy lịch sử lần đầu, các lượt sau cập nhật vùng gần nhất đã lưu |
| BCTC năm | [Kho Tumiqa](https://github.com/Tumiqa/vn-annual-report-miner) ghim phiên bản cho HOSE/HNX, tải Parquet vào cache để dùng lại; VCI bổ sung khi thiếu/cần đối soát. UPCoM thử VCI khi nguồn hỗ trợ |
| BCTC quý | VCI qua `vnstock`, lấy khi người dùng yêu cầu nạp quý |
| Vĩ mô và tỷ giá | Báo cáo NSO theo URL trong `config/sources.json`; tỷ giá từ XML Vietcombank |
| Tin tức | CafeF RSS; KBS và các URL công bố doanh nghiệp khi chạy `05`. RSS lưu tiêu đề, tóm tắt, ngày và URL |
| Dữ liệu nhập tay | CSV/JSON đã đối soát, nhập ở **Dữ liệu & hướng dẫn**; xem [mẫu và quy cách](docs/DATA_GUIDE.md) |

Web và CMD dùng chung `data/local/` trên mỗi máy. Cache BCTC nằm trong `data/reference/`. Hai thư mục này được tạo khi cần và không đi kèm GitHub. Bộ thực tế cố định trong `data/submission/` chỉ bổ sung phần còn thiếu vào local lần đầu; không thay cho việc nạp dữ liệu mới.

Ứng dụng không tự cập nhật theo lịch và không tự tìm báo cáo vĩ mô mới nhất. Kiểm tra ngày/kỳ công bố, đơn vị và phạm vi dữ liệu trước khi dùng kết quả; tin RSS và dữ liệu tự động chưa mặc nhiên được đối soát. Giá mục tiêu không hiển thị trên web/PDF.

Thư viện `vnstock`/`vnai` được cài từ kho chính thức của Vnstock, các thư viện còn lại từ PyPI. Nếu SDK yêu cầu đăng ký, làm theo thông báo của SDK; việc nạp vẫn chịu hạn mức của nguồn.

## 5. Cập nhật và xử lý lỗi

**Cập nhật source:** dừng ứng dụng trước. Nếu clone bằng Git, chạy `git pull --ff-only`; nếu dùng ZIP, tải bản mới và giải nén ra thư mục mới. Sau đó chạy lại `Cai-Dat.cmd` rồi `Mo-Ung-Dung.cmd`. Cập nhật source không tự cập nhật dữ liệu.

| Tình huống | Cách xử lý |
|---|---|
| Không tìm thấy Python | Kiểm tra Python 3.11 và PATH; đóng/mở lại cửa sổ lệnh |
| Cài thư viện thất bại | Kiểm tra Internet tới PyPI/`vnstocks.com`, đọc lỗi rồi chạy lại `Cai-Dat.cmd` |
| Không mở được web | Xem `logs/server-error.log`; nếu cổng 8001 đang dùng, dừng ứng dụng cũ trước |
| Giao diện chưa đổi sau cập nhật | Nhấn Ctrl+F5; dừng/mở lại server nếu vừa thay source |
| Nạp báo `partial`/`failed` hoặc hết hạn mức | Xem kết quả từng bước, đợi nguồn cho phép rồi nạp lại; dữ liệu đã lưu hợp lệ được giữ |

Không đưa `.env`, API key hoặc token lên GitHub. Các tùy chọn cài đặt và kiểm tra nâng cao nằm trong [hướng dẫn bảo trì](docs/MANUAL_RUN.md).

## 6. Tài liệu chi tiết

- [Quy cách nhập CSV/JSON](docs/DATA_GUIDE.md)
- [Kho BCTC Tumiqa và giới hạn](docs/KHO_BCTC_TUMIQA.md)
- [Chuẩn hóa BCTC và tính tái lập](docs/SUA_BCTC_VA_TAI_LAP.md)
- [Nguồn cụ thể](docs/SOURCES.md)
- [Bản VCB cố định và phạm vi đối soát](docs/CHAY_BAN_NOP.md)

Giấy phép đi kèm: [MIT của nguồn tham khảo](licenses/vn-annual-report-miner-MIT.txt), [font DejaVu](assets/fonts/LICENSE_DEJAVU).
