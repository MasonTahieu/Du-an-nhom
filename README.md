# StockInsight — VN Equity Research

**Hướng dẫn tải mã nguồn từ GitHub, cài đặt và chạy ứng dụng trên máy cá nhân (local).**

StockInsight là ứng dụng nghiên cứu cổ phiếu Việt Nam chạy trên máy tính cá nhân, sử dụng **Python + FastAPI**, giao diện **HTML/CSS/JavaScript**, lưu dữ liệu **Parquet/JSON** và hỗ trợ xuất báo cáo phân tích **PDF**. Các nhóm phân tích gồm tổng quan vĩ mô, ngành, doanh nghiệp, giá/giao dịch và cơ hội đầu tư.

> **Phạm vi hướng dẫn:** bản StockInsight đã tích hợp kho BCTC năm Tumiqa, chức năng **“Nạp / cập nhật mã này”**, khung nạp dữ liệu có thể thu gọn và bản sửa mã hóa UTF-8 trên Windows. Nếu GitHub đang chứa bản source cũ hơn, một số tên chức năng có thể khác.
>
> **Lưu ý:** Hướng dẫn bên dưới giả định người đăng GitHub đã commit đủ mã nguồn, thư mục `data/submission/`, `data/sample/`, `assets/fonts/`, file cấu hình và các script `.cmd` của dự án. Link GitHub cụ thể do chủ dự án cung cấp.

## 1. Yêu cầu hệ thống

- **Hệ điều hành:** Windows (các bước `.cmd` và PowerShell bên dưới dành cho Windows).
- **Python:** khuyến nghị **Python 3.11, bản 64-bit**; script cài đặt yêu cầu Python từ 3.11 trở lên. Bản đã kiểm thử và khóa thư viện là Python 3.11.
- **Kết nối Internet:** cần khi cài thư viện lần đầu và khi nạp dữ liệu trực tuyến; không cần Internet để xem/phân tích lại dữ liệu đã đóng gói hoặc cache hợp lệ sau khi cài xong.
- **Git:** *không bắt buộc*, chỉ cần nếu muốn dùng `git clone`, `git pull` hoặc tự cập nhật source từ repository.
- **Trình duyệt:** Chrome, Edge hoặc trình duyệt hiện đại tương đương.

> Không cần tự cài PostgreSQL, SQLite server, Node.js hoặc dịch vụ AI để chạy phiên bản này.

## 2. Tải source code từ GitHub

### Cách A — Download ZIP (dễ nhất, không cần cài Git)

1. Mở **trang GitHub của dự án StockInsight** do nhóm cung cấp.
2. Nhấn **Code** → **Download ZIP**.
3. Giải nén ZIP vào thư mục bạn muốn, ví dụ `D:\StockInsight`.
4. Mở thư mục sau giải nén và tìm **`Cai-Dat.cmd`** và **`Mo-Ung-Dung.cmd`**.

**Quan trọng:** Nếu file ZIP tạo thêm một thư mục trung gian như `StockInsight-main`, hãy thao tác **bên trong thư mục có các file `.cmd`**. Không cần đổi tên thư mục để chạy.

### Cách B — Clone bằng Git (phù hợp nếu thường xuyên cập nhật source)

Mở PowerShell, di chuyển đến thư mục muốn lưu rồi chạy:

```powershell
cd D:\
git clone <URL_GITHUB_CUA_DU_AN>
cd <TEN_THU_MUC_DU_AN>
```

Thay `<URL_GITHUB_CUA_DU_AN>` bằng URL **Clone HTTPS** trên nút **Code** của GitHub (ví dụ có đuôi `.git`), và thay `<TEN_THU_MUC_DU_AN>` bằng tên thư mục được tạo sau khi clone. **Đây là chỗ điền thông tin, không phải lệnh để chạy nguyên văn.**

Nếu clone repo riêng tư, bạn cần được cấp quyền truy cập GitHub tương ứng.

## 3. Kiểm tra Python trước khi cài

Mở **PowerShell** trong Windows và chạy:

```powershell
python --version
```

Kết quả mong muốn, ví dụ:

```text
Python 3.11.x
```

Nếu chưa có Python 3.11:

1. Tải từ [python.org/downloads](https://www.python.org/downloads/).
2. Cài bản Python 3.11 phù hợp với Windows.
3. Khi cài, bật tùy chọn **Add python.exe to PATH** (nếu trình cài đặt cung cấp).
4. Đóng/mở lại PowerShell rồi chạy `python --version` một lần nữa.

**Lưu ý:** `Cai-Dat.cmd` sử dụng lệnh `python` trên PATH. Nếu máy có nhiều phiên bản Python, hãy đảm bảo lệnh `python` trỏ tới bản 3.11 trước khi tiếp tục.

## 4. Cài đặt thư viện của dự án (chỉ cần làm lần đầu)

1. Mở thư mục gốc vừa tải từ GitHub.
2. Nhấp đúp **`Cai-Dat.cmd`**.
3. Chờ chương trình cài các thư viện từ `requirements.lock.txt` và kiểm tra dữ liệu demo.
4. Khi có thông báo sẵn sàng, hoàn tất bước cài đặt.

Script hiện tại tạo/tái sử dụng môi trường Python ở:

```text
C:\Users\<TEN_NGUOI_DUNG>\.venv\
```

Đây là thư mục **môi trường thư viện**, không phải nơi lưu dữ liệu cổ phiếu. Nếu đã có `.venv` ở thư mục người dùng do dự án Python khác tạo, nên lưu ý nguy cơ dùng chung các thư viện giữa các dự án.

### Muốn nạp dữ liệu mới từ Internet?

Chạy thêm **`01-Cai-Bo-Nap.cmd`** (một lần trên máy mới). Script này cài các thư viện thu thập trực tuyến như `vnstock` cùng các thư viện hỗ trợ đọc nguồn web. Nếu chỉ xem báo cáo VCB/FPT/HPG từ bộ dữ liệu đi kèm, bước này **không bắt buộc**.

## 5. Khởi động ứng dụng

1. Trong thư mục gốc, nhấp đúp **`Mo-Ung-Dung.cmd`**.
2. Đợi cửa sổ thông báo ứng dụng chạy thành công.
3. Trình duyệt thường tự mở. Nếu không, truy cập:

   **http://127.0.0.1:8001**

4. Trang **VN Equity Research** xuất hiện là bạn đã khởi chạy thành công.

Các lần sử dụng sau, thông thường chỉ cần chạy **`Mo-Ung-Dung.cmd`**, không cần chạy lại trình cài đặt.

### Dừng ứng dụng

Nhấp đúp **`Tat-Ung-Dung.cmd`** để dừng tiến trình server do script dự án khởi động. Nên dừng ứng dụng trước khi cập nhật mã nguồn hoặc áp dụng bản vá.

> Nếu mở lại mà vẫn thấy giao diện cũ, nhấn **Ctrl + F5** trên trình duyệt để tải lại HTML/CSS/JS.

## 6. Cách 1 — Xem dữ liệu đã có sẵn, không cần nạp lại

Sau khi mở giao diện:

1. Ở mục **Bộ dữ liệu**, chọn **“Bộ thực tế cố định · VCB, FPT, HPG”** (bản mới thường chọn sẵn).
2. Ở mục **Doanh nghiệp**, chọn **VCB**, **FPT** hoặc **HPG**.
3. Bấm **“Xem phân tích”**.
4. Dùng thanh điều hướng bên trái để xem: tổng quan, vĩ mô và ngành, giá/giao dịch, tài chính, so sánh và tin tức, định giá và rủi ro.
5. Bấm **“Xuất báo cáo PDF”** khi cần tạo báo cáo từ dữ liệu đã lưu.

**Phân biệt ba chế độ dữ liệu:**

| Chế độ trên giao diện | Thư mục | Mục đích |
|---|---|---|
| Demo cố định | `data/sample/` | Dữ liệu mẫu để thử chức năng |
| Bộ thực tế cố định | `data/submission/` | Dữ liệu đi kèm source, có thể dùng để trình bày VCB/FPT/HPG |
| Dữ liệu thực tế đang cập nhật | `data/local/` | Dữ liệu do người sử dụng chủ động nạp trên máy của họ |

Chế độ `submission` được thiết kế để giữ nguyên dữ liệu bản nộp. **Chỉ VCB có nhận định đã đối soát trong phạm vi được ghi ở báo cáo; FPT/HPG không mặc nhiên được coi là đã đối soát hoàn toàn.**

### Báo cáo PDF nằm ở đâu?

- PDF xuất mới qua giao diện: thường được ghi trong **`reports/generated/`** (tên file phụ thuộc mã và chế độ dữ liệu).
- PDF VCB mẫu đã đóng gói: **`output/pdf/`**, nếu chủ repo đã đưa thư mục này lên GitHub.
- Có thể tải PDF thông qua chức năng của giao diện khi tạo báo cáo.

## 7. Cách 2 — Nạp/cập nhật một mã cổ phiếu mới

Ví dụ bạn muốn phân tích **CTG**, **MWG** hoặc một mã khác chưa có dữ liệu đầy đủ trong `local`.

**Điều kiện:** đã chạy `01-Cai-Bo-Nap.cmd`, có Internet và ứng dụng đang mở.

1. Mở thanh **“Nạp dữ liệu theo mã”** (mặc định có thể đang thu gọn; bấm vào thanh để mở).
2. Nhập mã cổ phiếu, ví dụ `CTG`.
3. Nếu chỉ muốn thử quy trình cơ bản, **không tích** ô bổ sung dữ liệu ở lần đầu.
4. Bấm **“Nạp / cập nhật mã này”**.
5. Đợi từng bước hoàn thành, xem các trạng thái `complete`, `partial`, `failed` nếu có.
6. Sau khi nạp, chọn **“Dữ liệu thực tế đang cập nhật”**, chọn mã vừa nạp và bấm **“Xem phân tích”** (giao diện có thể tự chuyển sang chế độ này khi công việc kết thúc).

### Nút “Nạp / cập nhật mã này” lấy gì?

**Mặc định hệ thống thử nạp:**

- BCTC **năm** của mã được chọn và các doanh nghiệp đối chiếu đã cấu hình, ưu tiên kho Parquet lịch sử Tumiqa đã cache.
- Giá giao dịch lịch sử của mã được chọn qua KBS/vnstock.
- Giá chỉ số **VN-Index** để so sánh.

**Nếu tích ô “Bổ sung BCTC quý, vĩ mô và tin tức (lâu hơn)”**, hệ thống còn thử lấy:

- BCTC quý qua nguồn đã cấu hình (khả năng thành công phụ thuộc nguồn/SDK).
- Dữ liệu vĩ mô và tỷ giá từ các nguồn đã cấu hình.
- Tin tức doanh nghiệp từ các nguồn hỗ trợ.

**Lưu ý quan trọng:** `complete` chỉ nghĩa là một bước đã thực hiện xong theo quy tắc của chương trình; **không cam kết** đã có đầy đủ dữ liệu, cập nhật đến ngày hiện tại, đã kiểm toán hoặc đủ cơ sở định giá. Nguồn Tumiqa cung cấp **BCTC năm lịch sử**, không cung cấp giá cổ phiếu, VN-Index, toàn bộ BCTC quý hoặc toàn bộ tin tức.

### Có cần tải BCTC của từng mã thủ công không?

**Không cần tải lại toàn bộ BCTC năm lịch sử từng mã.** StockInsight có cơ chế dùng các file Parquet chung theo sàn HSX/HNX. Chương trình kiểm tra cache trước, chỉ tải file Parquet chưa có, sau đó lọc dữ liệu theo mã và năm. Một bộ file đã tải có thể được tái sử dụng cho nhiều mã trên cùng sàn.

Nếu muốn **tải trước toàn bộ 6 file BCTC năm của HSX/HNX**, nhấp đúp:

```text
08-Chuan-Bi-Kho-BCTC-Tumiqa.cmd
```

Đây là **tùy chọn**, không bắt buộc để mở ứng dụng hoặc xem các mã trong `submission`. Chức năng nạp theo mã vẫn cần lấy giá và các dữ liệu khác từ nguồn riêng.

> **Không cần chạy quét giá toàn thị trường** để dùng chức năng này. Các script quét toàn thị trường chỉ dành cho tác vụ nâng cao, có thể mất lâu và phụ thuộc hạn mức API.

## 8. Dữ liệu lưu ở đâu? Máy khác clone GitHub có được gì?

```text
StockInsight/
├── vnresearch/                   # Python: nạp, lưu, phân tích, API, PDF
├── static/                       # Giao diện web
├── config/                       # Danh sách mã, đối chiếu, nguồn và cấu hình
├── assets/fonts/                 # Font cần cho báo cáo PDF tiếng Việt
├── data/
│   ├── sample/                   # Dữ liệu mẫu đi kèm Git
│   ├── submission/               # Dữ liệu bản nộp cố định đi kèm Git
│   ├── local/                    # Dữ liệu tải trên máy người dùng; không lên Git
│   └── reference/tumiqa/         # Cache BCTC chung; không lên Git
├── reports/generated/           # PDF/JSON xuất mới; không lên Git
├── scripts/                     # Script cài đặt / khởi chạy / thu thập
├── logs/                        # Nhật ký vận hành; không lên Git
├── requirements.lock.txt        # Thư viện ứng dụng
├── requirements-market.txt      # Thư viện thu thập trực tuyến
├── Cai-Dat.cmd
├── 01-Cai-Bo-Nap.cmd
├── Mo-Ung-Dung.cmd
└── Tat-Ung-Dung.cmd
```

**Điểm cần nhớ:** `data/local/`, `data/reference/`, `logs/`, `tmp/` và các báo cáo người dùng tạo thường nằm trong `.gitignore`. Vì vậy:

- Máy mới **có sẵn dữ liệu** trong `sample` và `submission` **nếu người đăng repo đã commit các thư mục đó**.
- Máy mới **không có dữ liệu `local` và cache Tumiqa của máy cũ**. Cần nạp lại khi cần hoặc sao chép dữ liệu bằng cách riêng, nếu quyền sử dụng nguồn cho phép.
- Dữ liệu mới được lưu lại và tái sử dụng trên **chính máy mới**; không tự đồng bộ ngược lên GitHub.
- Không cần dùng database server. StockInsight lưu giá/BCTC bằng Parquet và một số loại thông tin bằng JSON.

## 9. Các file `.cmd` thường dùng

| File | Chức năng | Khi nào chạy? |
|---|---|---|
| `Cai-Dat.cmd` | Cài thư viện và kiểm tra demo | Lần đầu trên máy mới |
| `01-Cai-Bo-Nap.cmd` | Cài thêm thư viện nạp trực tuyến | Trước khi nạp mã mới |
| `Mo-Ung-Dung.cmd` | Khởi động web local | Mỗi khi sử dụng |
| `Tat-Ung-Dung.cmd` | Dừng web local | Khi muốn thoát/cập nhật source |
| `08-Chuan-Bi-Kho-BCTC-Tumiqa.cmd` | Tải trước 6 file BCTC năm chung | Tùy chọn |
| `06-Kiem-Tra-Du-Lieu.cmd` | Kiểm tra dữ liệu đã lưu | Khi cần kiểm tra |
| `07-Xuat-Bao-Cao-VCB.cmd` | Kiểm tra và tạo lại PDF VCB từ `submission` | Khi cần kiểm thử bản nộp |

Các script khác như `00-Nap-Danh-Muc-Thi-Truong.cmd`, `02-Nap-Lich-Su-Gia.cmd`, `03-Cap-Nhat-Gia.cmd`, `04-Nap-BCTC.cmd` và `05-Nap-Vi-Mo-Tin-Tuc.cmd` phục vụ thao tác thu thập nâng cao qua CMD. Bạn **không cần chạy tất cả** để xem bộ dữ liệu có sẵn hoặc nạp một mã qua giao diện.

## 10. Xử lý một số lỗi thường gặp

### `python is not recognized` hoặc không tìm thấy Python

Cài Python 3.11, bật PATH, mở lại PowerShell rồi chạy `python --version`. Kiểm tra Windows App Execution Aliases nếu `python` bị chuyển sang Microsoft Store.

### Mở ứng dụng nhưng trình duyệt không hiện

Truy cập thủ công **http://127.0.0.1:8001**. Nếu vẫn không được, kiểm tra:

```text
logs/server-error.log
logs/server.log
```

Trong PowerShell (mở tại thư mục dự án):

```powershell
Get-Content .\logs\server-error.log -Tail 80
```

### Cổng 8001 đang được sử dụng

Chạy **`Tat-Ung-Dung.cmd`**, rồi mở lại. Nếu lỗi vẫn còn, cần kiểm tra tiến trình đang dùng cổng 8001 trước khi dừng; không tắt toàn bộ tiến trình Python trên máy.

### Trang hiện phiên bản giao diện cũ

Nhấn **Ctrl + F5**. Nếu cần, dừng ứng dụng, xác nhận bạn đang khởi chạy đúng thư mục đã tải/cập nhật, rồi mở lại.

### Mã cổ phiếu có BCTC nhưng biểu đồ giá hiển thị “Chưa có”

BCTC năm và giá cổ phiếu là **hai nguồn khác nhau**. Hãy chạy **Nạp / cập nhật mã này**, chờ bước **Giá [MÃ]** hoàn thành. Nếu nguồn giá lỗi hoặc giới hạn lượt truy cập, có thể cần nạp lại sau.

### Nạp một phần (`partial`) hoặc thất bại (`failed`)

Xem **trạng thái của từng bước** ngay dưới khung nạp. Lượt nạp có thể thành công ở BCTC năm và giá nhưng thất bại ở BCTC quý, vĩ mô hoặc tin tức. Những phần đã lưu hợp lệ vẫn được giữ lại; lỗi không đồng nghĩa toàn bộ dữ liệu hỏng. Giữ ứng dụng chạy trong khi tác vụ nạp đang thực hiện.

### `charmap codec can't encode character`

Đây thường là lỗi mã hóa đầu ra trên Windows khi chương trình ghi tiếng Việt vào log. Hãy chắc chắn GitHub đã chứa bản cập nhật **UTF-8** của `scripts/Start.ps1`, `vnresearch/__main__.py` và `vnresearch/console.py`; dừng/mở lại ứng dụng sau khi cập nhật. Nếu lỗi vẫn còn, kiểm tra log và phiên bản thư viện.

### Không xuất được PDF tiếng Việt

Xác nhận thư mục **`assets/fonts/`** có các font DejaVu cần thiết và đã được đưa lên GitHub. Thư mục này không nên bị bỏ đi khi đóng gói source.

## 11. Kiểm tra sau khi cài đặt (tùy chọn)

Mở PowerShell tại thư mục gốc rồi chạy:

```powershell
.\_python.cmd -m vnresearch verify --mode submission
.\_python.cmd -m vnresearch analyze VCB --mode submission
.\_python.cmd -m vnresearch report VCB --mode submission
```

Bước 1 kiểm tra tính toàn vẹn các file trong manifest; bước 2 tạo snapshot kết quả phân tích và bước 3 tạo báo cáo PDF. Kết quả mặc định sẽ nằm trong `reports/generated/`.

Bạn cũng có thể xem tài liệu API của ứng dụng sau khi server chạy tại **http://127.0.0.1:8001/api/docs**.

## 12. Checklist dành cho người đăng dự án lên GitHub

Trước khi gửi link cho người khác, người quản lý dự án nên kiểm tra:

- [ ] Đã commit đầy đủ **source code**, `static/`, `vnresearch/`, `scripts/`, các file `.cmd` và `requirements*.txt`.
- [ ] Đã commit **`data/sample/` và `data/submission/`**, gồm manifest và dữ liệu Parquet/JSON cần dùng.
- [ ] Đã commit **`assets/fonts/`** và tài liệu giấy phép tương ứng.
- [ ] **Không** commit token, `.env`, dữ liệu cá nhân, `data/local/`, `data/reference/`, `.venv/`, `tmp/`, `logs/` và cache.
- [ ] Đã thử **clone vào một thư mục mới hoặc trên máy khác**, chạy `Cai-Dat.cmd`, `Mo-Ung-Dung.cmd`, xem VCB và xuất PDF.
- [ ] Nếu muốn người dùng nạp mã mới, đã thử `01-Cai-Bo-Nap.cmd` và một lượt nạp qua giao diện có Internet.
- [ ] Đã ghi rõ các giới hạn của BCTC quý, độ cập nhật tin/vĩ mô và mức đối soát của báo cáo.

## 13. Nguồn tham khảo và giới hạn dữ liệu

- Kho BCTC năm lịch sử: [Tumiqa/vn-annual-report-miner](https://github.com/Tumiqa/vn-annual-report-miner). Các file Parquet nguồn được quản lý theo commit được cấu hình; nguồn này không thay thế việc đối soát với công bố chính thức của doanh nghiệp.
- Giá cổ phiếu và VN-Index: các nguồn do KBS/vnstock hỗ trợ, tùy tính khả dụng của SDK và quyền truy cập nguồn.
- Vĩ mô, tỷ giá và tin tức: nguồn cấu hình trong `config/sources.json`.
- Xem thêm `THIRD_PARTY_NOTICES.md`, `docs/SOURCES.md`, `docs/NAP_THEO_MA.md` và `docs/CHAY_BAN_NOP.md`.

> **Cảnh báo sử dụng:** Đây là công cụ hỗ trợ nghiên cứu và học tập, không phải hệ thống khuyến nghị đầu tư được xác thực độc lập. Bản thân việc tải xong dữ liệu không đảm bảo mọi kỳ tài chính, ngành, giá, tin tức hoặc giả định định giá đều chính xác và đầy đủ.
