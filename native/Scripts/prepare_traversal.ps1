param([Parameter(Mandatory=$true)][string]$EngineRoot)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$templates = Join-Path $EngineRoot 'Templates'
# The locally installed Epic template supplies its own movement blueprint,
# animation graph and enhanced input. Only source for the Vesper map is published.
function Copy-TemplateTree([string]$Source, [string]$Destination) {
    if (!(Test-Path $Source)) { throw "Missing installed template content: $Source" }
    robocopy $Source $Destination /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Could not copy $Source" }
}
Copy-TemplateTree "$templates\TP_ThirdPersonBP\Content\ThirdPerson\Blueprints" "$project\Content\ThirdPerson\Blueprints"
foreach ($pack in @('Characters','Input','LevelPrototyping')) {
    Copy-TemplateTree "$templates\TemplateResources\High\$pack\Content" "$project\Content\$pack"
}
$source = Join-Path (Split-Path $project -Parent) 'public\textures'
$dest = Join-Path $project 'SourceAssets'
New-Item -ItemType Directory -Force $dest | Out-Null
function Stage-Source([string]$SourceDir, [string]$Name) {
    if (Test-Path "$SourceDir\$Name") {
        Copy-Item "$SourceDir\$Name" "$dest\$Name" -Force
    } elseif (!(Test-Path "$dest\$Name")) {
        throw "Missing source asset $Name in $SourceDir and $dest"
    }
}
foreach ($channel in @('color','normal','rough')) {
    Stage-Source $source "stone-$channel.jpg"
}
$models = Join-Path (Split-Path $project -Parent) 'public\models'
foreach ($model in @('pine.glb','rock_face_01.glb')) {
    Stage-Source $models $model
}
