#!/usr/bin/env python3
"""
CLI Tool for Google Maps Scraping
Usage:
    python -m scraper.cli --keyword "restaurants" --location "Delhi"
    python -m scraper.cli --keyword "plumber" --locations "Delhi,Mumbai,Bangalore" --results 50
"""

import argparse
import sys
from scraper.maps_scraper import GoogleMapsScraper, scrape_multiple_locations


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Google Maps for business data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Single location:
    python -m scraper.cli --keyword "restaurants" --location "Delhi"
  
  Multiple locations:
    python -m scraper.cli --keyword "plumber" --locations "Delhi,Mumbai,Bangalore"
  
  Custom results limit:
    python -m scraper.cli --keyword "ac repair" --location "Delhi" --results 100
  
  Headless mode (background):
    python -m scraper.cli --keyword "restaurants" --location "Delhi" --headless
        """
    )
    
    parser.add_argument("--keyword", required=True, help="Business type (e.g., 'restaurants')")
    parser.add_argument("--location", help="Single location")
    parser.add_argument("--locations", help="Multiple locations (comma-separated)")
    parser.add_argument("--results", type=int, default=50, help="Max results per location (default: 50)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no browser window)")
    
    args = parser.parse_args()
    
    # Validation
    if not args.location and not args.locations:
        print("❌ Error: Provide --location or --locations")
        sys.exit(1)
    
    if args.location and args.locations:
        print("❌ Error: Use either --location OR --locations, not both")
        sys.exit(1)
    
    # Parse locations
    if args.location:
        locations = [args.location]
    else:
        locations = [loc.strip() for loc in args.locations.split(",")]
    
    # Run scraper
    try:
        if len(locations) == 1:
            # Single location
            scraper = GoogleMapsScraper(headless=args.headless)
            scraper.scrape(
                keyword=args.keyword,
                location=locations[0],
                max_results=args.results
            )
        else:
            # Multiple locations
            scrape_multiple_locations(
                keyword=args.keyword,
                locations=locations,
                max_results=args.results,
                headless=args.headless
            )
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
