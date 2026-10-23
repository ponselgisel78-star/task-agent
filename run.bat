@echo off
title Task Automation Agent
cd /d "%~dp0"

echo ========================================================
echo Starting Task Automation Agent...
echo ========================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found (.venv)!
    echo Please ensure the project dependencies are installed.
    pause
    exit /b 1
)

:: Run Agent with virtualenv python
".venv\Scripts\python.exe" cli.py

echo.
echo ========================================================
echo Agent session ended.
echo ========================================================
pause
