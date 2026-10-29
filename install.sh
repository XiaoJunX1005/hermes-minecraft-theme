#!/usr/bin/env bash
# Hermes x Minecraft theme: install / update (macOS, Linux, WSL, Git Bash)
#   curl -fsSL https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.sh | bash
# Optional: HMT_SKIN=minecraft-end HMT_PET=mc-bee  (otherwise your current choice is kept)
set -euo pipefail
REPO="${HMT_REPO:-https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main}"
SKINS="minecraft minecraft-nether minecraft-end minecraft-snow minecraft-cherry"
PETS="creeper-blocky creeper-carved creeper-tall creeper-buddy lantern-buddy mc-pig mc-chicken mc-slime mc-bee mc-enderman"

if [ -n "${HERMES_HOME:-}" ]; then HOME_DIR="$HERMES_HOME"
elif [ -n "${LOCALAPPDATA:-}" ] && [ -d "$LOCALAPPDATA/hermes" ]; then HOME_DIR="$LOCALAPPDATA/hermes"
else HOME_DIR="$HOME/.hermes"; fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Downloading to a temporary folder..."
mkdir -p "$TMP/skins"
for s in $SKINS; do
  curl -fsSL "$REPO/skins/$s.yaml" > "$TMP/skins/$s.yaml"
done
for p in $PETS; do
  mkdir -p "$TMP/pets/$p"
  curl -fsSL "$REPO/pets/$p/pet.json" > "$TMP/pets/$p/pet.json"
  curl -fsSL "$REPO/pets/$p/spritesheet.png" > "$TMP/pets/$p/spritesheet.png"
done

# Only replace installed files once every download succeeded.
mkdir -p "$HOME_DIR/skins" "$HOME_DIR/pets"
cp "$TMP"/skins/*.yaml "$HOME_DIR/skins/"
for p in $PETS; do
  mkdir -p "$HOME_DIR/pets/$p"
  cp "$TMP/pets/$p/pet.json" "$TMP/pets/$p/spritesheet.png" "$HOME_DIR/pets/$p/"
done
echo "Installed into $HOME_DIR"

if ! command -v hermes >/dev/null 2>&1; then
  echo "hermes command not found. Apply it with: hermes config set display.skin minecraft"
  exit 0
fi

cfg() { hermes config get "$1" 2>/dev/null | tail -n 1 | tr -d "\r'\" " || true; }
cur_skin="$(cfg display.skin)"
cur_pet="$(cfg display.pet.slug)"

skin="${HMT_SKIN:-}"
if [ -z "$skin" ]; then
  case " $SKINS " in *" $cur_skin "*) skin="$cur_skin" ;; *) skin="minecraft" ;; esac
fi
pet="${HMT_PET:-}"
if [ -z "$pet" ]; then
  if [ -n "$cur_pet" ] && [ -d "$HOME_DIR/pets/$cur_pet" ]; then pet="$cur_pet"; else pet="creeper-blocky"; fi
fi
if [ "$skin" != "$cur_skin" ]; then hermes config set display.skin "$skin"; fi
if [ "$pet" != "$cur_pet" ]; then hermes pets select "$pet"; fi
echo "Theme: $skin   Pet: $pet"
echo "Revert: hermes config set display.skin default ; hermes pets off"
