#!/usr/bin/env python3
"""
Test Script for Hybrid Scraping System (OSM + Google Enrichment)

Demonstrates the new features:
- Pure OSM search
- OSM + Enrichment
- Cache statistics
- Performance comparison
"""

import requests
import json
import time
from typing import Dict, List

# Configuration
BASE_URL = "http://localhost:5000"
KEYWORD = "AC repair"
LOCATIONS = ["Delhi"]  # Start with 1 for testing

def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_results_summary(data: Dict):
    """Print summary of search results."""
    if "error" in data:
        print(f"❌ Error: {data['error']}")
        return
    
    print(f"📊 Results Summary:")
    print(f"  Locations requested: {data.get('locations_requested', 0)}")
    print(f"  Locations completed: {data.get('locations_completed', 0)}")
    print(f"  Search mode: {data.get('mode', 'unknown')}")
    
    for location, result_data in data.get('results', {}).items():
        print(f"\n  📍 {location}:")
        
        if "error" in result_data:
            print(f"     ❌ Error: {result_data['error']}")
            continue
        
        results = result_data.get('results', [])
        total = len(results)
        with_website = sum(1 for r in results if r.get('website', 'N/A') != 'N/A')
        enriched = sum(1 for r in results if r.get('website_source') == 'google_enriched')
        
        print(f"     Total businesses: {total}")
        print(f"     With website: {with_website} ({with_website*100//total if total > 0 else 0}%)")
        if enriched > 0:
            print(f"     Google-enriched: {enriched}")
        print(f"     Source: {result_data.get('source', 'unknown')}")
        
        if result_data.get('enrichment_applied'):
            print(f"     ✅ Enrichment: Applied")
        else:
            print(f"     ⚠️  Enrichment: Not applied or disabled")
        
        # Show first 3 results
        if results:
            print(f"\n     Sample results:")
            for i, r in enumerate(results[:3], 1):
                name = r.get('name', 'N/A')
                rating = r.get('rating', 'N/A')
                website = r.get('website', 'N/A')
                source = r.get('website_source', 'osm')
                print(f"       {i}. {name}")
                print(f"          Rating: {rating} | Website: {website} [{source}]")


def test_pure_osm_search():
    """Test 1: Pure OSM search without enrichment."""
    print_section("TEST 1: Pure OSM Search (No Enrichment)")
    
    print(f"Searching for: '{KEYWORD}' in {LOCATIONS}")
    print("Settings: enable_enrichment=False (original behavior)\n")
    
    start_time = time.time()
    
    response = requests.post(
        f"{BASE_URL}/search-multiple",
        json={
            "keyword": KEYWORD,
            "locations": ",".join(LOCATIONS),
            "enable_enrichment": False,
            "search_mode": "without_api",
            "websites_only": False
        },
        timeout=120
    )
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        print_results_summary(data)
        print(f"\n⏱️  Processing time: {elapsed:.1f}s")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Response: {response.text}")


def test_hybrid_search_with_enrichment():
    """Test 2: Hybrid search with enrichment."""
    print_section("TEST 2: Hybrid OSM + Google Enrichment")
    
    print(f"Searching for: '{KEYWORD}' in {LOCATIONS}")
    print("Settings: enable_enrichment=True, max_enrichments=30\n")
    
    start_time = time.time()
    
    response = requests.post(
        f"{BASE_URL}/search-multiple",
        json={
            "keyword": KEYWORD,
            "locations": ",".join(LOCATIONS),
            "enable_enrichment": True,
            "max_enrichments": 30,
            "search_mode": "without_api",
            "websites_only": False
        },
        timeout=120
    )
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        print_results_summary(data)
        print(f"\n⏱️  Processing time: {elapsed:.1f}s")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Response: {response.text}")


def test_cache_statistics():
    """Test 3: Check enrichment cache statistics."""
    print_section("TEST 3: Enrichment Cache Statistics")
    
    response = requests.get(f"{BASE_URL}/enrichment/cache/stats")
    
    if response.status_code == 200:
        data = response.json()
        stats = data.get('cache_stats', {})
        
        print(f"📊 Cache Statistics:")
        print(f"   Total cached: {stats.get('cached_websites', 0)}")
        print(f"   With website: {stats.get('with_website', 0)}")
        print(f"   Without website: {stats.get('without_website', 0)}")
    else:
        print(f"❌ Request failed: {response.status_code}")


def test_websites_only_filter():
    """Test 4: Filter to only results with websites."""
    print_section("TEST 4: Websites Only Filter")
    
    print(f"Searching for: '{KEYWORD}' in {LOCATIONS}")
    print("Settings: enable_enrichment=True, websites_only=True\n")
    print("(Only businesses with websites will be returned)\n")
    
    response = requests.post(
        f"{BASE_URL}/search-multiple",
        json={
            "keyword": KEYWORD,
            "locations": ",".join(LOCATIONS),
            "enable_enrichment": True,
            "max_enrichments": 20,
            "websites_only": True,
            "search_mode": "without_api"
        },
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        print_results_summary(data)
    else:
        print(f"❌ Request failed: {response.status_code}")


def test_clear_cache():
    """Test 5: Clear cache."""
    print_section("TEST 5: Clear Cache")
    
    response = requests.post(f"{BASE_URL}/enrichment/cache/clear")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data.get('message', 'Cache cleared')}")
        
        # Show new stats
        response = requests.get(f"{BASE_URL}/enrichment/cache/stats")
        if response.status_code == 200:
            data = response.json()
            stats = data.get('cache_stats', {})
            print(f"\n📊 Cache after clear:")
            print(f"   Total cached: {stats.get('cached_websites', 0)}")
    else:
        print(f"❌ Request failed: {response.status_code}")


def compare_results():
    """Test 6: Compare results before and after enrichment."""
    print_section("TEST 6: Performance Comparison")
    
    print(f"Comparing performance with/without enrichment\n")
    
    # Pure OSM
    print("Running OSM-only search...")
    start = time.time()
    r1 = requests.post(
        f"{BASE_URL}/search-multiple",
        json={
            "keyword": KEYWORD,
            "locations": ",".join(LOCATIONS),
            "enable_enrichment": False,
            "search_mode": "without_api",
            "websites_only": False
        },
        timeout=120
    )
    time_osm = time.time() - start
    
    # Clear cache
    requests.post(f"{BASE_URL}/enrichment/cache/clear")
    time.sleep(1)
    
    # With enrichment
    print("Running hybrid search with enrichment...")
    start = time.time()
    r2 = requests.post(
        f"{BASE_URL}/search-multiple",
        json={
            "keyword": KEYWORD,
            "locations": ",".join(LOCATIONS),
            "enable_enrichment": True,
            "max_enrichments": 30,
            "search_mode": "without_api",
            "websites_only": False
        },
        timeout=120
    )
    time_hybrid = time.time() - start
    
    if r1.status_code == 200 and r2.status_code == 200:
        data1 = r1.json()
        data2 = r2.json()
        
        # Extract metrics
        loc = LOCATIONS[0]
        results1 = data1['results'][loc]['results']
        results2 = data2['results'][loc]['results']
        
        websites1 = sum(1 for r in results1 if r.get('website', 'N/A') != 'N/A')
        websites2 = sum(1 for r in results2 if r.get('website', 'N/A') != 'N/A')
        
        print(f"\n📊 Comparison Results:")
        print(f"\n  Pure OSM Search:")
        print(f"    Total businesses: {len(results1)}")
        print(f"    With website: {websites1} ({websites1*100//len(results1) if results1 else 0}%)")
        print(f"    Processing time: {time_osm:.1f}s")
        
        print(f"\n  Hybrid (OSM + Enrichment):")
        print(f"    Total businesses: {len(results2)}")
        print(f"    With website: {websites2} ({websites2*100//len(results2) if results2 else 0}%)")
        print(f"    Processing time: {time_hybrid:.1f}s")
        
        print(f"\n  ✨ Improvement:")
        if len(results2) > len(results1):
            improvement = (len(results2) - len(results1)) * 100 // len(results1)
            print(f"    More businesses: +{improvement}% ({len(results2) - len(results1)} more)")
        
        if websites2 > websites1:
            improvement = (websites2 - websites1) * 100 // len(results1)
            print(f"    More websites: +{improvement}% ({websites2 - websites1} more)")
        
        if websites2 > 0:
            website_pct = websites2 * 100 // len(results2)
            print(f"    Website coverage: {website_pct}% (was {websites1*100//len(results1) if results1 else 0}%)")
        
        print(f"    Time tradeoff: +{time_hybrid - time_osm:.1f}s for much better results")
    else:
        print(f"❌ One or both requests failed")


def main():
    """Run all tests."""
    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  🚀 HYBRID SCRAPING SYSTEM - TEST SUITE".center(68) + "█")
    print("█" + "  OSM + Google Enrichment".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    print(f"\n📍 Testing Configuration:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Keyword: {KEYWORD}")
    print(f"   Locations: {LOCATIONS}")
    print(f"\n⏳ Starting tests...\n")
    
    try:
        # Run tests
        test_pure_osm_search()
        time.sleep(2)
        
        test_hybrid_search_with_enrichment()
        time.sleep(2)
        
        test_cache_statistics()
        time.sleep(2)
        
        test_websites_only_filter()
        time.sleep(2)
        
        test_clear_cache()
        time.sleep(2)
        
        compare_results()
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection failed!")
        print(f"Make sure Flask server is running on {BASE_URL}")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
    
    print("\n" + "█" * 70)
    print("█" + "  ✅ TEST SUITE COMPLETE".center(68) + "█")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
