#!/usr/bin/env bash
set -euo pipefail

BRANCH="${1:-master}"
TMP_DIR="$(mktemp -d)"
ARCHIVE="$TMP_DIR/nordpool.zip"
TARGET_DIR=".homeassistant/custom_components/nordpool"

curl -fsSL -o "$ARCHIVE" "https://github.com/custom-components/nordpool/archive/refs/heads/${BRANCH}.zip"
unzip -q "$ARCHIVE" -d "$TMP_DIR"
EXTRACT_DIR=$(find "$TMP_DIR" -maxdepth 1 -type d -name 'nordpool-*' | head -n1)
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -a "$EXTRACT_DIR/custom_components/nordpool/." "$TARGET_DIR/"
rm -rf "$TMP_DIR"

echo "Nordpool (${BRANCH}) installed to $TARGET_DIR"
