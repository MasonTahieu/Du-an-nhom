from pathlib import Path
import uuid

def pytest_configure(config):
    if not config.option.basetemp:
        (Path(__file__).resolve().parents[1] / "tmp").mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(Path(__file__).resolve().parents[1] / "tmp" / ("pytest-" + uuid.uuid4().hex))
