"""Small explicit article/release/PDF extraction. Documents are evidence, never instructions."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from .storage import ROOT, atomic_json, symbol
from .collectors import get_http, utc
from .locking import process_lock

TOPICS = {
    "kinh doanh": ["doanh thu","lợi nhuận","kết quả kinh doanh"],
    "tín dụng": ["tín dụng","nợ xấu","huy động"],
    "mở rộng thị trường": ["xuất khẩu","thị trường","khách hàng"],
    "đầu tư": ["dự án","công suất","đầu tư","nhà máy"],
    "cổ đông": ["cổ tức","cổ đông","chia tách"],
}
def topics(text):
    low = text.lower()
    return [k for k,words in TOPICS.items() if any(w in low for w in words)]

def extract_html(html, url):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    title = heading.get_text(" ",strip=True) if heading else soup.title.get_text(" ",strip=True) if soup.title else url
    text = ""
    extractor = "trafilatura"
    try:
        import trafilatura
        text = trafilatura.extract(html, url=url, include_comments=False, include_tables=True) or ""
    except ImportError:
        pass
    if len(text) < 120:
        extractor = "html_article"
        for node in soup(["script","style","nav","header","footer"]):
            node.decompose()
        article = soup.find("article") or soup.find("main") or soup.body or soup
        text = article.get_text("\n",strip=True)
    if len(text) < 120:
        raise ValueError("Không trích được nội dung bài; giữ URL để đối chiếu thủ công.")
    return {"title": title, "text": text, "extractor": extractor}

def collect_articles(store, records, *, refresh=False):
    out, failed, reused = [], [], 0
    old = {n["url"]:n for n in store.read_json("news.json",[])}
    for spec in records:
        url = spec["url"]
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            raise ValueError("Bài viết cần URL https hợp lệ.")
        ticker = symbol(spec["symbol"])
        cached = old.get(url)
        if cached and cached.get("body_file") and (store.path/cached["body_file"]).is_file() and not refresh:
            reused += 1
            continue
        try:
            response = get_http(url)
            payload = extract_html(response.text,url)
            key = hashlib.sha256(url.encode()).hexdigest()[:20]
            path = f"raw/news/{ticker}_{key}.json"
            body = {"symbol":ticker,"url":url,"published_at":spec["published_at"],"retrieved_at":utc(),**payload}
            store.write_json(path,body,{"source":"Publisher article", "source_url":url})
            tags = topics(payload["text"])
            news = {"symbol":ticker,"url":url,"title":payload["title"],
                    "published_at":spec["published_at"],"retrieved_at":body["retrieved_at"],
                    "content_status":"extracted_unreviewed","body_file":path,"topics":tags,
                    "summary":"Đã trích nội dung bài từ nguồn. Chủ đề phát hiện: "+(", ".join(tags) or "chưa phân loại")+
                              ". Cần đọc nguồn để đánh giá tác động; chưa dùng con số trong bài thay BCTC."}
            old[url] = news
            out.append(news)
        except Exception as exc:
            failed.append({"url":url,"error":str(exc)[:300]})
    if old:
        store.write_json("news.json",sorted(old.values(),key=lambda n:n["published_at"],reverse=True),
                         {"source":"KBS metadata và bài từ IR/báo chí được trích nội dung", "source_url":"see row url",
                          "as_of":max(n["published_at"][:10] for n in old.values()),
                          "note":"Nhận diện chủ đề bằng từ khóa; không tự suy ra dự báo hoặc khuyến nghị."})
    return {"loaded":len(out),"reused":reused,"failed":failed}

def collect_macro(store, spec):
    """Parser for a configured NSO nine-month release, fail closed if layout/wording changes."""
    url, year, period = spec["url"], int(spec["year"]), spec["period"]
    if urlparse(url).hostname not in {"www.nso.gov.vn","nso.gov.vn"}:
        raise ValueError("Nguồn vĩ mô tự động hiện hỗ trợ báo cáo NSO chính thức.")
    response = get_http(url)
    from bs4 import BeautifulSoup
    text = BeautifulSoup(response.text,"html.parser").get_text(" ",strip=True)
    text = re.sub(r"\s+"," ",text)
    rules = [
        ("gdp_yoy","GDP thực tăng trưởng","%", "so với cùng kỳ năm trước",
         rf"GDP chín tháng năm {year} ước tăng ([\d.,]+)%"),
        ("cpi_average_yoy","CPI bình quân","%", "bình quân so với cùng kỳ năm trước",
         rf"Bình quân chín tháng năm {year}, CPI tăng ([\d.,]+)%"),
        ("iip_yoy","Sản xuất công nghiệp (IIP)","%", "so với cùng kỳ năm trước",
         rf"Tính chung chín tháng năm {year}, IIP ước tăng ([\d.,]+)%"),
        ("fdi_disbursed","FDI thực hiện","tỷ USD", "giá trị giải ngân",
         rf"Vốn đầu tư trực tiếp nước ngoài thực hiện tại Việt Nam chín tháng năm {year} ước đạt ([\d.,]+) tỷ USD"),
    ]
    rows = []
    for indicator,label,unit,basis,pattern in rules:
        match = re.search(pattern,text,re.IGNORECASE)
        if not match:
            raise ValueError(f"Không nhận diện được {indicator}; cần đối chiếu nguồn và cập nhật bộ đọc hoặc nhập CSV.")
        rows.append({"indicator":indicator,"label":label,"value":float(match[1].replace(".","").replace(",",".")),
                     "unit":unit,"period":period,"basis":basis,"published_at":spec["published_at"],
                     "source_url":url,"retrieved_at":utc(),"source_evidence":match[0],
                     "content_status":"parsed_official_release"})
    # Capture the explicitly dated credit measure; do not label it as the full nine months.
    credit = re.search(rf"Tính đến thời điểm (\d{{1,2}}/\d{{1,2}}/{year}).{{0,250}}?tăng trưởng tín dụng của nền kinh tế đạt ([\d.,]+)%",text)
    if credit:
        rows.append({"indicator":"credit_ytd","label":"Tăng trưởng tín dụng","value":float(credit[2].replace(",",".")),
                     "unit":"%","period":credit[1],"basis":f"so với cuối năm {year-1}",
                     "published_at":spec["published_at"],"source_url":url,"retrieved_at":utc(),
                     "source_evidence":credit[0],"content_status":"parsed_official_release"})
    store.write_json(f"raw/macro/nso_{period}.json",{"url":url,"retrieved_at":utc(),"text":text},
                     {"source":"NSO official release","source_url":url})
    old = store.read_json("macro.json",[])
    keyed = {(r["indicator"],r["period"],r["basis"]):r for r in old+rows}
    store.write_json("macro.json",list(keyed.values()),{"source":"NSO official release parsed", "source_url":url,
                     "as_of":spec["published_at"],"units":"see row unit"})
    return {"rows":len(rows),"period":period,"url":url}

def collect_fx(store):
    url = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
    r = get_http(url)
    root = ET.fromstring(r.content)
    updated = root.findtext("DateTime") or ""
    records = []
    for element in root.findall("Exrate"):
        if element.attrib.get("CurrencyCode") != "USD": continue
        records.append({"currency":"USD", "name":element.attrib.get("CurrencyName"),
                        **{k.lower():float(element.attrib[k].replace(",","")) for k in ["Buy","Transfer","Sell"]},
                        "unit":"VND/USD","source_time":updated,"retrieved_at":utc(),"source_url":url})
    if not records: raise ValueError("Nguồn XML không có USD.")
    store.write_json("exchange_rates.json",records,{"source":"Vietcombank published exchange rates","source_url":url,
                     "as_of":updated,"note":"Tỷ giá niêm yết mua/CK/bán; không phải tỷ giá trung tâm SBV."})
    return records

def extract_pdf(store, path, ticker, source_url, *, keywords=None, max_pages=80):
    if not 1 <= max_pages <= 300: raise ValueError("max_pages cần 1–300.")
    if not source_url.startswith("https://"): raise ValueError("Cần URL bản báo cáo gốc để đối chiếu.")
    from pypdf import PdfReader
    path, ticker = Path(path), symbol(ticker)
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    reader = PdfReader(path)
    keys = keywords or ["rủi ro","doanh thu","lợi nhuận","nợ xấu","dòng tiền"]
    pages, hits = [], []
    for i,page in enumerate(reader.pages[:max_pages]):
        text = page.extract_text() or ""
        pages.append({"page":i+1,"text":text})
        low = text.lower()
        for key in keys:
            at = low.find(key.lower())
            if at >= 0:
                hits.append({"page":i+1,"keyword":key,"excerpt":text[max(0,at-80):at+240]})
    relative = f"raw/documents/{ticker}_{digest[:16]}.pdf"
    target = store.path/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_bytes(content)
    temporary.replace(target)
    result = {"symbol":ticker,"source_url":source_url,"sha256":digest,"pdf_file":relative,
              "pages_total":len(reader.pages),"pages_read":len(pages),"pages_with_text":sum(bool(p["text"].strip()) for p in pages),
              "hits":hits[:100],"pages":pages,"retrieved_at":utc(),
              "note":"Trích văn bản và tìm từ khóa; không tự biến bảng PDF thành số liệu BCTC. PDF scan cần OCR thủ công."}
    name = relative.replace(".pdf",".json")
    store.write_json(name,result,{"source":"PDF text evidence","source_url":source_url,"symbol":ticker})
    index = store.read_json("documents.json",[])
    index = [d for d in index if d["sha256"] != digest]
    index.append({k:result[k] for k in ["symbol","source_url","sha256","pdf_file","pages_total","pages_read","pages_with_text","retrieved_at","note"]}|{"text_file":name,"keywords":keys,"hits_count":len(hits)})
    store.write_json("documents.json",index,{"source":"Selected report PDF evidence","source_url":"see document source_url"})
    return {k:v for k,v in result.items() if k not in {"pages","hits"}}|{"hits_count":len(hits)}
