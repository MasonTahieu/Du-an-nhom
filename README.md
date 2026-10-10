# StockInsight — VN Equity Research

Ứng dụng nghiên cứu cổ phiếu Việt Nam chạy trên máy cá nhân: nạp giá/BCTC, lưu Parquet/JSON, phân tích trên web và xuất PDF tiếng Việt.

**Hai cách nạp dữ liệu:** nhập từng mã trên web, hoặc chủ động chạy CMD quét toàn thị trường. Sau mỗi phiên giao dịch, chạy CMD cập nhật giá để bổ sung các phiên mới. Cả hai cách dùng chung `data/local/`; mở phân tích hoặc xuất PDF không tự gọi API.

Repository: [MasonTahieu/Du-an-nhom](https://github.com/MasonTahieu/Du-an-nhom).

**Lưu ý về dữ liệu trên máy mới:** tải source từ GitHub là tải chương trình, **không nhận được kho dữ liệu thị trường mà tác giả hoặc người khác đã quét**. Mỗi máy cần có Internet và chủ động nạp dữ liệu bằng web hoặc CMD để xây dựng kho riêng. Cài đặt thư viện và mở ứng dụng không thay cho bước nạp dữ liệu.

Repository hiện có dữ liệu mẫu và một bản dữ liệu thực tế cố định để kiểm tra/tham khảo. Những dữ liệu này không phải kho toàn thị trường, không bảo đảm có mã/kỳ bạn cần và không tự cập nhật theo ngày. Người dùng vẫn cần tải dữ liệu phục vụ các mã muốn nghiên cứu và kiểm tra ngày giá, kỳ BCTC trước khi phân tích.

## 1. Tải source và chạy dự án trên Windows

### Bước 1 — Tải toàn bộ source từ GitHub

Mở [repository MasonTahieu/Du-an-nhom](https://github.com/MasonTahieu/Du-an-nhom), chọn một trong hai cách tải:

- **Tải ZIP, không cần Git:** bấm **Code → Download ZIP**, đợi tải xong, nhấp phải file ZIP → **Extract All / Giải nén tất cả**. Mở thư mục đã giải nén có `README.md`, `Cai-Dat.cmd`, `Mo-Ung-Dung.cmd`, `static/` và `vnresearch/`. Không chạy CMD ngay bên trong file ZIP và không chỉ tải riêng vài file Python.
- **Clone bằng Git:** nếu máy đã cài Git, mở PowerShell tại thư mục muốn lưu dự án rồi chạy:

```powershell
git clone https://github.com/MasonTahieu/Du-an-nhom.git
cd Du-an-nhom
```

Cả hai cách đều tải source của cùng dự án. Tải ZIP phù hợp khi chỉ muốn chạy ứng dụng; clone thuận tiện hơn khi cần cập nhật source về sau.

### Bước 2 — Cài Python và thư viện

1. Cài **Python 3.11, 64-bit**, bật **Add Python to PATH** khi cài. Bộ cài dự án chấp nhận Python từ 3.11; Python 3.11 là phiên bản khuyến nghị cho bộ thư viện đã khóa.
2. Nếu cần kiểm tra, mở PowerShell và chạy `python --version`. Sau khi mới cài Python, đóng và mở lại cửa sổ lệnh để PATH được cập nhật.
3. Trong thư mục dự án, nhấp đúp **`Cai-Dat.cmd`**. Cần Internet để cài thư viện.
4. Đợi thông báo **San sang. Chay Mo-Ung-Dung.cmd de mo giao dien.** Nếu có lỗi, xử lý theo thông báo rồi chạy lại bộ cài; chưa chuyển sang bước mở ứng dụng.

Bộ cài tạo/tái sử dụng `.venv` ngay trong thư mục dự án. Các CMD và script mở web đều dùng Python của môi trường này. Bộ cài cài thư viện ứng dụng từ `requirements.lock.txt`, kiểm tra dữ liệu mẫu đóng gói, rồi cài bộ nạp từ `requirements-market.txt` (dùng bản khóa `requirements-market.lock.txt`). `vnstock`/`vnai` lấy từ kho chính thức của Vnstock; các thư viện còn lại lấy từ PyPI. Cả thư viện nền và thư viện bộ nạp được giữ theo các file khóa để máy khác cài cùng phiên bản. Chỉ có **một bộ cài đầy đủ**, không cần cài riêng bộ quét thị trường. Thông thường chỉ cài một lần; chạy lại khi source hoặc yêu cầu thư viện thay đổi.

Nếu chỉ cần xem dữ liệu đã có, có thể chạy `.\Cai-Dat.cmd -Offline`. Tùy chọn này bỏ qua bộ nạp online; vẫn cần Internet để tải thư viện ứng dụng khi cài lần đầu. Muốn nạp dữ liệu mới, chạy lại `.\Cai-Dat.cmd` không kèm `-Offline`. Nếu bộ nạp cài lỗi, bộ cài báo rõ phần ứng dụng đã sẵn sàng nhưng cài đặt đầy đủ chưa hoàn tất, không báo thành công toàn bộ.

Máy đã dùng phiên bản cũ: chạy lại `Cai-Dat.cmd` để tạo môi trường riêng trong dự án; môi trường cũ ở thư mục người dùng được giữ nguyên. Khi chuyển dự án sang thư mục/máy khác, tải đủ source rồi chạy bộ cài tại nơi mới; không sao chép `.venv` cũ. macOS/Linux dùng `sh scripts/setup.sh` (hoặc thêm `--offline` nếu chỉ cần phần ứng dụng).

Không cần tự cài database server, Node.js hay dịch vụ AI. Không đưa `.env`, API key hoặc token vào GitHub. Nếu SDK yêu cầu đăng ký trên máy mới, thực hiện theo thông báo của SDK; hệ thống không bỏ qua hạn mức nguồn.

### Bước 3 — Mở và dừng ứng dụng

1. Nhấp đúp **`Mo-Ung-Dung.cmd`**. Script khởi động server trên máy và mở trình duyệt.
2. Nếu trình duyệt không tự mở, truy cập **http://127.0.0.1:8001** trên chính máy đang chạy dự án.
3. Chọn doanh nghiệp và bấm **Xem phân tích**. Có dữ liệu phù hợp thì có thể bấm **Xuất báo cáo PDF**.
4. Khi muốn dừng server, chạy **`Tat-Ung-Dung.cmd`**. Đóng tab trình duyệt không đồng nghĩa server đã dừng.

**Sau khi mở ứng dụng, còn bước nạp dữ liệu:** chọn cách 1 ở mục 2 để tải dữ liệu cho từng cổ phiếu, hoặc cách 2 ở mục 3 để dựng kho toàn danh mục. Chỉ cài `Cai-Dat.cmd` và mở `Mo-Ung-Dung.cmd` chưa có nghĩa đã tải xong dữ liệu thị trường.

Ứng dụng có thể hiển thị một số dữ liệu thực tế cố định đi kèm source: lần mở đầu sẽ bổ sung phần còn thiếu của bản này vào local. Đây là bản chốt để tham khảo, không phải lượt tải dữ liệu mới từ Internet. Không coi việc đã thấy bảng số liệu là bằng chứng dữ liệu hiện tại đã đầy đủ hoặc mới nhất.

Cần Internet và quyền truy cập nguồn phù hợp để nạp dữ liệu. **Chỉ sau khi dữ liệu cần dùng đã được lưu trên máy**, việc xem phân tích và xuất PDF từ phần đã lưu mới có thể thực hiện offline. Khi offline, ứng dụng không lấy được giá, BCTC hay tin mới.

Có thể thực hiện hai bước cài và mở bằng PowerShell trong thư mục dự án:

```powershell
.\Cai-Dat.cmd
.\Mo-Ung-Dung.cmd
```

**Chọn cách nạp phù hợp:** chỉ cần nghiên cứu một vài cổ phiếu thì dùng web ở mục 2; muốn dựng kho cho toàn danh mục thị trường thì dùng CMD ở mục 3. Không bắt buộc quét toàn thị trường mới sử dụng được ứng dụng.

## 2. Cách 1 — Nạp từng cổ phiếu trên web

### Nạp hoặc cập nhật một mã

1. Vào trang **Tổng quan đầu tư**. Khung **Nạp dữ liệu theo mã** chỉ xuất hiện ở trang này.
2. Bấm tiêu đề khung để mở, nhập mã muốn nạp như SSI, FPT hoặc VCB vào ô **Mã cần nạp**.
3. Nếu chỉ cần giá và BCTC năm, để lựa chọn bổ sung ở trạng thái chưa tích. Muốn thêm BCTC quý, vĩ mô và tin tức, tích **Bổ sung BCTC quý, vĩ mô và tin tức (lâu hơn)**.
4. Bấm **Nạp / cập nhật mã này**, đợi tiến trình và xem kết quả từng bước. Mặc định hệ thống thử nạp BCTC năm của mã và nhóm đối chiếu, giá của mã và VNINDEX.
5. Sau khi nạp, chọn doanh nghiệp trong thanh trên cùng, bấm **Xem phân tích** nếu cần làm mới, rồi xem các trang phân tích hoặc **Xuất báo cáo PDF**.

Nhập mã hoặc chọn doanh nghiệp chưa làm phát sinh lượt nạp. Chỉ bấm nút nạp mới yêu cầu thu thập/cập nhật dữ liệu. Có thể dùng lại nút này cho một mã đã nạp để bổ sung dữ liệu còn thiếu hoặc cập nhật giá gần nhất.

Có thể chuyển sang trang phân tích khác trong lúc nạp; tiến trình vẫn tiếp tục. Quay lại **Tổng quan đầu tư** để xem trạng thái và kết quả. Bấm tiêu đề khung để thu gọn cũng không hủy tiến trình. **Giữ server chạy trong lúc nạp**, không chạy `Tat-Ung-Dung.cmd` khi công việc chưa xong.

Nếu chỉ muốn cập nhật tin RSS, bấm **Cập nhật tin CafeF theo ngành / mã** trong cùng khung; thao tác này không tải lại giá/BCTC. Tin được thu thập từ các kênh đã cấu hình, sau đó giao diện lọc theo mã và ngành.

### Xem và kiểm tra dữ liệu

- Thanh **Tìm cổ phiếu / Doanh nghiệp** dùng để chọn mã cần xem. Chọn mã trong danh mục không có nghĩa mã đó đã có đầy đủ dữ liệu.
- Các trang **Vĩ mô & ngành**, **Giá & giao dịch**, **Tài chính doanh nghiệp**, **So sánh & tin tức**, **Cơ hội & rủi ro** đọc dữ liệu đã lưu; không hiển thị khung nạp theo mã.
- Ở **Dữ liệu & hướng dẫn**, bấm **Kiểm tra dữ liệu đã lưu** để mở bảng thống kê ngày giá cuối, số phiên, năm/quý BCTC và số tin. Nút đổi thành **Thu gọn bảng dữ liệu**; bấm lại để đóng bảng. Mở lại sẽ kiểm tra dữ liệu hiện tại. Thao tác kiểm tra không nạp dữ liệu mới.
- Khi một nguồn gặp lỗi, xem kết quả từng bước; phần dữ liệu đã lưu hợp lệ được giữ lại. Khi bị ngắt, bấm nạp lại để tái sử dụng phần đã lưu.

BCTC năm ưu tiên cache Tumiqa ghim commit cho HOSE/HNX, dùng VCI bổ sung khi thiếu hoặc phát hiện dữ liệu tự động đáng ngờ. UPCoM thử nguồn VCI khi có hỗ trợ. BCTC quý mới dùng VCI. Giá lấy từ KBS qua vnstock; lượt đầu từ `history_start`, lượt sau cập nhật vùng gần nhất.

Không có tác vụ tự chạy theo lịch. Dữ liệu chỉ được cập nhật khi người dùng chủ động bấm nút hoặc chạy CMD.

## 3. Cách 2 — Quét toàn thị trường bằng CMD

Các thao tác sau do người dùng chủ động chạy. CMD có thể chạy độc lập, không bắt buộc mở web. Cần cài xong `Cai-Dat.cmd` trước. Không mở nhiều lượt nạp web/CMD cùng lúc.

### Cách mở CMD và truyền tham số

- **Không thêm tham số:** nhấp đúp file `.cmd` trong thư mục dự án. Đọc tiến độ/kết quả trong cửa sổ lệnh; khi xuất hiện yêu cầu nhấn phím để tiếp tục thì lượt chạy đã kết thúc.
- **Có thêm tham số:** mở thư mục dự án trong File Explorer, gõ `powershell` vào thanh địa chỉ rồi Enter. Trong cửa sổ vừa mở, chạy tên file với tiền tố `.\` và tham số như các ví dụ bên dưới.

Đợi một CMD kết thúc rồi mới chạy CMD tiếp theo. Web có thể dùng để xem dữ liệu, nhưng tránh bấm nạp trên web trong khi CMD đang nạp.

### Thứ tự chạy lần đầu và cập nhật về sau

| Khi nào | Chạy gì | Mục đích |
|---|---|---|
| Lần đầu dựng kho toàn thị trường | `00` → `02` → `04` → `06` | Lấy danh mục → lịch sử giá → BCTC năm → kiểm tra dữ liệu |
| Sau mỗi phiên giao dịch, khi nguồn đã cập nhật | `03`, sau đó `06` nếu cần | Bổ sung giá các phiên mới, kiểm tra ngày giá cuối |
| Khi có cổ phiếu mới hoặc danh mục thay đổi | `00`, sau đó `02` và `04` khi cần | Làm mới danh mục và bổ sung dữ liệu cho mã mới |
| Khi có BCTC năm mới hoặc còn thiếu dữ liệu năm | `04` | Kiểm tra kho hiện có và thử bổ sung BCTC năm |
| Khi cần vĩ mô, tỷ giá hoặc tin mới | `05` | Cập nhật phần bối cảnh theo nguồn cấu hình |
| Khi cần BCTC quý mới của một mã | Nạp trên web, tích lựa chọn bổ sung | Thu thập BCTC quý cùng các bước được chọn |

`00`, `02`, `03`… trong bảng là phần đầu tên file CMD đầy đủ ở mục 4. Không cần chạy lại toàn bộ chuỗi sau mỗi phiên; thông thường chỉ chạy `03` để cập nhật giá. Không có bộ hẹn giờ tự chạy các CMD này.

### Chuẩn bị danh mục

Chạy **`00-Nap-Danh-Muc-Thi-Truong.cmd`** để cập nhật danh sách cổ phiếu HOSE, HNX, UPCoM vào `data/local/universe.json`. Danh mục là danh sách mã, chưa phải giá hay BCTC. Phạm vi gồm cổ phiếu thường đủ điều kiện theo nguồn; không gồm ETF, chứng quyền, phái sinh hoặc mọi mã từng hủy niêm yết.

Chạy lại `00` khi cần cập nhật danh mục. CMD quét toàn thị trường dùng danh mục đã lưu; nếu chưa có, chương trình báo cần chạy `00`.

### Dựng kho lịch sử giá

Chạy **`02-Nap-Lich-Su-Toan-Thi-Truong.cmd`** để lấy lịch sử cho toàn danh mục và VNINDEX, từ `history_start` trong `config/watchlist.json`.

Tiến độ được lưu theo từng mã/khoảng ngày. Chạy lại cùng lệnh sẽ dùng các khoảng đã hoàn tất hợp lệ và tiếp tục phần còn thiếu. Dữ liệu không trùng theo mã/ngày.

Cấu hình hiện tại đặt `history_start` là **2025-01-01**. Muốn lấy từ ngày khác, chỉnh cấu hình trước khi quét hoặc dùng `--start YYYY-MM-DD`. Quét toàn thị trường có thể kéo dài và cần nhiều lượt do hạn mức nguồn; không mặc định hoàn tất trong một lần chạy.

### Cập nhật giá sau phiên

Sau khi phiên kết thúc và nguồn đã có dữ liệu, chạy **`03-Cap-Nhat-Gia-Toan-Thi-Truong.cmd`**. Nên chạy sau 16:00 giờ Việt Nam.

Hệ thống lấy vùng gần ngày giá cuối đã lưu, chồng lấn 10 ngày để đối chiếu và bổ sung các phiên mới. Chưa có giá cho một mã thì lấy khoảng mặc định một năm; muốn dựng lịch sử từ ngày cấu hình thì chạy `02`. Chạy lại cùng ngày sẽ tái sử dụng checkpoint hợp lệ.

Ngày cuối được giới hạn theo thời điểm đóng phiên và cuối tuần; ngày nghỉ lễ thực tế phụ thuộc dữ liệu nguồn. Khi có điều chỉnh lịch sử do sự kiện doanh nghiệp, có thể chủ động tải lại khoảng bằng `02 --refresh` sau khi kiểm tra cơ sở giá.

### Quét BCTC năm

Chạy **`04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd`** để nạp BCTC năm cho toàn danh mục, từ `first_year` trong cấu hình. Luồng CMD và web dùng chung cách chọn nguồn và quy tắc giữ dữ liệu đã nhập thủ công.

Cấu hình hiện tại đặt `first_year` là **2022**. Lệnh `04` không cập nhật giá và không tự nạp BCTC quý. Khi có báo cáo năm mới, chạy lại `04` để chương trình kiểm tra và thử bổ sung theo dữ liệu nguồn; không cần chạy hằng ngày.

Kết quả được ghi theo từng mã trong `data/local/collection-run.json`, gồm mã hoàn tất, lỗi/cảnh báo và mã còn chờ. Khi nguồn chạm hạn mức, lượt quét dừng và giữ dữ liệu đã lưu. Chạy lại sẽ kiểm tra dữ liệu hiện có, dùng cache hợp lệ và bổ sung phần thiếu; có thể thử lại mã lỗi hoặc kỳ chưa đủ dữ liệu.

**CMD này chỉ quét BCTC năm.** BCTC quý hiện nạp từng mã trên web; chưa có CMD quét quý toàn thị trường. Nguồn có thể không chứa một mã/năm hoặc không trả đủ chỉ tiêu; quét hết danh mục không đồng nghĩa mọi BCTC đầy đủ.

### Cập nhật vĩ mô, tỷ giá và tin tức

Chạy **`05-Nap-Vi-Mo-Tin-Tuc.cmd`** khi cần cập nhật bối cảnh phân tích. Lệnh này lấy vĩ mô, tỷ giá, tin cho nhóm mã yêu cầu và các kênh RSS đã cấu hình; không cập nhật giá hay BCTC.

Nhấp đúp `05` sẽ dùng nhóm `symbols` trong `config/watchlist.json`, hiện là **VCB, FPT, HPG**, cho bước lấy tin theo mã. Đây là **nhóm mã cấu hình**, khác với **toàn danh mục thị trường** trong `data/local/universe.json` mà `02`, `03`, `04` sử dụng. Thu thập RSS vẫn theo các kênh trong `config/news_feeds.json`; lệnh `05` không quét tin từng mã của toàn thị trường.

Muốn chỉ định nhóm mã cho bước lấy tin, chạy:

```powershell
.\05-Nap-Vi-Mo-Tin-Tuc.cmd --symbols SSI NLG
```

### Kiểm tra và làm mới giao diện sau khi quét

Chạy **`06-Kiem-Tra-Du-Lieu.cmd`** để đọc thống kê độ đầy đủ và kết quả kiểm tra tính toàn vẹn trong cửa sổ lệnh. Lệnh này không tải dữ liệu mới và không sửa các file đã lưu. Có thể dùng nút **Kiểm tra dữ liệu đã lưu** trên web để xem bảng độ đầy đủ; kiểm tra manifest/file bằng CMD có thêm kết quả xác minh tính toàn vẹn.

Sau khi CMD hoàn tất, mở ứng dụng hoặc bấm **Xem phân tích** / tải lại trang nếu web đang mở. Một mã xuất hiện trong danh mục chưa bảo đảm đã có giá/BCTC; đối chiếu ngày cuối và các kỳ còn thiếu trong bảng kiểm tra.

### Giới hạn phạm vi khi cần

Chạy từ PowerShell trong thư mục dự án:

```powershell
# Xem trước kế hoạch, không gọi API và không nạp dữ liệu.
.\02-Nap-Lich-Su-Toan-Thi-Truong.cmd --limit 3 --dry-run
.\04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd --limit 3 --dry-run

# Chỉ quét HOSE hoặc thử ba mã đầu danh mục.
.\02-Nap-Lich-Su-Toan-Thi-Truong.cmd --exchanges HOSE
.\04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd --limit 3

# Chỉ cập nhật giá hoặc BCTC năm cho nhóm mã chỉ định.
.\03-Cap-Nhat-Gia-Toan-Thi-Truong.cmd --symbols FPT HPG
.\04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd --symbols SSI NLG

# Lấy lịch sử giá từ một ngày khác ngày cấu hình.
.\02-Nap-Lich-Su-Toan-Thi-Truong.cmd --symbols FPT --start 2024-01-01
```

Các bộ xử lý vẫn hỗ trợ `--symbols` để bảo trì một nhóm cụ thể; tham số này ưu tiên hơn phạm vi toàn thị trường. Sử dụng thông thường: nạp từng mã trên web, quét toàn danh mục bằng CMD.

## 4. Danh sách CMD hiện tại

| File | Chức năng |
|---|---|
| `Cai-Dat.cmd` | Cài đầy đủ thư viện ứng dụng và bộ nạp |
| `Mo-Ung-Dung.cmd` | Mở server và trình duyệt |
| `Tat-Ung-Dung.cmd` | Dừng server do script dự án mở |
| `00-Nap-Danh-Muc-Thi-Truong.cmd` | Cập nhật danh mục ba sàn |
| `02-Nap-Lich-Su-Toan-Thi-Truong.cmd` | Dựng kho lịch sử giá toàn danh mục |
| `03-Cap-Nhat-Gia-Toan-Thi-Truong.cmd` | Cập nhật giá toàn danh mục sau phiên |
| `04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd` | Quét BCTC năm toàn danh mục |
| `05-Nap-Vi-Mo-Tin-Tuc.cmd` | Công cụ bổ trợ: vĩ mô, tỷ giá và tin theo nguồn/nhóm mã cấu hình |
| `06-Kiem-Tra-Du-Lieu.cmd` | Chỉ đọc và kiểm tra độ đầy đủ/tính toàn vẹn dữ liệu |
| `09-Kiem-Tra-Va-Sua-BCTC-Toan-Nganh.cmd` | Chuẩn hóa lại BCTC quý đã lưu, ghi báo cáo toàn ngành; không gọi mạng |
| `10-Bo-Sung-Du-Lieu-Nen-2021.cmd` | Bổ sung năm nền từ cache có sẵn; mặc định 2021, thực tế là `first_year - 1` |
| `_python.cmd` | Bộ chạy Python chung cho các CMD; không cần nhấp đúp riêng |

`05`, `06`, `09`, `10` là công cụ bổ trợ, không bắt buộc chạy sau mỗi phiên. `06` không sửa dữ liệu; `09` có sửa ánh xạ và tạo bản sao lưu. `10` lưu dữ liệu nền riêng để hỗ trợ ROA/ROE/tăng trưởng năm đầu, không ghi đè BCTC chính và không tạo thêm năm báo cáo hiển thị.

## 5. Dữ liệu trên máy và tính tái lập

### Mỗi máy phải chủ động xây dựng kho dữ liệu

Source code là phần chương trình xử lý và hiển thị; dữ liệu giá, BCTC, tin tức và vĩ mô là phần được thu thập riêng. GitHub không chứa kho `data/local/` của người đã quét và cũng không chứa cache BCTC `data/reference/` của máy đó.

Trên máy mới, thực hiện theo nhu cầu:

1. **Nghiên cứu từng cổ phiếu:** cài đặt, mở web → **Tổng quan đầu tư** → nhập mã → bấm **Nạp / cập nhật mã này**. Tích bổ sung nếu cần BCTC quý, vĩ mô và tin tức. Lặp lại với các mã muốn nghiên cứu.
2. **Xây kho toàn thị trường:** cài đặt → chạy lần lượt `00-Nap-Danh-Muc-Thi-Truong.cmd`, `02-Nap-Lich-Su-Toan-Thi-Truong.cmd`, `04-Nap-BCTC-Nam-Toan-Thi-Truong.cmd` → kiểm tra bằng `06-Kiem-Tra-Du-Lieu.cmd`. Chạy `05-Nap-Vi-Mo-Tin-Tuc.cmd` khi cần bối cảnh; BCTC quý vẫn nạp theo mã trên web.

Ví dụ: bạn đã quét SSI trên máy A, nhưng người khác tải source lên máy B thì **không tự có dữ liệu SSI của máy A**. Người đó phải nạp SSI trên web hoặc quét bằng CMD ở máy B. Một danh sách mã cổ phiếu chỉ cho biết những mã có thể chọn/quét; chưa phải bộ giá và BCTC của các mã đó.

Dữ liệu tải xong được giữ trong `data/local/` của máy đang chạy. Không phải tải lại toàn bộ mỗi lần mở ứng dụng: các lần sau đọc phần đã lưu và chủ động cập nhật/bổ sung khi cần. Nếu xóa kho này hoặc chuyển sang thư mục dự án mới mà không mang dữ liệu theo, cần nạp lại phần dữ liệu muốn sử dụng. Các phần dữ liệu thiếu do nguồn không cung cấp vẫn được báo thiếu; không có cam kết quét một lần là đủ mọi chỉ tiêu.

Cache Tumiqa được chương trình tự tải từ nguồn tham khảo khi cần, rồi giữ trên máy để tái sử dụng. Không cần xin cache riêng từ tác giả hoặc tự tìm file dữ liệu để đặt vào dự án. Lượt tải đầu cần Internet; nguồn trực tuyến có thể yêu cầu tài khoản/quyền truy cập và chịu hạn mức.

### Phân biệt các thư mục dữ liệu

| Vị trí | Vai trò |
|---|---|
| `data/local/` | Kho làm việc do mỗi máy nạp; không đi kèm GitHub ngoài file giữ thư mục. Web và CMD cùng đọc/ghi vào đây |
| `data/submission/` | Bản dữ liệu thực tế cố định đi kèm source để tham khảo/tái lập; chỉ đọc. Bổ sung phần thiếu vào local lần đầu, không thay cho việc nạp dữ liệu cần dùng |
| `data/sample/` | Dữ liệu mẫu cho kiểm tra cài đặt/kiểm thử; không trộn vào local |
| `data/reference/tumiqa/` | Cache BCTC không đi kèm GitHub; tự tải khi cần và giữ lại để dùng tiếp |
| `reports/generated/` | PDF và JSON phân tích xuất mới |
| `output/pdf/` | Báo cáo VCB cố định đã đóng gói |
| `logs/` | Nhật ký server |

Một mã được quét bằng CMD có thể xem ngay trên web; dữ liệu nạp trên web cũng được CMD sử dụng. Sau khi CMD hoàn tất, bấm **Xem phân tích** hoặc tải lại trang để cập nhật danh sách/hiển thị.

“Dùng chung” ở đây là web và CMD dùng cùng kho trên **cùng máy, cùng thư mục dự án**. Các máy khác nhau có kho local riêng, không tự đồng bộ với nhau. Source trên GitHub không chứa dữ liệu cá nhân bạn đã quét; máy mới sẽ dùng dữ liệu đóng gói và tự nạp bổ sung.

Dữ liệu local được ưu tiên khi hợp nhất bộ đóng gói; không ghi đè dữ liệu cá nhân đã có. Chỉ VCB có nhận định đã đối soát trong phạm vi ghi ở báo cáo; các mã khác chưa mặc nhiên được đối soát toàn bộ.

### Tái lập trên máy khác

Máy khác tải đủ source, `config/`, `assets/fonts/`, `data/sample/`, `data/submission/` và các `requirements*.txt`, chạy `Cai-Dat.cmd`, **sau đó tự nạp dữ liệu bằng web hoặc CMD**. Không phụ thuộc thư mục cache hay đường dẫn riêng của máy tác giả. `data/local/` và `data/reference/` bị Git bỏ qua, được tạo khi cần. Tải lại source không tự lấy về dữ liệu mà bạn hoặc thành viên khác đã quét.

`vnstock==4.0.9`, `vnai==2.6.2` được ghim; kho Tumiqa dùng `reference_commit` trong cấu hình. Cùng source/cấu hình và cùng bản dữ liệu cho cùng quy tắc tính toán. API trực tuyến có thể thay đổi dữ liệu theo ngày tải: muốn tái lập chính xác một báo cáo, giữ dữ liệu gốc, manifest, cấu hình và JSON phân tích cùng phiên bản source. SHA-256 xác nhận file không đổi, không xác nhận nguồn đã đúng.

## 6. Nguồn, chỉ tiêu và giới hạn

- Giá KBS là dữ liệu ngày; cổ phiếu được đổi sang VND, VNINDEX giữ đơn vị điểm. Chưa đối soát mọi sự kiện điều chỉnh giá doanh nghiệp.
- BCTC năm ghim Tumiqa và VCI dự phòng; bản dữ liệu tự động đáng ngờ chỉ thay khi nguồn mới được kiểm tra, có sao lưu. CSV đối soát thủ công không bị tự thay.
- Ngân hàng dùng tổng thu nhập hoạt động; công ty chứng khoán dùng doanh thu hoạt động; doanh nghiệp khác dùng doanh thu thuần theo quy tắc ngành. Không tự điền 0 cho số thiếu.
- BCTC quý giữ kỳ nguồn; chưa xác minh mọi kỳ là quý riêng hay lũy kế, không tự cộng TTM hoặc tính ROE quý.
- Vĩ mô dùng URL đã cấu hình trong `config/sources.json`; nguồn cũ không tự biến thành kỳ công bố mới.
- CafeF RSS lưu tiêu đề, tóm tắt, ngày và URL. Phân loại mã/ngành được đánh dấu chưa đối soát; không coi metadata là nội dung đã xác minh. Cấu hình kênh ở `config/news_feeds.json`.
- Đọc phân tích/xuất PDF không tự nạp mạng. Giá mục tiêu và kịch bản P/E–P/B không hiển thị trên giao diện/PDF; chỉ số lịch sử còn dùng khi có cơ sở dữ liệu.

Xem [quy cách nhập CSV/JSON](docs/DATA_GUIDE.md), [kho BCTC Tumiqa](docs/KHO_BCTC_TUMIQA.md), [chuẩn hóa BCTC và tái lập](docs/SUA_BCTC_VA_TAI_LAP.md), [nguồn dữ liệu](docs/SOURCES.md) và [bản VCB cố định](docs/CHAY_BAN_NOP.md). Giấy phép tham khảo: [MIT của vn-annual-report-miner](licenses/vn-annual-report-miner-MIT.txt), [font DejaVu](assets/fonts/LICENSE_DEJAVU).

## 7. Khi gặp lỗi

- **Python không tìm thấy:** cài Python 3.11, bật PATH, đóng/mở lại cửa sổ lệnh rồi kiểm tra `python --version`.
- **Cài thư viện lỗi:** kiểm tra mạng/thông báo lỗi và chạy lại `Cai-Dat.cmd`; bộ cài báo thất bại nếu bộ nạp chưa cài xong.
- **Không mở được web:** xem `logs/server-error.log` và `logs/server.log`. Nếu cổng 8001 đã dùng, dừng ứng dụng bằng `Tat-Ung-Dung.cmd` trước khi mở lại.
- **Giao diện cũ:** nhấn Ctrl+F5; dừng/mở server sau khi cập nhật source.
- **Partial/failed:** xem lỗi từng nguồn/mã, giữ dữ liệu đã lưu và chạy lại khi nguồn cho phép. Lỗi nguồn tùy chọn không đồng nghĩa mã chính hoàn toàn thất bại; thiếu chỉ tiêu vẫn được báo rõ.
- **Hết hạn mức API:** đợi nguồn khôi phục hạn mức rồi chạy lại cùng CMD hoặc nạp lại trên web. Không liên tục mở thêm lượt quét.
- **Không xuất được PDF tiếng Việt:** giữ đủ `assets/fonts/` và cài lại thư viện nếu cần.

## 8. Cập nhật source từ GitHub

Dừng server bằng **`Tat-Ung-Dung.cmd`** trước khi thay source. Nếu đang nạp, đợi lượt nạp kết thúc trước khi dừng.

- **Nếu đã clone bằng Git:** mở PowerShell trong thư mục dự án và chạy `git pull --ff-only`. Nếu Git báo có thay đổi local hoặc nhánh không thể cập nhật trực tiếp, xử lý các thay đổi đó trước; không ghi đè source đang chỉnh để ép cập nhật.
- **Nếu tải bằng ZIP:** tải ZIP mới và giải nén ra một thư mục mới. Nếu muốn giữ kho đã nạp, sao chép `data/local/` từ bản cũ sang đúng vị trí của bản mới; có thể sao chép thêm `data/reference/` để dùng lại cache BCTC. Giữ bản cũ cho đến khi kiểm tra bản mới hoạt động và đối chiếu các cấu hình bạn đã tùy chỉnh.

Sau khi cập nhật, chạy lại **`Cai-Dat.cmd`** để đồng bộ thư viện, rồi **`Mo-Ung-Dung.cmd`**. Nếu trình duyệt vẫn hiện giao diện cũ, nhấn **Ctrl+F5**. Thay source không tự cập nhật giá hay BCTC; vẫn dùng web hoặc các CMD nạp dữ liệu tương ứng.

## 9. Bảo trì và tái tạo bản cố định

Lệnh bên dưới chỉ dành cho người bảo trì; không cần để sử dụng thường ngày:

```powershell
# Kiểm tra dữ liệu đóng gói và tái tạo PDF VCB từ bộ cố định.
.\_python.cmd -m vnresearch verify --mode submission
if ($LASTEXITCODE -eq 0) {
    .\_python.cmd -m vnresearch report VCB --mode submission --output output/pdf/VCB_Bao_cao_2026-10-09.pdf
}

# Tải sẵn cache Tumiqa nếu chủ động cần.
.\_python.cmd -m vnresearch.reference_cache --exchange HSX HNX

# Xem trước việc bổ sung năm nền, không ghi dữ liệu.
.\10-Bo-Sung-Du-Lieu-Nen-2021.cmd --dry-run
```

Bộ kiểm thử ở `tests/`; các công cụ dựng mẫu và kiểm tra portable ở `scripts/`. Không đưa `.venv/`, `.env`, API key, `tmp/`, `logs/` hoặc dữ liệu local cá nhân lên GitHub.
