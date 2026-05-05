"""
Google Maps Business Lead Scraper using Playwright.
Scrapes business listings without API - extracts name, rating, reviews, and website.

Production-ready scraper with error handling, dynamic loading support, and CSV export.
"""

import asyncio
import csv
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('google_maps_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    """Main scraper class for Google Maps business listings."""
    
    def __init__(self, headless: bool = False, max_results: int = 100, debug: bool = True):
        """
        Initialize scraper configuration.
        
        Args:
            headless: Run browser in headless mode (no GUI)
            max_results: Maximum number of results to collect
            debug: Print detailed debug messages
        """
        self.headless = headless
        self.max_results = max_results
        self.debug = debug
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.results: List[Dict] = []
        
    async def initialize(self):
        """Initialize Playwright browser and page."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            self.page = await self.context.new_page()
            # Add stealth script to avoid detection
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """)
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def close(self):
        """Close browser and cleanup."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def open_map(self, keyword: str, location: str) -> bool:
        """
        Open Google Maps search for keyword and location.
        
        Args:
            keyword: Business type (e.g., 'restaurants', 'AC repair')
            location: Location (e.g., 'Delhi', 'Mumbai')
            
        Returns:
            True if page loaded successfully
        """
        try:
            search_query = f"{keyword} {location}"
            url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            logger.info(f"Opening Google Maps: {url}")
            
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)  # Wait for dynamic content
            
            # Wait for results list to appear
            await self.page.wait_for_selector('[role="region"] [role="button"]', timeout=15000)
            logger.info("Google Maps page loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open Google Maps: {e}")
            return False

    async def scroll_results(self) -> int:
        """
        Scroll the left sidebar to load all available results.
        
        Returns:
            Number of results loaded
        """
        try:
            results_loaded = 0
            previous_count = 0
            no_change_count = 0
            scroll_attempts = 0
            max_scroll_attempts = 50
            
            logger.info("Starting to scroll results panel...")
            
            # Find the scrollable results container
            results_container = await self.page.query_selector('[role="region"] [role="main"]')
            if not results_container:
                results_container = await self.page.query_selector('[role="region"]')
            
            while scroll_attempts < max_scroll_attempts and results_loaded < self.max_results:
                try:
                    # Count current results
                    current_count = len(await self.page.query_selector_all(
                        '[role="region"] [role="button"][jsaction*="click"]'
                    ))
                    
                    results_loaded = current_count
                    
                    if current_count == previous_count:
                        no_change_count += 1
                        if no_change_count > 3:  # No new results after 3 attempts
                            logger.info("No more new results - likely reached end")
                            break
                    else:
                        no_change_count = 0
                        logger.info(f"Results loaded: {current_count}")
                    
                    # Scroll down using JavaScript for smooth scrolling
                    await self.page.evaluate("""
                        () => {
                            const container = document.querySelector('[role="region"] [role="main"]');
                            if (container) {
                                container.scrollTop = container.scrollHeight;
                            }
                        }
                    """)
                    
                    previous_count = current_count
                    scroll_attempts += 1
                    await asyncio.sleep(1.5)  # Delay to avoid blocking
                    
                except Exception as e:
                    logger.warning(f"Error during scroll: {e}")
                    scroll_attempts += 1
                    await asyncio.sleep(1)
            
            logger.info(f"Scrolling complete. Total results loaded: {results_loaded}")
            return results_loaded
            
        except Exception as e:
            logger.error(f"Error scrolling results: {e}")
            return 0

    async def extract_list(self) -> List[Dict]:
        """
        Extract basic info (name, rating, reviews) from results list.
        
        Returns:
            List of businesses with basic info
        """
        try:
            businesses = []
            
            # Get all result buttons
            result_buttons = await self.page.query_selector_all(
                '[role="region"] [role="button"][jsaction*="click"]'
            )
            
            logger.info(f"Found {len(result_buttons)} result items")
            
            for idx, button in enumerate(result_buttons[:self.max_results]):
                try:
                    # Extract text content
                    text_content = await button.text_content()
                    
                    if not text_content or len(text_content.strip()) < 2:
                        continue
                    
                    # Parse the text to extract info
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    
                    if len(lines) < 1:
                        continue
                    
                    business = {
                        'name': lines[0] if lines else 'N/A',
                        'rating': 'N/A',
                        'reviews': 'N/A',
                        'website': 'N/A',
                        'element': button  # Keep reference for detail extraction
                    }
                    
                    # Extract rating and review count (usually in format "4.5★ (123)")
                    for line in lines:
                        # Look for rating pattern: "4.5" or "★" or "(123 reviews)"
                        rating_match = re.search(r'(\d+\.?\d*)\s*★', line)
                        if rating_match:
                            business['rating'] = rating_match.group(1)
                        
                        review_match = re.search(r'\((\d+(?:,\d+)*)\)', line)
                        if review_match:
                            business['reviews'] = review_match.group(1)
                    
                    businesses.append(business)
                    logger.debug(f"Extracted: {business['name']} - Rating: {business['rating']}")
                    
                except Exception as e:
                    logger.warning(f"Error extracting result {idx}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(businesses)} businesses from list")
            self.results = businesses
            return businesses
            
        except Exception as e:
            logger.error(f"Error extracting results list: {e}")
            return []

    async def extract_website(self, business: Dict) -> Optional[str]:
        """
        Click on business detail and extract website from the detail panel.
        
        Args:
            business: Business dict with element reference
            
        Returns:
            Website URL or None
        """
        try:
            if 'element' not in business:
                return None
            
            element = business['element']
            
            # Click on the business to open detail panel
            await element.click()
            await asyncio.sleep(1.5)  # Wait for detail panel to load
            
            # Try multiple selectors for website link
            website_selectors = [
                'a[href*="http"]:has-text("Website")',
                'a[aria-label*="website"]',
                'a[data-tooltip="Visit website"]',
                'a[href*="www."]',
                'div[role="button"][aria-label*="website"]'
            ]
            
            website = None
            
            for selector in website_selectors:
                try:
                    element_link = await self.page.query_selector(selector)
                    if element_link:
                        website = await element_link.get_attribute('href')
                        if website and website.startswith('http'):
                            logger.debug(f"Found website: {website}")
                            return website
                except:
                    continue
            
            # Alternative: Extract from the detail panel text
            try:
                detail_panel = await self.page.query_selector('[role="main"]')
                if detail_panel:
                    text = await detail_panel.text_content()
                    # Look for URL pattern
                    url_match = re.search(r'(https?://[^\s]+)', text)
                    if url_match:
                        website = url_match.group(1)
                        logger.debug(f"Found website from text: {website}")
                        return website
            except:
                pass
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting website for {business['name']}: {e}")
            return None

    async def extract_details(self) -> List[Dict]:
        """
        Extract full details including websites by clicking on each business.
        
        Returns:
            List of businesses with complete info
        """
        try:
            logger.info(f"Extracting details for {len(self.results)} businesses...")
            
            for idx, business in enumerate(self.results):
                try:
                    # Extract website by clicking detail
                    website = await self.extract_website(business)
                    business['website'] = website if website else 'N/A'
                    
                    # Remove element reference before saving
                    business.pop('element', None)
                    
                    if (idx + 1) % 10 == 0:
                        logger.info(f"Processed {idx + 1}/{len(self.results)} businesses")
                    
                    # Small delay between requests to avoid blocking
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Error processing detail {idx}: {e}")
                    business.pop('element', None)
                    continue
            
            logger.info("Detail extraction complete")
            return self.results
            
        except Exception as e:
            logger.error(f"Error extracting details: {e}")
            return self.results

    async def save_csv(self, filename: Optional[str] = None) -> str:
        """
        Save scraped results to CSV file.
        
        Args:
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to saved file
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"google_maps_results_{timestamp}.csv"
            
            filepath = Path(filename)
            
            # Prepare data for CSV
            csv_data = []
            for business in self.results:
                csv_data.append({
                    'name': business.get('name', 'N/A'),
                    'rating': business.get('rating', 'N/A'),
                    'reviews': business.get('reviews', 'N/A'),
                    'website': business.get('website', 'N/A')
                })
            
            # Write to CSV
            if csv_data:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['name', 'rating', 'reviews', 'website'])
                    writer.writeheader()
                    writer.writerows(csv_data)
                
                logger.info(f"Results saved to {filepath} ({len(csv_data)} records)")
                return str(filepath)
            else:
                logger.warning("No data to save")
                return ""
            
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            return ""

    async def scrape(self, keyword: str, location: str, output_file: Optional[str] = None) -> List[Dict]:
        """
        Main scraping workflow.
        
        Args:
            keyword: Business type to search
            location: Location to search in
            output_file: Output CSV filename
            
        Returns:
            List of scraped businesses
        """
        try:
            logger.info(f"Starting scrape: '{keyword}' in '{location}'")
            
            # Step 1: Open map
            if not await self.open_map(keyword, location):
                logger.error("Failed to open Google Maps")
                return []
            
            # Step 2: Scroll to load results
            await self.scroll_results()
            
            # Step 3: Extract basic info from list
            await self.extract_list()
            
            if not self.results:
                logger.warning("No results extracted from list")
                return []
            
            # Step 4: Extract details (websites)
            await self.extract_details()
            
            # Step 5: Save to CSV
            if output_file:
                self.save_csv(output_file)
            else:
                self.save_csv()
            
            logger.info(f"Scraping complete: {len(self.results)} businesses scraped")
            return self.results
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return []


async def main():
    """Main entry point - example usage."""
    
    # Configuration
    KEYWORD = "AC repair"
    LOCATION = "Delhi"
    MAX_RESULTS = 50
    HEADLESS_MODE = False  # Set to True for production
    
    scraper = GoogleMapsScraper(
        headless=HEADLESS_MODE,
        max_results=MAX_RESULTS,
        debug=True
    )
    
    try:
        await scraper.initialize()
        
        # Run scraper
        results = await scraper.scrape(
            keyword=KEYWORD,
            location=LOCATION,
            output_file=f"maps_leads_{KEYWORD.replace(' ', '_')}_{LOCATION}.csv"
        )
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info(f"SCRAPING SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Keyword: {KEYWORD}")
        logger.info(f"Location: {LOCATION}")
        logger.info(f"Total Results: {len(results)}")
        logger.info(f"With Websites: {sum(1 for r in results if r.get('website') != 'N/A')}")
        logger.info(f"With Ratings: {sum(1 for r in results if r.get('rating') != 'N/A')}")
        logger.info(f"{'='*60}\n")
        
        # Print first 5 results
        if results:
            logger.info("Sample Results:")
            for i, r in enumerate(results[:5], 1):
                logger.info(f"{i}. {r['name']}")
                logger.info(f"   Rating: {r['rating']} | Reviews: {r['reviews']}")
                logger.info(f"   Website: {r['website']}\n")
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
