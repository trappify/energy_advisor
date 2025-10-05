#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-2.0.5}"

COMMAND="set -euo pipefail; TMP_DIR=\$(mktemp -d); cd \$TMP_DIR; wget -q https://github.com/hacs/integration/releases/download/${VERSION}/hacs.zip; unzip -q hacs.zip -d extracted; rm -rf /config/custom_components/hacs; mkdir -p /config/custom_components/hacs; cp -a extracted/. /config/custom_components/hacs/; chown -R 1000:1000 /config/custom_components/hacs; rm -rf \$TMP_DIR; echo 'HACS ${VERSION} installed'"

docker compose run --rm homeassistant bash -lc "${COMMAND}"
