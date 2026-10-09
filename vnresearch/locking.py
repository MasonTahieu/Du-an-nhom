"""OS releases advisory locks even after Ctrl+C/crash; works on Windows and Unix."""
from contextlib import contextmanager
from pathlib import Path
import os

@contextmanager
def process_lock(path: Path, *, wait=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if wait else msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except OSError as exc:
            raise RuntimeError("Một tiến trình khác đang nạp dữ liệu. Chờ lần chạy đó hoàn tất.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
