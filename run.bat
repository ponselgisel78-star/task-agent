@echo off
title Task Automation Agent
set "PROJECT_DIR=C:\Users\sang1\.gemini\antigravity\scratch\task-agent"
cd /d "%PROJECT_DIR%"
set "PYTHONPATH=%PROJECT_DIR%"

echo Starting Task Automation Agent...
"%PROJECT_DIR%\.venv\Scripts\python.exe" "%PROJECT_DIR%\cli.py"

echo.
echo Agent session ended.
pause
