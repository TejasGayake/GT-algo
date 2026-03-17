@echo off
title GT Trading - GitHub Setup
color 0A

echo ========================================
echo   GT Trading - GitHub Repository Setup
echo ========================================
echo.

REM Get the directory where this batch file is located
set "BATCH_DIR=%~dp0"
cd /d "%BATCH_DIR%"
echo Working directory: %cd%
echo.

REM Step 1: Fix the Project2 submodule issue
echo [93mStep 1: Fixing Project2 folder structure...[0m
git rm --cached Project2 2>nul
if exist "Project2\.git" (
    echo Removing nested git repository...
    rmdir /s /q "Project2\.git"
)
git add Project2/
echo [92m✓ Project2 folder fixed[0m
echo.

REM Step 2: Create .gitignore file
echo [93mStep 2: Creating .gitignore...[0m
(
echo # Python
echo __pycache__/
echo *.py[cod]
echo *.so
echo *.egg
echo *.egg-info/
echo dist/
echo build/
echo 
echo # Excel files
echo *.xlsx
echo *.xls
echo 
echo # VS Code
echo .vscode/
echo 
echo # Windows
echo Thumbs.db
echo desktop.ini
echo 
echo # Shortcuts
echo *.lnk
echo 
echo # Git
echo .git/
) > .gitignore
echo [92m✓ .gitignore created[0m
echo.

REM Step 3: Ask for GitHub repo name
set /p "REPO_NAME=Enter GitHub repository name (default: GT-Trading-Algo): "
if "%REPO_NAME%"=="" set "REPO_NAME=GT-Trading-Algo"

set /p "GITHUB_USER=Enter your GitHub username: "

echo.
echo Repository will be: https://github.com/%GITHUB_USER%/%REPO_NAME%
echo.
echo Choose visibility:
echo 1. Public
echo 2. Private
set /p "VISIBILITY=Enter choice (1 or 2): "

if "%VISIBILITY%"=="1" (
    set "VISIBILITY_FLAG=--public"
) else (
    set "VISIBILITY_FLAG=--private"
)

echo.
echo [93mStep 3: Creating repository on GitHub...[0m
echo You may be prompted to login to GitHub.
echo.

REM Try to create repo using GitHub CLI if available
gh repo create "%REPO_NAME%" %VISIBILITY_FLAG% --source=. --remote=origin --push 2>nul

if errorlevel 1 (
    echo [93mGitHub CLI not available or failed. Using manual method...[0m
    echo.
    echo [93mPlease follow these steps:[0m
    echo 1. Go to https://github.com/new
    echo 2. Repository name: %REPO_NAME%
    echo 3. Choose %VISIBILITY_FLAG:~1% (without --)
    echo 4. DO NOT initialize with README
    echo 5. Click "Create repository"
    echo.
    pause
    
    REM Remove old remote
    git remote remove origin 2>nul
    
    REM Add new remote
    git remote add origin https://github.com/%GITHUB_USER%/%REPO_NAME%.git
    
    REM Push to GitHub
    echo.
    echo [93mStep 4: Pushing to GitHub...[0m
    git branch -M main
    git push -u origin main --force
) else (
    echo [92m✓ Repository created and code pushed via GitHub CLI[0m
)

if errorlevel 1 (
    echo [91mFailed to push to GitHub![0m
    echo.
    echo Troubleshooting:
    echo - Make sure your repository exists: https://github.com/%GITHUB_USER%/%REPO_NAME%
    echo - Check your internet connection
    echo - Try pushing manually: git push -u origin main --force
) else (
    echo.
    echo [92m========================================[0m
    echo [92m✅ Setup Complete![0m
    echo [92m========================================[0m
    echo.
    echo Repository: https://github.com/%GITHUB_USER%/%REPO_NAME%
)

echo.
echo Window will close in 10 seconds...
timeout /t 10 /nobreak >nul