param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RequiredFiles = @(
    "resources\models\cpsam_v2",
    "resources\templates\donor_1_point_each_with_to.ims",
    "resources\graphics\Icon.png",
    "resources\graphics\Icon.ico"
)

if (Test-Path -LiteralPath $PythonExe -PathType Leaf) {
    $PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path
}
else {
    $PythonCommand = Get-Command $PythonExe -ErrorAction SilentlyContinue
    if ($null -eq $PythonCommand) {
        throw "Python interpreter not found: $PythonExe"
    }
    $PythonExe = $PythonCommand.Source
}

foreach ($RelativePath in $RequiredFiles) {
    $Resolved = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $Resolved -PathType Leaf)) {
        throw "Required release resource is missing: $Resolved"
    }
}

Push-Location $ProjectRoot
try {
    & $PythonExe -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath (Join-Path $ProjectRoot "dist") `
        --workpath (Join-Path $ProjectRoot "build") `
        (Join-Path $ProjectRoot "packaging\neurodot.spec")
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$Executable = Join-Path $ProjectRoot "dist\Neurodot\Neurodot.exe"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Portable executable was not produced: $Executable"
}

Write-Host "Portable Neurodot build created at:"
Write-Host (Split-Path -Parent $Executable)
