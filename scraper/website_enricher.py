"""
Website Enrichment Module

Finds missing websites for businesses using lightweight Google search (no API).
Complements OSM data with web search results to maximize lead quality.

Features:
- Google organic search (no API key required)
- BeautifulSoup-based URL extraction
- Caching to avoid duplicate searches
- Smart fallbacks and error handling
"""

import requests
import logging
import time
import hashlib
from typing import Optional, Dict, List
from urllib.parse import quote_plus, urlparse
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Simple in-memory cache for website searches
_website_cache: Dict[str, Optional[str]] = {}

# Google search headers to avoid blocking
GOOGLE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# Domain patterns to validate
VALID_DOMAIN_EXTENSIONS = ['.com', '.org', '.net', '.in', '.co', '.io', '.biz', '.info', '.shop', '.store']

# Last request time for rate limiting
_last_google_request_time = 0
GOOGLE_MIN_DELAY = 2.0  # 2 seconds between Google searches


def _rate_limit_google():
    """Enforce rate limiting for Google searches to avoid blocking."""
    global _last_google_request_time
    elapsed = time.time() - _last_google_request_time
    if elapsed < GOOGLE_MIN_DELAY:
        time.sleep(GOOGLE_MIN_DELAY - elapsed)
    _last_google_request_time = time.time()


def _normalize_url(url: str) -> str:
    """Normalize URL to domain-only format."""
    if not url:
        return ""
    
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix for consistency
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return url


def _is_valid_domain(url: str) -> bool:
    """Check if URL is a valid business domain."""
    if not url or len(url) < 5:
        return False
    
    url = url.lower()
    
    # Check for valid extension
    has_valid_ext = any(url.endswith(ext) for ext in VALID_DOMAIN_EXTENSIONS)
    if not has_valid_ext:
        return False
    
    # Exclude common non-business domains
    excluded = ['google.com', 'facebook.com', 'twitter.com', 'instagram.com', 
                'youtube.com', 'wikipedia.org', 'linkedin.com', 'reddit.com',
                'maps.google.com', 'maps.apple.com']
    for exc in excluded:
        if exc in url:
            return False
    
    return True


def _extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from text content."""
    urls = []
    
    # Simple regex to find URLs
    import re
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]*|www\.[^\s<>"{}|\\^`\[\]]*'
    matches = re.findall(pattern, text)
    
    for match in matches:
        normalized = _normalize_url(match)
        if _is_valid_domain(normalized) and normalized not in urls:
            urls.append(normalized)
    
    return urls


def _search_google_organic(query: str, num_results: int = 5) -> List[str]:
    """
    Perform a Google search and extract organic result URLs.
    
    Args:
        query: Search query
        num_results: Number of results to return
        
    Returns:
        List of domain URLs found
    """
    try:
        _rate_limit_google()
        
        # Google search URL
        url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results * 2}"
        
        response = requests.get(
            url,
            headers=GOOGLE_HEADERS,
            timeout=10,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Extract URLs from HTML content
        urls = _extract_urls_from_text(response.text)
        
        # Return only valid business domains
        valid_urls = [u for u in urls if _is_valid_domain(u)]
        
        logger.debug(f"Google search for '{query}' found {len(valid_urls)} valid domains")
        return valid_urls[:num_results]
        
    except requests.exceptions.Timeout:
        logger.warning(f"Google search timeout for '{query}'")
        return []
    except requests.exceptions.ConnectionError:
        logger.warning(f"Google search connection error for '{query}'")
        return []
    except Exception as e:
        logger.warning(f"Error searching Google for '{query}': {e}")
        return []


def _cache_key(name: str, location: str) -> str:
    """Generate cache key for website lookup."""
    key_str = f"{name.lower()}|{location.lower()}"
    return hashlib.md5(key_str.encode()).hexdigest()


def find_website_from_google(name: str, location: str, skip_cache: bool = False) -> Optional[str]:
    """
    Find website for a business using Google search (no API).
    
    Args:
        name: Business name
        location: Location/city
        skip_cache: Force fresh search (ignore cache)
        
    Returns:
        Website URL or None
    """
    if not name or not location:
        return None
    
    name = name.strip()
    location = location.strip()
    
    # Check cache first
    cache_key = _cache_key(name, location)
    if not skip_cache and cache_key in _website_cache:
        result = _website_cache[cache_key]
        logger.debug(f"Cache hit for '{name}': {result}")
        return result
    
    # Search query variations
    queries = [
        f"{name} {location} website",
        f"{name} {location} official site",
        f"{name} {location}",
    ]
    
    found_website = None
    
    for query in queries:
        try:
            results = _search_google_organic(query, num_results=3)
            if results:
                # Take the first valid result
                found_website = results[0]
                logger.info(f"Found website for '{name}': {found_website}")
                break
        except Exception as e:
            logger.debug(f"Error in query '{query}': {e}")
            continue
    
    # Cache the result (even if None)
    _website_cache[cache_key] = found_website
    
    return found_website


def validate_website(url: str) -> bool:
    """
    Validate that a website is accessible and not an error page.
    
    Args:
        url: Website URL to validate
        
    Returns:
        True if website is valid and accessible
    """
    if not url or not _is_valid_domain(url):
        return False
    
    try:
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        response = requests.head(
            url,
            timeout=5,
            allow_redirects=True,
            headers={'User-Agent': GOOGLE_HEADERS['User-Agent']}
        )
        
        # 2xx and 3xx are OK, 4xx/5xx are not
        return 200 <= response.status_code < 400
        
    except requests.exceptions.Timeout:
        logger.debug(f"Website validation timeout: {url}")
        return False
    except Exception as e:
        logger.debug(f"Website validation error for {url}: {e}")
        return False


def enrich_results(results: List[Dict], location: str, max_enrichments: int = 30, 
                   validate: bool = False) -> List[Dict]:
    """
    Enrich business results with websites using Google search.
    
    Args:
        results: List of business records
        location: Search location
        max_enrichments: Max number of businesses to enrich (to avoid timeouts)
        validate: Validate websites with HTTP requests
        
    Returns:
        List of enriched business records
    """
    enriched = []
    enrichment_count = 0
    
    for idx, business in enumerate(results):
        try:
            # Skip if already has website
            if business.get('website') and business['website'] != 'N/A':
                enriched.append(business)
                continue
            
            # Skip if reached enrichment limit
            if enrichment_count >= max_enrichments:
                enriched.append(business)
                continue
            
            name = business.get('name', '').strip()
            if not name:
                enriched.append(business)
                continue
            
            # Find website using Google search
            website = find_website_from_google(name, location)
            
            if website:
                # Optionally validate website
                if validate and not validate_website(website):
                    logger.debug(f"Website validation failed: {website}")
                    enriched.append(business)
                    enrichment_count += 1
                    continue
                
                # Update business record
                business['website'] = website
                business['website_source'] = 'google_enriched'
                enrichment_count += 1
                logger.info(f"Enriched '{name}' with website: {website}")
            
            enriched.append(business)
            
        except Exception as e:
            logger.warning(f"Error enriching result {idx}: {e}")
            enriched.append(business)
            continue
    
    logger.info(f"Enrichment complete: {enrichment_count} businesses enriched")
    return enriched


def load_website_cache(filepath: str) -> bool:
    """Load website cache from JSON file."""
    try:
        if Path(filepath).exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                _website_cache.update(cache_data)
                logger.info(f"Loaded {len(cache_data)} cached websites from {filepath}")
                return True
    except Exception as e:
        logger.warning(f"Failed to load website cache: {e}")
    return False


def save_website_cache(filepath: str) -> bool:
    """Save website cache to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(_website_cache, f, indent=2)
            logger.info(f"Saved {len(_website_cache)} cached websites to {filepath}")
            return True
    except Exception as e:
        logger.warning(f"Failed to save website cache: {e}")
    return False


def clear_website_cache():
    """Clear all cached websites."""
    global _website_cache
    _website_cache.clear()
    logger.info("Website cache cleared")


def get_cache_stats() -> Dict:
    """Get cache statistics."""
    return {
        'cached_websites': len(_website_cache),
        'with_website': sum(1 for v in _website_cache.values() if v),
        'without_website': sum(1 for v in _website_cache.values() if v is None),
    }
