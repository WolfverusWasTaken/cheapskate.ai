@echo off
REM Setup script for Carousell Lowballer Agent
REM Installs dependencies and Playwright browser

echo ============================================
echo CAROUSELL LOWBALLER - SETUP
echo ============================================
echo.

echo [1/3] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [2/3] Installing Playwright Chromium browser...
playwright install chromium

echo.
echo [3/3] Creating .env file from template...
if not exist .env (
    copy .env.example .env
    echo Created .env file. Please edit it with your settings.
) else (
    echo .env file already exists, skipping.
)

echo.
echo ============================================
echo SETUP COMPLETE!
echo ============================================
echo.
echo Next steps:
echo   1. Edit .env with your LLM settings
echo   2. Ensure Ollama is running (if using Ollama)
echo   3. Run: python main.py
echo.
pause
