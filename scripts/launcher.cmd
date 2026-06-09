@echo off
setlocal
set "scriptPath=%~dp0"
set "repoPath=%scriptPath%.."
set "launcherPath=%scriptPath%launcher.ps1"
where wt.exe >nul 2>&1
if %errorlevel% == 0 (
    wt.exe -d "%repoPath%" powershell -ExecutionPolicy Bypass -File "%launcherPath%"
) else (
    powershell -ExecutionPolicy Bypass -File "%launcherPath%"
)
endlocal
exit
