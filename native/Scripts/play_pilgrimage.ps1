param([string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8')
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$descriptor = Join-Path $project 'Vesper.uproject'
$bin = Join-Path $EngineRoot 'Engine\Binaries\Win64'
$map = '/Game/Vesper/Maps/MountainPilgrimage'
$gameMode = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C'
if (!(Test-Path "$bin\UnrealEditor.exe")) { throw "Unreal Editor missing at $bin" }
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
Start-Process "$bin\UnrealEditor.exe" -WorkingDirectory $project -ArgumentList @(
    "`"$descriptor`"", "$map`?game=$gameMode", '-game', '-windowed', '-ResX=1600', '-ResY=900', '-NoP4'
)
