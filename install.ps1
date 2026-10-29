# Hermes × Minecraft theme installer (Windows PowerShell)
#   irm https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'
$repo = 'https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main'

$home_ = if ($env:HERMES_HOME) { $env:HERMES_HOME }
         elseif (Test-Path "$env:LOCALAPPDATA\hermes") { "$env:LOCALAPPDATA\hermes" }
         else { Join-Path $HOME '.hermes' }

New-Item -ItemType Directory -Force "$home_\skins", "$home_\pets\creeper-buddy", "$home_\pets\lantern-buddy" | Out-Null
foreach ($s in 'minecraft','minecraft-cubic','minecraft-mixed','minecraft-pixelify') {
    Invoke-WebRequest "$repo/skins/$s.yaml" -OutFile "$home_\skins\$s.yaml"
}
foreach ($p in 'creeper-buddy','lantern-buddy') {
    Invoke-WebRequest "$repo/pets/$p/pet.json" -OutFile "$home_\pets\$p\pet.json"
    Invoke-WebRequest "$repo/pets/$p/spritesheet.png" -OutFile "$home_\pets\$p\spritesheet.png"
}
if (Get-Command hermes -ErrorAction SilentlyContinue) {
    hermes config set display.skin minecraft
    hermes pets select creeper-buddy
    Write-Host "`n⛏  Minecraft theme applied!  Revert: hermes config set display.skin default" -ForegroundColor Green
} else {
    Write-Host "Files installed to $home_. Run: hermes config set display.skin minecraft"
}
