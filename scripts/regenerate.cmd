@echo off
setlocal
set "scriptPath=%~dp0"
set "pythonScriptPath=%scriptPath%regenerate.ps1"
powershell -ExecutionPolicy Bypass -File "%pythonScriptPath%"
endlocal
