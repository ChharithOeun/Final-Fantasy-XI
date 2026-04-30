@echo off
REM One-click Bastok Markets blockout runner.
REM
REM What it does:
REM   1. Closes any open UnrealEditor instance for the demoncore project (so the
REM      Python plugin enable + script copy can complete cleanly).
REM   2. Enables the Python Editor Script Plugin in demoncore.uproject (idempotent).
REM   3. Copies bastok_markets_blockout.py into the project's Content/Python folder
REM      (also creates the folder if missing) so it shows up in Tools - Execute
REM      Python Script... AND can be referenced by short path.
REM   4. Launches UnrealEditor with -ExecutePythonScript pointing at the script.
REM      UE5 boots, opens the demoncore project, then auto-runs the blockout —
REM      ~30 actors representing Bastok Markets pop into the level.
REM
REM Result: by the time the editor finishes loading, you can see the city block.

setlocal EnableExtensions EnableDelayedExpansion

set "UE=F:\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe"
set "PROJ_DIR=F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\demoncore"
set "PROJ=%PROJ_DIR%\demoncore.uproject"
set "STAGE_SCRIPT=%~dp0ue5_scripts\bastok_markets_blockout.py"
set "DEST_DIR=%PROJ_DIR%\Content\Python"
set "DEST_SCRIPT=%DEST_DIR%\bastok_markets_blockout.py"

echo.
echo === Bastok Markets Blockout Runner ===
echo.

REM --- preflight ---
if not exist "%UE%"           ( echo [x] UnrealEditor not found at %UE% & pause & exit /b 1 )
if not exist "%PROJ%"         ( echo [x] demoncore.uproject not found at %PROJ% & pause & exit /b 1 )
if not exist "%STAGE_SCRIPT%" ( echo [x] Source script missing: %STAGE_SCRIPT% & pause & exit /b 1 )

REM --- step 1: close any existing UnrealEditor with this project open ---
echo [1/4] Closing any existing UnrealEditor.exe (this project)...
tasklist /FI "IMAGENAME eq UnrealEditor.exe" | find /I "UnrealEditor.exe" >NUL
if not errorlevel 1 (
  echo     UnrealEditor is running. Forcing close so we can stage cleanly.
  taskkill /F /IM UnrealEditor.exe >NUL 2>&1
  REM small pause for handles to release
  ping 127.0.0.1 -n 3 >NUL
) else (
  echo     UnrealEditor not running — good.
)

REM --- step 2: enable Python Editor Script Plugin in the .uproject ---
echo.
echo [2/4] Enabling Python Editor Script Plugin in demoncore.uproject...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = '%PROJ%';" ^
  "$j = Get-Content $p -Raw | ConvertFrom-Json;" ^
  "if (-not $j.Plugins) { $j | Add-Member -NotePropertyName Plugins -NotePropertyValue @() };" ^
  "$want = @('PythonScriptPlugin','EditorScriptingUtilities');" ^
  "foreach ($name in $want) {" ^
  "  $existing = $j.Plugins | Where-Object { $_.Name -eq $name };" ^
  "  if (-not $existing) {" ^
  "    $j.Plugins += [PSCustomObject]@{ Name = $name; Enabled = $true };" ^
  "    Write-Host ('     + enabled ' + $name)" ^
  "  } else {" ^
  "    $existing.Enabled = $true;" ^
  "    Write-Host ('     . already enabled ' + $name)" ^
  "  }" ^
  "}" ^
  "$j | ConvertTo-Json -Depth 10 | Set-Content $p -Encoding utf8"

if errorlevel 1 (
  echo     [x] Failed to update demoncore.uproject. Aborting.
  pause
  exit /b 1
)

REM --- step 3: copy the blockout script into the project ---
echo.
echo [3/4] Copying script to %DEST_DIR%
if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"
copy /Y "%STAGE_SCRIPT%" "%DEST_SCRIPT%" >NUL
if errorlevel 1 (
  echo     [x] Copy failed. Aborting.
  pause
  exit /b 1
)
echo     Copied: %DEST_SCRIPT%

REM --- step 4: launch UE5 with the script auto-executed ---
echo.
echo [4/4] Launching UE5 with -ExecutePythonScript...
echo     This will take 30-60 seconds for shaders to compile on first run.
echo     When the editor finishes loading, ~30 actors will have spawned in
echo     your current level. Switch to the viewport — you should see the
echo     Bastok Markets blockout: walls, central elevator pillar, vendor
echo     stalls, shops, smokestack, forge.
echo.
echo     If your level is empty or you'd rather start fresh:
echo       File - New Level - Basic
echo     then run from inside the editor: Tools - Execute Python Script...
echo     and pick %DEST_SCRIPT%
echo.

start "" "%UE%" "%PROJ%" -ExecutePythonScript="%DEST_SCRIPT%"

echo === Launched. Watch UE5 boot — Bastok Markets will appear when ready. ===
endlocal
