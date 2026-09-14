$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$PortableRoot = Join-Path $ProjectRoot "dist\Neurodot"
$PortableExe = Join-Path $PortableRoot "Neurodot.exe"
$InstallerScript = Join-Path $PSScriptRoot "neurodot-installer.iss"
$OutputDir = Join-Path $ProjectRoot "installer"
$ChecksumFile = Join-Path $OutputDir "Neurodot-Setup.sha256"

if (-not (Test-Path -LiteralPath $PortableExe -PathType Leaf)) {
    throw "The verified portable build is missing: $PortableExe"
}

$InnoCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$Compiler = $InnoCandidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1
if (-not $Compiler) {
    throw "Inno Setup 6 was not found. Install JRSoftware.InnoSetup first."
}

Write-Host "Verifying the portable application before packaging..."
& (Join-Path $PSScriptRoot "verify_portable.ps1")

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Get-ChildItem -LiteralPath $OutputDir -File -Filter "Neurodot-Setup*" |
    Remove-Item -Force

Write-Host "Building the Neurodot installer..."
& $Compiler $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE."
}

$InstallerFiles = Get-ChildItem -LiteralPath $OutputDir -File |
    Where-Object { $_.Name -like "Neurodot-Setup*" -and $_.Extension -ne ".sha256" } |
    Sort-Object Name
if (-not $InstallerFiles) {
    throw "The installer compiler produced no output files in $OutputDir"
}

$ChecksumLines = foreach ($File in $InstallerFiles) {
    $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash
    "$Hash  $($File.Name)"
}
$ChecksumLines | Set-Content -LiteralPath $ChecksumFile -Encoding ascii

Write-Host "Installer created successfully:"
$InstallerFiles | ForEach-Object {
    Write-Host ("  {0} ({1:N2} GiB)" -f $_.FullName, ($_.Length / 1GB))
}
Write-Host "Checksums: $ChecksumFile"
