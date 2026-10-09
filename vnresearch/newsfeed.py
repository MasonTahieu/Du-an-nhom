"""On-demand CafeF RSS *metadata* collection and conservative rule-based tagging.

Never contacts a site while rendering analyses or importing the module.  The
source's title, small excerpt, timestamp and link are attributed, not treated
as verified facts.  No articles are scraped and no LLM is used.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import xml.etree.ElementTree as ET

from .storage import ROOT, Store, symbol

ALLOWED_HOSTS = {"cafef.vn", "www.cafef.vn"}
SECTOR_TERMS = {
    "bank": ("ngan hang", "tin dung", "no xau", "huy dong von", "lai suat", "nim", "casa", "cho vay", "tai chinh ngan hang"),
    "technology": ("cong nghe", "phan mem", "chuyen doi so", "ban dan", "tri tue nhan tao", "ai", "cloud", "data center", "dien toan dam may"),
    "steel": ("thep", "quang sat", "than luyen coc", "ton ma", "lo cao", "dung quat"),
    "real_estate": ("bat dong san", "nha o", "khu cong nghiep", "du an nha o", "dat nen"),
    "retail": ("ban le", "sieu thi", "chuoi cua hang", "tieu dung"),
    "energy": ("dien luc", "dien gio", "dien mat troi", "thuy dien", "nhiet dien"),
    "oil_gas": ("dau khi", "gia dau", "khai thac dau", "lng"),
    "securities": ("cong ty chung khoan", "moi gioi chung khoan", "cho vay margin", "tu doanh", "chung khoan"),
}
MACRO_TERMS = ("gdp", "cpi", "lam phat", "tang truong kinh te", "ngan sach nha nuoc", "dau tu cong", "fdi", "xuat nhap khau", "ty gia", "chinh sach tien te", "lai suat dieu hanh")
TOPIC_TERMS = {
    "business_results": ("ket qua kinh doanh", "doanh thu", "loi nhuan", "bao cao tai chinh"),
    "dividend": ("co tuc", "chia co phieu", "chot quyen"),
    "rates": ("lai suat", "tien te"),
    "credit": ("tin dung", "no xau", "cho vay"),
    "investment": ("dau tu cong", "du an", "nha may", "cong suat"),
    "exports": ("xuat khau", "don hang", "thuong mai"),
    "macro_indicators": ("gdp", "cpi", "iip", "fdi", "lam phat"),
}
# Only established, unambiguous company aliases. Unknown companies require exact
# stock-code context or manually configured, verified aliases; never guess from a
# three-letter word alone in arbitrary running text.
KNOWN_ALIASES = {
    "VCB": ("vietcombank", "ngan hang ngoai thuong viet nam"),
    "CTG": ("vietinbank", "ngan hang cong thuong viet nam"),
    "BID": ("bidv", "ngan hang dau tu va phat trien viet nam"),
    "FPT": ("tap doan fpt", "cong ty fpt", "fpt"),
    "HPG": ("hoa phat", "tap doan hoa phat"),
    "VND": ("vndirect", "vn direct"),
    "SSI": ("chung khoan ssi", "ssi securities"),
    "NKG": ("thep nam kim", "nam kim"),
    "ELC": ("elcom",),
    "MBB": ("mb bank", "mbbank", "ngan hang quan doi"),
    "TCB": ("techcombank",),
    "ACB": ("ngan hang a chau", "acb bank"),
    "MWG": ("the gioi di dong", "bach hoa xanh"),
    "VHM": ("vinhomes",),
    "VIC": ("vingroup",),
}


class _Plain(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments = []
    def handle_data(self, value):
        self.fragments.append(value)


def plain_html(value: str) -> str:
    parser = _Plain()
    parser.feed(str(value or "")[:20000])
    return re.sub(r"\s+", " ", unescape(" ".join(parser.fragments))).strip()


def fold(s):
    s = unicodedata.normalize("NFKD", str(s).lower().replace("đ", "d"))
    return "".join(c for c in s if not unicodedata.combining(c))


def mentions(text, term):
    # Unicode word boundaries avoid classifying "AI" inside "mai" or "FPT" in other strings.
    return bool(re.search(r"(?<![\w])" + re.escape(fold(term)) + r"(?![\w])", text))


def safe_url(url):
    p = urlsplit(unescape(str(url or "").strip()))
    if p.scheme != "https" or p.hostname not in ALLOWED_HOSTS or p.username or p.password or p.port not in (None, 443):
        raise ValueError("Nguồn RSS/bài phải thuộc https://cafef.vn")
    if not p.path or p.path == "/":
        raise ValueError("Đường dẫn bài RSS rỗng")
    params = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit(("https", "cafef.vn", p.path, urlencode(params), ""))


def date_from_rss(value):
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try: dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError: return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if dt.year < 2010 or dt > datetime.now(timezone.utc).replace(hour=23,minute=59,second=59):
        return None
    return dt.date().isoformat()


def parse_feed(xml, *, max_items=25):
    """Parse bounded RSS2 / Atom; return publisher metadata only."""
    if isinstance(xml, str): xml = xml.encode("utf-8")
    if len(xml) > 2_000_000:
        raise ValueError("RSS vượt giới hạn 2 MB")
    root = ET.fromstring(xml)  # no DTD/entity resolution in stdlib ElementTree
    rss_items = root.findall("./channel/item")
    atom_items = root.findall("{http://www.w3.org/2005/Atom}entry")
    if not rss_items and not atom_items:
        raise ValueError("RSS không có item/entry; nguồn có thể đã thay đổi định dạng")
    items = []
    for node in (rss_items or atom_items)[:max_items]:
        atom = node in atom_items if atom_items else False
        if atom:
            ns = "{http://www.w3.org/2005/Atom}"
            title = node.findtext(ns + "title")
            desc = node.findtext(ns + "summary") or ""
            stamp = node.findtext(ns + "published") or node.findtext(ns + "updated")
            link = next((x.get("href") for x in node.findall(ns + "link") if x.get("rel", "alternate") == "alternate"), None)
        else:
            title, desc, stamp, link = (node.findtext(tag) for tag in ("title", "description", "pubDate", "link"))
        published = date_from_rss(stamp)
        if not title or not link or not published:
            continue
        try: url = safe_url(link)
        except ValueError: continue
        items.append({"title": plain_html(title)[:240], "summary": plain_html(desc)[:280], "url": url, "published_at": published})
    return items


def sector_for_ticker(ticker, profile=None):
    """Honor user profile first; fall back to curated provisional sector mapping."""
    if isinstance(profile, dict) and profile.get("sector") not in (None, "", "other"):
        return profile["sector"]
    reference = json.loads((ROOT / "config/company_sectors.json").read_text(encoding="utf-8"))
    return reference["symbols"].get(ticker, "other")


def company_aliases(profiles):
    aliases = dict(KNOWN_ALIASES)
    for ticker, p in profiles.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9]{2,4}", ticker): continue
        # Manually verified aliases are opt-in, not inferred from broad company names.
        extra = [v for v in p.get("news_aliases", []) if isinstance(v, str) and len(v.strip()) >= 5]
        if extra: aliases[ticker] = tuple(dict.fromkeys([*aliases.get(ticker, ()), *extra]))
    return aliases


def classify(title, summary, feed, profiles):
    text = fold(title + " " + summary)
    aliases = company_aliases(profiles)
    selected = []
    for ticker, vals in aliases.items():
        if any(mentions(text, alias) for alias in vals):
            selected.append(ticker)
    # Unknown code can only match with an explicit stock-code cue; for 3 letter
    # common words exact free-text matches are too error prone.
    for ticker in profiles:
        if ticker not in selected and re.search(r"\b(?:ma co phieu|co phieu|ma ck)\s*[:\-]?\s*"+re.escape(ticker.lower())+r"\b", text):
            selected.append(ticker)
    sectors = set()
    for sector, terms in SECTOR_TERMS.items():
        if any(mentions(text, term) for term in terms): sectors.add(sector)
    if feed.get("sector"): sectors.add(feed["sector"])
    for ticker in selected:
        key = sector_for_ticker(ticker, profiles.get(ticker))
        if key and key != "other": sectors.add(key)
    topics = [key for key, vals in TOPIC_TERMS.items() if any(mentions(text, term) for term in vals)]
    is_macro = bool(feed.get("category") == "macro" or any(mentions(text, word) for word in MACRO_TERMS))
    category = "company" if selected else "macro" if is_macro else "sector" if sectors else "market"
    return {"symbols": sorted(set(selected)), "sectors": sorted(sectors), "topics": topics, "category": category,
            "classification_status": "auto_unverified"}


def relevant_news(news, ticker, sector):
    """Use both legacy and new news fields; no cross-sector pollution."""
    symbols = news.get("symbols")
    if not isinstance(symbols, list): symbols = [news.get("symbol")] if news.get("symbol") else []
    sectors = news.get("sectors") if isinstance(news.get("sectors"), list) else []
    category = news.get("category")
    if category not in {"company", "sector", "macro", "market"}:
        category = "company" if any(s not in {"MARKET", None} for s in symbols) else "macro"
    company = ticker in symbols
    macro = category == "macro" and not company
    industry = category == "sector" and sector != "other" and sector in sectors and not company
    return company, macro, industry


def merge_records(old, incoming, *, max_stored=750):
    if not isinstance(old, list): raise ValueError("news.json phải là mảng JSON")
    # Keep verified/extracted/manual text and source metadata when an RSS entry overlaps.
    merged = {n["url"]: dict(n) for n in old if isinstance(n, dict) and n.get("url")}
    added, updated = 0, 0
    for n in incoming:
        k = n["url"]
        if k not in merged:
            merged[k] = n
            added += 1
        else:
            prior = merged[k]
            syms = set(prior.get("symbols", []) if isinstance(prior.get("symbols"), list) else [])
            if prior.get("symbol") not in {"MARKET", None}: syms.add(prior["symbol"])
            syms.update(n.get("symbols", []))
            combined = {**prior, "symbols": sorted(syms), "sectors": sorted(set(prior.get("sectors", [])) | set(n.get("sectors", []))),
                        "topics": sorted(set(prior.get("topics", [])) | set(n.get("topics", [])))}
            if prior.get("content_status") in ("metadata_only", "rss_metadata"):
                combined["content_status"] = "rss_metadata"
            if prior.get("category") not in {"company", "sector", "macro"}:
                combined["category"] = n["category"]
            merged[k] = combined
            updated += 1
    result = sorted(merged.values(), key=lambda n: (str(n.get("published_at", "")), str(n.get("url", ""))), reverse=True)
    # Never drop old manually curated or imported records due to RSS retention.
    rss = [r for r in result if r.get("content_status") == "rss_metadata"]
    drop = {r["url"] for r in rss[max_stored:]}
    return [r for r in result if r["url"] not in drop], added, updated


def collect_rss_feeds(store: Store, *, fetch=None, max_per_feed=None):
    """Run only on user action, store RSS metadata and provenance in local."""
    if store.mode != "local": raise ValueError("RSS chỉ lưu ở data/local")
    settings = json.loads((ROOT / "config/news_feeds.json").read_text(encoding="utf-8"))
    cap = min(50, max(1, max_per_feed or settings["max_per_feed"]))
    if fetch is None:
        import requests
        session = requests.Session()
        session.headers.update({"User-Agent": "StockInsight/0.3 (+local, RSS metadata reader)"})
        def fetch(url):
            r = session.get(url, timeout=(5, 20), allow_redirects=False)
            r.raise_for_status()
            return r.content
    profiles = store.read_json("companies.json", {})
    records, failures, source_stats = {}, [], []
    for source in settings["feeds"]:
        try:
            if not source["url"].endswith(".rss") or safe_url(source["url"]) != source["url"]:
                raise ValueError("RSS không thuộc danh sách nguồn HTTPS hợp lệ")
            items = parse_feed(fetch(source["url"]), max_items=cap)
            for row in items:
                row.update(classify(row["title"], row["summary"], source, profiles))
                row.update({"symbol": row["symbols"][0] if row["symbols"] else "MARKET",
                            "source": "CafeF", "feed_id": source["id"], "content_status": "rss_metadata",
                            "retrieved_at": datetime.now(timezone.utc).isoformat(),
                            "attribution": "Theo CafeF"})
                if row["url"] not in records: records[row["url"]] = row
                else:
                    known = records[row["url"]]
                    known["symbols"] = sorted(set(known["symbols"]) | set(row["symbols"]))
                    known["sectors"] = sorted(set(known["sectors"]) | set(row["sectors"]))
                    known["topics"] = sorted(set(known["topics"]) | set(row["topics"]))
            source_stats.append({"feed": source["id"], "items": len(items)})
        except Exception as exc:
            failures.append({"feed": source["id"], "error": str(exc)[:220]})
    old = store.read_json("news.json", [])
    updated, added, matched = merge_records(old, list(records.values()), max_stored=int(settings["max_stored"]))
    if records:
        store.write_json("news.json", updated, {"source": "CafeF RSS (metadata) + tin đã có",
                         "source_url": "https://cafef.vn/index.rss", "as_of": max(r["published_at"] for r in updated),
                         "note": "Theo CafeF; chỉ lưu tiêu đề/trích ngắn/URL, phân loại quy tắc chưa xác minh; không dùng làm chỉ số vĩ mô."})
    return {"status": ("failed" if failures and not source_stats else "partial" if failures else "complete"), "loaded": added, "matched": matched,
            "unique_fetched": len(records), "total_news": len(updated), "sources": source_stats, "failed": failures}
