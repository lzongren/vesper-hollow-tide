param([Parameter(Mandatory=$true)][string]$EngineRoot)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot\local_storage.ps1"
Assert-VesperLocalPath $project
foreach ($subdir in @('Content','Art','SourceAssets','Saved','Intermediate','DerivedDataCache')) {
    Assert-VesperLocalPath (Join-Path $project $subdir)
}
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
foreach ($pack in @('Anims','Blueprints','Input','UI','VFX')) {
    $destination = Join-Path $project "Content\Variant_Combat\$pack"
    Assert-VesperLocalPath $destination
    Copy-TemplateTree "$templates\TemplateResources\Standard\Variant_Combat\Content\$pack" $destination
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
foreach ($channel in @('color','normal','rough')) {
    Stage-Source $source "rock-$channel.jpg"
}
$models = Join-Path (Split-Path $project -Parent) 'public\models'
foreach ($channel in @('color','normal')) {
    Stage-Source $source "pilgrim-brocade-$channel.jpg"
}
foreach ($model in @('pine.glb','rock_face_01.glb','pilgrim.glb','tide-bell.glb','wraith.glb','cinder-ascetic.glb','cinder-relief.glb')) {
    Stage-Source $models $model
}
$courtArt = Join-Path (Split-Path $project -Parent) 'public\art'
Stage-Source $source "heron-damask.jpg"
Stage-Source $source "cinder-brocade.jpg"
Stage-Source $source "shrine-fire.rg8.gz"
foreach ($piece in @('heron-quill.png','warden-mask.png','dragon-mantle.jpg','belfry-plaque.jpg','belfry-paper.jpg','belfry-dragon-beam.jpg','tide-icon.jpg')) {
    Stage-Source $courtArt $piece
}
foreach ($channel in @('color','normal')) {
    Stage-Source $source "metal-$channel.jpg"
}

foreach ($channel in @('color','normal')) {
    Stage-Source $source "wood-$channel.jpg"
}
