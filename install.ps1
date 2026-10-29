# Hermes × Minecraft theme installer (Windows PowerShell)
#   irm https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'
$repo = 'https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main'

$home_ = if ($env:HERMES_HOME) { $env:HERMES_HOME }
         elseif (Test-Path "$env:LOCALAPPDATA\hermes") { "$env:LOCALAPPDATA\hermes" }
         else { Join-Path $HOME '.hermes' }

New-Item -ItemType Directory -Force "$home_\skins" | Out-Null
foreach ($s in 'minecraft','minecraft-nether','minecraft-end','minecraft-snow','minecraft-cherry') {
    Invoke-WebRequest "$repo/skins/$s.yaml" -OutFile "$home_\skins\$s.yaml"
}
foreach ($p in 'creeper-blocky','creeper-carved','creeper-tall','creeper-buddy','lantern-buddy','mc-pig','mc-chicken','mc-slime','mc-bee','mc-enderman') {
    New-Item -ItemType Directory -Force "$home_\pets\$p" | Out-Null
    Invoke-WebRequest "$repo/pets/$p/pet.json" -OutFile "$home_\pets\$p\pet.json"
    Invoke-WebRequest "$repo/pets/$p/spritesheet.png" -OutFile "$home_\pets\$p\spritesheet.png"
}
if (Get-Command hermes -ErrorAction SilentlyContinue) {
    hermes config set display.skin minecraft
    hermes pets select creeper-blocky
    Write-Host "`n⛏  Minecraft theme applied!  Revert: hermes config set display.skin default" -ForegroundColor Green
} else {
    Write-Host "Files installed to $home_. Run: hermes config set display.skin minecraft"
}
