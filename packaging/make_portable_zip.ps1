$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$PortableFolder = Join-Path $ProjectRoot "dist\Neurodot"
$Archive = Join-Path $ProjectRoot "Neurodot-portable.zip"
$ChecksumFile = Join-Path $ProjectRoot "Neurodot-portable.sha256"

if (-not (Test-Path -LiteralPath (Join-Path $PortableFolder "Neurodot.exe") -PathType Leaf)) {
    throw "Build and verify the portable application first: $PortableFolder"
}

if (Test-Path -LiteralPath $Archive -PathType Leaf) {
    [System.IO.File]::Delete($Archive)
}

& "$env:SystemRoot\System32\tar.exe" `
    -a `
    -cf $Archive `
    -C (Split-Path -Parent $PortableFolder) `
    (Split-Path -Leaf $PortableFolder)

if ($LASTEXITCODE -ne 0) {
    throw "Portable ZIP creation failed with exit code $LASTEXITCODE."
}

Write-Host "Portable ZIP created at:"
Write-Host $Archive

$Hash = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
"$Hash  $([IO.Path]::GetFileName($Archive))" |
    Set-Content -LiteralPath $ChecksumFile -Encoding ascii
Write-Host "Checksum:"
Write-Host $ChecksumFile
