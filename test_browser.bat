@echo off
REM Test Browser Loader Module
REM Launches a visible browser and navigates to Carousell

echo ============================================
echo BROWSER LOADER TEST
echo ============================================
echo.
echo This will launch a visible Chromium browser...
echo.

python -c "import asyncio; from browser_loader import BrowserLoader; loader = BrowserLoader(headless=False); asyncio.run(loader.launch()); print('Browser launched! Waiting 5 seconds...'); import time; time.sleep(5); asyncio.run(loader.close())"

echo.
echo ============================================
echo TEST COMPLETE
echo ============================================
pause
