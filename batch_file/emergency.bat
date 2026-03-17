@echo off
title GT Trading - Delete Live Feed Data
color 0C

echo ========================================
echo   GT Trading - Delete Live Feed Data
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
if exist "%BATCH_DIR%\..\Project2" (
    set "PROJECT2_PATH=%BATCH_DIR%\..\Project2"
    set "FOUND=1"
    echo [92mMethod 1: Found Project2 in parent directory[0m
    goto :execute
)

REM Method 2: Check if Project2 is in the same directory as the batch file
if %FOUND%==0 if exist "%BATCH_DIR%\Project2" (
    set "PROJECT2_PATH=%BATCH_DIR%\Project2"
    set "FOUND=1"
    echo [92mMethod 2: Found Project2 in same directory[0m
    goto :execute
)

REM Method 3: Search for Project2 folder in parent directory
if %FOUND%==0 (
    for /d %%i in ("%BATCH_DIR%\..\*") do (
        if /i "%%~nxi"=="Project2" (
            set "PROJECT2_PATH=%%i"
            set "FOUND=1"
            echo [92mMethod 3: Found Project2 folder: %%i[0m
            goto :execute
        )
    )
)

REM Method 4: Ask user for path if not found
if %FOUND%==0 (
    echo [91mCould not automatically locate Project2 folder![0m
    echo.
    echo Please enter the full path to the Project2 folder:
    echo (Example: C:\Users\Mayur\algo\Project2)
    echo.
    set /p "USER_PATH=Path: "
    
    REM Remove quotes if user added them
    set "USER_PATH=%USER_PATH:"=%"
    
    if exist "%USER_PATH%" (
        set "PROJECT2_PATH=%USER_PATH%"
        set "FOUND=1"
        echo [92mValid path confirmed![0m
        goto :execute
    ) else (
        echo [91mInvalid path! Folder not found.[0m
        echo.
        echo Window will close in 5 seconds...
        timeout /t 5 /nobreak >nul
        exit /b 1
    )
)

:execute
REM Set the target file path
set "TARGET_FILE=%PROJECT2_PATH%\Live_Feed_Data.xlsx"

echo.
echo Looking for: %TARGET_FILE%
echo.

REM Check if the file exists
if exist "%TARGET_FILE%" (
    echo [93mFound: Live_Feed_Data.xlsx[0m
    echo.
    
    REM Ask for confirmation using CHOICE command (more reliable)
    echo Are you sure you want to delete this file?
    choice /c YN /n /m "Press Y for Yes or N for No: "
    
    REM Check the error level from CHOICE
    if errorlevel 2 (
        echo [93mDeletion cancelled.[0m
    ) else (
        del /f /q "%TARGET_FILE%"
        if errorlevel 1 (
            echo [91mFailed to delete the file![0m
        ) else (
            echo [92mFile successfully deleted![0m
        )
    )
) else (
    echo [91mLive_Feed_Data.xlsx not found in Project2 folder![0m
    echo.
    echo The file may not exist or may have been deleted already.
)

echo.
echo Window will close automatically in 5 seconds...
timeout /t 5 /nobreak >nul
exit /b 0