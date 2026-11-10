#!/usr/bin/env bash
# Run all tests with the project virtualenv (it also sets JAVA_HOME for PySpark).
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
java -version 2>&1 | head -1
python -m pytest -q tests "$@"
