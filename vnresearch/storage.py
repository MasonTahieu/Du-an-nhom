"""Local, versioned datasets. Viewing sample data never needs a network."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import uuid
from .locking import process_lock

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
_LOCK = threading.RLock()
_DEPTH = threading.local()


def symbol(value: str) -> str:
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", value):
        raise ValueError("Mã cổ phiếu không hợp lệ.")
    return value


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


class Store:
    def __init__(self, mode="sample", base: Path | str | None = None):
        if mode not in {"sample", "local", "submission"}:
            raise ValueError("Chọn bộ dữ liệu sample, local hoặc submission.")
        self.mode = mode
        self.base = Path(base) if base else ROOT / "data"
        self.path = self.base / mode

    def manifest(self):
        p = self.path / "manifest.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {
            "schema_version": SCHEMA_VERSION, "mode": self.mode, "files": {}
        }

    def read_json(self, name, default=None):
        p = self.path / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    def read(self, name):
        p = self.path / name
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()

    @contextmanager
    def transaction(self):
        # Reentrant within a process; OS lock protects the same dataset across CLI and web.
        with _LOCK:
            depths = getattr(_DEPTH, "datasets", {})
            key = str(self.path.resolve())
            if depths.get(key, 0):
                depths[key] += 1
                try:
                    yield
                finally:
                    depths[key] -= 1
            else:
                _DEPTH.datasets = depths
                with process_lock(self.path / ".write.lock", wait=True):
                    depths[key] = 1
                    try:
                        yield
                    finally:
                        depths[key] = 0

    def _writable(self, bootstrap=False):
        if self.mode in {"sample", "submission"} and not bootstrap:
            raise ValueError("Bộ demo hoặc bản nộp cố định chỉ để đọc. Hãy chọn local để nạp dữ liệu.")

    def _record(self, name, metadata, rows=None):
        manifest = self.manifest()
        p = self.path / name
        manifest["files"][name] = {
            **metadata, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "bytes": p.stat().st_size, "rows": rows,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        atomic_json(self.path / "manifest.json", manifest)

    def write_json(self, name, value, metadata, *, bootstrap=False):
        self._writable(bootstrap)
        with self.transaction():
            atomic_json(self.path / name, value)
            self._record(name, metadata)

    def write(self, name, frame, metadata, *, bootstrap=False):
        self._writable(bootstrap)
        with self.transaction():
            p = self.path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_name(p.name + "." + uuid.uuid4().hex + ".tmp")
            try:
                frame.to_parquet(tmp, index=False)
                os.replace(tmp, p)
            finally:
                tmp.unlink(missing_ok=True)
            self._record(name, metadata, len(frame))

    def merge_prices(self, incoming, metadata, *, bootstrap=False):
        self._writable(bootstrap)
        incoming = validate_prices(incoming)
        with self.transaction():
            old = self.read("prices.parquet")
            if not old.empty:
                # Never combine differently scaled/adjusted feeds silently.
                for ticker in incoming.symbol.unique():
                    a = set(old.loc[old.symbol == ticker, "price_basis"].unique())
                    b = set(incoming.loc[incoming.symbol == ticker, "price_basis"].unique())
                    if a and a != b:
                        raise ValueError(f"{ticker}: khác cơ sở điều chỉnh giá; hãy nhập lại trọn lịch sử.")
            out = pd.concat([old, incoming], ignore_index=True)
            out = out.drop_duplicates(["symbol", "date"], keep="last").sort_values(["symbol", "date"])
            self.write("prices.parquet", out, {**metadata,"as_of":str(out.date.max())}, bootstrap=bootstrap)
        return len(out)

    def verify(self):
        result = []
        for name, meta in self.manifest().get("files", {}).items():
            p = self.path / name
            okay = p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == meta["sha256"]
            result.append({"file": name, "ok": okay})
        return result


def validate_prices(frame):
    required = {"symbol", "date", "open", "high", "low", "close", "volume", "price_basis"}
    if not required <= set(frame.columns) or frame.empty:
        raise ValueError("Giá cần đủ symbol,date,open,high,low,close,volume,price_basis và ít nhất một dòng.")
    d = frame.copy()
    d["symbol"] = d.symbol.map(symbol)
    d["date"] = pd.to_datetime(d.date, errors="raise").dt.strftime("%Y-%m-%d")
    for col in ["open", "high", "low", "close", "volume"]:
        d[col] = pd.to_numeric(d[col], errors="raise")
    if d[list(required)].isna().any().any():
        raise ValueError("Giá thiếu trường bắt buộc.")
    finite = d[["open", "high", "low", "close", "volume"]].apply(lambda col: col.map(math.isfinite)).all(axis=1)
    valid = (
        finite
        &         (d[["open", "high", "low", "close"]] > 0).all(axis=1)
        & (d.volume >= 0)
        & (d.volume.mod(1) == 0)
        & (d.high >= d[["open", "close", "low"]].max(axis=1))
        & (d.low <= d[["open", "close", "high"]].min(axis=1))
    )
    if not valid.all():
        raise ValueError("OHLC hoặc khối lượng không hợp lệ; dữ liệu cũ được giữ lại.")
    if not d.price_basis.isin(["kbs_provider", "raw", "adjusted"]).all():
        raise ValueError("price_basis phải là raw, adjusted hoặc kbs_provider.")
    return d.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")
