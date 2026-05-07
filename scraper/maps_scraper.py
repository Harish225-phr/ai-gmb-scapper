"""
Google Maps Scraper using Playwright
Real data extraction - Name, Website, Rating, Reviews, Phone, Address
"""

import time
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class GoogleMapsScraper:
    """Scrape Google Maps for business data"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.results = []
        self.browser = None
        self.page = None
        
    def _pause(self, min_sec: float = 1, max_sec: float = 3):
        """Random pause to avoid detection"""
        import random
        time.sleep(random.uniform(min_sec, max_sec))
    
    def open_map(self, keyword: str, location: str):
        """Open Google Maps search"""
        query = f"{keyword} {location}"
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        
        print(f"🌐 Opening Maps: {query}")
        self.page.goto(url, wait_until="networkidle")
        self._pause(2, 3)
    
    def scroll_results(self, max_scroll: int = 10):
        """Scroll sidebar to load all results"""
        print("📜 Scrolling results...")
        
        for i in range(max_scroll):
            try:
                # Get scroll container
                scroll_div = self.page.query_selector('div[role="feed"]')
                if not scroll_div:
                    print("   ❌ Feed not found")
                    break
                
                # Scroll down
                scroll_div.evaluate("el => el.scrollBy(0, 5000)")
                self._pause(1.5, 2.5)
                
                # Check if new results loaded
                results = self.page.query_selector_all('div[role="article"]')
                print(f"   ✓ {len(results)} results loaded")
                
            except Exception as e:
                print(f"   ⚠ Scroll error: {e}")
                break
    
    def extract_business_list(self, max_results: int = 50) -> List[Dict]:
        """Extract basic info from results list"""
        print(f"📋 Extracting top {max_results} businesses...")
        
        businesses = []
        cards = self.page.query_selector_all('div[role="article"]')
        
        for idx, card in enumerate(cards[:max_results]):
            try:
                # Name
                name_elem = card.query_selector('h3')
                name = name_elem.inner_text() if name_elem else "N/A"
                
                # Rating (e.g., "4.5")
                rating_elem = card.query_selector('[aria-label*="stars"]')
                rating = "N/A"
                if rating_elem:
                    label = rating_elem.get_attribute("aria-label")
                    # Extract "4.5" from "4.5 stars (123 reviews)"
                    match = re.search(r'([\d.]+)\s+stars?', label)
                    if match:
                        rating = match.group(1)
                
                # Reviews
                reviews_elem = card.query_selector('[aria-label*="review"]')
                reviews = "0"
                if reviews_elem:
                    label = reviews_elem.get_attribute("aria-label")
                    match = re.search(r'([\d,]+)\s+review', label)
                    if match:
                        reviews = match.group(1)
                
                businesses.append({
                    "name": name,
                    "rating": rating,
                    "reviews": reviews,
                    "website": "N/A",
                    "phone": "N/A",
                    "address": "N/A"
                })
                
                print(f"   ✓ {idx + 1}. {name}")
                
            except Exception as e:
                print(f"   ⚠ Error extracting: {e}")
                continue
        
        return businesses
    
    def extract_details(self, businesses: List[Dict], location: str):
        """Click each result and extract website/phone/address"""
        print(f"🔍 Extracting details from {len(businesses)} businesses...")
        
        for idx, business in enumerate(businesses):
            try:
                # Find the card for this business
                cards = self.page.query_selector_all('div[role="article"]')
                if idx >= len(cards):
                    break
                
                card = cards[idx]
                
                # Click to open details
                card.click()
                self._pause(1, 2)
                
                # Wait for details panel
                try:
                    self.page.wait_for_selector('div[data-tab="0"]', timeout=3000)
                except PlaywrightTimeout:
                    print(f"   ⚠ Details timeout for {business['name']}")
                    continue
                
                # Extract website
                try:
                    website_elem = self.page.query_selector('a[href^="http"][data-item-id="website"]')
                    if website_elem:
                        website_url = website_elem.get_attribute("href")
                        # Clean URL
                        business["website"] = website_url.replace("http://www.google.com/url?q=", "").split("&")[0] if website_url else "N/A"
                except:
                    pass
                
                # Extract phone
                try:
                    phone_elem = self.page.query_selector('button[data-item-id="phone:tel:"]')
                    if phone_elem:
                        business["phone"] = phone_elem.inner_text()
                except:
                    pass
                
                # Extract address
                try:
                    address_elem = self.page.query_selector('button[data-item-id="address"]')
                    if address_elem:
                        business["address"] = address_elem.inner_text()
                except:
                    pass
                
                status = "✓" if business["website"] != "N/A" else "⊘"
                print(f"   {status} {idx + 1}. {business['name']}: {business['website']}")
                
                self._pause(0.5, 1)
                
            except Exception as e:
                print(f"   ❌ Error extracting details: {e}")
                continue
        
        return businesses
    
    def save_csv(self, businesses: List[Dict], location: str, keyword: str):
        """Save results to CSV"""
        filename = f"results_{keyword}_{location}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = Path(filename)
        
        print(f"\n💾 Saving to {filename}...")
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'website', 'rating', 'reviews', 'phone', 'address', 'location', 'keyword'])
            writer.writeheader()
            
            for b in businesses:
                writer.writerow({
                    'name': b['name'],
                    'website': b['website'],
                    'rating': b['rating'],
                    'reviews': b['reviews'],
                    'phone': b['phone'],
                    'address': b['address'],
                    'location': location,
                    'keyword': keyword
                })
        
        print(f"✅ Saved: {filepath}")
        
        # Print summary
        with_website = sum(1 for b in businesses if b['website'] != 'N/A')
        print(f"\n📊 Summary:")
        print(f"   Total: {len(businesses)}")
        print(f"   With website: {with_website} ({with_website*100//len(businesses) if businesses else 0}%)")
        print(f"   File: {filepath}")
        
        return filepath
    
    def scrape(self, keyword: str, location: str, max_results: int = 50) -> Path:
        """Main scraping workflow"""
        print("\n" + "="*70)
        print(f"🚀 Scraping: {keyword} in {location}")
        print("="*70 + "\n")
        
        try:
            with sync_playwright() as p:
                # Launch Chromium with network-friendly flags to reduce ERR_NETWORK_IO_SUSPENDED
                launch_args = [
                    "--disable-features=NetworkService",
                    "--disable-features=NetworkServiceInProcess",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ]
                self.browser = p.chromium.launch(headless=self.headless, args=launch_args)
                self.page = self.browser.new_page()
                # Increase default timeout for slow networks
                self.page.set_default_timeout(30000)
                
                # Open map with retry in case of transient network suspension
                retries = 3
                for attempt in range(1, retries + 1):
                    try:
                        self.open_map(keyword, location)
                        break
                    except Exception as e:
                        print(f"   ⚠ open_map attempt {attempt} failed: {e}")
                        if attempt < retries:
                            time.sleep(2 * attempt)
                            continue
                        else:
                            raise
                
                # Scroll to load results
                self.scroll_results(max_scroll=8)
                
                # Extract business list
                businesses = self.extract_business_list(max_results)
                
                if not businesses:
                    print("❌ No results found!")
                    return None
                
                # Extract details (website, phone, address)
                businesses = self.extract_details(businesses, location)
                
                # Save to CSV
                filepath = self.save_csv(businesses, location, keyword)
                
                self.browser.close()
                
                return filepath
                
        except Exception as e:
            print(f"❌ Scraping error: {e}")
            if self.browser:
                self.browser.close()
            return None


def scrape_multiple_locations(keyword: str, locations: List[str], max_results: int = 50, headless: bool = True):
    """Scrape multiple locations for same keyword"""
    print("\n" + "█"*70)
    print("█" + f" 🚀 GOOGLE MAPS SCRAPER - BATCH MODE".center(68) + "█")
    print("█" * 70)
    
    scraper = GoogleMapsScraper(headless=headless)
    results_files = []
    
    for idx, location in enumerate(locations, 1):
        print(f"\n[{idx}/{len(locations)}] Processing: {location}")
        filepath = scraper.scrape(keyword, location, max_results)
        
        if filepath:
            results_files.append(filepath)
        
        # Delay between locations
        if idx < len(locations):
            print("⏳ Waiting 5 seconds before next location...")
            time.sleep(5)
    
    print("\n" + "="*70)
    print(f"✅ COMPLETE! Generated {len(results_files)} CSV files")
    print("="*70)
    
    return results_files


if __name__ == "__main__":
    # Test
    scraper = GoogleMapsScraper(headless=False)
    scraper.scrape(
        keyword="restaurants",
        location="Delhi",
        max_results=20
    )
