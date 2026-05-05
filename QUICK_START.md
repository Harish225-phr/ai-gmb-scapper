# Google Maps Scraper - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies (1 min)

```bash
# Windows
pip install -r scraper_requirements.txt
playwright install chromium

# Linux/Mac
pip3 install -r scraper_requirements.txt
playwright install chromium
```

### 2. Run Scraper (4 min)

**Option A: Windows Batch File (Easiest)**
```bash
run_scraper.bat
```

**Option B: Direct Python**
```bash
python google_maps_scraper.py
```

**Option C: CLI with Options**
```bash
python cli.py -k "restaurants" -l "Delhi" -n 50
```

**Option D: Interactive Mode**
```bash
python cli.py --interactive
```

---

## Common Use Cases

### 1️⃣ Search One Location
```bash
python cli.py -k "AC repair" -l "Delhi"
```

### 2️⃣ Search Multiple Locations
```bash
python cli.py -k "restaurants" -l "Delhi,Mumbai,Bangalore" --batch
```

### 3️⃣ Production Mode (Headless)
```bash
python cli.py -k "plumbers" -l "Mumbai" --headless -n 100
```

### 4️⃣ Custom Output File
```bash
python cli.py -k "hospitals" -l "Delhi" -o my_results.csv
```

### 5️⃣ Interactive Mode
```bash
python cli.py --interactive
# Prompts for all settings
```

---

## Files Explained

| File | Purpose |
|------|---------|
| `google_maps_scraper.py` | Main scraper class (core logic) |
| `cli.py` | Command-line interface (easy usage) |
| `google_maps_examples.py` | 7 advanced examples & patterns |
| `scraper_config.py` | Configuration settings |
| `run_scraper.bat` | Windows quick-start |
| `run_scraper.sh` | Linux/Mac quick-start |
| `GOOGLE_MAPS_SCRAPER_README.md` | Full documentation |

---

## Output

After running, you'll get a CSV file like:

```csv
name,rating,reviews,website
Taj Hotel Delhi,4.5,2345,https://tajhoteldelhi.com
Blue Sky Cafe,4.2,856,N/A
Spice Garden,4.8,1234,https://spicegarden.in
```

**Files created**:
- `google_maps_results_YYYYMMDD_HHMMSS.csv` - Results (auto-named)
- `google_maps_scraper.log` - Debug logs

---

## Python Code Example

```python
import asyncio
from google_maps_scraper import GoogleMapsScraper

async def main():
    scraper = GoogleMapsScraper(headless=True, max_results=50)
    
    try:
        await scraper.initialize()
        results = await scraper.scrape("restaurants", "Delhi")
        print(f"Found {len(results)} restaurants")
    finally:
        await scraper.close()

asyncio.run(main())
```

---

## Troubleshooting

### ❌ "No module named 'playwright'"
```bash
pip install -r scraper_requirements.txt
```

### ❌ "Chrome/Chromium not found"
```bash
playwright install chromium
```

### ❌ Results are empty
1. Try `python cli.py --interactive` to see what's happening
2. Run without `--headless` to watch browser
3. Check internet connection
4. Verify keyword/location is valid on Google Maps manually

### ❌ Getting blocked (HTTP 429)
- Wait 30 minutes
- Use VPN/Proxy
- Reduce `max_results`
- Increase `SCROLL_DELAY` in `scraper_config.py`

### ❌ Website extraction not working
- Some businesses don't have websites
- Edit `EXTRACT_WEBSITES = False` in `scraper_config.py` to skip

---

## Performance

| Mode | Speed | Use Case |
|------|-------|----------|
| **Headless** | Fast ⚡ | Production, batch jobs |
| **Visual** | Slower | Debugging, testing |
| **30 Results** | ~2 min | Quick test |
| **50 Results** | ~3-4 min | Typical use |
| **100 Results** | ~6-8 min | Comprehensive |

---

## Tips & Tricks

✅ **Add delays between batch requests**
```bash
# Scrape multiple times safely
python cli.py -k "gyms" -l "Delhi" && sleep 30 && \
python cli.py -k "gyms" -l "Mumbai"
```

✅ **Filter results after scraping**
```python
# Keep only high-rated businesses
results = [r for r in results if float(r['rating'] or 0) >= 4.0]
```

✅ **Export as JSON**
```python
import json
with open("results.json", "w") as f:
    json.dump(results, f, indent=2)
```

✅ **Combine multiple files**
```python
import pandas as pd
df = pd.concat([
    pd.read_csv("results_delhi.csv"),
    pd.read_csv("results_mumbai.csv")
])
df.to_csv("all_results.csv", index=False)
```

---

## Advanced: Edit Configuration

Edit `scraper_config.py` for defaults:

```python
KEYWORD = "AC repair"           # Default search
LOCATION = "Delhi"              # Default location
MAX_RESULTS = 50                # Default limit
HEADLESS_MODE = False           # Show browser by default
SCROLL_DELAY = 1.5              # Delay between scrolls (increase if blocking)
```

Then run:
```bash
python google_maps_scraper.py  # Uses config.py defaults
```

---

## When to Use CLI vs Python Code

### Use CLI (`cli.py`)
- One-time scraping
- Simple requirements
- Bash/batch scripts
- Non-programmers

### Use Python API (`google_maps_scraper.py`)
- Complex workflows
- Data processing
- Integration with other tools
- Programmatic control

---

## Support

- **Logs**: Check `google_maps_scraper.log` for errors
- **Debug**: Run with `--headless` (off) to watch browser
- **Full Docs**: See `GOOGLE_MAPS_SCRAPER_README.md`
- **Examples**: Run `python google_maps_examples.py`

---

## Next Steps

1. ✅ Install dependencies: `pip install -r scraper_requirements.txt`
2. ✅ Install browser: `playwright install chromium`
3. ✅ Try it: `python cli.py --interactive`
4. ✅ Customize: Edit `scraper_config.py`
5. ✅ Scale up: Use batch mode for multiple locations

---

**Happy scraping! 🚀**
