@echo off
REM YouTube MCP Server - Git Push Script
REM Automates the process of committing and pushing changes to GitHub

echo ========================================
echo  YouTube MCP Server - Git Push
echo ========================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check if git is initialized
if not exist ".git" (
    echo ERROR: Git repository not found!
    echo Please run: git init
    pause
    exit /b 1
)

REM Get commit message from user
set /p commit_message="Enter commit message: "

if "%commit_message%"=="" (
    echo ERROR: Commit message cannot be empty!
    pause
    exit /b 1
)

echo.
echo Step 1: Checking status...
echo ----------------------------------------
git status

echo.
echo Step 2: Adding all changes...
echo ----------------------------------------
git add .

echo.
echo Step 3: Committing changes...
echo ----------------------------------------
git commit -m "%commit_message%"

if %errorlevel% neq 0 (
    echo.
    echo No changes to commit or commit failed.
    pause
    exit /b 1
)

echo.
echo Step 4: Pushing to GitHub...
echo ----------------------------------------
git push origin main

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Push failed!
    echo.
    echo Possible solutions:
    echo 1. Check your internet connection
    echo 2. Verify GitHub credentials
    echo 3. Try: git push -u origin main
    echo 4. Check if remote is configured: git remote -v
    pause
    exit /b 1
)

echo.
echo ========================================
echo  SUCCESS! Changes pushed to GitHub
echo ========================================
echo.
echo Repository: https://github.com/aihenryai/youtube-mcp-server
echo.

pause
