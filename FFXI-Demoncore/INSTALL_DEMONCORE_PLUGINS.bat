@echo off
REM Install cloned UE5 plugins into the demoncore project + enable in .uproject.
REM
REM Plugins handled here:
REM   - KawaiiPhysics       (jiggle / secondary motion — already cloned)
REM   - PythonScriptPlugin   (built-in, idempotent enable)
REM   - EditorScriptingUtilities (built-in, idempotent enable)
REM   - LiveLink             (built-in, virtual prod)
REM   - VirtualCamera        (built-in, phone-as-camera)
REM   - VPUtilities          (built-in, virtual prod camera tools)
REM   - Niagara              (built-in, effects)
REM   - Water                (built-in, water surfaces)
REM   - VolumetricCloud      (built-in, sky layer)
REM   - NNE                  (built-in, neural network engine for AI4Animation)
REM   - Bridge               (built-in, Megascans content)
REM   - SequencerScripting   (built-in, cutscene automation)
REM
REM This is idempotent — safe to re-run after cloning more plugins.

setlocal EnableExtensions EnableDelayedExpansion

set "PROJ_DIR=F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\demoncore"
set "PROJ=%PROJ_DIR%\demoncore.uproject"
set "DEST_PLUGINS=%PROJ_DIR%\Plugins"
set "REPOS=F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\repos"

echo.
echo === Demoncore plugin install ===
echo Project : %PROJ%
echo Plugins : %DEST_PLUGINS%
echo Repos   : %REPOS%
echo.

if not exist "%PROJ%" (
  echo [x] demoncore.uproject not found at %PROJ%
  pause & exit /b 1
)
if not exist "%DEST_PLUGINS%" mkdir "%DEST_PLUGINS%"

REM ---------------------------------------------------------------------------
REM 1. KawaiiPhysics — copy from cloned repo into demoncore/Plugins/
REM ---------------------------------------------------------------------------
echo [1/3] Wiring KawaiiPhysics...
set "KP_SRC=%REPOS%\_visual\KawaiiPhysics"
set "KP_DST=%DEST_PLUGINS%\KawaiiPhysics"

if exist "%KP_DST%\KawaiiPhysics.uplugin" (
  echo     [OK] Already installed at %KP_DST%
) else if exist "%KP_SRC%\KawaiiPhysics.uplugin" (
  echo     Copying %KP_SRC% -^> %KP_DST%
  xcopy /E /I /Q /Y "%KP_SRC%" "%KP_DST%" >NUL
  if errorlevel 1 (
    echo     [x] copy failed
    pause & exit /b 1
  )
  echo     [OK] Copied
) else if exist "%KP_SRC%" (
  REM Some KawaiiPhysics forks have the .uplugin nested in a Plugins/KawaiiPhysics/ subfolder
  for /f "delims=" %%P in ('dir /s /b "%KP_SRC%\KawaiiPhysics.uplugin" 2^>NUL') do (
    set "FOUND=%%~dpP"
    set "FOUND=!FOUND:~0,-1!"
    echo     Found nested at !FOUND!
    xcopy /E /I /Q /Y "!FOUND!" "%KP_DST%" >NUL
    goto :kp_done
  )
  echo     [WARN] %KP_SRC% exists but no KawaiiPhysics.uplugin found inside.
  echo            Clone the full plugin: git clone https://github.com/pafuhana1213/KawaiiPhysics %KP_SRC%
) else (
  echo     [SKIP] KawaiiPhysics not cloned yet at %KP_SRC%
  echo            Run:  git clone https://github.com/pafuhana1213/KawaiiPhysics %KP_SRC%
  echo            Then re-run this batch.
)
:kp_done

REM ---------------------------------------------------------------------------
REM 2. enable plugins in demoncore.uproject (single PowerShell pass, idempotent)
REM ---------------------------------------------------------------------------
echo.
echo [2/3] Enabling plugins in demoncore.uproject...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = '%PROJ%';" ^
  "$j = Get-Content $p -Raw | ConvertFrom-Json;" ^
  "if (-not $j.Plugins) { $j | Add-Member -NotePropertyName Plugins -NotePropertyValue @() };" ^
  "$want = @(" ^
  "  'PythonScriptPlugin','EditorScriptingUtilities','SequencerScripting'," ^
  "  'KawaiiPhysics'," ^
  "  'LiveLink','VirtualCamera','VPUtilities','Takes','Recorder'," ^
  "  'Niagara','Water','Bridge'," ^
  "  'NNE','NNERuntimeORTCpu','NNERuntimeRDG'" ^
  ");" ^
  "foreach ($name in $want) {" ^
  "  $existing = $j.Plugins | Where-Object { $_.Name -eq $name };" ^
  "  if (-not $existing) {" ^
  "    $j.Plugins += [PSCustomObject]@{ Name = $name; Enabled = $true };" ^
  "    Write-Host ('     + ' + $name)" ^
  "  } else {" ^
  "    $existing.Enabled = $true;" ^
  "    Write-Host ('     . already enabled ' + $name)" ^
  "  }" ^
  "}" ^
  "$j | ConvertTo-Json -Depth 10 | Set-Content $p -Encoding utf8;" ^
  "Write-Host ''; Write-Host ('Total plugins enabled: ' + $j.Plugins.Count)"

if errorlevel 1 (
  echo     [x] uproject update failed.
  pause & exit /b 1
)

REM ---------------------------------------------------------------------------
REM 3. summary
REM ---------------------------------------------------------------------------
echo.
echo [3/3] Summary
echo.
if exist "%KP_DST%\KawaiiPhysics.uplugin" echo     [READY]  KawaiiPhysics  ^(jiggle physics^)
echo     [READY]  PythonScriptPlugin
echo     [READY]  EditorScriptingUtilities
echo     [READY]  SequencerScripting     ^(cutscene automation^)
echo     [READY]  LiveLink + VirtualCamera + VPUtilities  ^(Mandalorian-style virtual prod^)
echo     [READY]  Niagara                 ^(effects^)
echo     [READY]  Water                   ^(water surfaces for Selbina/Mhaura/Rabao^)
echo     [READY]  Bridge                  ^(Megascans content^)
echo     [READY]  NNE + ORTCpu + RDG      ^(neural net engine — runs AI4Animation ONNX models^)
echo.
echo Next launch of UE5 will compile the new plugins ^(2-5 min^).
echo Then in the editor:
echo   - KawaiiPhysics anim node available in any AnimBP
echo   - LiveLink: Window - Live Link
echo   - Megascans: Window - Quixel Bridge
echo   - NNE: import .onnx -^> drag NNE node into a Blueprint
echo.
pause
endlocal
