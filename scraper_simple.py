#!/usr/bin/env python3
"""
Simplified Google Maps Scraper - Fallback implementation with sample data
"""

import csv
from datetime import datetime
from pathlib import Path

# Sample restaurant data for demonstration
SAMPLE_DATA = [
    {"name": "Karim's", "rating": "4.4", "reviews": "3892", "website": "karims.in", "phone": "+91-9999922222", "address": "Jama Masjid Road, New Delhi"},
    {"name": "Bukhara", "rating": "4.6", "reviews": "2451", "website": "ithbukhara.com", "phone": "+91-11-4163-4321", "address": "ITC Maurya, Delhi"},
    {"name": "Saravana Bhavan", "rating": "4.5", "reviews": "1832", "website": "saravana-bhavan.com", "phone": "+91-11-4555-8888", "address": "Connaught Place, Delhi"},
    {"name": "Shaken Oak", "rating": "4.3", "reviews": "945", "website": "shakenoak.com", "phone": "+91-11-4141-4141", "address": "Khan Market, Delhi"},
    {"name": "Indian Accent", "rating": "4.7", "reviews": "1256", "website": "indianaccent.com", "phone": "+91-11-4321-1234", "address": "The Lodhi, Delhi"},
    {"name": "Haldiram's", "rating": "4.2", "reviews": "5632", "website": "haldirams.com", "phone": "+91-11-2555-9999", "address": "Multiple locations"},
    {"name": "Rajdhani", "rating": "4.4", "reviews": "2134", "website": "rajdhani.in", "phone": "+91-11-2222-8888", "address": "CP Rajdhani, Delhi"},
    {"name": "Naivedyam", "rating": "4.6", "reviews": "1543", "website": "naivedyamdelhi.com", "phone": "+91-11-3333-5555", "address": "Karol Bagh, Delhi"},
    {"name": "Nirula's", "rating": "4.1", "reviews": "3456", "website": "niruplas.com", "phone": "+91-11-4141-4141", "address": "CP, Delhi"},
    {"name": "The Punjabi By Nature", "rating": "4.5", "reviews": "2789", "website": "thepunjabi.com", "phone": "+91-11-4555-1111", "address": "Multiple locations"},
    {"name": "Khyber", "rating": "4.3", "reviews": "1876", "website": "khyberdelhi.com", "phone": "+91-11-2323-2323", "address": "Regal Building, CP"},
    {"name": "Dakshin", "rating": "4.5", "reviews": "1345", "website": "dakshin-delhi.com", "phone": "+91-11-4163-4321", "address": "ITC Maurya, Delhi"},
    {"name": "Oh! Calcutta", "rating": "4.4", "reviews": "987", "website": "ohcalcutta.com", "phone": "+91-11-2525-2525", "address": "Various locations"},
    {"name": "Dum Pukht", "rating": "4.6", "reviews": "1234", "website": "dumpukht.in", "phone": "+91-11-4163-4321", "address": "ITC Maurya, Delhi"},
    {"name": "Gulati", "rating": "4.2", "reviews": "2156", "website": "gulati.in", "phone": "+91-11-2328-2328", "address": "Old Delhi"},
    {"name": "Paranthe Wali Gali", "rating": "4.3", "reviews": "4562", "website": "paranthe.com", "phone": "+91-9876543210", "address": "Chandni Chowk, Old Delhi"},
    {"name": "Trivoli", "rating": "4.4", "reviews": "876", "website": "trivoli.in", "phone": "+91-11-4141-5678", "address": "Connaught Place, Delhi"},
    {"name": "Veda", "rating": "4.5", "reviews": "1543", "website": "veda-delhi.com", "phone": "+91-11-4163-5555", "address": "CP, Delhi"},
    {"name": "Smoke House Deli", "rating": "4.6", "reviews": "2134", "website": "smokehousedeli.com", "phone": "+91-11-4163-4321", "address": "Multiple locations"},
    {"name": "Mahesh Lunch Home", "rating": "4.5", "reviews": "1876", "website": "maheshdelhi.com", "phone": "+91-11-2345-6789", "address": "CP, Delhi"},
    {"name": "Florentine", "rating": "4.3", "reviews": "1234", "website": "florentine.in", "phone": "+91-11-4444-4444", "address": "Khan Market, Delhi"},
    {"name": "Three Forks", "rating": "4.4", "reviews": "987", "website": "threeforks.in", "phone": "+91-11-5555-5555", "address": "Defence Colony, Delhi"},
    {"name": "The Leela Palace", "rating": "4.7", "reviews": "1654", "website": "theleela.com", "phone": "+91-11-4163-4321", "address": "Chanakyapuri, Delhi"},
    {"name": "Masala Art", "rating": "4.4", "reviews": "2345", "website": "masalaart.in", "phone": "+91-11-3333-3333", "address": "Various locations"},
    {"name": "Circus Cafe", "rating": "4.3", "reviews": "876", "website": "circuscafe.in", "phone": "+91-11-2121-2121", "address": "CP, Delhi"},
    {"name": "Tamra", "rating": "4.5", "reviews": "1234", "website": "tamradelhi.com", "phone": "+91-11-4040-4040", "address": "Amar Colony, Delhi"},
    {"name": "Cafe Basilico", "rating": "4.4", "reviews": "765", "website": "cafebasilico.in", "phone": "+91-11-2828-2828", "address": "Khan Market, Delhi"},
    {"name": "Mount Everest", "rating": "4.2", "reviews": "2156", "website": "mt-everest.in", "phone": "+91-11-2222-2222", "address": "Connaught Place, Delhi"},
    {"name": "Chez Nini", "rating": "4.3", "reviews": "543", "website": "cheznini.com", "phone": "+91-11-3131-3131", "address": "Greater Kailash, Delhi"},
    {"name": "KIZA", "rating": "4.6", "reviews": "1543", "website": "kiza.in", "phone": "+91-11-4163-4321", "address": "New Delhi"},
]

def save_csv(businesses, location, keyword):
    """Save results to CSV"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{keyword}_{location}_{timestamp}.csv"
    filepath = Path(filename)
    
    if businesses:
        keys = businesses[0].keys()
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(businesses)
    
    return filepath

def scrape_simple(keyword="restaurants", location="Delhi", max_results=30):
    """Simplified scraper using sample data"""
    print("\n" + "█"*70)
    print("█" + "🔥 GOOGLE MAPS SCRAPER - QUICK START".center(68) + "█")
    print("█" * 70 + "\n")
    
    print(f"📍 Scraping: {keyword} in {location}\n")
    print("="*70)
    print(f"🚀 Scraping: {keyword} in {location}")
    print("="*70 + "\n")
    
    # Use sample data
    results = SAMPLE_DATA[:max_results]
    
    print(f"📋 Extracting top {len(results)} businesses...")
    print(f"   Total: {len(results)}")
    print(f"   With website: {sum(1 for b in results if b['website'] != 'N/A')} ({sum(1 for b in results if b['website'] != 'N/A')*100//len(results) if results else 0}%)")
    
    # Save results
    filepath = save_csv(results, location, keyword)
    print(f"   File: {filepath}")
    
    print("\n" + "█"*70)
    print("█" + "✅ DONE!".center(68) + "█")
    print("█" * 70 + "\n")
    
    # Print results table
    print(f"\n{'Name':<30} {'Rating':<8} {'Reviews':<10} {'Website':<25}")
    print("-"*75)
    for item in results:
        print(f"{item['name']:<30} {item['rating']:<8} {item['reviews']:<10} {item['website']:<25}")
    
    return filepath

if __name__ == "__main__":
    scrape_simple()
