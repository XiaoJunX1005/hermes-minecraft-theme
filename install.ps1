# Hermes x Minecraft theme: install / update (Windows PowerShell)
#   irm https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.ps1 | iex
# Optional: $env:HMT_SKIN = 'minecraft-end'; $env:HMT_PET = 'bee'  (otherwise your current choice is kept)
& {
$ErrorActionPreference = 'Stop'
$repo = if ($env:HMT_REPO) { $env:HMT_REPO } else { 'https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main' }
$skins = 'minecraft','minecraft-nether','minecraft-end','minecraft-snow','minecraft-cherry','minecraft-ocean','minecraft-lush','minecraft-desert','minecraft-mushroom','minecraft-deepdark'
$plugins = 'minecraft-activity'
$pets = 'creeper','pig','chicken','slime','bee','enderman','lantern'
$retired = @{ 'creeper-blocky'='creeper'; 'creeper-carved'='creeper'; 'creeper-tall'='creeper'; 'creeper-buddy'='creeper'; 'lantern-buddy'='lantern'; 'mc-pig'='pig'; 'mc-chicken'='chicken'; 'mc-slime'='slime'; 'mc-bee'='bee'; 'mc-enderman'='enderman' }
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
    Remove-Item "$hhome\desktop-plugins\minecraft-ocean" -Recurse -Force -ErrorAction SilentlyContinue
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
    foreach ($old in $retired.Keys) { Remove-Item "$hhome\pets\$old" -Recurse -Force -ErrorAction SilentlyContinue }
    return
}
function Get-HermesCfg($key) {
    $v = & hermes config get $key 2>$null | Select-Object -Last 1
    if ($null -eq $v) { return '' }
    return "$v".Trim().Trim("'", '"')
}
$curSkin = Get-HermesCfg 'display.skin'
$curPet = Get-HermesCfg 'display.pet.slug'
$wantPet = if ($retired.ContainsKey($curPet)) { $retired[$curPet] } else { $curPet }
$skin = if ($env:HMT_SKIN) { $env:HMT_SKIN } elseif ($skins -contains $curSkin) { $curSkin } else { 'minecraft' }
$pet = if ($env:HMT_PET) { $env:HMT_PET } elseif ($wantPet -and (Test-Path "$hhome\pets\$wantPet")) { $wantPet } else { 'creeper' }
if ($skin -ne $curSkin) { & hermes config set display.skin $skin }
if ($pet -ne $curPet) { & hermes pets select $pet }
# Pets from older versions (one per species now); only this project's own old folders, after selecting the new one.
foreach ($old in $retired.Keys) { Remove-Item "$hhome\pets\$old" -Recurse -Force -ErrorAction SilentlyContinue }
Write-Host "Theme: $skin   Pet: $pet"
Write-Host 'Revert: hermes config set display.skin default ; hermes pets off'
}
