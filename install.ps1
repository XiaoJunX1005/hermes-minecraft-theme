# Hermes · Voxel Lantern theme installer (Windows PowerShell)
#   irm https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'
$repo = 'https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main'

$home_ = if ($env:HERMES_HOME) { $env:HERMES_HOME }
         elseif (Test-Path "$env:LOCALAPPDATA\hermes") { "$env:LOCALAPPDATA\hermes" }
         else { Join-Path $HOME '.hermes' }

New-Item -ItemType Directory -Force "$home_\skins", "$home_\pets\lantern-buddy" | Out-Null
Invoke-WebRequest "$repo/skins/minecraft.yaml" -OutFile "$home_\skins\minecraft.yaml"
Invoke-WebRequest "$repo/pets/lantern-buddy/pet.json" -OutFile "$home_\pets\lantern-buddy\pet.json"
Invoke-WebRequest "$repo/pets/lantern-buddy/spritesheet.png" -OutFile "$home_\pets\lantern-buddy\spritesheet.png"

if (Get-Command hermes -ErrorAction SilentlyContinue) {
    hermes config set display.skin minecraft
    hermes pets select lantern-buddy
    Write-Host "`n⛏  Voxel Lantern theme applied!  Revert: hermes config set display.skin default" -ForegroundColor Green
} else {
    Write-Host "Files installed to $home_. Run: hermes config set display.skin minecraft"
}
