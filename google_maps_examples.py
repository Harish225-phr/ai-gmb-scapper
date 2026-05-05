"""
Google Maps Scraper - Advanced Examples

Demonstrates various usage patterns and configurations.
"""

import asyncio
import json
from pathlib import Path
from google_maps_scraper import GoogleMapsScraper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Example 1: Single Location Search
async def example_single_location():
    """Scrape one location with basic config."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 1: Single Location Search")
    logger.info("="*60)
    
    scraper = GoogleMapsScraper(
        headless=False,  # Show browser
        max_results=30
    )
    
    try:
        await scraper.initialize()
        
        results = await scraper.scrape(
            keyword="coffee shops",
            location="Delhi",
            output_file="example1_coffee_delhi.csv"
        )
        
        logger.info(f"Found {len(results)} coffee shops in Delhi")
        
    finally:
        await scraper.close()


# Example 2: Multi-Location Search
async def example_multi_location():
    """Scrape multiple locations sequentially."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 2: Multi-Location Search")
    logger.info("="*60)
    
    locations = ["Delhi", "Mumbai", "Bangalore"]
    keyword = "restaurants"
    all_results = {}
    
    scraper = GoogleMapsScraper(
        headless=True,
        max_results=50
    )
    
    try:
        await scraper.initialize()
        
        for location in locations:
            logger.info(f"\nScraping {location}...")
            
            results = await scraper.scrape(
                keyword=keyword,
                location=location,
                output_file=f"restaurants_{location}.csv"
            )
            
            all_results[location] = {
                "count": len(results),
                "with_website": sum(1 for r in results if r['website'] != 'N/A'),
                "avg_rating": sum(float(r['rating'] or 0) for r in results if r['rating'] != 'N/A') / max(1, sum(1 for r in results if r['rating'] != 'N/A'))
            }
            
            # Delay between locations to avoid blocking
            await asyncio.sleep(10)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        for location, stats in all_results.items():
            logger.info(f"\n{location}:")
            logger.info(f"  Total Results: {stats['count']}")
            logger.info(f"  With Website: {stats['with_website']}")
            logger.info(f"  Avg Rating: {stats['avg_rating']:.2f}")
        
    finally:
        await scraper.close()


# Example 3: Filter and Process Results
async def example_advanced_filtering():
    """Scrape and filter results by custom criteria."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 3: Advanced Filtering")
    logger.info("="*60)
    
    scraper = GoogleMapsScraper(
        headless=True,
        max_results=75
    )
    
    try:
        await scraper.initialize()
        
        results = await scraper.scrape(
            keyword="hospitals",
            location="Delhi"
        )
        
        # Filter 1: High-rated (4.0+)
        high_rated = [r for r in results if r['rating'] != 'N/A' and float(r['rating']) >= 4.0]
        logger.info(f"\nHigh-rated (4.0+): {len(high_rated)}")
        
        # Filter 2: Have website
        with_website = [r for r in results if r['website'] != 'N/A']
        logger.info(f"With website: {len(with_website)}")
        
        # Filter 3: Many reviews (1000+)
        many_reviews = [r for r in results if r['reviews'] != 'N/A' and int(r['reviews'].replace(',', '')) >= 1000]
        logger.info(f"Many reviews (1000+): {len(many_reviews)}")
        
        # Save filtered results as JSON
        output = {
            "total_results": len(results),
            "high_rated": high_rated,
            "with_website": with_website,
            "many_reviews": many_reviews
        }
        
        with open("hospitals_filtered.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nFiltered results saved to hospitals_filtered.json")
        
    finally:
        await scraper.close()


# Example 4: Export to Multiple Formats
async def example_multiple_formats():
    """Scrape and export to CSV and JSON."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 4: Multiple Export Formats")
    logger.info("="*60)
    
    scraper = GoogleMapsScraper(
        headless=True,
        max_results=40
    )
    
    try:
        await scraper.initialize()
        
        results = await scraper.scrape(
            keyword="plumbers",
            location="Mumbai",
            output_file="plumbers_mumbai.csv"
        )
        
        # Export as JSON
        json_output = {
            "metadata": {
                "keyword": "plumbers",
                "location": "Mumbai",
                "total_results": len(results)
            },
            "data": results
        }
        
        with open("plumbers_mumbai.json", "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported to:")
        logger.info(f"  - CSV: plumbers_mumbai.csv")
        logger.info(f"  - JSON: plumbers_mumbai.json")
        
    finally:
        await scraper.close()


# Example 5: Error Handling and Retry Logic
async def example_retry_logic():
    """Scrape with retry logic for failed attempts."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 5: Retry Logic")
    logger.info("="*60)
    
    max_retries = 3
    attempt = 0
    
    while attempt < max_retries:
        try:
            scraper = GoogleMapsScraper(
                headless=True,
                max_results=35
            )
            
            await scraper.initialize()
            
            results = await scraper.scrape(
                keyword="gyms",
                location="Bangalore"
            )
            
            if results:
                logger.info(f"Success! Found {len(results)} gyms")
                await scraper.close()
                return results
            else:
                raise Exception("No results found")
                
        except Exception as e:
            attempt += 1
            logger.error(f"Attempt {attempt} failed: {e}")
            
            try:
                await scraper.close()
            except:
                pass
            
            if attempt < max_retries:
                wait_time = 5 * attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Failed after {max_retries} attempts")
                return []


# Example 6: Headless vs Visual Mode
async def example_debug_mode():
    """Compare headless mode (fast) vs visual mode (debuggable)."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 6: Debug Mode Comparison")
    logger.info("="*60)
    
    # Visual mode for debugging
    logger.info("\nRunning in VISUAL mode (headless=False)...")
    scraper_visual = GoogleMapsScraper(headless=False, max_results=20)
    
    try:
        await scraper_visual.initialize()
        
        results = await scraper_visual.scrape(
            keyword="banks",
            location="Delhi"
        )
        
        logger.info(f"Visual mode: Found {len(results)} results")
        
    finally:
        await scraper_visual.close()
    
    # Headless mode for production
    logger.info("\nRunning in HEADLESS mode (production)...")
    scraper_headless = GoogleMapsScraper(headless=True, max_results=20)
    
    try:
        await scraper_headless.initialize()
        
        results = await scraper_headless.scrape(
            keyword="banks",
            location="Delhi"
        )
        
        logger.info(f"Headless mode: Found {len(results)} results")
        
    finally:
        await scraper_headless.close()


# Example 7: Large-Scale Scraping
async def example_large_scale():
    """Scrape with large result limit."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 7: Large-Scale Scraping (100 results)")
    logger.info("="*60)
    
    scraper = GoogleMapsScraper(
        headless=True,
        max_results=100  # Maximum
    )
    
    try:
        await scraper.initialize()
        
        results = await scraper.scrape(
            keyword="restaurants",
            location="Delhi"
        )
        
        # Statistics
        logger.info(f"\nTotal Results: {len(results)}")
        logger.info(f"With Websites: {sum(1 for r in results if r['website'] != 'N/A')}")
        logger.info(f"With Ratings: {sum(1 for r in results if r['rating'] != 'N/A')}")
        
        # Top rated
        rated = [(r['name'], r['rating']) for r in results if r['rating'] != 'N/A']
        if rated:
            top_5 = sorted(rated, key=lambda x: float(x[1]), reverse=True)[:5]
            logger.info("\nTop 5 Rated:")
            for name, rating in top_5:
                logger.info(f"  {name}: {rating}★")
        
    finally:
        await scraper.close()


async def main():
    """Run all examples."""
    examples = [
        ("Single Location", example_single_location),
        ("Multi-Location", example_multi_location),
        ("Advanced Filtering", example_advanced_filtering),
        ("Multiple Export Formats", example_multiple_formats),
        ("Retry Logic", example_retry_logic),
        ("Debug vs Headless", example_debug_mode),
        ("Large-Scale Scraping", example_large_scale),
    ]
    
    print("\n" + "="*60)
    print("Google Maps Scraper - Advanced Examples")
    print("="*60)
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    try:
        choice = int(input("\nSelect example (1-7) or 0 for all: "))
    except ValueError:
        choice = 0
    
    if choice == 0:
        logger.info("Running all examples...\n")
        for name, example_func in examples:
            try:
                await example_func()
                await asyncio.sleep(5)  # Delay between examples
            except Exception as e:
                logger.error(f"Example failed: {e}")
    elif 1 <= choice <= len(examples):
        try:
            await examples[choice - 1][1]()
        except Exception as e:
            logger.error(f"Example failed: {e}")
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
