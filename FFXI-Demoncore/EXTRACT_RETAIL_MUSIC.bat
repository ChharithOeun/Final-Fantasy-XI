@echo off
REM Extract canonical FFXI music from the retail client.
REM
REM Per MUSIC_REMIX_PIPELINE.md. Sister batch to
REM EXTRACT_BASTOK_FROM_RETAIL.bat. Auto-installs POLUtils, walks every
REM BGW file in the ROM directories, converts to WAV. Output lands at
REM F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted\music_retail\
REM
REM Total expected output: ~150 WAV tracks across all FFXI expansions,
REM ~1 GB uncompressed audio. Tractable on any modern disk.

setlocal EnableExtensions EnableDelayedExpansion

set "FFXI_CLIENT=F:\ffxi\client\FINAL FANTASY XI"
set "TOOLS=F:\tools\polutils"
set "POLUTILS_EXE=%TOOLS%\POLUtils.exe"
set "POLUTILS_ZIP=%TOOLS%\polutils.zip"
set "POLUTILS_URL=https://sourceforge.net/projects/aspritise/files/POLUtils/POLUtils-1.5.0.zip/download"
set "OUT_BASE=F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted"
set "OUT=%OUT_BASE%\music_retail"

echo.
echo === FFXI Retail Music Extraction ===
echo Client : %FFXI_CLIENT%
echo Out    : %OUT%
echo.

REM --- preflight ---
if not exist "%FFXI_CLIENT%\FTABLE.DAT" (
  echo [x] Retail client not found at %FFXI_CLIENT%\
  pause & exit /b 1
)
if not exist "%OUT_BASE%" mkdir "%OUT_BASE%"
if not exist "%OUT%"      mkdir "%OUT%"
if not exist "%TOOLS%"    mkdir "%TOOLS%"

REM --- step 1: locate POLUtils ---
echo [1/4] Locating POLUtils...
if exist "%POLUTILS_EXE%" (
  echo     [OK] POLUtils already at %POLUTILS_EXE%
) else (
  echo     POLUtils not found. Downloading (~10 MB)...
  powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%POLUTILS_URL%' -OutFile '%POLUTILS_ZIP%' -UseBasicParsing } catch { Write-Host 'download failed: ' $_.Exception.Message; exit 1 }"
  if errorlevel 1 (
    echo     [x] Download failed.
    echo         Manually grab from: https://sourceforge.net/projects/aspritise/files/POLUtils/
    echo         Unzip into: %TOOLS%\
    pause & exit /b 1
  )
  powershell -NoProfile -Command "Expand-Archive -Force -Path '%POLUTILS_ZIP%' -DestinationPath '%TOOLS%'"
  REM Some POLUtils zips nest into a versioned subfolder
  if not exist "%POLUTILS_EXE%" (
    for /d %%D in ("%TOOLS%\POLUtils*") do (
      if exist "%%D\POLUtils.exe" xcopy /E /Y "%%D\*" "%TOOLS%\" >NUL
    )
  )
  if not exist "%POLUTILS_EXE%" (
    echo     [x] POLUtils.exe not found after extract. Check %TOOLS%
    pause & exit /b 1
  )
  echo     [OK] POLUtils installed
)

REM --- step 2: ensure CLI batch-extraction is available ---
echo.
echo [2/4] POLUtils CLI smoke test...
"%POLUTILS_EXE%" --help 2>NUL | findstr /I "music" >NUL
if errorlevel 1 (
  echo     [WARN] POLUtils CLI options unclear. Falling back to GUI mode.
  echo            In the GUI:
  echo              File - Open FFXI Folder - %FFXI_CLIENT%
  echo              Tools - Music Browser
  echo              Select all tracks - Right-click - Save All as WAV
  echo              Save to: %OUT%
  echo.
  echo     Press a key when extraction is done in the GUI.
  start "" "%POLUTILS_EXE%"
  pause
  goto :verify
)

REM --- step 3: CLI batch extraction (preferred path) ---
echo.
echo [3/4] Running POLUtils CLI music extraction...
echo     This typically takes 8-15 minutes for the full library.
"%POLUTILS_EXE%" --client "%FFXI_CLIENT%" --extract music --format wav --output "%OUT%"
if errorlevel 1 (
  echo     [WARN] CLI returned an error. Try the GUI fallback above.
  pause
)

:verify
REM --- step 4: verify outputs + write manifest ---
echo.
echo [4/4] Verifying outputs + writing manifest...

dir /b "%OUT%\*.wav" 2>NUL | find /c "" > "%TEMP%\__wavcount.txt"
set /p WAVCOUNT=<"%TEMP%\__wavcount.txt"

if "%WAVCOUNT%"=="0" (
  echo     [MISS] no WAV files in %OUT%\
  echo            Either CLI extraction failed or GUI step skipped.
  pause & exit /b 1
)

echo     [OK] %WAVCOUNT% music tracks extracted

REM Write a manifest.json the music_remix_pipeline can read
powershell -NoProfile -Command "$tracks = @(); Get-ChildItem '%OUT%\*.wav' | ForEach-Object { $tracks += @{ filename = $_.Name; size_bytes = $_.Length; track_id = $_.BaseName } }; @{ source = 'retail FFXI client extraction'; track_count = $tracks.Count; tracks = $tracks } | ConvertTo-Json -Depth 4 | Set-Content '%OUT%\manifest.json' -Encoding utf8"

echo     Manifest at: %OUT%\manifest.json

echo.
echo === Music extraction complete ===
echo.
echo Next steps:
echo   1. Define music_remix_targets.json catalog mapping tracks -> zones + variants
echo   2. (when YouTube reference lands) Update style_config in music_remix_targets.json
echo   3. Run python -m music_pipeline.remix_all (overnight job, ~3 weeks compute)
echo.
pause
endlocal
