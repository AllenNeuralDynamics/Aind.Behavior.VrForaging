$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path (Split-Path -Parent $scriptPath)
.\.venv\Scripts\Activate.ps1
& clabe