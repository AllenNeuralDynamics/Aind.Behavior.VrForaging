@echo off
setlocal
set "scriptPath=%~dp0"
set "launcherPath=%scriptPath%launcher.ps1"
powershell -ExecutionPolicy Bypass -File "%launcherPath%"
endlocal
