@echo off
REM Upscale every extracted Bastok Markets texture 4x with Real-ESRGAN.
REM
REM Uses realesrgan-ncnn-vulkan — a single-binary, GPU-agnostic upscaler.
REM Works on AMD GPUs via Vulkan (the user's RX 7000-series), no DirectML
REM or CUDA required. ~1 second per 256x256 -> 1024x1024 texture.
REM
REM Inputs : F:\ChharithOeun\...\extracted\bastok_markets\textures\*.png
REM Outputs: F:\ChharithOeun\...\extracted\bastok_markets\textures_4k\*.png
REM
REM Same filename, same UV layout. UE5 just sees higher-res versions.

setlocal EnableExtensions EnableDelayedExpansion

set "ZONE_NAME=bastok_markets"
set "OUT_BASE=F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted"
set "IN=%OUT_BASE%\%ZONE_NAME%\textures"
set "OUT=%OUT_BASE%\%ZONE_NAME%\textures_4k"
set "TOOLS=F:\tools\realesrgan"
set "ESRGAN=%TOOLS%\realesrgan-ncnn-vulkan.exe"
set "ESRGAN_ZIP=%TOOLS%\realesrgan.zip"
set "ESRGAN_URL=https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
set "MODEL=realesrgan-x4plus"

echo.
echo === Bastok Markets texture upscale (Real-ESRGAN x4) ===
echo In  : %IN%
echo Out : %OUT%
echo.

if not exist "%IN%" (
  echo [x] No extracted textures at %IN%
  echo     Run EXTRACT_BASTOK_FROM_RETAIL.bat first.
  pause & exit /b 1
)
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%TOOLS%" mkdir "%TOOLS%"

REM --- step 1: Real-ESRGAN binary ---
echo [1/2] Locating Real-ESRGAN ncnn-vulkan...
if exist "%ESRGAN%" (
  echo     [OK] Already at %ESRGAN%
) else (
  echo     Downloading (~50 MB)...
  powershell -NoProfile -Command "Invoke-WebRequest -Uri '%ESRGAN_URL%' -OutFile '%ESRGAN_ZIP%' -UseBasicParsing"
  if errorlevel 1 (
    echo     [x] Download failed.
    echo         Manually grab from: https://github.com/xinntao/Real-ESRGAN/releases
    echo         Pick the *-windows.zip, extract to %TOOLS%
    pause & exit /b 1
  )
  powershell -NoProfile -Command "Expand-Archive -Force -Path '%ESRGAN_ZIP%' -DestinationPath '%TOOLS%'"
  REM Some zips nest into a versioned subfolder
  if not exist "%ESRGAN%" (
    for /d %%D in ("%TOOLS%\realesrgan*") do (
      if exist "%%D\realesrgan-ncnn-vulkan.exe" xcopy /E /Y "%%D\*" "%TOOLS%\" >NUL
    )
  )
  if not exist "%ESRGAN%" (
    echo     [x] realesrgan-ncnn-vulkan.exe not found after extract. Check %TOOLS%
    pause & exit /b 1
  )
  echo     [OK] Real-ESRGAN installed
)

REM --- step 2: walk the textures directory ---
echo.
echo [2/2] Upscaling textures...
set /a TOTAL=0
set /a OK=0
set /a FAIL=0
for %%F in ("%IN%\*.png") do (
  set /a TOTAL+=1
  echo     [!TOTAL!] %%~nxF  -^>  4K
  "%ESRGAN%" -i "%%F" -o "%OUT%\%%~nxF" -n %MODEL% -s 4 -f png 2>NUL
  if exist "%OUT%\%%~nxF" (
    set /a OK+=1
  ) else (
    set /a FAIL+=1
    echo         [WARN] failed
  )
)

echo.
echo === Upscale complete ===
echo Total : %TOTAL%
echo OK    : %OK%
echo Fail  : %FAIL%
echo.
echo Output: %OUT%
echo.
echo Next step: open UE5 and run bastok_import_extracted.py via
echo            Tools - Execute Python Script... to import the .fbx + 4K
echo            textures into the demoncore project.
echo.
pause
endlocal
