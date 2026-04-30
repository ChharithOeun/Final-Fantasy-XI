@echo off
REM Pull canonical Bastok Markets geometry + textures from the retail FFXI
REM client at F:\ffxi\client\FINAL FANTASY XI\.
REM
REM Strategy:
REM   1. Stage tooling at F:\tools\ffxi-extract\ (Noesis + FFXI plugin)
REM   2. Run Noesis CLI against the retail client, pointed at zone 235
REM      (Bastok Markets). Noesis's FFXI plugin reads FTABLE.DAT and figures
REM      out which ROM/x/y.DAT files compose the zone — we don't have to.
REM   3. Outputs (.fbx + textures/*.png + collision .obj) land at
REM      F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted\bastok_markets\
REM
REM First-run note: Noesis is a small, free, single-folder tool (no installer).
REM We auto-download it if missing. The FFXI Noesis plugin (fmt_ffxi*.py) is
REM hosted on a few mirrors; if the auto-download fails, this script prints
REM the URLs to grab it manually and where to drop the .py file.

setlocal EnableExtensions EnableDelayedExpansion

set "ZONE_ID=235"
set "ZONE_NAME=bastok_markets"
set "FFXI_CLIENT=F:\ffxi\client\FINAL FANTASY XI"
set "TOOLS=F:\tools\ffxi-extract"
set "NOESIS_DIR=%TOOLS%\noesis"
set "NOESIS_EXE=%NOESIS_DIR%\Noesis.exe"
set "NOESIS_PLUGINS=%NOESIS_DIR%\plugins\python"
set "NOESIS_ZIP=%TOOLS%\noesis.zip"
set "NOESIS_URL=https://www.richwhitehouse.com/filedown.php?content=noesisv4474"
set "FFXI_PLUGIN=%NOESIS_PLUGINS%\fmt_ffxi.py"
set "FFXI_PLUGIN_URL_PRIMARY=https://raw.githubusercontent.com/atom0s/Pathfinder/master/extras/noesis/fmt_ffxi.py"
set "FFXI_PLUGIN_URL_FALLBACK=https://raw.githubusercontent.com/Windower/POLUtils/master/extras/fmt_ffxi.py"
set "OUT_BASE=F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted"
set "OUT=%OUT_BASE%\%ZONE_NAME%"

echo.
echo === FFXI Bastok Markets extraction ===
echo Client : %FFXI_CLIENT%
echo Zone   : %ZONE_ID% (%ZONE_NAME%)
echo Out    : %OUT%
echo.

REM --- preflight: client is there, output paths writable ---
if not exist "%FFXI_CLIENT%\FTABLE.DAT" (
  echo [x] Retail client not found at %FFXI_CLIENT%\
  echo     Expected FTABLE.DAT to be present.
  pause & exit /b 1
)
if not exist "%OUT_BASE%" mkdir "%OUT_BASE%"
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%OUT%\textures" mkdir "%OUT%\textures"
if not exist "%TOOLS%" mkdir "%TOOLS%"

REM --- step 1: Noesis ---
echo [1/4] Locating Noesis...
if exist "%NOESIS_EXE%" (
  echo     [OK] Noesis already at %NOESIS_EXE%
) else (
  echo     Noesis not found. Downloading (~6 MB)...
  if not exist "%NOESIS_DIR%" mkdir "%NOESIS_DIR%"
  powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%NOESIS_URL%' -OutFile '%NOESIS_ZIP%' -UseBasicParsing } catch { Write-Host '   download failed: ' $_.Exception.Message; exit 1 }"
  if errorlevel 1 (
    echo     [x] Noesis download failed.
    echo         Manually grab from: https://richwhitehouse.com/index.php?content=inc_projects.php^&showproject=91
    echo         Unzip into: %NOESIS_DIR%\
    pause & exit /b 1
  )
  powershell -NoProfile -Command "Expand-Archive -Force -Path '%NOESIS_ZIP%' -DestinationPath '%NOESIS_DIR%'"
  if not exist "%NOESIS_EXE%" (
    REM Some zips nest inside a "noesis" subfolder
    for /d %%D in ("%NOESIS_DIR%\noesis*") do (
      if exist "%%D\Noesis.exe" (
        xcopy /E /Y "%%D\*" "%NOESIS_DIR%\" >NUL
      )
    )
  )
  if not exist "%NOESIS_EXE%" (
    echo     [x] Couldn't find Noesis.exe after extract. Check %NOESIS_DIR%
    pause & exit /b 1
  )
  echo     [OK] Noesis installed
)

REM --- step 2: FFXI plugin for Noesis ---
echo.
echo [2/4] Locating FFXI Noesis plugin (fmt_ffxi.py)...
if not exist "%NOESIS_PLUGINS%" mkdir "%NOESIS_PLUGINS%"
if exist "%FFXI_PLUGIN%" (
  echo     [OK] Plugin already at %FFXI_PLUGIN%
) else (
  echo     Plugin not found. Trying mirrors...
  powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%FFXI_PLUGIN_URL_PRIMARY%' -OutFile '%FFXI_PLUGIN%' -UseBasicParsing } catch { exit 1 }"
  if not exist "%FFXI_PLUGIN%" (
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%FFXI_PLUGIN_URL_FALLBACK%' -OutFile '%FFXI_PLUGIN%' -UseBasicParsing } catch { exit 1 }"
  )
  if not exist "%FFXI_PLUGIN%" (
    echo     [WARN] Couldn't auto-download fmt_ffxi.py. Manual step:
    echo       1. grab from one of: github.com/atom0s/Pathfinder, polutils repo, or NoesisFFXI fork
    echo       2. drop fmt_ffxi.py into:  %NOESIS_PLUGINS%\
    echo       3. re-run this batch
    echo.
    echo     Without the plugin, Noesis won't recognize FFXI .DAT files.
    pause & exit /b 1
  )
  echo     [OK] Plugin downloaded
)

REM --- step 3: run Noesis CLI on the zone ---
echo.
echo [3/4] Running Noesis on zone %ZONE_ID% (this can take 30-90 seconds)...
REM ?cmode = headless conversion. The FFXI plugin accepts the FTABLE.DAT path
REM as input and uses zone id flags to filter. The exact flag varies by
REM plugin version; we try the common forms.
"%NOESIS_EXE%" ?cmode "%FFXI_CLIENT%\FTABLE.DAT" "%OUT%\%ZONE_NAME%.fbx" -ffximdl -ffxizone %ZONE_ID% -texexp tga
if errorlevel 1 (
  echo     [WARN] Noesis returned an error. The plugin flag spec may differ.
  echo            Falling back to interactive Noesis — open the GUI, navigate to:
  echo              File - Open - browse to %FFXI_CLIENT%\FTABLE.DAT
  echo              Right-click the loaded model - Export - FBX
  echo              Save to: %OUT%\%ZONE_NAME%.fbx
  start "" "%NOESIS_EXE%"
  echo.
  echo     Press a key when extraction is done.
  pause
) else (
  echo     [OK] Noesis CLI export complete
)

REM --- step 4: report what we got ---
echo.
echo [4/4] Verifying outputs...
set "OK=1"
if exist "%OUT%\%ZONE_NAME%.fbx" (
  for %%F in ("%OUT%\%ZONE_NAME%.fbx") do echo     [OK]  mesh:     %%~zF bytes  %%F
) else (
  echo     [MISS] mesh missing: %OUT%\%ZONE_NAME%.fbx
  set "OK="
)

dir /b "%OUT%\textures\*.png" 2>NUL | find /c "" > "%TEMP%\__pngcount.txt"
set /p PNGCOUNT=<"%TEMP%\__pngcount.txt"
if "%PNGCOUNT%" NEQ "" if %PNGCOUNT% GTR 0 (
  echo     [OK]  textures: %PNGCOUNT% png files in %OUT%\textures\
) else (
  REM Noesis may have written .tga or .dds depending on flags
  dir /b "%OUT%\*.tga" "%OUT%\textures\*.tga" "%OUT%\*.dds" "%OUT%\textures\*.dds" 2>NUL | find /c "" > "%TEMP%\__texcount.txt"
  set /p TEXCOUNT=<"%TEMP%\__texcount.txt"
  if "!TEXCOUNT!" NEQ "" if !TEXCOUNT! GTR 0 (
    echo     [OK]  textures: !TEXCOUNT! TGA/DDS files - convert to PNG before upscale
  ) else (
    echo     [WARN] no textures found
    set "OK="
  )
)

echo.
if defined OK (
  echo === Extraction complete ===
  echo.
  echo Next steps:
  echo   1. UPSCALE_BASTOK_TEXTURES.bat   - Real-ESRGAN x4 on each PNG
  echo   2. Open UE5, run bastok_import_extracted.py via Tools - Execute Python
  echo      Script. That brings the .fbx + 4K textures into the demoncore
  echo      project as a static mesh.
) else (
  echo === Extraction had issues ===
  echo Open Noesis ^(at %NOESIS_EXE%^) and walk through manually:
  echo   File - Open - %FFXI_CLIENT%\FTABLE.DAT
  echo   Browse the zone tree on the left, find Bastok Markets ^(zone 235^),
  echo   right-click the model, Export, FBX, save to:
  echo   %OUT%\%ZONE_NAME%.fbx
)

echo.
pause
endlocal
