@echo off
REM Clone the 4 upstream repos for FFXI Hardcore. Run via double-click from Explorer.
REM   - facebookresearch/ai4animationpy   (AI character animation, locomotion)
REM   - flopperam/unreal-engine-mcp        (MCP server that drives Unreal Engine)
REM   - xathei/Pathfinder                  (FFXI zone collision -> OBJ + navmesh)
REM   - LandSandBoat/FFXI-NavMesh-Builder  (LSB navmesh builder from collision data)

setlocal EnableExtensions
set "REPOS=F:\ffxi\hardcore\repos"
set "MANIFEST=F:\ffxi\hardcore\MANIFEST.md"

echo.
echo === FFXI Hardcore - cloning upstream repos ===
echo Target: %REPOS%
echo.

if not exist "%REPOS%" mkdir "%REPOS%"

REM --- step 1: nuke any partial / broken clones from a prior attempt ---------
echo [1/3] Cleaning any partial clones...
for %%R in (ai4animationpy unreal-engine-mcp Pathfinder FFXI-NavMesh-Builder) do (
  if exist "%REPOS%\%%R" (
    echo   removing stale %%R
    rmdir /s /q "%REPOS%\%%R"
  )
)

REM --- step 2: clone fresh, full history (not shallow - we may want history) -
echo.
echo [2/3] Cloning repos...

pushd "%REPOS%"

git clone https://github.com/facebookresearch/ai4animationpy.git
if errorlevel 1 echo   WARNING: ai4animationpy clone returned %ERRORLEVEL%

git clone https://github.com/flopperam/unreal-engine-mcp.git
if errorlevel 1 echo   WARNING: unreal-engine-mcp clone returned %ERRORLEVEL%

git clone https://github.com/xathei/Pathfinder.git
if errorlevel 1 echo   WARNING: Pathfinder clone returned %ERRORLEVEL%

git clone https://github.com/LandSandBoat/FFXI-NavMesh-Builder.git
if errorlevel 1 echo   WARNING: FFXI-NavMesh-Builder clone returned %ERRORLEVEL%

popd

REM --- step 3: write a MANIFEST.md capturing what we cloned + commit SHAs ----
echo.
echo [3/3] Writing manifest...

> "%MANIFEST%" echo # FFXI Hardcore - upstream manifest
>>"%MANIFEST%" echo.
>>"%MANIFEST%" echo Snapshot of which upstream repos and commits we engineered against.
>>"%MANIFEST%" echo Re-run `scripts\CLONE_REPOS.bat` to refresh.
>>"%MANIFEST%" echo.
>>"%MANIFEST%" echo Generated: %DATE% %TIME%
>>"%MANIFEST%" echo.
>>"%MANIFEST%" echo ^| Repo ^| URL ^| HEAD commit ^| Last upstream commit message ^|
>>"%MANIFEST%" echo ^|------^|-----^|-------------^|------------------------------^|

for %%R in (ai4animationpy unreal-engine-mcp Pathfinder FFXI-NavMesh-Builder) do (
  if exist "%REPOS%\%%R\.git" (
    pushd "%REPOS%\%%R"
    for /f "delims=" %%S in ('git rev-parse --short HEAD 2^>NUL') do set "SHA_%%R=%%S"
    for /f "tokens=2 delims=/" %%U in ('git config --get remote.origin.url 2^>NUL') do set "URL_%%R=%%U"
    for /f "delims=" %%M in ('git log -1 --pretty^=%%s 2^>NUL') do set "MSG_%%R=%%M"
    popd
  )
)

for %%R in (ai4animationpy unreal-engine-mcp Pathfinder FFXI-NavMesh-Builder) do (
  pushd "%REPOS%\%%R" 2>NUL
  if not errorlevel 1 (
    for /f "delims=" %%S in ('git rev-parse --short HEAD 2^>NUL') do set "S=%%S"
    for /f "delims=" %%U in ('git config --get remote.origin.url 2^>NUL') do set "U=%%U"
    for /f "delims=" %%M in ('git log -1 --pretty^=format:%%s 2^>NUL') do set "M=%%M"
    call :emit %%R "!S!" "!U!" "!M!"
    popd
  ) else (
    >>"%MANIFEST%" echo ^| %%R ^| (clone failed) ^| - ^| - ^|
  )
)

goto :postmanifest

:emit
>>"%MANIFEST%" echo ^| %~1 ^| %~3 ^| %~2 ^| %~4 ^|
exit /b 0

:postmanifest

echo.
echo === Done ===
echo.
echo Manifest:    %MANIFEST%
echo Repos at:    %REPOS%
echo.
dir "%REPOS%" /b
echo.
pause
endlocal
