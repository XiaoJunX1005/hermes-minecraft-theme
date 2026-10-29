#!/usr/bin/env bash
# Hermes · Voxel Lantern theme installer (macOS / Linux / WSL / Git Bash)
#   curl -fsSL https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.sh | bash
set -euo pipefail
REPO="https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main"

if [ -n "${HERMES_HOME:-}" ]; then HOME_DIR="$HERMES_HOME"
elif [ -n "${LOCALAPPDATA:-}" ] && [ -d "$LOCALAPPDATA/hermes" ]; then HOME_DIR="$LOCALAPPDATA/hermes"
else HOME_DIR="$HOME/.hermes"; fi

mkdir -p "$HOME_DIR/skins" "$HOME_DIR/pets/lantern-buddy"
curl -fsSL "$REPO/skins/minecraft.yaml" > "$HOME_DIR/skins/minecraft.yaml"
curl -fsSL "$REPO/pets/lantern-buddy/pet.json" > "$HOME_DIR/pets/lantern-buddy/pet.json"
curl -fsSL "$REPO/pets/lantern-buddy/spritesheet.png" > "$HOME_DIR/pets/lantern-buddy/spritesheet.png"

if command -v hermes >/dev/null 2>&1; then
  hermes config set display.skin minecraft
  hermes pets select lantern-buddy || true
  printf '\n⛏  Voxel Lantern theme applied!  Revert: hermes config set display.skin default\n'
else
  echo "Files installed to $HOME_DIR. Run: hermes config set display.skin minecraft"
fi
