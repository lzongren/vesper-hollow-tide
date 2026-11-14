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
if (!(Test-Path "$project\Saved\MountainEvening.json")) {
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
if ($duelReport.revision -ne 3 -or !(Test-Path "$project\Content\Vesper\Duel\BP_BelfryMode.uasset")) {
    Invoke-MapPass 'build_bellwarden' 'VESPER_BELFRY_READY'
}
if (!(Test-Path "$project\Saved\BellHall.json")) {
    Invoke-MapPass 'raise_belfry' 'VESPER_BELL_HALL_SAVED'
}
if (!(Test-Path "$project\Saved\Forecourt.json")) {
    Invoke-MapPass 'lay_belfry_court' 'VESPER_FORECOURT_SAVED'
}
if (!(Test-Path "$project\Saved\HeronDuel.json")) {
    Invoke-MapPass 'build_heron' 'VESPER_HERON_READY'
}
Start-Process "$bin\UnrealEditor.exe" -WorkingDirectory $project -ArgumentList @(
    "`"$descriptor`"", "$map`?game=$gameMode", '-game', '-windowed', '-ResX=1600', '-ResY=900', '-NoP4',
    '-ForceEnablePython', '-ExecCmds="py __import__(''runpy'').run_path(__import__(''unreal'').Paths.convert_relative_path_to_full(__import__(''unreal'').Paths.project_dir())+''Scripts/belfry_combat.py'')"'
)
