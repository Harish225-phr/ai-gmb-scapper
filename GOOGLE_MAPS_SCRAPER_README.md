# Google Maps Business Scraper - Playwright

A production-ready Python scraper for Google Maps search results without using Google Maps API. Extracts business names, ratings, review counts, and websites.

## Features

✅ **No API Required** - Uses Playwright browser automation
✅ **Dynamic Loading** - Scrolls sidebar to load all available results
✅ **Website Extraction** - Opens detail panels to get business websites
✅ **Error Handling** - Graceful error handling, won't crash on missing data
✅ **CSV Export** - Saves results to timestamped CSV files
✅ **Modular Code** - Clean, reusable functions for each step
✅ **Anti-Detection** - Includes stealth scripts to avoid blocking
✅ **Logging** - Detailed logs to file and console
✅ **Configurable** - Max results, headless mode, timeouts

## Installation

### 1. Install Dependencies

```bash
pip install -r scraper_requirements.txt
```

Or install manually:
```bash
pip install playwright==1.40.0
```

### 2. Install Browser

```bash
playwright install chromium
```

## Quick Start

### Basic Usage

```python
import asyncio
from google_maps_scraper import GoogleMapsScraper

async def main():
    scraper = GoogleMapsScraper(
        headless=False,  # Show browser for debugging
        max_results=50
    )
    
    try:
        await scraper.initialize()
        results = await scraper.scrape(
            keyword="restaurants",
            location="Delhi"
        )
        
        # Print results
        for business in results:
            print(f"{business['name']}")
            print(f"  Rating: {business['rating']}")
            print(f"  Reviews: {business['reviews']}")
            print(f"  Website: {business['website']}\n")
            
    finally:
        await scraper.close()

asyncio.run(main())
```

### Run Direct Script

```bash
python google_maps_scraper.py
```

Modify these variables in `main()`:
```python
KEYWORD = "AC repair"           # Business type
LOCATION = "Delhi"              # City/area
MAX_RESULTS = 50                # Limit results
HEADLESS_MODE = False           # Show browser
```

## Advanced Usage

### Custom Configuration

```python
scraper = GoogleMapsScraper(
    headless=True,              # Production: no GUI
    max_results=100,            # Up to 100 results
    debug=False                 # Disable debug logs
)

# Multi-location search
locations = ["Delhi", "Mumbai", "Bangalore"]
all_results = []

for location in locations:
    results = await scraper.scrape(
        keyword="restaurants",
        location=location,
        output_file=f"results_{location}.csv"
    )
    all_results.extend(results)
```

### Process Results Programmatically

```python
# Filter by rating
good_rated = [r for r in results if float(r['rating'] or 0) >= 4.0]

# Filter by website availability
with_website = [r for r in results if r['website'] != 'N/A']

# Export custom format
import json
with open("results.json", "w") as f:
    json.dump(results, f, indent=2)
```

## How It Works

### Step-by-Step Process

1. **`open_map()`** - Opens Google Maps search URL with keyword + location
2. **`scroll_results()`** - Scrolls sidebar to trigger lazy-loading until all results appear
3. **`extract_list()`** - Parses visible results to extract name, rating, review count
4. **`extract_details()`** - Clicks each result to open detail panel and extract website
5. **`save_csv()`** - Exports all data to timestamped CSV file

### Output CSV Format

```csv
name,rating,reviews,website
Taj Hotel Delhi,4.5,2345,https://tajhoteldelhi.com
Blue Sky Cafe,4.2,856,N/A
Spice Garden,4.8,1234,https://spicegarden.in
...
```

## Troubleshooting

### Browser Crashes

**Issue**: "Browser launch failed"
```python
# Solution: Ensure Chromium is installed
playwright install chromium
```

### No Results Found

**Issue**: Scraper returns empty list

**Solutions**:
1. Check if keyword/location is valid on Google Maps manually
2. Increase `max_results` threshold
3. Check network/proxy issues
4. Set `headless=False` to see what's happening

```python
scraper = GoogleMapsScraper(headless=False, max_results=100)
```

### Websites Not Extracted

**Issue**: All websites show "N/A"

**Possible reasons**:
- Business detail panel not opening
- Website selector changed on Google Maps
- Small delay needed between clicks

**Solutions**:
```python
# Increase delay between requests
# Edit this line in extract_details():
await asyncio.sleep(1.0)  # Increase from 0.5
```

### Getting Blocked/Rate Limited

**Issue**: "403 Forbidden" or "429 Too Many Requests"

**Solutions**:
1. Increase delays between requests
2. Use proxy/VPN
3. Reduce `max_results`
4. Wait 15 minutes before retrying

```python
# Add longer delays
await asyncio.sleep(2.0)  # Between clicks
await asyncio.sleep(3.0)  # Between scrolls
```

## Performance Tips

### For Speed
- Use `headless=True` (no GUI rendering)
- Lower `max_results` limit
- Reduce delays between requests

```python
scraper = GoogleMapsScraper(
    headless=True,
    max_results=30
)
```

### For Reliability
- Use `headless=False` for debugging
- Increase delays between requests
- Add try-except around scraper calls
- Check logs: `google_maps_scraper.log`

## Code Structure

```
google_maps_scraper.py
├── GoogleMapsScraper
│   ├── __init__()           # Initialize config
│   ├── initialize()         # Start browser
│   ├── open_map()          # Open search URL
│   ├── scroll_results()    # Load all results
│   ├── extract_list()      # Parse result list
│   ├── extract_website()   # Get website from detail
│   ├── extract_details()   # Full detail extraction
│   ├── save_csv()          # Export to CSV
│   ├── scrape()            # Main workflow
│   └── close()             # Cleanup browser
└── main()                  # Example usage
```

## Limitations & Notes

⚠️ **Rate Limiting**: Google blocks requests if you scrape too fast. Add delays!

⚠️ **Page Updates**: Google Maps UI changes may require selector updates

⚠️ **Accuracy**: Website extraction may fail for ~10-20% of businesses

⚠️ **Dynamic Content**: Some results may not load if sidebar is scrolled too fast

## Best Practices

1. **Add delays** - At least 0.5-1s between clicks/scrolls
2. **Monitor logs** - Check `google_maps_scraper.log` for errors
3. **Test locally first** - Use `headless=False` to debug
4. **Handle None values** - Always check for 'N/A' in results
5. **Batch requests** - Scrape one location at a time with delays
6. **Respect robots.txt** - Don't scrape excessively

## Example: Batch Processing Multiple Locations

```python
import asyncio
from google_maps_scraper import GoogleMapsScraper

async def scrape_all_locations():
    locations = ["Delhi", "Mumbai", "Bangalore", "Pune"]
    keyword = "restaurants"
    
    scraper = GoogleMapsScraper(
        headless=True,
        max_results=50
    )
    
    try:
        await scraper.initialize()
        
        all_results = []
        for location in locations:
            print(f"\nScraping {location}...")
            results = await scraper.scrape(
                keyword=keyword,
                location=location,
                output_file=f"results_{location}.csv"
            )
            all_results.extend(results)
            
            # Cool down between locations
            await asyncio.sleep(5)
        
        print(f"\nTotal results: {len(all_results)}")
        
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(scrape_all_locations())
```

## License

MIT - Feel free to use and modify

## Support

For issues or improvements, check:
- Logs: `google_maps_scraper.log`
- Browser console: Open with `headless=False`
- Playwright docs: https://playwright.dev/python
