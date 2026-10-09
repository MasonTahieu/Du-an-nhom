"""Download the pinned Tumiqa annual dataset once, then reuse it offline.

The upstream data consists of three Parquet statements per HSX/HNX exchange,
not one request per ticker. This module never runs on import or on report views.
Downloaded reference files live outside the editable 'local' dataset and its
integrity manifest: data/reference/tumiqa/<commit>/<statement>/<exchange>.parquet.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import uuid

import pandas as pd

from .locking import process_lock
from .storage import ROOT

STATEMENTS = ("balance_sheet", "income_statement", "cash_flow")
EXCHANGES = ("HSX", "HNX")
BASE_URL = "https://raw.githubusercontent.com/Tumiqa/vn-annual-report-miner"
_REQUIRED = {"ticker", "year", "item_code", "item_name", "value"}


def _validate_request(commit: str, exchange: str, statement: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Cần commit Git cố định gồm 40 ký tự hex.")
    if exchange not in EXCHANGES or statement not in STATEMENTS:
        raise ValueError("Chỉ hỗ trợ BCTC HSX/HNX và ba loại báo cáo chuẩn.")


def _validate_parquet(path: Path) -> None:
    """Check the real Parquet schema instead of trusting a successful HTTP 200."""
    try:
        columns = list(pd.read_parquet(path, columns=sorted(_REQUIRED)).columns)
    except Exception as exc:
        raise ValueError(f"File BCTC tham khảo không phải Parquet hợp lệ: {path.name}") from exc
    if not _REQUIRED.issubset(columns):
        raise ValueError(f"BCTC tham khảo thiếu cột: {_REQUIRED - set(columns)}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _http_download(url: str, timeout: int) -> bytes:
    """Use Python standard library; vnstock/requests are not required for BCTC years."""
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": "StockInsight/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def ensure_file(store, commit: str, exchange: str, statement: str, *,
                getter=None) -> tuple[Path, bool]:
    """Return (verified cached path, downloaded_now).

    A previous version cached the same upstream data under
    data/local/raw/reference/<commit>; that cache is accepted for migration.
    Never replace a verified local copy just because GitHub is unavailable.
    """
    _validate_request(commit, exchange, statement)
    root = store.base / "reference" / "tumiqa" / commit
    relative = Path("src/arminer/data/bctc_data") / statement / f"{exchange}.parquet"
    destination = root / statement / f"{exchange}.parquet"
    digest_path = destination.with_suffix(".sha256")
    with process_lock(root / ".reference-cache.lock", wait=True):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_file():
            actual_digest = _sha256(destination)
            expected_digest = digest_path.read_text(encoding="ascii").strip() if digest_path.exists() else ""
            if not expected_digest or expected_digest == actual_digest:
                try:
                    _validate_parquet(destination)
                except ValueError:
                    pass  # Corrupted cached source: try the original legacy cache or re-download.
                else:
                    if not expected_digest:
                        digest_path.write_text(actual_digest + "\n", encoding="ascii")
                    return destination, False

        # Reuse the verified source files from the previous StockInsight layout.
        legacy = store.path / "raw" / "reference" / commit / relative
        if legacy.exists():
            try:
                _validate_parquet(legacy)
            except ValueError:
                pass
            else:
                temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
                try:
                    shutil.copyfile(legacy, temporary)
                    os.replace(temporary, destination)
                    digest_path.write_text(_sha256(destination) + "\n", encoding="ascii")
                    return destination, False
                finally:
                    temporary.unlink(missing_ok=True)

        if getter is None:
            getter = _http_download
        url = f"{BASE_URL}/{commit}/{relative.as_posix()}"
        response = getter(url, 60)
        content = response if isinstance(response, bytes) else response.content
        # Avoid caching proxy/HTML failures with HTTP 200.
        if not isinstance(content, bytes) or len(content) < 12 or content[:4] != b"PAR1" or content[-4:] != b"PAR1":
            raise ValueError("Nguồn trả về không phải Parquet. Đã giữ cache cũ (nếu có).")
        temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            temporary.write_bytes(content)
            _validate_parquet(temporary)
            digest = _sha256(temporary)
            os.replace(temporary, destination)
            digest_path.write_text(digest + "\n", encoding="ascii")
        finally:
            temporary.unlink(missing_ok=True)
        return destination, True


def prefetch(store, commit: str, exchanges=EXCHANGES, *, progress=print):
    """Optional one-time preparation; online only when a file isn't cached."""
    out = {"commit": commit, "files": [], "downloaded": 0, "reused": 0}
    for exchange in exchanges:
        for statement in STATEMENTS:
            path, downloaded = ensure_file(store, commit, exchange, statement)
            progress(f"{exchange}/{statement}: {'đã tải' if downloaded else 'đã có cache'}")
            out["files"].append({"exchange": exchange, "statement": statement,
                                 "bytes": path.stat().st_size, "downloaded": downloaded})
            out["downloaded" if downloaded else "reused"] += 1
    return out


def main():
    import argparse
    from .storage import Store
    p = argparse.ArgumentParser(description="Chuẩn bị bộ BCTC năm Tumiqa (không quét từng mã).")
    p.add_argument("--exchange", nargs="+", choices=EXCHANGES, default=list(EXCHANGES))
    p.add_argument("--commit", default=None, help="Mặc định dùng reference_commit từ config/watchlist.json")
    a = p.parse_args()
    settings = json.loads((ROOT / "config/watchlist.json").read_text(encoding="utf-8"))
    print(json.dumps(prefetch(Store("local"), a.commit or settings["reference_commit"], a.exchange),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
