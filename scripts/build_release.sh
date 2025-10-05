#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-dev}"
DIST_DIR="dist"
ARCHIVE_NAME="energy_advisor-${VERSION}.zip"
OUTPUT_PATH="${DIST_DIR}/${ARCHIVE_NAME}"

rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

EA_OUTPUT_PATH="${OUTPUT_PATH}" EA_ROOT="$(pwd)" python3 <<'PY'
import os
import sys
from pathlib import Path
import zipfile

root = Path(os.environ["EA_ROOT"]).resolve()
output = Path(os.environ["EA_OUTPUT_PATH"]).resolve()
payloads = [
    Path("custom_components/energy_advisor"),
    Path("hacs.json"),
    Path("README.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("AGENTS.md"),
]

skip_dirs = {"__pycache__"}
skip_suffixes = {".pyc"}

with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
    for item in payloads:
        full = root / item
        if full.is_dir():
            for file in full.rglob("*"):
                if any(part in skip_dirs for part in file.parts):
                    continue
                if file.suffix in skip_suffixes or not file.is_file():
                    continue
                zf.write(file, file.relative_to(root))
        elif full.is_file():
            zf.write(full, item.as_posix())
        else:
            print(f"Warning: {item} not found; skipping", file=sys.stderr)

print(f"Created {output}")
PY
