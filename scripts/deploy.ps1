$scriptPath = $MyInvocation.MyCommand.Path
$scriptDirectory = Split-Path -Parent $scriptPath
Set-Location (Split-Path -Parent $scriptDirectory)
Write-Output "Creating a Python environment..."
if (Test-Path -Path ./.venv) {
    Remove-Item ./.venv -Recurse -Force
}
&python -m venv ./.venv
.\.venv\Scripts\Activate.ps1
Write-Output "Installing python packages..."
&pip install .
Write-Output "Creating a Bonsai environment and installing packages..."
Set-Location "bonsai"
.\setup.ps1
Set-Location ..