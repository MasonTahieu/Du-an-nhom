#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 -c "import sys; assert sys.version_info >= (3,11)"
if [ ! -x "$HOME/.venv/bin/python" ]; then python3 -m venv "$HOME/.venv"; fi
. "$HOME/.venv/bin/activate"
python -m pip install -r requirements.lock.txt
python -m vnresearch verify
printf '%s\n' 'Ready: python -m vnresearch serve'
