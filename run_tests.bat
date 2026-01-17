@echo off
REM Run all module tests
REM Executes tests for each standalone module

echo ============================================
echo CAROUSELL LOWBALLER - FULL TEST SUITE
echo ============================================
echo.

echo [1/4] Testing DOM Parser...
echo ----------------------------------------
python dom_parser.py
echo.

echo [2/4] Testing DOM Extractor...
echo ----------------------------------------
python dom_extractor.py
echo.

echo [3/4] Testing LLM Factory...
echo ----------------------------------------
python llm_factory.py
echo.

echo [4/4] Testing Lowballer Agent...
echo ----------------------------------------
python lowballer.py
echo.

echo ============================================
echo ALL TESTS COMPLETE
echo ============================================
echo.
echo Note: Browser tests require Playwright installed.
echo Run 'pip install playwright' then 'playwright install chromium'
echo.
echo To test browser: test_browser.bat
echo To test with Ollama: test_controller.bat, test_lowballer.bat
echo.
pause
