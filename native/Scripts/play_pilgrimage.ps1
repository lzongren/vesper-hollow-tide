param([string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8')
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$descriptor = Join-Path $project 'Vesper.uproject'
$bin = Join-Path $EngineRoot 'Engine\Binaries\Win64'
$map = '/Game/Vesper/Maps/MountainPilgrimage'
$gameMode = '/Game/Vesper/Duel/BP_BelfryMode.BP_BelfryMode_C'
if (!(Test-Path "$bin\UnrealEditor.exe")) { throw "Unreal Editor missing at $bin" }
. "$PSScriptRoot\local_storage.ps1"
$localCache = Join-Path $env:LOCALAPPDATA 'VesperDevelopment\DerivedDataCache'
Assert-VesperLocalPath $project
Assert-VesperLocalPath $localCache
[Environment]::SetEnvironmentVariable('UE-LocalDataCachePath', $localCache, 'Process')
& "$PSScriptRoot\prepare_traversal.ps1" -EngineRoot $EngineRoot

function Invoke-MapPass([string]$Script, [string]$SuccessMarker) {
    $scriptPath = Join-Path $PSScriptRoot "$Script.py"
    $log = Join-Path $project "Saved\$Script.log"
    $arguments = @("`"$descriptor`"", '-run=pythonscript', "-script=`"$scriptPath`"", '-unattended',
                   '-nosplash', '-NoSound', '-NoP4', "-abslog=`"$log`"")
    $process = Start-Process "$bin\UnrealEditor-Cmd.exe" -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0 -or !(Select-String -LiteralPath $log -Pattern $SuccessMarker -SimpleMatch -Quiet)) {
        throw "$Script failed. See $log"
    }
}

New-Item -ItemType Directory -Force "$project\Saved" | Out-Null
if (!(Test-Path "$project\Content\Vesper\Maps\MountainPilgrimage.umap") -or !(Test-Path "$project\Saved\Pilgrimage.json")) {
    Invoke-MapPass 'build_pilgrimage' 'Vesper pilgrimage built'
}
if (!(Test-Path "$project\Saved\PilgrimageDressed.json")) {
    Invoke-MapPass 'finish_pilgrimage' 'VESPER_ROUTE_DRESSED'
}
if (!(Test-Path "$project\Saved\Valley.json")) {
    Invoke-MapPass 'plant_valley' 'VESPER_VALLEY_SAVED'
}
if (!(Test-Path "$project\Saved\RouteMeshes.json")) {
    Invoke-MapPass 'prepare_route_meshes' 'VESPER_ROUTE_MESHES_READY'
}
if (!(Test-Path "$project\Saved\Procession.json")) {
    Invoke-MapPass 'dress_procession' 'VESPER_PROCESSION_SAVED'
}
$lightingReport = if (Test-Path "$project\Saved\MountainEvening.json") {
    Get-Content -Raw "$project\Saved\MountainEvening.json" | ConvertFrom-Json
}
if ($lightingReport.sun_forward_priority -ne 1) {
    Invoke-MapPass 'light_mountain' 'VESPER_MOUNTAIN_EVENING'
}
if (!(Test-Path "$project\Saved\Pines.json")) {
    Invoke-MapPass 'plant_pines' 'VESPER_PINES_SAVED'
}
if (!(Test-Path "$project\Saved\Understory.json")) {
    Invoke-MapPass 'dress_ground' 'VESPER_UNDERSTORY_SAVED'
}
if (!(Test-Path "$project\Saved\Ashlar.json")) {
    Invoke-MapPass 'fit_causeway' 'VESPER_ASHLAR_SAVED'
}
$fitReport = if (Test-Path "$project\Saved\FittedPilgrim.json") {
    Get-Content -Raw "$project\Saved\FittedPilgrim.json" | ConvertFrom-Json
}
if ($fitReport.locomotion_revision -ne 2 -or $fitReport.palm_revision -ne 1) {
    Invoke-MapPass 'fit_pilgrim' 'VESPER_PILGRIM_FITTED'
}
$duelReport = if (Test-Path "$project\Saved\BelfryDuel.json") {
    Get-Content -Raw "$project\Saved\BelfryDuel.json" | ConvertFrom-Json
}
$rebuildDuel = $duelReport.revision -ne 3 -or !(Test-Path "$project\Content\Vesper\Duel\BP_BelfryMode.uasset")
if ($rebuildDuel) {
    Invoke-MapPass 'build_bellwarden' 'VESPER_BELFRY_READY'
}
if (!(Test-Path "$project\Saved\BellHall.json")) {
    Invoke-MapPass 'raise_belfry' 'VESPER_BELL_HALL_SAVED'
}
if (!(Test-Path "$project\Saved\Forecourt.json")) {
    Invoke-MapPass 'lay_belfry_court' 'VESPER_FORECOURT_SAVED'
}
$heronReport = if (Test-Path "$project\Saved\HeronDuel.json") {
    Get-Content -Raw "$project\Saved\HeronDuel.json" | ConvertFrom-Json
}
$rebuildHeron = $heronReport.revision -ne 2
if ($rebuildHeron) {
    Invoke-MapPass 'build_heron' 'VESPER_HERON_READY'
}
$cinderReport = if (Test-Path "$project\Saved\CinderDuel.json") {
    Get-Content -Raw "$project\Saved\CinderDuel.json" | ConvertFrom-Json
}
if ($cinderReport.revision -ne 2) {
    Invoke-MapPass 'build_cinder' 'VESPER_CINDER_READY'
}
$fanReport = if (Test-Path "$project\Saved\HeronFan.json") {
    Get-Content -Raw "$project\Saved\HeronFan.json" | ConvertFrom-Json
}
if ($rebuildHeron -or $fanReport.revision -ne 3) {
    Invoke-MapPass 'fit_heron_fan' 'VESPER_HERON_FAN_READY'
}
$outfitReport = if (Test-Path "$project\Saved\WayfarerOutfit.json") {
    Get-Content -Raw "$project\Saved\WayfarerOutfit.json" | ConvertFrom-Json
}
if ($rebuildDuel -or $outfitReport.revision -ne 25 -or !(Test-Path "$project\Content\Vesper\Duel\ZhaoyueHaitang\ZhaoyueHaitang\SkeletalMeshes\ZhaoyueHaitang.uasset")) {
    Invoke-MapPass 'fit_wayfarer' 'VESPER_WAYFARER_READY'
}
if (!(Test-Path "$project\Saved\WestPass.json")) {
    Invoke-MapPass 'raise_karst_pass' 'VESPER_WEST_PASS_READY'
}
if (!(Test-Path "$project\Saved\LotusLanterns.json")) {
    Invoke-MapPass 'fit_lotus_lanterns' 'VESPER_LOTUS_LANTERNS_READY'
}
if (!(Test-Path "$project\Saved\PineFoliage.json")) {
    Invoke-MapPass 'fit_pine_foliage' 'VESPER_PINE_FOLIAGE_READY'
}
$ridgeReport = if (Test-Path "$project\Saved\RiverPeaks.json") {
    Get-Content -Raw "$project\Saved\RiverPeaks.json" | ConvertFrom-Json
}
if ($ridgeReport.revision -ne 3) {
    Invoke-MapPass 'fit_river_peaks' 'VESPER_RIVER_PEAKS_READY'
}
$gateReport = if (Test-Path "$project\Saved\BellGateLions.json") {
    Get-Content -Raw "$project\Saved\BellGateLions.json" | ConvertFrom-Json
}
if ($gateReport.revision -ne 2) {
    Invoke-MapPass 'fit_lion_gate' 'VESPER_BELL_GATE_LIONS_READY'
}
$screeReport = if (Test-Path "$project\Saved\ShrineTalus.json") {
    Get-Content -Raw "$project\Saved\ShrineTalus.json" | ConvertFrom-Json
}
if ($screeReport.revision -ne 5) {
    Invoke-MapPass 'fit_shrine_scree' 'VESPER_SHRINE_TALUS_READY'
}
$galleryReport = if (Test-Path "$project\Saved\BellRainGallery.json") {
    Get-Content -Raw "$project\Saved\BellRainGallery.json" | ConvertFrom-Json
}
if ($galleryReport.revision -ne 3) {
    Invoke-MapPass 'fit_bell_gallery' 'VESPER_RAIN_GALLERY_READY'
}
$pondReport = if (Test-Path "$project\Saved\MoonWater.json") {
    Get-Content -Raw "$project\Saved\MoonWater.json" | ConvertFrom-Json
}
if ($rebuildDuel -or $cinderReport.revision -ne 2 -or $ridgeReport.revision -ne 3 -or $screeReport.revision -ne 5 -or $pondReport.revision -ne 7) {
    Invoke-MapPass 'fit_moon_water' 'VESPER_MOON_WATER_READY'
}
Start-Process "$bin\UnrealEditor.exe" -WorkingDirectory $project -ArgumentList @(
    "`"$descriptor`"", "$map`?game=$gameMode", '-game', '-windowed', '-ResX=1600', '-ResY=900', '-NoP4',
    '-ForceEnablePython', '-ExecCmds="t.MaxFPS 60,py __import__(''runpy'').run_path(__import__(''unreal'').Paths.convert_relative_path_to_full(__import__(''unreal'').Paths.project_dir())+''Scripts/belfry_combat.py'')"'
)
