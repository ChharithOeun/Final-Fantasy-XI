@echo off
REM Init F:\ffxi\hardcore as a git repo, create the GitHub remote
REM ChharithOeun/FFXI-Hardcore (public), and push the scaffold.
REM
REM Requires: gh CLI logged in (already set up on this box for the
REH mcp-graphify-autotrigger workflow).

setlocal EnableExtensions
set "ROOT=F:\ffxi\hardcore"
set "REMOTE=ChharithOeun/FFXI-Hardcore"

echo.
echo === Publishing FFXI Hardcore scaffold to GitHub ===
echo Local : %ROOT%
echo Remote: %REMOTE%
echo.

pushd "%ROOT%"

if not exist ".git" (
  echo [1/5] git init...
  git init -b main
) else (
  echo [1/5] git already initialized.
)

echo.
echo [2/5] Configuring local identity (chharith@gmail.com)...
git config user.email "chharith@gmail.com"
git config user.name "Chharith Oeun"

echo.
echo [3/5] Staging files (respecting .gitignore)...
git add .

git diff --cached --quiet
if %errorlevel% EQU 0 (
  echo Nothing to commit. Tree already published.
  goto :remote
)

echo.
echo [4/5] Initial commit...
git commit -m "feat: scaffold FFXI Hardcore - vision, architecture, upstream manifest"

:remote
echo.
echo [5/5] Creating / updating remote...

git remote get-url origin >NUL 2>&1
if errorlevel 1 (
  echo   creating GitHub repo %REMOTE% via gh...
  gh repo create %REMOTE% --public --source=. --remote=origin --description "AI-engineered HD/4K remake of Final Fantasy XI on top of LandSandBoat + Unreal Engine 5"
  if errorlevel 1 (
    echo gh repo create failed. Trying manual remote add against an existing repo...
    git remote add origin https://github.com/%REMOTE%.git
  )
) else (
  echo   origin already configured.
)

echo.
echo Pushing main...
git push -u origin main

popd

echo.
echo === Done ===
echo Repo: https://github.com/%REMOTE%
echo.
pause
endlocal
