#!/usr/bin/env bash
# Rendert docs/diagrams/*.mmd zu PNG (funktioniert ueberall, auch wenn GitHubs Mermaid-Renderer ausfaellt).
# Voraussetzung: Node.js + Chromium. Nutzung: ./scripts/render-diagrams.sh
set -euo pipefail
cd "$(dirname "$0")/../docs/diagrams"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
echo '{"executablePath":"'"${CHROMIUM:-/usr/bin/chromium}"'","args":["--no-sandbox"]}' > "$T/pp.json"
echo '{"theme":"default","flowchart":{"htmlLabels":false}}' > "$T/cfg.json"
for f in *.mmd; do
  npx -y @mermaid-js/mermaid-cli@11 -p "$T/pp.json" -c "$T/cfg.json" -b white -s 2 -i "$f" -o "${f%.mmd}.png"
done
