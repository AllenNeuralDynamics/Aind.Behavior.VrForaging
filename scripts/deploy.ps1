Write-Output "Creating a Python environment..."
if (Test-Path -Path ./.venv) {
    Remove-Item ./.venv -Recurse -Force
}
&python -m venv ./.venv
.\.venv\Scripts\Activate.ps1
Write-Output "Installing python packages..."
&pip install .
Write-Output "Creating a Bonsai environment and installing packages..."
cd "bonsai"
.\setup.ps1