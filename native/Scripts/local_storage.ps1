# Fail before the first project write, including when a junction leads into OneDrive.
function Assert-VesperLocalPath([Parameter(Mandatory=$true)][string]$Path) {
    $roots = @($env:OneDrive, $env:OneDriveConsumer, $env:OneDriveCommercial)
    $accounts = 'HKCU:\Software\Microsoft\OneDrive\Accounts'
    if (Test-Path $accounts) {
        $roots += Get-ChildItem $accounts | ForEach-Object { (Get-ItemProperty $_.PSPath).UserFolder }
    }
    $roots = @($roots | Where-Object { $_ } | ForEach-Object { [IO.Path]::GetFullPath($_).TrimEnd('\') } | Sort-Object -Unique)
    $item = [IO.DirectoryInfo]::new([IO.Path]::GetFullPath($Path))
    while ($item) {
        foreach ($root in $roots) {
            if ($item.FullName.TrimEnd('\').Equals($root, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Vesper requires local storage. Put this checkout under $env:LOCALAPPDATA\VesperDevelopment before launching. OneDrive root: $root"
            }
        }
        if ($item.Exists -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Use a physical local project and cache directory for Vesper. Linked or cloud-managed directory: $($item.FullName)"
        }
        $item = $item.Parent
    }
}
