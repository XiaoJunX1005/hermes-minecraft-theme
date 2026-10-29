# Hermes x Minecraft theme: install / update (Windows PowerShell)
#   irm https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.ps1 | iex
# Optional: $env:HMT_SKIN = 'minecraft-end'; $env:HMT_PET = 'mc-bee'  (otherwise your current choice is kept)
& {
$ErrorActionPreference = 'Stop'
$repo = if ($env:HMT_REPO) { $env:HMT_REPO } else { 'https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main' }
$skins = 'minecraft','minecraft-nether','minecraft-end','minecraft-snow','minecraft-cherry'
$plugins = 'minecraft-activity'
$pets = 'creeper-blocky','creeper-carved','creeper-tall','creeper-buddy','lantern-buddy','mc-pig','mc-chicken','mc-slime','mc-bee','mc-enderman'
$hhome = if ($env:HERMES_HOME) { $env:HERMES_HOME }
         elseif (Test-Path "$env:LOCALAPPDATA\hermes") { "$env:LOCALAPPDATA\hermes" }
         else { Join-Path $HOME '.hermes' }
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('hmt-' + [guid]::NewGuid().ToString('N'))
try {
    Write-Host 'Downloading to a temporary folder...'
    New-Item -ItemType Directory -Force "$tmp\skins" | Out-Null
    foreach ($s in $skins) { Invoke-WebRequest -UseBasicParsing "$repo/skins/$s.yaml" -OutFile "$tmp\skins\$s.yaml" }
    foreach ($g in $plugins) {
        New-Item -ItemType Directory -Force "$tmp\plugins\$g" | Out-Null
        Invoke-WebRequest -UseBasicParsing "$repo/desktop-plugins/$g/plugin.js" -OutFile "$tmp\plugins\$g\plugin.js"
    }
    foreach ($p in $pets) {
        New-Item -ItemType Directory -Force "$tmp\pets\$p" | Out-Null
        foreach ($f in 'pet.json', 'spritesheet.png') { Invoke-WebRequest -UseBasicParsing "$repo/pets/$p/$f" -OutFile "$tmp\pets\$p\$f" }
    }
    # Only replace installed files once every download succeeded.
    New-Item -ItemType Directory -Force "$hhome\skins" | Out-Null
    foreach ($s in $skins) { Copy-Item "$tmp\skins\$s.yaml" "$hhome\skins\$s.yaml" -Force }
    foreach ($p in $pets) {
        New-Item -ItemType Directory -Force "$hhome\pets\$p" | Out-Null
        foreach ($f in 'pet.json', 'spritesheet.png') { Copy-Item "$tmp\pets\$p\$f" "$hhome\pets\$p\$f" -Force }
    }
    Remove-Item "$hhome\desktop-plugins\minecraft-ocean", "$hhome\skins\minecraft-ocean.yaml" -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($g in $plugins) {
        New-Item -ItemType Directory -Force "$hhome\desktop-plugins\$g" | Out-Null
        Copy-Item "$tmp\plugins\$g\plugin.js" "$hhome\desktop-plugins\$g\plugin.js" -Force
    }
} finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "Installed into $hhome"

$ErrorActionPreference = 'Continue'
if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {
    Write-Host 'hermes command not found. Apply it with: hermes config set display.skin minecraft'
    return
}
function Get-HermesCfg($key) {
    $v = & hermes config get $key 2>$null | Select-Object -Last 1
    if ($null -eq $v) { return '' }
    return "$v".Trim().Trim("'", '"')
}
$curSkin = Get-HermesCfg 'display.skin'
$curPet = Get-HermesCfg 'display.pet.slug'
$skin = if ($env:HMT_SKIN) { $env:HMT_SKIN } elseif ($skins -contains $curSkin) { $curSkin } else { 'minecraft' }
$pet = if ($env:HMT_PET) { $env:HMT_PET } elseif ($curPet -and (Test-Path "$hhome\pets\$curPet")) { $curPet } else { 'creeper-blocky' }
if ($skin -ne $curSkin) { & hermes config set display.skin $skin }
if ($pet -ne $curPet) { & hermes pets select $pet }
Write-Host "Theme: $skin   Pet: $pet"
Write-Host 'Revert: hermes config set display.skin default ; hermes pets off'
}
