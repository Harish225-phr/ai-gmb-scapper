#!/usr/bin/env python3
"""
Google Maps Scraper - Command Line Interface

Simple CLI for scraping Google Maps without API.
Supports interactive mode and command-line arguments.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from google_maps_scraper import GoogleMapsScraper
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Google Maps Business Scraper - Extract leads without API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple search
  python cli.py -k "restaurants" -l "Delhi"
  
  # Advanced options
  python cli.py -k "plumbers" -l "Mumbai" -n 100 --headless -o results.csv
  
  # Multi-location batch
  python cli.py -k "gyms" -l "Delhi,Mumbai,Bangalore" -n 50 --batch
  
  # Interactive mode
  python cli.py --interactive
        """
    )
    
    parser.add_argument(
        '-k', '--keyword',
        type=str,
        help='Business type to search (e.g., "restaurants", "AC repair")'
    )
    
    parser.add_argument(
        '-l', '--location',
        type=str,
        help='Location to search in (e.g., "Delhi"). Use comma for multiple.'
    )
    
    parser.add_argument(
        '-n', '--max-results',
        type=int,
        default=50,
        help='Maximum results to collect (default: 50, max: 100)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (no browser GUI) - use for production'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output CSV filename (auto-generated if not specified)'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Batch mode: search multiple locations (location should be comma-separated)'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Interactive mode - prompts for all settings'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with verbose logging'
    )
    
    return parser.parse_args()


async def interactive_mode():
    """Run in interactive mode with prompts."""
    print("\n" + "="*60)
    print("Google Maps Scraper - Interactive Mode")
    print("="*60 + "\n")
    
    # Get keyword
    keyword = input("Enter business type (e.g., 'restaurants'): ").strip()
    if not keyword:
        print("Error: Keyword is required")
        return
    
    # Get location(s)
    location = input("Enter location (e.g., 'Delhi'): ").strip()
    if not location:
        print("Error: Location is required")
        return
    
    # Get max results
    try:
        max_results = int(input("Maximum results (50-100) [default: 50]: ") or "50")
        max_results = min(100, max(50, max_results))
    except ValueError:
        max_results = 50
    
    # Get headless mode
    headless = input("Run headless? (y/n) [default: n]: ").lower() == 'y'
    
    # Get output file
    output_file = input("Output filename [auto-generate]: ").strip() or None
    
    # Check for batch mode
    batch_mode = ',' in location
    
    logger.info(f"\nStarting scrape with:")
    logger.info(f"  Keyword: {keyword}")
    logger.info(f"  Location: {location}")
    logger.info(f"  Max Results: {max_results}")
    logger.info(f"  Headless: {headless}")
    logger.info(f"  Batch Mode: {batch_mode}\n")
    
    await scrape(keyword, location, max_results, headless, output_file, batch_mode)


async def scrape(keyword: str, location: str, max_results: int, 
                headless: bool, output_file: str = None, batch_mode: bool = False):
    """Execute scraping."""
    
    if batch_mode:
        await batch_scrape(keyword, location, max_results, headless)
    else:
        await single_scrape(keyword, location, max_results, headless, output_file)


async def single_scrape(keyword: str, location: str, max_results: int, 
                       headless: bool, output_file: str = None):
    """Scrape a single location."""
    
    scraper = GoogleMapsScraper(
        headless=headless,
        max_results=max_results,
        debug=True
    )
    
    try:
        await scraper.initialize()
        
        results = await scraper.scrape(
            keyword=keyword,
            location=location,
            output_file=output_file
        )
        
        # Print summary
        if results:
            logger.info("\n" + "="*60)
            logger.info("RESULTS SUMMARY")
            logger.info("="*60)
            logger.info(f"Total Results: {len(results)}")
            logger.info(f"With Websites: {sum(1 for r in results if r['website'] != 'N/A')}")
            logger.info(f"With Ratings: {sum(1 for r in results if r['rating'] != 'N/A')}")
            
            # Top 5
            rated = [(r['name'], r['rating']) for r in results if r['rating'] != 'N/A']
            if rated:
                top_5 = sorted(rated, key=lambda x: float(x[1]), reverse=True)[:5]
                logger.info("\nTop 5 Rated:")
                for i, (name, rating) in enumerate(top_5, 1):
                    logger.info(f"  {i}. {name}: {rating}★")
        else:
            logger.warning("No results found")
            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)
    finally:
        await scraper.close()


async def batch_scrape(keyword: str, location_str: str, max_results: int, headless: bool):
    """Scrape multiple locations."""
    
    locations = [loc.strip() for loc in location_str.split(',') if loc.strip()]
    logger.info(f"Batch mode: Scraping {len(locations)} locations\n")
    
    all_results = {}
    scraper = GoogleMapsScraper(
        headless=headless,
        max_results=max_results,
        debug=True
    )
    
    try:
        await scraper.initialize()
        
        for i, location in enumerate(locations, 1):
            logger.info(f"\n[{i}/{len(locations)}] Scraping {location}...")
            
            results = await scraper.scrape(
                keyword=keyword,
                location=location,
                output_file=f"results_{keyword.replace(' ', '_')}_{location}.csv"
            )
            
            all_results[location] = len(results)
            
            if i < len(locations):
                logger.info(f"Waiting before next location...")
                await asyncio.sleep(10)
        
        # Print batch summary
        logger.info("\n" + "="*60)
        logger.info("BATCH SUMMARY")
        logger.info("="*60)
        total = sum(all_results.values())
        logger.info(f"Total Locations: {len(locations)}")
        logger.info(f"Total Results: {total}")
        for location, count in all_results.items():
            logger.info(f"  {location}: {count} results")
            
    except Exception as e:
        logger.error(f"Batch scraping failed: {e}")
        sys.exit(1)
    finally:
        await scraper.close()


async def main():
    """Main entry point."""
    
    args = parse_arguments()
    
    # Check if running in interactive mode
    if args.interactive:
        await interactive_mode()
        return
    
    # Check required arguments
    if not args.keyword or not args.location:
        print("Error: --keyword and --location are required (or use --interactive)")
        print("Use -h for help")
        sys.exit(1)
    
    # Validate max_results
    args.max_results = min(100, max(10, args.max_results))
    
    # Detect batch mode
    batch_mode = args.batch or ',' in args.location
    
    logger.info(f"Google Maps Scraper")
    logger.info(f"Keyword: {args.keyword}")
    logger.info(f"Location: {args.location}")
    logger.info(f"Max Results: {args.max_results}")
    logger.info(f"Headless: {args.headless}")
    if batch_mode:
        logger.info("Mode: Batch")
    
    try:
        await scrape(
            keyword=args.keyword,
            location=args.location,
            max_results=args.max_results,
            headless=args.headless,
            output_file=args.output,
            batch_mode=batch_mode
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
