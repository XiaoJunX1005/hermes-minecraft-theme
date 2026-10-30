#!/usr/bin/env bash
# Hermes x Minecraft theme: install / update (macOS, Linux, WSL, Git Bash)
#   curl -fsSL https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.sh | bash
# Optional: HMT_SKIN=minecraft-end HMT_PET=bee  (otherwise your current choice is kept)
set -euo pipefail
REPO="${HMT_REPO:-https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main}"
SKINS="minecraft minecraft-nether minecraft-end minecraft-snow minecraft-cherry minecraft-ocean minecraft-lush minecraft-desert minecraft-mushroom minecraft-deepdark"
PLUGINS="minecraft-activity"
PETS="creeper pig chicken slime bee enderman lantern"
RETIRED="creeper-blocky creeper-carved creeper-tall creeper-buddy lantern-buddy mc-pig mc-chicken mc-slime mc-bee mc-enderman"

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
for g in $PLUGINS; do
  mkdir -p "$TMP/plugins/$g"
  curl -fsSL "$REPO/desktop-plugins/$g/plugin.js" > "$TMP/plugins/$g/plugin.js"
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
rm -rf "$HOME_DIR/desktop-plugins/minecraft-ocean"
for g in $PLUGINS; do
  mkdir -p "$HOME_DIR/desktop-plugins/$g"
  cp "$TMP/plugins/$g/plugin.js" "$HOME_DIR/desktop-plugins/$g/plugin.js"
done
echo "Installed into $HOME_DIR"

if ! command -v hermes >/dev/null 2>&1; then
  echo "hermes command not found. Apply it with: hermes config set display.skin minecraft"
  for p in $RETIRED; do rm -rf "$HOME_DIR/pets/$p"; done
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
want_pet="$cur_pet"
case "$cur_pet" in
    creeper-blocky) want_pet=creeper ;;
    creeper-carved) want_pet=creeper ;;
    creeper-tall) want_pet=creeper ;;
    creeper-buddy) want_pet=creeper ;;
    lantern-buddy) want_pet=lantern ;;
    mc-pig) want_pet=pig ;;
    mc-chicken) want_pet=chicken ;;
    mc-slime) want_pet=slime ;;
    mc-bee) want_pet=bee ;;
    mc-enderman) want_pet=enderman ;;
esac
if [ -z "$pet" ]; then
  if [ -n "$want_pet" ] && [ -d "$HOME_DIR/pets/$want_pet" ]; then pet="$want_pet"; else pet="creeper"; fi
fi
if [ "$skin" != "$cur_skin" ]; then hermes config set display.skin "$skin"; fi
if [ "$pet" != "$cur_pet" ]; then hermes pets select "$pet"; fi
# Pets from older versions (one per species now); only this project's own old folders, after selecting the new one.
for p in $RETIRED; do rm -rf "$HOME_DIR/pets/$p"; done
echo "Theme: $skin   Pet: $pet"
echo "Revert: hermes config set display.skin default ; hermes pets off"
