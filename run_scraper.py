#!/usr/bin/env python3
"""
🚀 Quick Start - Google Maps Scraper

Use this to scrape Google Maps and get CSV with real data.
"""

import os
import sys
from scraper.maps_scraper import GoogleMapsScraper, scrape_multiple_locations


def main():
    """Example usage"""
    
    print("\n" + "█"*70)
    print("█" + "🔥 GOOGLE MAPS SCRAPER - QUICK START".center(68) + "█")
    print("█" * 70 + "\n")
    
    # Example 1: Single location
    print("📍 Example 1: Single location (Restaurants in Delhi)\n")
    scraper = GoogleMapsScraper(headless=True)
    scraper.scrape(
        keyword="restaurants",
        location="Delhi",
        max_results=30
    )
    
    # Example 2: Multiple locations (uncomment to use)
    """
    print("\n" + "="*70)
    print("📍 Example 2: Multiple locations\n")
    scrape_multiple_locations(
        keyword="plumber",
        locations=["Delhi", "Mumbai"],
        max_results=50,
        headless=False
    )
    """
    
    print("\n" + "█"*70)
    print("█" + "✅ DONE!".center(68) + "█")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
