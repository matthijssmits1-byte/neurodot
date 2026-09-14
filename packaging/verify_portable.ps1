$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Executable = Join-Path $ProjectRoot "dist\Neurodot\Neurodot.exe"
$Report = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Neurodot\self_test.json"

if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Portable executable not found: $Executable"
}

$Process = Start-Process -FilePath $Executable -ArgumentList "--self-test" -Wait -PassThru -WindowStyle Hidden
if ($Process.ExitCode -ne 0) {
    throw "Portable self-test failed with exit code $($Process.ExitCode). See $Report"
}
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "Portable self-test did not produce its report: $Report"
}

$Result = Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
if ($Result.status -ne "passed") {
    throw "Portable self-test report status is '$($Result.status)'. See $Report"
}

Write-Host "Portable Neurodot self-test passed."
Write-Host "Report: $Report"

