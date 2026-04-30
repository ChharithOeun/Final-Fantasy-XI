@echo off
REM Extract canonical FFXI sound effects from the retail client.
REM
REM Per SFX_PIPELINE.md. Sister batch to EXTRACT_RETAIL_MUSIC.bat.
REM Auto-installs POLUtils, walks every .SE2 / .SPW file in the
REM retail ROM directories, converts to WAV, organizes into category
REM subfolders. Output to:
REM   F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted\sfx_retail\
REM
REM Total expected output: ~3000-4000 SFX files across all FFXI
REM expansions, ~3 GB uncompressed audio. Categories:
REM   spells/         (Fire, Cure, Banish, Drain etc — preserve canonical)
REM   weapon_skills/  (Crescent Moon, Asuran Fists, Hexa Strike etc)
REM   footsteps/      (per surface × per race)
REM   ambient/        (city beds, dungeon ambience, weather)
REM   ui/             (tab clicks, menu chimes, item-use sounds)
REM   combat_impacts/ (sword-on-flesh thuds, spell impact crackles)
REM   voice_lines/    (mob voice barks, NPC speech samples)

setlocal EnableExtensions EnableDelayedExpansion

set "FFXI_CLIENT=F:\ffxi\client\FINAL FANTASY XI"
set "TOOLS=F:\tools\polutils"
set "POLUTILS_EXE=%TOOLS%\POLUtils.exe"
set "OUT_BASE=F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted"
set "OUT=%OUT_BASE%\sfx_retail"

echo.
echo === FFXI Retail SFX Extraction ===
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

REM Pre-create category subfolders so POLUtils CLI can drop files in
for %%C in (spells weapon_skills footsteps ambient ui combat_impacts voice_lines) do (
  if not exist "%OUT%\%%C" mkdir "%OUT%\%%C"
)

REM --- step 1: ensure POLUtils is present ---
echo [1/4] Locating POLUtils...
if not exist "%POLUTILS_EXE%" (
  echo     POLUtils not found. Run EXTRACT_RETAIL_MUSIC.bat first
  echo     ^(it auto-installs POLUtils into %TOOLS%^).
  echo     Or download manually from:
  echo       https://sourceforge.net/projects/aspritise/files/POLUtils/
  pause & exit /b 1
)
echo     [OK] POLUtils at %POLUTILS_EXE%

REM --- step 2: CLI extraction (preferred path) ---
echo.
echo [2/4] POLUtils CLI SFX extraction...
"%POLUTILS_EXE%" --help 2>NUL | findstr /I "sound" >NUL
if errorlevel 1 (
  echo     [WARN] POLUtils CLI options unclear. Falling back to GUI mode.
  echo            In the GUI:
  echo              File - Open FFXI Folder - %FFXI_CLIENT%
  echo              Tools - Sound Browser
  echo              Filter by category, save batches per category subfolder above
  echo.
  echo     Press a key when extraction is done.
  start "" "%POLUTILS_EXE%"
  pause
  goto :verify
)

echo     This typically takes 20-40 minutes for the full library.
"%POLUTILS_EXE%" --client "%FFXI_CLIENT%" --extract sfx --format wav --output "%OUT%" --categorize
if errorlevel 1 (
  echo     [WARN] CLI returned an error. Try the GUI fallback above.
  pause
)

:verify
REM --- step 3: organize + count ---
echo.
echo [3/4] Counting + categorizing extracted files...
set /a TOTAL=0
for %%C in (spells weapon_skills footsteps ambient ui combat_impacts voice_lines) do (
  dir /b "%OUT%\%%C\*.wav" 2>NUL | find /c "" > "%TEMP%\__sfxc.txt"
  set /p N=<"%TEMP%\__sfxc.txt"
  set /a TOTAL+=!N!
  echo     %%C: !N! files
)

if %TOTAL%==0 (
  echo     [MISS] no WAV files found in any category folder
  echo            Try the GUI extraction path or check POLUtils version
  pause & exit /b 1
)

echo.
echo     Total extracted: %TOTAL% SFX files

REM --- step 4: write manifest ---
echo.
echo [4/4] Writing manifest...
powershell -NoProfile -Command "$assets = @(); foreach ($cat in 'spells','weapon_skills','footsteps','ambient','ui','combat_impacts','voice_lines') { Get-ChildItem \"%OUT%\$cat\*.wav\" -ErrorAction SilentlyContinue | ForEach-Object { $assets += @{ asset_id = ($cat + '/' + $_.BaseName); category = $cat; filename = $_.Name; size_bytes = $_.Length } } }; @{ source = 'retail FFXI client extraction'; asset_count = $assets.Count; assets = $assets } | ConvertTo-Json -Depth 4 | Set-Content '%OUT%\manifest.json' -Encoding utf8"

echo     Manifest at: %OUT%\manifest.json

echo.
echo === SFX extraction complete ===
echo.
echo Next steps:
echo   1. python -m sfx_pipeline.upscale_all
echo      ^(runs Class 1+2 HD upscale on all extracted assets;
echo       takes ~2-4 hours of GPU time on a 4090^)
echo   2. python -m sfx_pipeline.author_new_mechanic_sounds
echo      ^(generates Class 3 authored sounds via prompts^)
echo   3. python -m sfx_pipeline.generate_variations
echo      ^(produces Class 4 variation sets for footsteps + hits^)
echo.
pause
endlocal
