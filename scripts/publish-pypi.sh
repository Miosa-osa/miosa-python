#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

project_version="$(
  python3 - <<'PY'
import pathlib
import tomllib

data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
print(data["project"]["version"])
PY
)"

echo "Publishing miosa ${project_version} to PyPI"
echo "This script will prompt for the PyPI API token without echoing it."
echo

python3 -m pip index versions miosa 2>/dev/null | head -5 || true
echo

read -r -s -p "PyPI token: " pypi_token
echo

if [[ -z "${pypi_token}" ]]; then
  echo "No token entered; aborting." >&2
  exit 1
fi

rm -rf dist
uv run --with build python -m build
uv run --with twine twine check "dist/miosa-${project_version}"*

TWINE_USERNAME="__token__" TWINE_PASSWORD="${pypi_token}" \
  uv run --with twine twine upload "dist/miosa-${project_version}"*

unset pypi_token

echo
echo "Verifying PyPI sees miosa ${project_version}..."
for _ in 1 2 3 4 5; do
  if python3 -m pip index versions miosa 2>/dev/null | head -5 | grep -q "miosa (${project_version})"; then
    python3 -m pip index versions miosa 2>/dev/null | head -5
    exit 0
  fi
  sleep 3
done

echo "Upload completed, but PyPI index did not show ${project_version} yet. Check again in a minute." >&2
