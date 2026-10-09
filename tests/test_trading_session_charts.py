"""Regression tests: charts must not allocate x-axis space to market holidays."""
from datetime import date

import pytest
from vnresearch import report


SESSIONS = [
    {"date": "2026-10-02", "close": 100000, "volume": 10_000_000},  # Friday
    {"date": "2026-10-05", "close": 101000, "volume": 13_000_000},  # Monday
    {"date": "2026-10-06", "close": 103000, "volume": 12_000_000},
]


def capture_chart(monkeypatch, kind, rows):
    original_subplots = report.plt.subplots
    axes = []

    def recorded_subplots(*args, **kwargs):
        fig, ax = original_subplots(*args, **kwargs)
        axes.append(ax)
        return fig, ax

    monkeypatch.setattr(report.plt, "subplots", recorded_subplots)
    rendered = report.chart({"prices": rows}, kind)
    assert rendered is not None
    assert len(axes) == 1
    return axes[0]


@pytest.mark.parametrize("kind", ["price", "volume"])
def test_pdf_market_charts_use_consecutive_trading_sessions(monkeypatch, kind):
    # The passed data is deliberately unordered; Friday and Monday must be adjacent.
    ax = capture_chart(monkeypatch, kind, [SESSIONS[1], SESSIONS[2], SESSIONS[0]])
    assert ax.get_xlim() == pytest.approx((-.5, 2.5))
    assert [t.get_text() for t in ax.get_xticklabels()] == ["02/10/26", "05/10/26", "06/10/26"]

    if kind == "volume":
        bars = ax.patches
        assert len(bars) == 3
        assert [b.get_x() + b.get_width() / 2 for b in bars] == pytest.approx([0, 1, 2])
        assert [b.get_height() for b in bars] == pytest.approx([10, 13, 12])
    else:
        assert list(ax.lines[0].get_xdata()) == [0, 1, 2]
        assert list(ax.lines[0].get_ydata()) == [100, 101, 103]


def test_chart_single_session_keeps_its_original_date(monkeypatch):
    ax = capture_chart(monkeypatch, "volume", [SESSIONS[0]])
    assert [t.get_text() for t in ax.get_xticklabels()] == ["02/10/26"]
    assert ax.patches[0].get_x() + ax.patches[0].get_width() / 2 == pytest.approx(0)
