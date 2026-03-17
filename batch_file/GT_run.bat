@echo off
title GT Trading - Created for Mayur
color 0A

echo ========================================
echo      GT Trading - Created for Mayur
echo ========================================
echo.

REM Get the directory where this batch file is located
set "BATCH_DIR=%~dp0"
set "BATCH_DIR=%BATCH_DIR:~0,-1%"  REM Remove trailing backslash

echo Batch file location: %BATCH_DIR%
echo.

REM Try to find Project2 folder using multiple methods
set "PROJECT2_PATH="
set "FOUND=0"

REM Method 1: Check if Project2 is in the same directory as batch_file's parent (algo/Project2)
if exist "%BATCH_DIR%\..\Project2\run.py" (
    set "PROJECT2_PATH=%BATCH_DIR%\..\Project2"
    set "FOUND=1"
    echo [92mMethod 1: Found Project2 in parent directory[0m
    goto :execute
)

REM Method 2: Check if Project2 is in the same directory as the batch file
if %FOUND%==0 if exist "%BATCH_DIR%\Project2\run.py" (
    set "PROJECT2_PATH=%BATCH_DIR%\Project2"
    set "FOUND=1"
    echo [92mMethod 2: Found Project2 in same directory[0m
    goto :execute
)

REM Method 3: Search for Project2 folder in parent directory
if %FOUND%==0 (
    for /d %%i in ("%BATCH_DIR%\..\*") do (
        if /i "%%~nxi"=="Project2" (
            if exist "%%i\run.py" (
                set "PROJECT2_PATH=%%i"
                set "FOUND=1"
                echo [92mMethod 3: Found Project2 folder: %%i[0m
                goto :execute
            )
        )
    )
)

REM Method 4: Ask user for path if not found (only reaches here if all above methods fail)
if %FOUND%==0 (
    echo [91mCould not automatically locate Project2 folder![0m
    echo.
    echo Please enter the full path to the Project2 folder:
    echo (Example: C:\Users\Mayur\algo\Project2)
    echo.
    set /p "USER_PATH=Path: "
    
    REM Remove quotes if user added them
    set "USER_PATH=%USER_PATH:"=%"
    
    if exist "%USER_PATH%\run.py" (
        set "PROJECT2_PATH=%USER_PATH%"
        set "FOUND=1"
        echo [92mValid path confirmed![0m
        goto :execute
    ) else (
        echo [91mInvalid path! run.py not found.[0m
        echo.
        echo Window will close in 5 seconds...
        timeout /t 5 /nobreak >nul
        exit /b 1
    )
)

:execute
REM Change to Project2 directory
cd /d "%PROJECT2_PATH%"
echo.
echo [92mChanged to directory: %cd%[0m
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [91mPython is not installed or not in PATH![0m
    echo Please install Python and try again.
    echo.
    echo Window will close in 5 seconds...
    timeout /t 5 /nobreak >nul
    exit /b 1
)

REM Show Python version
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PY_VERSION=%%i"
echo Using: %PY_VERSION%
echo.

REM Check if run.py exists (should by now)
if not exist "run.py" (
    echo [91mERROR: run.py not found in current directory![0m
    echo Current directory: %cd%
    echo.
    echo Window will close in 5 seconds...
    timeout /t 5 /nobreak >nul
    exit /b 1
)

REM Run the Python script
echo [92mStarting run.py...[0m
echo ========================================
echo.

python run.py

REM Store the exit code
set "EXIT_CODE=%errorlevel%"

echo.
echo ========================================

REM Check the exit code
if %EXIT_CODE% NEQ 0 (
    echo [91mScript finished with errors (Exit code: %EXIT_CODE%)[0m
    color 0C
) else (
    echo [92mScript completed successfully![0m
)

echo.
echo Window will close automatically in 5 seconds...
timeout /t 5 /nobreak >nul

REM Reset color
color 07
exit /b %EXIT_CODE%