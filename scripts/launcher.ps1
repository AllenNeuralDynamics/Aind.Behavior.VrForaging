$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path (Split-Path -Parent $scriptPath)
&uv run clabe run ./scripts/aind.py @args
