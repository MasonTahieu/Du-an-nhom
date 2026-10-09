# VN EQUITY RESEARCH
# Tài liệu nền để viết báo cáo dự án và đối chiếu yêu cầu đề

Ngày chốt bản trình bày: 09/10/2026.
Dự án: Hệ thống phân tích cơ hội đầu tư cổ phiếu Việt Nam.
Bản minh họa thực tế: VCB; CTG và MBB là doanh nghiệp đối chiếu.
Sản phẩm: ứng dụng web local, bộ dữ liệu cố định và báo cáo phân tích PDF.

## 1. Cách sử dụng tài liệu

Tài liệu này phục vụ viết báo cáo thuyết minh dự án, không thay cho báo cáo phân tích cổ phiếu.

Có hai phạm vi cần phân biệt:
- HIỆN TRẠNG: chức năng đã triển khai và kết quả đã kiểm tra trong bản nộp.
- KỊCH BẢN HOÀN THIỆN: giả định các đợt quét được thực hiện đầy đủ và các bước bổ sung được nghiệm thu. Đây là mô hình vận hành mục tiêu, chưa phải kết quả thực nghiệm toàn thị trường.

Có thể dùng các mục 2–9 để viết phần thuyết minh hệ thống. Mục 10 trình bày giả định hoàn thiện theo yêu cầu; mục 11 là điều kiện để chuyển giả định đó thành kết quả được kiểm chứng.

Thông tin nhóm, lớp, môn học, thành viên và phân công: người viết bổ sung theo thực tế.

## 2. Bài toán và mục tiêu

Đề bài yêu cầu xây dựng và vận hành hệ thống khai thác dữ liệu giá/giao dịch, báo cáo tài chính, chỉ số tài chính và tin tức doanh nghiệp để đánh giá tổng quan vĩ mô, phân tích ngành và cơ hội đầu tư của cổ phiếu được người dùng chọn. Kết quả phải được tự động trích xuất thành PDF. Các tiêu chí trọng tâm là tính chính xác của dữ liệu, sự phù hợp của phân tích và tính sáng tạo.

Dự án giải quyết bài toán dữ liệu phân tán ở nhiều nguồn, khác kỳ báo cáo, đơn vị và thời điểm cập nhật. Hệ thống đưa dữ liệu về cấu trúc thống nhất, lưu trên máy, tính toán chỉ tiêu theo công thức và tạo báo cáo có nguồn, kỳ tham chiếu và giới hạn dữ liệu.

Mục tiêu chức năng:
1. Cho phép tìm và chọn mã cổ phiếu trong danh mục thị trường.
2. Nạp dữ liệu chủ động, giữ lại kết quả để sử dụng nhiều lần.
3. Phân tích theo trình tự vĩ mô → ngành → doanh nghiệp → cơ hội và rủi ro.
4. Xuất PDF tự động từ cùng bộ dữ liệu đang hiển thị trên giao diện.
5. Cho phép chạy lại bản nghiên cứu từ bộ dữ liệu cố định trên máy khác.

Phạm vi vận hành:
- Giá lịch sử theo ngày/EOD, không phải hệ thống giao dịch realtime.
- Người dùng chạy các CMD nạp dữ liệu; việc mở giao diện hoặc xuất PDF không tự quét.
- Hỗ trợ danh mục toàn thị trường không đồng nghĩa mọi mã đã có đủ dữ liệu.
- Bản nộp ưu tiên đối soát VCB; khả năng mở rộng sang mã khác được cung cấp qua công cụ nạp và cấu hình hồ sơ doanh nghiệp.

## 3. Đối chiếu với yêu cầu đề bài

| Yêu cầu | Cách hệ thống thực hiện | Bằng chứng hiện có | Mức đáp ứng và điều kiện còn lại |
|---|---|---|---|
| Giá và dữ liệu giao dịch | Lấy OHLCV ngày; lưu Parquet; tính MA20/50, lợi suất, biến động, sụt giảm, so sánh VNINDEX | VCB có 437 phiên đến 08/10/2026; giá cuối đã đối chiếu | Có ở bản VCB; điều chỉnh giá/cổ tức toàn chuỗi chưa xác minh |
| BCTC và chỉ số tài chính | Đọc BCTC năm từ bộ Parquet; chuẩn hóa khoản mục; tính ROE, ROA, tăng trưởng, CIR và các tỷ lệ phù hợp | VCB có năm 2022–2025; chỉ tiêu trọng yếu 2024–2025 đã đối soát | Có ở bản VCB; chưa kiểm tra toàn bộ khoản mục và các năm |
| Tin tức cập nhật | Lưu URL, ngày công bố, nội dung tóm tắt và trạng thái đối soát | Bài IR VCB ngày 17/08/2026 đã được đọc, đối chiếu | Có bằng chứng tin mới hơn BCTC năm; chưa bao phủ mọi sự kiện đến ngày chốt |
| Đánh giá vĩ mô | Lưu chỉ tiêu có kỳ tham chiếu; diễn giải ảnh hưởng có điều kiện tới ngành | 5 chỉ tiêu NSO, kỳ 9 tháng/28-09-2026, được đối chiếu | Có; chuỗi lãi suất và dữ liệu định lượng chuyên sâu có thể bổ sung |
| Phân tích ngành | Cấu hình ngành, đặc thù chỉ tiêu, nhóm doanh nghiệp so sánh cùng kỳ | Ngân hàng: VCB, CTG, MBB; có phân tích bối cảnh, vốn, chất lượng tài sản | Có cho tình huống VCB; nhóm ba mã không đại diện toàn ngành |
| Cơ hội đầu tư | Kết hợp tài chính, giá, vĩ mô, tin; nêu điểm thuận lợi, rủi ro và điều kiện theo dõi | Kết luận VCB: theo dõi có điều kiện | Có đánh giá; chưa đủ giả định để đưa giá mục tiêu hoặc kết luận cổ phiếu rẻ |
| Cổ phiếu bất kỳ | Danh mục động, công cụ nạp theo mã, cấu hình hồ sơ/ngành và xử lý thiếu dữ liệu | Local có danh mục 1.522 mã; nạp theo --symbols | Hỗ trợ chọn và nạp; phân tích đầy đủ mọi mã/ngành chưa được chứng minh |
| PDF tự động | Kết xuất báo cáo từ kết quả phân tích bằng giao diện hoặc CLI | PDF VCB 9 trang, có bảng, biểu đồ, nguồn và phụ lục đối soát | Đã kiểm tra ở bản nộp |
| Dữ liệu chính xác | Kiểm tra OHLC, đơn vị, khóa trùng, giá trị thiếu; đối soát nguồn; công thức có giải thích | Bảng đối soát VCB và 54 kiểm thử đạt | Xác nhận trong phạm vi kiểm tra; không coi dấu SHA-256 là xác nhận số liệu nguồn đúng |
| Phân tích phù hợp | Tách ngân hàng với doanh nghiệp thường; không gán số 0 cho dữ liệu thiếu | VCB dùng thu nhập hoạt động/CIR; không dùng thanh toán hiện hành cho ngân hàng | Đã áp dụng; cần mở rộng phương pháp theo ngành khi mở rộng danh mục |
| Sáng tạo | Báo cáo có dấu vết nguồn, bộ dữ liệu tái lập, nhận định rà soát gắn với đầu vào | Nhận định cũ bị vô hiệu khi đầu vào liên quan thay đổi | Là đóng góp của dự án; không cần dựa vào số lượng API hay mô hình phức tạp |

Kết luận đối chiếu: bản VCB chứng minh được luồng xử lý đầu cuối từ dữ liệu thực tế tới phân tích và PDF. Phạm vi “phân tích đầy đủ mọi cổ phiếu” còn phụ thuộc độ phủ dữ liệu, cấu hình ngành và kiểm chứng theo từng nhóm doanh nghiệp. Đề không yêu cầu phải tải sẵn lịch sử của toàn bộ thị trường trước khi trình bày hệ thống.

## 4. Nguồn dữ liệu và phương pháp thu thập

### 4.1. Giá và giao dịch

Nguồn đang tích hợp: KBS thông qua thư viện Vnstock.
Dữ liệu: mã, ngày, giá mở/cao/thấp/đóng, khối lượng; thêm nguồn, đơn vị, cơ sở giá và thời điểm thu thập.

Quy trình hiện tại:
- Người dùng yêu cầu mã và khoảng thời gian bằng CMD.
- Bộ quét chia khoảng lịch sử thành từng lô, tải tuần tự và kiểm tra kết quả.
- Giá cổ phiếu được chuẩn hóa về VND; VNINDEX giữ đơn vị điểm.
- Ghi dữ liệu gốc, ghép dữ liệu chuẩn hóa và loại trùng theo mã/ngày.
- Lưu tiến độ để chạy tiếp sau khi bị ngắt hoặc gặp giới hạn nguồn.
- Khi cập nhật, quét chồng lấn một khoảng ngắn để tiếp nhận thay đổi từ nguồn.

Điểm hạn chế: cấu hình hiện tại chia lô 180 ngày, chờ giữa các lượt và ghi lại tệp giá tổng sau từng lô; chưa tối ưu khi nạp toàn thị trường. Bản nộp tận dụng dữ liệu đã có, không phụ thuộc hoàn thành đợt quét lớn.

### 4.2. BCTC năm — phương pháp tham khảo repo

Repo: https://github.com/Tumiqa/vn-annual-report-miner
Phiên bản tham khảo: f8cad8d7d4276cd22aee20113fe3214230daf919.

Code được đọc để xác nhận:
- src/arminer/data/financial.py: ưu tiên Parquet đi kèm repo, tiếp theo cache Hugging Face, sau đó tải qua vnfinancialdata; có bộ nhớ đệm trong tiến trình.
- src/arminer/export/financial_excel.py: danh mục công thức và tính tỷ số tài chính.
- src/arminer/core/smart_mode.py: mô tả biến/codebook phục vụ dữ liệu phân tích.
- src/arminer/data/industry.py: đọc danh mục phân ngành ICB từ CSV.
- src/arminer/data/catalog.py: tổ chức danh mục và chỉ mục tìm báo cáo.
- src/arminer/data/news_scraper.py: thu thập, trích nội dung tin và dùng lại kết nối.
- src/arminer/data/zenodo_downloader.py: đọc từng phần kho ZIP từ xa để lấy PDF; chưa cần đưa vào luồng bản nộp.

Kiểm tra trực tiếp sáu Parquet của bản clone cho thấy:
- 716 mã HSX/HNX và 702 mã chỉ tiêu trong hợp dữ liệu.
- Tổng dung lượng khoảng 9,18 MB.
- Có dữ liệu đến 2025; năm bắt đầu và độ đầy đủ khác nhau giữa các bảng/mã.
- Có 116 định nghĩa chỉ số trong financial_excel.py.
Các con số này mô tả đúng bản dữ liệu đã kiểm tra, không phải cam kết cho mọi phiên bản repo.

Cách dự án hiện tại áp dụng:
- Tải ba tệp báo cáo cho mỗi sàn theo commit cố định.
- Lưu cache rồi lọc mã/năm trên máy, không tải lại cho mỗi mã.
- Chuẩn hóa thành bảng khoản mục tài chính có mã, kỳ, đơn vị, nguồn.
- Chọn công thức cần thiết và kiểm tra theo đặc thù ngành; không sao chép toàn bộ bộ công thức.
- Nguồn tham khảo không cung cấp đủ BCTC năm cho toàn bộ UPCoM.

Đây là lý do tải BCTC năm có thể nhanh: dữ liệu đã được nguồn đóng gói theo lô. Repo không cung cấp bộ lịch sử giá tương đương để thay thế ngay bộ quét giá.

### 4.3. BCTC quý

Đã có công cụ nạp báo cáo quý qua KBS/Vnstock; lưu phản hồi gốc và chuẩn hóa theo kỳ.

Trong bản VCB cố định: chưa có BCTC quý chuẩn hóa. Các thông tin 6 tháng 2026 trong bài IR được trình bày riêng với nhãn nguồn công bố, không ghép thành BCTC quý và không cộng TTM khi chưa xác minh riêng quý/lũy kế.

### 4.4. Vĩ mô

Nguồn: Cục Thống kê, báo cáo kinh tế xã hội quý III và 9 tháng 2026, công bố 03/10/2026.

Các chỉ tiêu đã đối chiếu:
- GDP 9 tháng: tăng 9,01% so cùng kỳ.
- CPI bình quân 9 tháng: tăng 4,52% so cùng kỳ.
- IIP 9 tháng: tăng 12,3% so cùng kỳ.
- FDI thực hiện 9 tháng: 21,07 tỷ USD.
- Tín dụng đến 28/09/2026: tăng 10,89% so cuối 2025.

Dữ liệu vĩ mô dùng chung cho các mã; cập nhật theo kỳ công bố. Cấu hình nguồn hiện theo kỳ cụ thể, chưa phải cơ chế tự tìm mọi bản công bố mới nhất.

### 4.5. Tin tức và bằng chứng gốc

Tin được lưu kèm mã, URL, ngày công bố, tóm tắt và trạng thái đọc/đối soát. Phân biệt tiêu đề, nội dung đã trích và nội dung đã kiểm tra.

Bản VCB sử dụng bài IR ngày 17/08/2026 về quý II và 6 tháng đầu năm. CASA khoảng 32%, NPL 0,98% là số ngân hàng công bố; tăng tín dụng khoảng 13% là mục tiêu năm, không phải kết quả đã đạt.

Các chỉ tiêu tài chính chính được đối chiếu BCTN VCB 2025, bản sao tài liệu công bố trên FinancialReports. Vốn chủ sở hữu ở trang in 151/trang tệp 77; LNST ở trang in 153/trang tệp 78. Bản nộp lưu số liệu/tóm tắt/URL, không đóng gói nguyên kho PDF hay toàn bộ bài báo.

## 5. Kiến trúc và lưu trữ

Luồng tổng quát:

Nguồn dữ liệu
  → CMD nạp thủ công
  → dữ liệu gốc và kiểm tra
  → chuẩn hóa Parquet/JSON
  → tính chỉ tiêu và đánh giá
  → giao diện / báo cáo PDF.

Công nghệ chính:
- Python và Pandas/PyArrow: xử lý, chuẩn hóa và lưu dữ liệu.
- FastAPI: cung cấp dữ liệu cho ứng dụng web chạy local.
- HTML/CSS/JavaScript: giao diện.
- Matplotlib: biểu đồ.
- ReportLab: xuất PDF tiếng Việt.
- Pytest: kiểm thử.

Tổ chức dữ liệu:
- data/local: dữ liệu người dùng đang nạp/cập nhật; không đưa vào Git.
- data/submission: bộ thực tế cố định của bản VCB; đi kèm source.
- data/sample: bộ demo riêng để thử chức năng.
- prices.parquet: giá và khối lượng đã chuẩn hóa.
- financials.parquet: khoản mục BCTC năm.
- financial_quarterly.parquet: BCTC quý nếu đã nạp.
- companies.json: tên, ngành, nhóm đối chiếu.
- macro.json, news.json: vĩ mô và tin tức.
- manifest.json: nguồn, mốc dữ liệu và SHA-256 của tệp.
- research_reviews.json: đối soát và nhận định gắn với dấu kiểm tra đầu vào.
- Các tệp tiến độ: khoảng lịch sử đã xử lý, lỗi và phần cần chạy tiếp.

Dự án dùng kho dữ liệu dạng tệp local, không triển khai hệ quản trị cơ sở dữ liệu SQL. Parquet phù hợp với bảng số liệu; JSON phù hợp với cấu hình, nguồn và trạng thái. Ghi tệp tạm rồi thay thế và khóa ghi giúp giảm nguy cơ hỏng dữ liệu khi các tiến trình cùng sử dụng kho.

SHA-256 giúp phát hiện tệp thay đổi; nó không chứng minh dữ liệu của nhà cung cấp là đúng. Tính đúng cần kiểm tra đơn vị, công thức và đối chiếu nguồn độc lập/tài liệu công bố.

## 6. Phương pháp phân tích

### Giá và giao dịch
- MA20/MA50: trung bình giá đóng cửa khi đủ số phiên.
- Lợi suất 20 phiên: giá cuối / giá cách 20 phiên - 1.
- Biến động năm hóa: độ lệch chuẩn lợi suất ngày nhân căn 252.
- Sụt giảm lớn nhất: mức giảm so với đỉnh tích lũy trong khoảng đã lưu.
- Hiệu suất tương đối: so cổ phiếu với VNINDEX trên ngày giao dịch chung.
- Lợi suất chưa bao gồm cổ tức tiền mặt; lịch sử điều chỉnh cần xác minh.

### Tài chính
- ROE = LNST / VCSH bình quân đầu–cuối năm.
- ROA = LNST / tổng tài sản bình quân đầu–cuối năm.
- Tăng trưởng lợi nhuận và thu nhập được so cùng kỳ năm trước.
- CIR ngân hàng = trị tuyệt đối chi phí hoạt động / tổng thu nhập hoạt động.
- Thiếu đầu kỳ thì không tự tạo ROE/ROA.
- Không áp dụng hệ số thanh toán hiện hành của doanh nghiệp thường cho ngân hàng.
- Phân biệt LNST hợp nhất với lợi nhuận của cổ đông ngân hàng/công ty mẹ.

### Vĩ mô → ngành → cổ phiếu
1. Ghi nhận số liệu vĩ mô và kỳ tham chiếu.
2. Giải thích kênh tác động tới ngành: nhu cầu vốn, chi phí vốn, chất lượng tài sản.
3. Đối chiếu phản ứng của doanh nghiệp bằng lợi nhuận, vốn, hiệu quả và tin công bố.
4. Kết hợp diễn biến giá, nêu điều kiện thuận lợi và điều kiện làm suy yếu luận điểm.
5. Chỉ đưa định giá định lượng khi có giả định cùng cơ sở, có nguồn.

Hệ thống dùng công thức và quy tắc xác định, không cần API LLM để chạy phân tích. Bản VCB có thêm nhận định được rà soát thủ công và gắn với đúng đầu vào. Tự động tính/xuất báo cáo không có nghĩa mọi nhận định đã được máy tự kiểm chứng.

## 7. Kết quả thực nghiệm VCB để đưa vào báo cáo

| Chỉ tiêu | Kết quả | Kỳ / cách kiểm tra |
|---|---|---|
| Giá đóng cửa | 56.600 đồng/cổ phiếu | 08/10/2026; KBS khớp nguồn Investing ở phiên cuối |
| LNST hợp nhất | 35.197,940 tỷ đồng | Năm 2025; khớp BCTN |
| VCSH cuối kỳ | 224.558,726 tỷ đồng | 31/12/2025; khớp BCTN |
| VCSH đầu kỳ | 196.209,168 tỷ đồng | 31/12/2024; số so sánh trong BCTN 2025 |
| ROE | 16,7303% | 35.197,940 / [(196.209,168 + 224.558,726)/2] |
| Tăng trưởng LNST | 3,97% | Tự tính từ 2024–2025 |
| Lợi suất 20 phiên | -4,07% | Tự tính từ chuỗi giá đã lưu |
| PDF | 9 trang | Có biểu đồ, bảng, nguồn và phụ lục đối soát |

Diễn giải có thể dùng trong phần kết quả:

“VCB duy trì tăng trưởng lợi nhuận trong năm 2025, nhưng vốn chủ sở hữu tăng nhanh hơn lợi nhuận nên ROE bình quân giảm. CIR tăng cho thấy chi phí hoạt động tăng nhanh hơn thu nhập. Bối cảnh kinh tế và nhu cầu tín dụng hỗ trợ cơ hội kinh doanh, song lợi ích thực tế còn phụ thuộc NIM, chất lượng tài sản và chi phí dự phòng. Giá ngắn hạn chưa đồng thuận với giả thuyết phục hồi hiệu quả. Vì vậy, hệ thống đưa ra trạng thái theo dõi có điều kiện, chưa xác định giá mục tiêu khi thiếu giả định định giá có nguồn.”

Phạm vi đối soát: giá phiên cuối; chỉ tiêu trọng yếu VCB 2024–2025; 5 chỉ tiêu NSO và bài IR đã nêu. Chuỗi năm 2022–2023, toàn bộ điều chỉnh giá và PDF BCTC của peers chưa được đối soát trong lần này. ROE 2024 và so sánh peers sử dụng dữ liệu lưu từ nguồn tham khảo, không có cùng mức xác nhận như các số được liệt kê trong bảng đối soát.

## 8. Kiểm thử và tính tái lập

Kết quả đã thực hiện:
- 54 kiểm thử đạt ở lần kiểm tra cuối của bản VCB.
- Kiểm tra dữ liệu giá không hợp lệ, ghi trùng, chạy tiếp sau lỗi và hạn mức.
- Kiểm tra công thức, dữ liệu thiếu, API và bảo vệ dữ liệu cố định.
- Kiểm tra nhận định rà soát bị vô hiệu khi đầu vào thay đổi.
- Kiểm tra giao diện bảy phần và chuyển giữa local/submission.
- Kiểm tra PDF 9 trang, bố cục và phạm vi văn bản trong trang.
- Sao chép source và bộ submission sang thư mục riêng, chặn kết nối mạng, tạo lại PDF giống hệt từng byte.

Giới hạn kiểm thử:
- Đây là phép thử thư mục độc lập trên môi trường hiện có, chưa phải thử trên một máy vật lý mới.
- Chưa đo hoàn thành quét toàn thị trường.
- Không dùng số kiểm thử phần mềm để thay cho kiểm toán dữ liệu tài chính.

Máy khác:
1. Cài Python 3.11.
2. Tải/clone dự án, giữ assets/fonts và data/submission.
3. Chạy Cai-Dat.cmd một lần; bước cài thư viện cần Internet.
4. Chạy Mo-Ung-Dung.cmd; chọn bản VCB đã đối soát.
5. Xuất PDF trên giao diện hoặc chạy 07-Xuat-Bao-Cao-VCB.cmd.

Sau khi cài, phân tích và xuất bản cố định không cần API key, quét lại hoặc Internet. Bộ thư viện được khóa phiên bản. Chi tiết ở docs/CHAY_BAN_NOP.md.

## 9. Điểm đóng góp và hạn chế

Đóng góp:
- Ghép dữ liệu nhiều nguồn vào quy trình nghiên cứu đầu cuối.
- Tách nạp dữ liệu với đọc/phân tích để giảm số lần gọi nguồn.
- Dùng Parquet/JSON local, dễ mang theo và tái lập.
- Có nguồn, đơn vị, kỳ, trạng thái đối soát và dữ liệu thiếu.
- Có báo cáo tự động và nhận định đã rà soát gắn với phiên bản dữ liệu.
- Cấu trúc đơn giản, phù hợp quy mô bài tập.

Hạn chế:
- Quét lịch sử toàn thị trường còn chậm; cách ghi tệp tổng cần tối ưu.
- BCTC năm nguồn tham khảo không phủ hết thị trường và không tự cập nhật theo mọi kỳ mới.
- Chưa có BCTC quý chuẩn hóa trong bản nộp.
- Phân ngành/nhận định chuyên biệt chưa đầy đủ mọi ngành.
- Tin đã kiểm tra cho VCB còn ít, không bảo đảm bao phủ tất cả sự kiện.
- Chưa định giá hoặc đưa khuyến nghị mua/bán dựa trên mô hình được kiểm định.

## 10. Kịch bản giả định: đã quét đủ và hoàn thiện dự án

TRẠNG THÁI: MÔ HÌNH MỤC TIÊU. Mục này mô tả dự án sau khi hoàn thành các điều kiện bên dưới; không dùng làm phần “kết quả thực nghiệm hiện tại”.

Giả định:
- Danh mục được cập nhật và mọi mã trong phạm vi nghiên cứu có dữ liệu hoặc lý do thiếu rõ ràng.
- Lịch sử giá đủ khoảng yêu cầu, đã xác minh đơn vị/cơ sở điều chỉnh.
- BCTC năm và quý có nguồn, kỳ và phạm vi hợp nhất thống nhất.
- Ngành và nhóm so sánh đã được cấu hình đúng cho mã chọn.
- Vĩ mô và tin có mốc công bố, nội dung đã kiểm tra.
- Không còn lỗi trọng yếu làm ảnh hưởng kết luận/PDF trong các trường hợp nghiệm thu.

Quy trình vận hành mục tiêu:
1. Lấy danh mục toàn thị trường.
2. Nạp BCTC năm theo lô Parquet và lưu phiên bản nguồn.
3. Nạp lịch sử giá ban đầu; tái sử dụng dữ liệu đã có.
4. Các ngày sau, người dùng chạy cập nhật sau phiên để lấy phần thiếu.
5. Nạp BCTC theo kỳ công bố; vĩ mô theo lịch phát hành; tin theo mã cần nghiên cứu.
6. Lưu giá theo từng mã hoặc ghi gộp theo lô để giảm việc ghi lại toàn kho; lựa chọn cụ thể cần đo và kiểm thử.
7. Kiểm tra độ phủ và chất lượng trước khi đưa mã vào trạng thái “đủ dữ liệu phân tích”.
8. Người dùng chọn mã, hệ thống tính toán và tạo báo cáo từ dữ liệu local.
9. Chốt phiên bản báo cáo với dữ liệu/nguồn tương ứng để chạy lại.

Đoạn mô tả mục tiêu có thể đưa vào phần thiết kế:

“Trong kịch bản hoàn thiện, hệ thống sử dụng dữ liệu được lưu local và cập nhật tăng dần. Dữ liệu BCTC lịch sử được tải theo lô và tái sử dụng; dữ liệu giá được bổ sung sau phiên thay vì tải lại toàn bộ. Mỗi cổ phiếu được kiểm tra độ đầy đủ, đơn vị, kỳ báo cáo và hồ sơ ngành trước khi phân tích. Báo cáo được xây dựng theo chuỗi vĩ mô, ngành và doanh nghiệp, có luận điểm, rủi ro, điều kiện theo dõi và dấu vết nguồn. Người dùng có thể tự động xuất PDF và tái lập báo cáo từ bộ dữ liệu đã chốt.”

Các cải tiến như lưu giá từng mã, mở rộng ICB, đối soát BCTC quý và bao phủ mọi mã là phần cần triển khai/nghiệm thu tiếp; chúng chưa được mặc định coi là đã có trong source hiện tại.

## 11. Điều kiện nghiệm thu để đáp ứng đầy đủ phạm vi mở rộng

| Nhóm | Điều kiện kiểm chứng |
|---|---|
| Độ phủ danh mục | Báo cáo tổng mã theo sàn; mỗi mã có trạng thái đủ/thiếu/không được nguồn hỗ trợ |
| Giá | Có ngày đầu/cuối, số phiên, cơ sở giá, kiểm tra trùng và OHLC; phân biệt mã mới niêm yết/ngừng giao dịch với lỗi tải |
| Cập nhật | Chạy lại không sinh bản ghi trùng; không tải lại toàn lịch sử khi chỉ thiếu phiên mới |
| BCTC | Xác minh đơn vị và hợp nhất/riêng lẻ; tách riêng quý với lũy kế; không cộng sai TTM |
| Ngành | Mã chưa có ngành không nhận diễn giải đặc thù ngành sai; peers so cùng kỳ và cùng phương pháp |
| Tin và vĩ mô | Có URL, ngày công bố/kỳ, trạng thái rà soát; không dùng bài cũ như dữ liệu mới |
| Nhận định | Nêu bằng chứng, điều kiện và rủi ro; dữ liệu thiếu không tạo kết luận chắc chắn |
| PDF | Khớp dữ liệu trên giao diện, có nguồn và giới hạn; không lỗi font, tràn bảng hoặc thiếu trang |
| Tái lập | Máy khác mở được bộ cố định, kiểm tra manifest và xuất báo cáo mà không nạp online |
| Hiệu năng | Đo thời gian gọi nguồn/ghi tệp; thử ít mã trước khi chạy rộng; lưu log thực tế thay cho ước lượng |
| Bảo mật cấu hình | Không đưa API key, .env hoặc thư mục môi trường lên GitHub |

Việc hỗ trợ mã bất kỳ được nghiệm thu bằng lựa chọn nhiều mã thuộc các ngành/sàn khác nhau và tình huống thiếu dữ liệu, không chỉ bằng số mã xuất hiện trong ô chọn.

## 12. Dàn ý báo cáo thuyết minh đề xuất

1. Giới thiệu bài toán và yêu cầu đề.
2. Phạm vi nghiên cứu, mục tiêu và tình huống VCB.
3. Tổng quan repo tham khảo và nội dung thực sự được kế thừa.
4. Nguồn dữ liệu, phương pháp thu thập và chuẩn hóa.
5. Thiết kế lưu trữ, kiến trúc và luồng vận hành.
6. Công thức và phương pháp vĩ mô → ngành → cơ hội cổ phiếu.
7. Kết quả thực nghiệm VCB và ảnh giao diện/PDF.
8. Kiểm thử, độ chính xác, tính tái lập.
9. Ma trận đối chiếu yêu cầu.
10. Hạn chế và kịch bản hoàn thiện.
11. Kết luận.
12. Tài liệu tham khảo.

Ảnh/bằng chứng nên chọn:
- Giao diện bản VCB, ghi rõ bộ dữ liệu thực tế cố định.
- Bảng giá/tài chính và chuỗi lập luận vĩ mô → ngành → VCB.
- Trang đối soát ROE, LNST, VCSH.
- Một trang PDF hoàn chỉnh và bảng kết quả kiểm thử.
- Sơ đồ luồng nguồn → kho local → phân tích → PDF.

Không cần đưa toàn bộ source hoặc mọi trang dữ liệu vào báo cáo thuyết minh.

## 13. Tài liệu tham khảo và vị trí sản phẩm

Nguồn:
1. Đề giữa kỳ 261BFF401102_Dethigiuaky.pdf — yêu cầu chức năng và tiêu chí đánh giá.
2. Repo vn-annual-report-miner:
   https://github.com/Tumiqa/vn-annual-report-miner
   Commit: f8cad8d7d4276cd22aee20113fe3214230daf919.
   Giấy phép MIT của code; nguồn dữ liệu cần được ghi riêng.
3. Mẫu VCB_report (1).pdf của MiQuant — tham khảo bố cục/trình bày, không lấy nguyên kết luận hoặc giả định định giá.
4. Giá VCB đối chiếu phiên 08/10/2026:
   https://vn.investing.com/equities/joint-stock-commercial-bank-historical-data
5. BCTN VCB 2025, bản sao tài liệu công bố:
   https://cdn.financialreports.eu/financialreports/media/filings/67042/2026/RNS/67042_rns_2026-04-17_ec71ebc1-1e53-44c8-aa94-45a7b9d87c07.pdf
6. Cục Thống kê, kinh tế xã hội 9 tháng 2026:
   https://www.nso.gov.vn/bai-top/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/
7. Tin IR Vietcombank 17/08/2026:
   https://vietcombank.com.vn/vi-VN/Trang-thong-tin-dien-tu/Articles/2026/08/17/20260812_TSC_CLTKHDQT_CongboKQKDquyII

Trong thư mục dự án:
- output/pdf/VCB_Bao_cao_2026-10-09.pdf: báo cáo phân tích cổ phiếu.
- output/pdf/VCB_Bao_cao_2026-10-09.json: đầu vào/kết quả để truy vết bản PDF.
- data/submission: bộ dữ liệu cố định.
- docs/CHAY_BAN_NOP.md: hướng dẫn chạy máy khác.
- docs/MANUAL_RUN.md: hướng dẫn nạp dữ liệu sau.
- vnresearch: xử lý dữ liệu, tính toán, API và PDF.
- tests: kiểm thử.
- requirements.lock.txt: phiên bản thư viện.
