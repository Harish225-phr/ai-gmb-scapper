#!/bin/bash
# Quick setup and run script for Google Maps Scraper

echo "=================================="
echo "Google Maps Scraper Setup"
echo "=================================="

# Step 1: Install dependencies
echo -e "\n[1/3] Installing Python dependencies..."
pip install -r scraper_requirements.txt

# Step 2: Install Playwright browsers
echo -e "\n[2/3] Installing Playwright browsers..."
playwright install chromium

# Step 3: Run scraper
echo -e "\n[3/3] Starting Google Maps Scraper..."
echo -e "\nChoose an option:"
echo "  1. Run main scraper (default: AC repair in Delhi, 50 results)"
echo "  2. Run advanced examples (interactive)"
echo -e "\nChoice (1 or 2): "
read choice

if [ "$choice" = "2" ]; then
    python google_maps_examples.py
else
    python google_maps_scraper.py
fi

echo -e "\n=================================="
echo "Done! Check CSV files in current directory"
echo "=================================="
