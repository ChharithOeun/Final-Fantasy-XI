@echo off
REM Verify Visual Studio 2022 install completed and the UE5 C++ workloads landed.

setlocal EnableExtensions
set "VS_DIR=C:\Program Files\Microsoft Visual Studio\2022\Community"
set "VSWHERE=C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"

echo.
echo === VS2022 install verification ===
echo.

REM 1. directory present?
if exist "%VS_DIR%" (
  echo [OK]    VS2022 Community dir found:  %VS_DIR%
) else (
  echo [MISS]  VS2022 Community dir not yet at %VS_DIR%
  echo         Install may still be running. Look for a 'Visual Studio Installer' window
  echo         in the taskbar, or check Task Manager for 'setup.exe' / 'vs_installer.exe'.
  goto :installer_check
)

REM 2. is the installer process still going?
:installer_check
echo.
tasklist /FI "IMAGENAME eq setup.exe" 2>NUL | find /I "setup.exe" >NUL && (
  echo [...]   setup.exe is still running — install in progress.
)
tasklist /FI "IMAGENAME eq vs_installer.exe" 2>NUL | find /I "vs_installer.exe" >NUL && (
  echo [...]   vs_installer.exe is still running — install in progress.
)
tasklist /FI "IMAGENAME eq vs_installershell.exe" 2>NUL | find /I "vs_installershell.exe" >NUL && (
  echo [...]   vs_installershell.exe is still running — install in progress.
)

REM 3. workload report via vswhere
echo.
if exist "%VSWHERE%" (
  echo [3] Installed workloads via vswhere:
  "%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Workload.NativeGame   -property displayName  >NUL 2>&1 && echo     [OK] Game development with C++ ^(NativeGame^)         || echo     [MISS] NativeGame
  "%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Workload.NativeDesktop -property displayName  >NUL 2>&1 && echo     [OK] Desktop development with C++ ^(NativeDesktop^)   || echo     [MISS] NativeDesktop
  "%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.UnrealEngine -property displayName  >NUL 2>&1 && echo     [OK] Unreal Engine integration                       || echo     [MISS] UnrealEngine
  "%VSWHERE%" -latest -products * -requires Microsoft.Net.Component.4.6.2.TargetingPack   -property displayName  >NUL 2>&1 && echo     [OK] .NET Framework 4.6.2 targeting pack             || echo     [MISS] .NET 4.6.2 TargetingPack
  "%VSWHERE%" -latest -products * -requires Microsoft.NetCore.Component.SDK              -property displayName  >NUL 2>&1 && echo     [OK] .NET SDK                                        || echo     [MISS] .NET SDK
) else (
  echo [3] vswhere.exe not at expected path — VS installer not yet bootstrapped.
)

REM 4. NetFXSDK presence is the actual gate UE5 hits when compiling C++
echo.
echo [4] NetFXSDK ^(the file UE5's SwarmInterface complains about^):
set "NETFXFOUND="
for %%P in (
  "C:\Program Files (x86)\Windows Kits\NETFXSDK\4.6.2"
  "C:\Program Files (x86)\Windows Kits\NETFXSDK\4.7.2"
  "C:\Program Files (x86)\Windows Kits\NETFXSDK\4.8"
  "C:\Program Files (x86)\Windows Kits\NETFXSDK\4.8.1"
) do (
  if exist %%P (
    echo     [OK] %%P
    set "NETFXFOUND=1"
  )
)
if not defined NETFXFOUND echo     [MISS] no NETFXSDK install found yet

echo.
echo === Summary ===
if exist "%VS_DIR%" (
  if defined NETFXFOUND (
    echo VS2022 looks ready. UE5 C++ projects should compile.
    echo Try: open demoncore in UE5 → File → New C++ Class → Empty → Compile.
  ) else (
    echo VS2022 dir is here but NETFXSDK is missing. The installer may still be
    echo running, or .NET 4.6.2 TargetingPack didn't get checked. Re-run
    echo INSTALL_VS2022.bat with the --add Microsoft.Net.Component.4.6.2.TargetingPack
    echo line if needed.
  )
) else (
  echo VS2022 not installed yet. Either it's still running, or the installer
  echo bailed early. Check the Visual Studio Installer window for status.
)

echo.
pause
endlocal
