#!/usr/bin/env sh
set -eu
task_offline=0
task_dev=0
task_market=0
for task_arg in "$@"; do
    case "$task_arg" in
        --offline|-Offline) task_offline=1 ;;
        --dev|-Dev) task_dev=1 ;;
        --market|-Market) task_market=1 ;;
        *) printf '%s\n' "Unknown option: $task_arg" >&2; exit 1 ;;
    esac
done
if [ "$task_offline" -eq 1 ] && [ "$task_market" -eq 1 ]; then
    printf '%s\n' 'Do not combine --offline and --market.' >&2
    exit 1
fi
cd "$(dirname "$0")/.."
task_root=$(pwd -P)
task_venv="$task_root/.venv"
task_python="$task_venv/bin/python"
if [ ! -x "$task_python" ]; then
    python3 -c "import sys; assert sys.version_info >= (3,11), 'Python >=3.11 required'"
    python3 -m venv "$task_venv"
fi
"$task_python" -c "import sys; assert sys.version_info >= (3,11), 'Python >=3.11 required'"
. "$task_venv/bin/activate"
"$task_python" -m pip install --index-url https://pypi.org/simple -r requirements.lock.txt
"$task_python" -m vnresearch verify
if [ "$task_offline" -eq 0 ]; then
    if ! "$task_python" -m pip install --index-url https://pypi.org/simple -r requirements-market.txt; then
        printf '%s\n' 'App and sample data are ready; market collector installation failed. Check PyPI/vnstocks.com access and rerun setup. Existing data can be viewed; online collection is not ready.' >&2
        exit 1
    fi
fi
if [ "$task_dev" -eq 1 ]; then
    "$task_python" -m pip install --index-url https://pypi.org/simple -c requirements.lock.txt -r requirements-dev.txt
fi
"$task_python" -m pip check
if [ "$task_offline" -eq 1 ]; then
    printf '%s\n' 'App portion ready; online collector was skipped in this run. Rerun without --offline for a complete installation check.'
fi
printf '%s\n' 'Ready: activate the project .venv, then run python -m vnresearch serve'
