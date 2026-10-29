#!/usr/bin/env bash
# Hermes × Minecraft theme installer (macOS / Linux / WSL / Git Bash)
#   curl -fsSL https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.sh | bash
set -euo pipefail
REPO="https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main"

if [ -n "${HERMES_HOME:-}" ]; then HOME_DIR="$HERMES_HOME"
elif [ -n "${LOCALAPPDATA:-}" ] && [ -d "$LOCALAPPDATA/hermes" ]; then HOME_DIR="$LOCALAPPDATA/hermes"
else HOME_DIR="$HOME/.hermes"; fi

mkdir -p "$HOME_DIR/skins" "$HOME_DIR/pets/creeper-buddy" "$HOME_DIR/pets/lantern-buddy"
for s in minecraft minecraft-cubic minecraft-mixed minecraft-pixelify; do
  curl -fsSL "$REPO/skins/$s.yaml" > "$HOME_DIR/skins/$s.yaml"
done
for p in creeper-buddy lantern-buddy; do
  curl -fsSL "$REPO/pets/$p/pet.json" > "$HOME_DIR/pets/$p/pet.json"
  curl -fsSL "$REPO/pets/$p/spritesheet.png" > "$HOME_DIR/pets/$p/spritesheet.png"
done

if command -v hermes >/dev/null 2>&1; then
  hermes config set display.skin minecraft
  hermes pets select creeper-buddy || true
  printf '\n⛏  Minecraft theme applied!  Revert: hermes config set display.skin default\n'
else
  echo "Files installed to $HOME_DIR. Run: hermes config set display.skin minecraft"
fi
