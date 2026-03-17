@echo off
echo ========================================
echo   Create New GitHub Repository
echo ========================================
echo.

REM Set variables
set "REPO_NAME=GT-Trading-Algo"
set "GITHUB_USER=TejasGayake"
set "REPO_PATH=G:\mnt\algo"

echo This will create a new repository: %GITHUB_USER%/%REPO_NAME%
echo.
echo Choose repository visibility:
echo 1. Public
echo 2. Private
echo.
set /p "VISIBILITY=Enter choice (1 or 2): "

if "%VISIBILITY%"=="1" (
    set "PRIVATE=false"
) else (
    set "PRIVATE=true"
)

echo.
echo Creating repository on GitHub...
echo.

REM Create repository using GitHub API
curl -u "%GITHUB_USER%" https://api.github.com/user/repos -d "{\"name\":\"%REPO_NAME%\", \"private\":%PRIVATE%}"

if errorlevel 1 (
    echo [91mFailed to create repository![0m
    echo Please check your GitHub username and password/token.
    pause
    exit /b 1
)

echo.
echo [92mRepository created successfully![0m
echo.

REM Navigate to repo path
cd /d "%REPO_PATH%"

REM Remove existing remote if any
git remote remove origin 2>nul

REM Add new remote
git remote add origin https://github.com/%GITHUB_USER%/%REPO_NAME%.git

REM Push to new repository
echo Pushing to new repository...
git branch -M main
git push -u origin main --force

echo.
echo [92mDone! Repository created and code pushed.[0m
echo https://github.com/%GITHUB_USER%/%REPO_NAME%
echo.
pause
