$scriptPath = $MyInvocation.MyCommand.Path
$scriptDirectory = Split-Path -Parent $scriptPath
Set-Location (Split-Path -Parent $scriptDirectory)

Write-Output "Initializing and updating submodules..."
&git submodule update --init --recursive

Write-Output "Creating a Python  environment..."

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "The 'uv' command was not found. See https://docs.astral.sh/uv/getting-started/installation/ for instructions."
}

if (Test-Path -Path ./.venv) {
    Remove-Item ./.venv -Recurse -Force
}
&uv venv
.\.venv\Scripts\Activate.ps1
Write-Output "Synchronizing environment..."
&uv sync --extra launcher
Write-Output "Creating a Bonsai environment and installing packages..."
if (Test-Path -Path "bonsai") {
    Set-Location "bonsai"
    .\setup.ps1
} elseif (Test-Path -Path ".bonsai") {
    Set-Location ".bonsai"
    .\setup.ps1
} else {
    throw "Neither 'bonsai' nor '.bonsai' directory found."
}
Set-Location ..