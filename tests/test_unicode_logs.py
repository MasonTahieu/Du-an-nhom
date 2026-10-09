"""Regression tests for Windows cp1252 redirected stdout/stderr."""
import io
import sys
from pathlib import Path

import pytest

from vnresearch.console import configure_utf8_stdio


def test_console_supports_vietnamese_when_logs_begin_as_cp1252(monkeypatch):
    stdout_bytes = io.BytesIO()
    stderr_bytes = io.BytesIO()
    stdout = io.TextIOWrapper(stdout_bytes, encoding="cp1252", errors="strict")
    stderr = io.TextIOWrapper(stderr_bytes, encoding="cp1252", errors="strict")

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", stdout)
        patch.setattr(sys, "stderr", stderr)
        with pytest.raises(UnicodeEncodeError):
            print("VND: đã lấy balance_sheet")
        with pytest.raises(UnicodeEncodeError):
            print("Vĩ mô NSO")

        configure_utf8_stdio()
        print("VND: đã lấy balance_sheet")
        print("Vĩ mô NSO", file=sys.stderr)
        stdout.flush()
        stderr.flush()

        assert stdout.encoding.lower().replace("-", "") == "utf8"
        assert stdout_bytes.getvalue().decode("utf-8").splitlines() == ["VND: đã lấy balance_sheet"]
        assert stderr_bytes.getvalue().decode("utf-8").splitlines() == ["Vĩ mô NSO"]


def test_stdio_without_reconfigure_is_left_untouched(monkeypatch):
    class SimpleStream:
        def __init__(self): self.output = ""
        def write(self, text): self.output += text
        def flush(self): pass
    stream = SimpleStream()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", stream)
        patch.setattr(sys, "stderr", None)
        configure_utf8_stdio()
        print("Vĩ mô NSO")
        assert stream.output == "Vĩ mô NSO\n"


def test_windows_launcher_configures_child_encoding():
    project_root = Path(__file__).resolve().parents[1]
    start = (project_root / "scripts" / "Start.ps1").read_text(encoding="utf-8")
    assert "$env:PYTHONUTF8 = '1'" in start
    assert "$env:PYTHONIOENCODING = 'utf-8:backslashreplace'" in start
    assert start.index("$env:PYTHONIOENCODING") < start.index("$taskProcess = Start-Process")
    assert "-RedirectStandardOutput" in start
    assert "-RedirectStandardError" in start


def test_collapsible_panel_included_and_trade_chart_untouched():
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "static" / "index.html").read_text(encoding="utf-8")
    assert '<details class="card load-panel" id="loadPanel">' in html
    assert '<div id="loadProgress"' in html
