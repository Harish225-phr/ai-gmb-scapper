"""
Configuration file for Google Maps Scraper
Modify these settings before running the scraper
"""

# Search Configuration
KEYWORD = "AC repair"              # Business type to search
LOCATION = "Delhi"                 # City/area to search
MAX_RESULTS = 50                   # Maximum results (50-100 recommended)

# Browser Configuration
HEADLESS_MODE = False              # False = show browser, True = no GUI (production)
BROWSER_TIMEOUT = 30000            # Milliseconds to wait for page load
ANTI_DETECTION = True              # Add stealth scripts to avoid blocking

# Performance Settings
SCROLL_DELAY = 1.5                 # Seconds between scroll actions
CLICK_DELAY = 0.5                  # Seconds between element clicks
REQUEST_DELAY = 0.5                # Seconds between website extraction requests
SCROLL_ATTEMPTS = 50               # Max scroll iterations before stopping

# Extraction Settings
EXTRACT_WEBSITES = True            # Extract website URLs (slower but more data)
SKIP_NO_RATING = False             # Skip businesses without ratings
MIN_REVIEWS = 0                    # Skip businesses with fewer reviews

# Output Configuration
OUTPUT_FORMAT = "csv"              # 'csv' or 'json'
OUTPUT_DIR = "./"                  # Directory to save results
AUTO_TIMESTAMP = True              # Add timestamp to filename

# Logging
DEBUG_MODE = True                  # Print debug messages
LOG_FILE = "google_maps_scraper.log"  # Log filename
SAVE_LOGS = True                   # Save logs to file

# Retry Configuration
MAX_RETRIES = 3                    # Max retry attempts on failure
RETRY_DELAY = 5                    # Seconds to wait before retry

# Multi-Location Batch Settings
BATCH_MODE = False                 # Scrape multiple locations
LOCATIONS = [                      # List of locations for batch mode
    "Delhi",
    "Mumbai",
    "Bangalore"
]
BATCH_DELAY = 10                   # Seconds delay between location scrapes

# Example usage in code:
# from config import KEYWORD, LOCATION, MAX_RESULTS, HEADLESS_MODE
# scraper = GoogleMapsScraper(
#     headless=HEADLESS_MODE,
#     max_results=MAX_RESULTS
# )
