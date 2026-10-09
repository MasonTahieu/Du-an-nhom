from __future__ import annotations
from datetime import datetime
from pathlib import Path
import tempfile
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .storage import ROOT, Store, atomic_json, symbol
from .analysis import analyze

app = FastAPI(title="VN Equity Research", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
_REPORT_LOCK = threading.Lock()


class ImportBody(BaseModel):
    content: str = Field(max_length=2_000_000)
    kind: str


@app.exception_handler(ValueError)
async def bad_value(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.middleware("http")
async def local_writes(request: Request, call_next):
    if request.method in {"POST", "PUT", "DELETE"}:
        origin = request.headers.get("origin", "")
        from urllib.parse import urlparse
        if origin and urlparse(origin).hostname not in {"127.0.0.1", "localhost", "testserver"}:
            return __import__("fastapi").responses.JSONResponse(status_code=403, content={"detail": "Chỉ cho phép nạp từ giao diện local."})
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/api/status")
def status(mode: str = "sample"):
    store = Store(mode)
    companies = store.read_json("companies.json", {})
    catalogue={r["symbol"]:r for r in store.read_json("universe.json",{}).get("symbols",[])}
    frames = [store.read(name) for name in ("prices.parquet","financials.parquet","financial_quarterly.parquet")]
    data_symbols = set().union(*(set(f.symbol) for f in frames if not f.empty))
    tickers = sorted(set(catalogue) | set(companies) | data_symbols)
    tickers = [t for t in tickers if t != "VNINDEX"]
    checks = store.verify()
    return {"mode": mode, "symbols": [{"symbol": t, "name": companies.get(t, {}).get("name", catalogue.get(t,{}).get("name",t)), "has_data": t in data_symbols, "exchange":catalogue.get(t,{}).get("exchange","")} for t in tickers],
            "manifest": store.manifest(), "verified": bool(checks) and all(c["ok"] for c in checks), "checks": checks}


@app.get("/api/analysis/{ticker}")
def analysis(ticker: str, mode: str = "sample"):
    return analyze(Store(mode), ticker)


@app.get("/api/report/{ticker}")
def report(ticker: str, mode: str = "sample"):
    from .report import build_pdf
    result = analyze(Store(mode), ticker)
    out = ROOT / "reports" / "generated" / (symbol(ticker) + "_" + mode + ".pdf")
    with _REPORT_LOCK:
        build_pdf(result, out)
        atomic_json(out.with_suffix(".json"), result)
    return FileResponse(out, media_type="application/pdf", filename=out.name)


@app.post("/api/seed-local")
def seed():
    from .ingest import seed_local
    seed_local()
    return {"message": "Đã tạo bộ dữ liệu cá nhân từ demo; các file cá nhân hiện có được giữ."}


@app.post("/api/import")
def import_data(body: ImportBody):
    from .ingest import import_financials, import_macro, import_news
    funcs = {"financials": (import_financials, ".csv"), "macro": (import_macro, ".csv"), "news": (import_news, ".json")}
    if body.kind not in funcs:
        raise ValueError("Chọn BCTC CSV, vĩ mô CSV hoặc tin tức JSON.")
    fn, ext = funcs[body.kind]
    folder = ROOT / "tmp" / "imports"
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=ext, encoding="utf-8", dir=folder, delete=False) as f:
        f.write(body.content)
        path = Path(f.name)
    try:
        count = fn(Store("local"), path)
    finally:
        path.unlink(missing_ok=True)
    return {"message": f"Đã nhập {count} dòng vào bộ dữ liệu cá nhân."}


@app.get("/api/template/{name}")
def template(name: str):
    allowed = {"financials.csv", "macro.csv", "news.json", "valuation.json", "company.json", "prices.csv"}
    if name not in allowed:
        raise HTTPException(404)
    return FileResponse(ROOT / "templates" / name, filename=name)


@app.get("/api/readiness")
def data_readiness(mode: str = "local"):
    from .quality import readiness
    return readiness(Store(mode))

# Only an explicit POST initiates network ingestion.
from .ondemand import LoadJobs
_LOAD_JOBS = LoadJobs()

class LoadBody(BaseModel):
    extended: bool = False

@app.post("/api/load/{ticker}", status_code=202)
def load_ticker(ticker: str, body: LoadBody):
    try:
        return _LOAD_JOBS.start(ticker, body.extended)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))

@app.get("/api/load-status")
def load_status():
    return {"job": _LOAD_JOBS.current()}
