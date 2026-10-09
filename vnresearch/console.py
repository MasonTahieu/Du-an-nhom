"""Keep redirected Python logs Unicode-safe on Windows.

This module configures only standard output/error; it does not alter financial
records, downloaded data, text extraction, or the system-wide Windows code page.
"""
import sys


def configure_utf8_stdio():
    """Use UTF-8 for application log streams when a launcher did not set it.

    For example, redirected stdout on Windows can default to cp1252 and crash
    when reporting a Vietnamese progress message.  On captured/non-text streams,
    leave the stream unchanged rather than failing application startup.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError, TypeError):
            pass
