@echo off
REM Quick setup and run script for Google Maps Scraper (Windows)

cls
echo ==================================
echo Google Maps Scraper Setup
echo ==================================

REM Step 1: Install dependencies
echo.
echo [1/3] Installing Python dependencies...
pip install -r scraper_requirements.txt

REM Step 2: Install Playwright browsers
echo.
echo [2/3] Installing Playwright browsers...
playwright install chromium

REM Step 3: Run scraper
echo.
echo [3/3] Starting Google Maps Scraper...
echo.
echo Choose an option:
echo   1. Run main scraper (default: AC repair in Delhi, 50 results)
echo   2. Run advanced examples (interactive)
echo.
set /p choice="Choice (1 or 2): "

if "%choice%"=="2" (
    python google_maps_examples.py
) else (
    python google_maps_scraper.py
)

echo.
echo ==================================
echo Done! Check CSV files in current directory
echo ==================================
pause
