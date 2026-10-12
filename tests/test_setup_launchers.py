"""Exercise Windows launchers with a separate project and a real empty venv."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows launchers")


def run_wrapper(wrapper, arguments, cwd):
    return subprocess.run(
        ["cmd.exe", "/d", "/c", "call", str(wrapper), *arguments],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )


def test_wrapper_uses_its_own_venv_and_preserves_arguments_and_exit_code(tmp_path):
    project = tmp_path / "Dự án có khoảng trắng"
    project.mkdir()
    wrapper = project / "_python.cmd"
    shutil.copy2(ROOT / "_python.cmd", wrapper)
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(project / ".venv")],
        check=True, capture_output=True, timeout=30,
    )
    code = (
        "import json,os,sys; "
        "print(json.dumps(dict(executable=sys.executable,prefix=sys.prefix,"
        "cwd=os.getcwd(),args=sys.argv[1:]),ensure_ascii=True))"
    )
    result = run_wrapper(wrapper, ["-c", code, "argument with spaces"], tmp_path)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout.strip())
    assert Path(output["executable"]) == project / ".venv" / "Scripts" / "python.exe"
    assert Path(output["prefix"]) == project / ".venv"
    assert Path(output["cwd"]) == project
    assert output["args"] == ["argument with spaces"]
    failure = run_wrapper(wrapper, ["-c", "import sys; sys.exit(17)"], tmp_path)
    assert failure.returncode == 17


def test_wrapper_requires_project_venv_instead_of_using_another_environment(tmp_path):
    wrapper = tmp_path / "_python.cmd"
    shutil.copy2(ROOT / "_python.cmd", wrapper)
    result = run_wrapper(wrapper, ["-c", "print('SHOULD_NOT_RUN')"], ROOT)
    assert result.returncode == 1
    assert "Chay Cai-Dat.cmd truoc." in result.stdout
    assert "SHOULD_NOT_RUN" not in result.stdout


def test_setup_rejects_conflicting_modes_before_creating_environment(tmp_path):
    project = tmp_path / "separate project"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    setup = scripts / "Setup.ps1"
    shutil.copy2(ROOT / "scripts" / "Setup.ps1", setup)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(setup), "-Market", "-Offline"],
        cwd=tmp_path, capture_output=True, text=True, errors="replace", timeout=30,
    )
    assert result.returncode != 0
    assert "Khong dung -Market va -Offline cung luc." in result.stderr
    assert not (project / ".venv").exists()


def test_stored_price_launcher_from_another_directory_preserves_scope_and_exit_code(tmp_path):
    project = tmp_path / "Dự án có khoảng trắng"
    project.mkdir()
    launcher = project / "03-Cap-Nhat-Gia-Cac-Ma-Da-Luu.cmd"
    shutil.copy2(ROOT / launcher.name, launcher)
    shutil.copy2(ROOT / "_python.cmd", project / "_python.cmd")
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(project / ".venv")],
                   check=True, capture_output=True, timeout=30)
    module = project / "vnresearch"
    module.mkdir()
    (module / "__init__.py").write_text("", encoding="utf-8")
    (module / "manual.py").write_text(
        "import json,os,sys\n"
        "print('ARGS=' + json.dumps(dict(args=sys.argv[1:],cwd=os.getcwd())))\n"
        "sys.exit(17 if '--fail' in sys.argv else 0)\n", encoding="utf-8")
    def launch(arguments):
        return subprocess.run(["cmd.exe", "/d", "/c", "call", str(launcher), *arguments],
                              input="\n", cwd=tmp_path, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=30)
    result = launch(["--dry-run", "--limit", "2"])
    assert result.returncode == 0, result.stderr
    output = json.loads(next(row[5:] for row in result.stdout.splitlines() if row.startswith("ARGS=")))
    assert output["args"] == ["history", "--stored", "--dry-run", "--limit", "2"]
    assert Path(output["cwd"]) == project
    result = launch(["--fail"])
    assert result.returncode == 17
    assert "Chua hoan tat" in result.stdout
