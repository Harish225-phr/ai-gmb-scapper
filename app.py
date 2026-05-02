"""
Flask application using refactored lead scraper engine.
Production-grade API for lead generation with geo-grid expansion, caching, and deduplication.
Enhanced with batch processing for free-tier stability.
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from scraper.lead_scraper import LeadScraperEngine
from scraper.batch_processor import get_batch_processor
from scraper.config import config
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import json
import sys
import os
import time
import uuid
import re
from threading import Lock
import difflib

import requests
from werkzeug.exceptions import HTTPException

# Setup logging
logging.basicConfig(
    level=logging.INFO if not config.DEBUG_MODE else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={
    r"/search": {"origins": "*"},
    r"/search-multiple": {"origins": "*"},
    r"/search-batch": {"origins": "*"},
    r"/batch-status": {"origins": "*"},
    r"/health": {"origins": "*"},
    r"/metrics": {"origins": "*"},
    r"/config": {"origins": "*"},
    r"/cache/clear": {"origins": "*"}
})

# Initialize lead scraper engine (global instance) with error handling
scraper_engine = None

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]
OSM_HEADERS = {
    "User-Agent": "GMD-Tool/2.0 (free-no-api-mode)",
    "Accept": "application/json",
}
OSM_MIN_DELAY_SECONDS = 1.2
_osm_lock = Lock()
_last_osm_request_at = 0.0
COMMON_BUSINESS_TERMS = [
    "cafe", "coffee", "restaurant", "hotel", "hospital", "doctor", "clinic",
    "dentist", "school", "college", "gym", "salon", "spa", "pharmacy",
    "plumber", "electrician", "lawyer", "bank", "atm", "bakery", "barber",
]

def initialize_scraper():
    """Initialize scraper engine safely."""
    global scraper_engine
    
    # Check if API key is configured
    if not config.GOOGLE_API_KEY:
        logger.warning("⚠️ WARNING: Google API key not configured. Check environment variables.")
        api_key_status = "NOT_CONFIGURED"
    else:
        api_key_status = "CONFIGURED"
        logger.info(f"✅ API Key configured (first 10 chars: {config.GOOGLE_API_KEY[:10]}...)")
    
    try:
        scraper_engine = LeadScraperEngine(
            api_key=config.GOOGLE_API_KEY if config.GOOGLE_API_KEY else None,
            enable_caching=config.CACHE_ENABLED,
            enable_geo_expansion=True,
            fetch_websites_by_default=config.FETCH_WEBSITES_BY_DEFAULT,
        )
        logger.info("✅ Lead Scraper Engine initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize scraper engine: {str(e)}")
        return False

# Try to initialize on startup
try:
    if initialize_scraper():
        logger.info("🚀 Application started successfully")
    else:
        logger.warning("⚠️ Application started but scraper engine has issues")
except Exception as e:
    logger.error(f"Critical error during initialization: {str(e)}")
    scraper_engine = None


def log_error(msg):
    """Log errors to both stdout and stderr"""
    logger.error(msg)
    print(f"[ERROR] {msg}", file=sys.stderr)


def _normalize_search_mode(payload: dict) -> str:
    """Normalize requested search mode to supported values."""
    # If caller explicitly provided a search_mode, respect it (with common aliases).
    explicit = (payload or {}).get("search_mode")
    if explicit:
        mode = str(explicit).strip().lower()
        return "without_api" if mode in {"without_api", "without-api", "no_api", "no-api"} else "with_api"

    # No explicit mode requested — choose a sensible default based on availability of API key.
    return "with_api" if config.GOOGLE_API_KEY else "without_api"


def _extract_website(tags: dict) -> str:
    """Extract best possible website field from OSM tags."""
    if not tags:
        return "N/A"

    website = (
        tags.get("website")
        or tags.get("contact:website")
        or tags.get("url")
        or tags.get("contact:url")
    )
    if not website:
        return "N/A"

    website = website.strip()
    if not website:
        return "N/A"

    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"

    return website


def _extract_phone(tags: dict) -> str:
    """Extract phone from OSM tags where available."""
    if not tags:
        return "N/A"

    phone = (
        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("mobile")
        or tags.get("contact:mobile")
    )

    if not phone:
        return "N/A"

    phone = str(phone).strip()
    return phone if phone else "N/A"


def _normalize_website_url(url: str) -> str:
    """Ensure website URL has a valid scheme before checking."""
    if not url or url == "N/A":
        return ""

    normalized = url.strip()
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"
    return normalized


def _check_website_working(url: str) -> tuple:
    """Return (is_working, reason) for a website URL."""
    target = _normalize_website_url(url)
    if not target:
        return False, "no_website"

    try:
        response = requests.get(
            target,
            headers={"User-Agent": "Mozilla/5.0 (compatible; GMD-Tool/2.0)"},
            timeout=8,
            allow_redirects=True,
        )
        if 200 <= response.status_code < 400:
            return True, "working"
        return False, f"http_{response.status_code}"
    except requests.exceptions.SSLError:
        return False, "ssl_error"
    except requests.exceptions.Timeout:
        return False, "timeout"
    except requests.exceptions.ConnectionError:
        return False, "connection_error"
    except Exception:
        return False, "request_error"


def _filter_website_issue_results(result_rows: list) -> list:
    """
    Keep only rows where website is missing or website is not working.
    Also annotate each row with website_issue_reason.
    """
    if not result_rows:
        return []

    filtered = []

    def evaluate_row(row):
        row = dict(row)
        row.setdefault("phone", "N/A")
        website = row.get("website", "N/A")

        if not website or website == "N/A":
            row["website_issue_reason"] = "no_website"
            return row

        is_working, reason = _check_website_working(website)
        if not is_working:
            row["website_issue_reason"] = reason
            return row

        return None

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(evaluate_row, row) for row in result_rows]
        for future in as_completed(futures):
            candidate = future.result()
            if candidate:
                filtered.append(candidate)

    return filtered


def _geocode_location(location: str):
    """Resolve a location name to latitude/longitude using Nominatim."""
    _wait_for_osm_rate_limit()
    params = {
        "q": location,
        "format": "jsonv2",
        "limit": 1,
    }
    response = requests.get(
        NOMINATIM_SEARCH_URL,
        params=params,
        headers=OSM_HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not data:
        return None, None
    return float(data[0]["lat"]), float(data[0]["lon"])


def _wait_for_osm_rate_limit():
    """Throttle OSM calls to avoid public endpoint rate limits."""
    global _last_osm_request_at
    with _osm_lock:
        now = time.time()
        wait_time = OSM_MIN_DELAY_SECONDS - (now - _last_osm_request_at)
        if wait_time > 0:
            time.sleep(wait_time)
        _last_osm_request_at = time.time()


def _nominatim_keyword_search(keyword: str, location: str, limit: int) -> list:
    """Search businesses from Nominatim as primary no-key fallback."""
    results = []
    seen = set()

    query_variants = [
        f"{keyword} in {location}",
        f"{keyword} near {location}",
        f"{keyword} {location}",
    ]

    for query in query_variants:
        _wait_for_osm_rate_limit()
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": max(1, min(limit, 40)),
            "addressdetails": 1,
            "extratags": 1,
        }
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params=params,
            headers=OSM_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json() or []

        for item in data:
            display_name = (item.get("display_name") or "").strip()
            name = (item.get("name") or "").strip()
            if not name and display_name:
                name = display_name.split(",")[0].strip()
            if not name:
                continue

            extratags = item.get("extratags") or {}
            website = _extract_website(extratags)
            phone = _extract_phone(extratags)
            dedup_key = f"{name.lower()}|||{website.lower()}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            results.append({
                "name": name,
                "rating": "N/A",
                "reviews": "N/A",
                "website": website,
                "phone": phone,
            })

            if len(results) >= limit:
                return results

    return results


def _post_overpass_with_retry(query: str) -> dict:
    """Execute Overpass query with endpoint rotation and retry backoff."""
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(1):
            try:
                _wait_for_osm_rate_limit()
                response = requests.post(
                    endpoint,
                    data=query,
                    headers=OSM_HEADERS,
                    timeout=12,
                )

                if response.status_code == 429:
                    raise requests.HTTPError(
                        f"429 Too Many Requests from {endpoint}",
                        response=response,
                    )

                response.raise_for_status()
                return response.json() or {}
            except Exception as exc:
                last_error = exc
                # brief backoff before trying next mirror endpoint
                time.sleep(0.8 * (attempt + 1))

    if last_error:
        raise last_error
    return {"elements": []}


def _overpass_keyword_search(keyword: str, lat: float, lon: float, limit: int) -> list:
    """Use Overpass for richer POI coverage and websites when available."""
    keyword_pattern = re.escape(keyword).replace("\\ ", ".*")
    overpass_query = f"""
[out:json][timeout:25];
(
  nwr(around:12000,{lat},{lon})[name~"{keyword_pattern}",i][~"^(shop|amenity|office|craft|tourism|leisure)$"~"."];
);
out tags center {limit};
"""
    data = _post_overpass_with_retry(overpass_query.strip())

    unique = set()
    results = []
    for item in data.get("elements", []):
        tags = item.get("tags") or {}
        name = (tags.get("name") or "").strip()
        if not name:
            continue

        website = _extract_website(tags)
        phone = _extract_phone(tags)
        dedup_key = f"{name.lower()}|||{website.lower()}"
        if dedup_key in unique:
            continue
        unique.add(dedup_key)

        results.append({
            "name": name,
            "rating": "N/A",
            "reviews": "N/A",
            "website": website,
            "phone": phone,
        })

        if len(results) >= limit:
            break

    return results


def _infer_osm_category_filters(keyword: str) -> str:
    """Infer OSM amenity/shop filters from user keyword."""
    k = (keyword or "").strip().lower()

    category_map = {
        "cafe": "cafe",
        "coffee": "cafe",
        "restaurant": "restaurant|fast_food|food_court",
        "hotel": "hotel|guest_house|hostel|motel",
        "hospital": "hospital|clinic|doctors|dentist",
        "doctor": "doctors|clinic|hospital",
        "clinic": "clinic|hospital|doctors|dentist",
        "dentist": "dentist|clinic",
        "school": "school|college|university|kindergarten",
        "college": "college|university|school",
        "gym": "gym|fitness_centre|sports_centre",
        "salon": "hairdresser|beauty_salon",
        "spa": "spa|beauty_salon",
        "pharmacy": "pharmacy",
        "medical": "pharmacy|clinic|hospital|doctors",
        "plumber": "plumber",
        "electric": "electrician",
        "lawyer": "lawyer",
        "bank": "bank|atm",
        "atm": "atm|bank",
    }

    for key, value in category_map.items():
        if key in k:
            return value

    return ""


def _keyword_alternatives(keyword: str) -> list:
    """Return keyword alternatives including typo-corrected common business term."""
    base = (keyword or "").strip().lower()
    if not base:
        return []

    alternatives = [base]
    nearest = difflib.get_close_matches(base, COMMON_BUSINESS_TERMS, n=1, cutoff=0.72)
    if nearest and nearest[0] not in alternatives:
        alternatives.append(nearest[0])

    return alternatives


def _generic_nearby_fallback(location: str, limit: int) -> list:
    """Return generic local business results to avoid hard-zero UX."""
    generic_queries = [
        f"services in {location}",
        f"business in {location}",
        f"shops in {location}",
    ]

    merged = []
    seen = set()
    for query in generic_queries:
        try:
            rows = _nominatim_keyword_search(query, location, limit)
        except Exception:
            rows = []

        for row in rows:
            key = f"{row['name'].lower()}|||{row['website'].lower()}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
            if len(merged) >= limit:
                return merged

    return merged


def _overpass_category_search(keyword: str, lat: float, lon: float, limit: int) -> list:
    """Fallback category-based Overpass search when keyword search returns empty."""
    amenity_filter = _infer_osm_category_filters(keyword)
    if not amenity_filter:
        return []

    overpass_query = f"""
[out:json][timeout:12];
(
  nwr(around:12000,{lat},{lon})[amenity~"^({amenity_filter})$",i];
    nwr(around:12000,{lat},{lon})[shop~"^({amenity_filter})$",i];
    nwr(around:12000,{lat},{lon})[craft~"^({amenity_filter})$",i];
);
out tags center {limit};
"""
    data = _post_overpass_with_retry(overpass_query.strip())

    seen = set()
    results = []
    for item in data.get("elements", []):
        tags = item.get("tags") or {}
        name = (tags.get("name") or "").strip()
        if not name:
            continue

        website = _extract_website(tags)
        phone = _extract_phone(tags)
        dedup_key = f"{name.lower()}|||{website.lower()}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        results.append({
            "name": name,
            "rating": "N/A",
            "reviews": "N/A",
            "website": website,
            "phone": phone,
        })

        if len(results) >= limit:
            break

    return results


def search_without_api(keyword: str, location: str, max_results: int = 50) -> dict:
    """
    Free search mode using OpenStreetMap (no Google API key needed).
    Returns response in the same shape as existing search endpoints.
    """
    safe_limit = max(1, min(int(max_results or 50), 120))

    keyword_options = _keyword_alternatives(keyword)

    # Primary fallback: Nominatim keyword search (more stable under public limits)
    results = []
    source = "openstreetmap-nominatim"
    for kw in keyword_options:
        try:
            results = _nominatim_keyword_search(kw, location, safe_limit)
            if results:
                if kw != keyword.strip().lower():
                    source = "openstreetmap-nominatim-corrected-keyword"
                break
        except Exception as e:
            logger.warning(f"Nominatim keyword search failed for '{location}' ({kw}): {e}")

    # Secondary enrichment: Overpass only when Nominatim returned nothing.
    if len(results) == 0:
        try:
            lat, lon = _geocode_location(location)
            if lat is not None and lon is not None:
                primary_kw = keyword_options[-1] if keyword_options else keyword
                overpass_results = _overpass_keyword_search(primary_kw, lat, lon, safe_limit)
                merged = []
                seen = set()
                for row in results + overpass_results:
                    key = f"{row['name'].lower()}|||{row['website'].lower()}"
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(row)
                    if len(merged) >= safe_limit:
                        break
                results = merged
                source = "openstreetmap-nominatim+overpass"
        except Exception as e:
            logger.warning(f"Overpass fallback failed for '{location}': {e}")

    # Tertiary fallback: category-based nearby POIs for common local-business terms.
    if len(results) == 0:
        try:
            lat, lon = _geocode_location(location)
            if lat is not None and lon is not None:
                primary_kw = keyword_options[-1] if keyword_options else keyword
                category_results = _overpass_category_search(primary_kw, lat, lon, safe_limit)
                if category_results:
                    results = category_results
                    source = "openstreetmap-category-fallback"
        except Exception as e:
            logger.warning(f"Category fallback failed for '{location}': {e}")

    # Final fallback: generic local-business search (no key required).
    if len(results) == 0:
        generic_results = _generic_nearby_fallback(location, safe_limit)
        if generic_results:
            results = generic_results
            source = "openstreetmap-generic-fallback"

    return {
        "keyword": keyword,
        "location": location,
        "results": results,
        "next_page_token": None,
        "total_results": len(results),
        "mode": "without_api",
        "source": source,
    }


def _apply_result_filters(result_data: dict, website_issue_only: bool) -> dict:
    """Apply result-level filters and keep response shape intact."""
    if not website_issue_only or not isinstance(result_data, dict):
        return result_data

    rows = result_data.get("results") or []
    if not isinstance(rows, list):
        return result_data

    filtered_rows = _filter_website_issue_results(rows)
    updated = dict(result_data)
    updated["results"] = filtered_rows
    updated["total_results"] = len(filtered_rows)
    updated["website_issue_filter_applied"] = True
    return updated


def _apply_websites_only_filter(result_data: dict, websites_only: bool) -> dict:
    """If requested, reduce results to entries that have a website and return minimal fields.

    This is intentionally lightweight and does not perform any network checks so it's fast.
    """
    if not websites_only or not isinstance(result_data, dict):
        return result_data

    rows = result_data.get("results") or []
    if not isinstance(rows, list):
        return result_data

    filtered = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        website = r.get("website") or r.get("url") or ""
        if website and website != "N/A":
            filtered.append({
                "name": r.get("name") or r.get("display_name") or "N/A",
                "website": website,
            })

    updated = dict(result_data)
    updated["results"] = filtered
    updated["total_results"] = len(filtered)
    updated["websites_only"] = True
    return updated


# Global error handler to ensure all responses are valid JSON
@app.errorhandler(Exception)
def handle_error(error):
    """Catch all unhandled exceptions and return proper JSON error"""
    # If this is an HTTPException (404, 405, etc.), return its status and message
    if isinstance(error, HTTPException):
        error_msg = error.description
        log_error(f"HTTP error: {error_msg}")
        response = jsonify({
            "error": error_msg,
            "code": error.code
        })
        response.headers['Content-Type'] = 'application/json'
        return response, error.code

    error_msg = str(error)
    log_error(f"Unhandled exception: {error_msg}")
    import traceback
    traceback.print_exc()
    
    response = jsonify({
        "error": "Server error. Please try again later.",
        "details": error_msg if config.DEBUG_MODE else None
    })
    response.headers['Content-Type'] = 'application/json'
    return response, 500


# Ensure JSON responses have proper Content-Type
@app.after_request
def after_request(response):
    """Ensure JSON responses have proper Content-Type - skip HTML pages"""
    if response.content_type and 'text/html' in response.content_type:
        return response
    
    if response.is_json:
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    api_key_configured = bool(config.GOOGLE_API_KEY)
    scraper_ready = scraper_engine is not None
    
    return jsonify({
        "status": "ok",
        "message": "App is running",
        "version": "2.0",
        "api_key_configured": api_key_configured,
        "scraper_ready": scraper_ready,
        "features": {
            "geo_expansion": True,
            "caching": config.CACHE_ENABLED,
            "website_fetching": config.FETCH_WEBSITES_BY_DEFAULT,
            "parallel_requests": True,
        },
        "warning": "Google API key not configured" if not api_key_configured else None
    }), 200


@app.route('/favicon.ico')
def favicon():
    """Return no content for favicon to avoid 404 noise when no static file is provided."""
    return ('', 204)


@app.route("/")
def home():
    """Serve frontend."""
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    """
    Search for leads in a single location or with geo-grid expansion.
    
    Request JSON:
    {
        "keyword": "restaurants",
        "location": "Delhi",
        "use_expansion": true,  # Enable geo-grid expansion
        "fetch_websites": true,  # Fetch business websites
        "max_results": 60
    }
    """
    try:
        # Validate request
        if not request.json:
            return jsonify({"error": "Invalid JSON request"}), 400
        
        keyword = request.json.get("keyword", "").strip()
        location = request.json.get("location", "").strip()
        use_expansion = request.json.get("use_expansion", True)
        fetch_websites = request.json.get("fetch_websites")
        max_results = request.json.get("max_results")
        search_mode = _normalize_search_mode(request.json)
        website_issue_only = bool(request.json.get("website_issue_only", False))
        websites_only = bool(request.json.get("websites_only", False))
        websites_only = bool(request.json.get("websites_only", False))
        
        if not keyword or not location:
            return jsonify({"error": "Keyword and location are required"}), 400

        if search_mode == "with_api":
            # Check if scraper is initialized
            if scraper_engine is None:
                return jsonify({
                    "error": "Search service not available",
                    "details": "Google API Key not configured. Set GOOGLE_MAPS_API_KEY environment variable, or switch to WITHOUT API mode."
                }), 503

            # Check if API key is configured
            if not config.GOOGLE_API_KEY:
                return jsonify({
                    "error": "API Key not configured",
                    "details": "Set GOOGLE_MAPS_API_KEY environment variable or switch to WITHOUT API mode"
                }), 503

            logger.info(
                f"Search request: '{keyword}' in '{location}' "
                f"(mode={search_mode}, expansion={use_expansion})"
            )

            # Execute API-based search
            if use_expansion:
                result = scraper_engine.search_with_expansion(
                    keyword=keyword,
                    location=location,
                    fetch_websites=fetch_websites,
                    max_results_per_location=max_results
                )
            else:
                result = scraper_engine.search_single_location(
                    keyword=keyword,
                    location=location,
                    fetch_websites=fetch_websites,
                    max_results=max_results
                )

            response_data = result.to_dict()
            response_data["cache_stats"] = scraper_engine.get_metrics().get("cache_stats")
            response_data["mode"] = "with_api"
            response_data = _apply_result_filters(response_data, website_issue_only)
            response_data = _apply_websites_only_filter(response_data, websites_only)
            return jsonify(response_data), 200
        
        logger.info(f"Search request: '{keyword}' in '{location}' (mode=without_api)")
        response_data = search_without_api(keyword, location, max_results=max_results or 50)
        response_data = _apply_result_filters(response_data, website_issue_only)
        response_data = _apply_websites_only_filter(response_data, websites_only)
        return jsonify(response_data), 200
    
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        log_error(f"Search error: {str(e)}")
        return jsonify({
            "error": "Search failed. Please try again.",
            "details": str(e) if config.DEBUG_MODE else None
        }), 500


@app.route("/search-batch", methods=["POST"])
def search_batch():
    """
    Search for leads using batch processing (free-tier optimized).
    Processes one batch at a time to avoid timeouts.
    
    Request JSON:
    {
        "session_id": "optional-id",  # Optional, generated if not provided
        "keyword": "restaurants",
        "locations": ["Delhi", "Mumbai", "Bangalore"],  # Array of locations
        "batch_size": 2,  # How many locations per batch
        "use_expansion": false,
        "fetch_websites": true,
        "batch_index": 0  # Which batch to process (0 = first)
    }
    
    Response:
    {
        "session_id": "...",
        "batch_results": {...},  # Results for this batch
        "progress": {
            "current_batch": 1,
            "total_batches": 3,
            "locations_completed": 2,
            "total_locations": 6,
            "percent_complete": 33.3,
            "has_next_batch": true
        },
        "next_batch_index": 1
    }
    """
    try:
        if not request.json:
            return jsonify({"error": "Invalid JSON request"}), 400
        
        # Parse request
        session_id = request.json.get("session_id") or str(uuid.uuid4())
        keyword = request.json.get("keyword", "").strip()
        locations_input = request.json.get("locations", [])
        batch_size = request.json.get("batch_size", 2)
        batch_index = request.json.get("batch_index", 0)
        use_expansion = request.json.get("use_expansion", False)
        fetch_websites = request.json.get("fetch_websites", True)
        websites_only = bool(request.json.get("websites_only", False))
        search_mode = _normalize_search_mode(request.json)
        website_issue_only = bool(request.json.get("website_issue_only", False))

        if search_mode == "with_api":
            # Check if scraper is initialized
            if scraper_engine is None:
                return jsonify({
                    "error": "Search service not available",
                    "details": "Google API Key not configured. Set GOOGLE_MAPS_API_KEY environment variable, or switch to WITHOUT API mode."
                }), 503

            if not config.GOOGLE_API_KEY:
                return jsonify({
                    "error": "API Key not configured",
                    "details": "Set GOOGLE_MAPS_API_KEY environment variable or switch to WITHOUT API mode"
                }), 503
        
        if not keyword:
            return jsonify({"error": "Keyword is required"}), 400
        
        if not locations_input:
            return jsonify({"error": "Locations array is required"}), 400
        
        # Ensure locations is a list
        if isinstance(locations_input, str):
            locations = [loc.strip() for loc in locations_input.split(",") if loc.strip()]
        else:
            locations = [str(loc).strip() for loc in locations_input if loc.strip()]
        
        if not locations:
            return jsonify({"error": "At least one location is required"}), 400
        
        # Get or create batch session
        batch_processor = get_batch_processor()
        session = batch_processor.get_session(session_id)
        
        if not session:
            # Create new session
            session = batch_processor.create_session(
                session_id=session_id,
                keyword=keyword,
                locations=locations,
                use_expansion=use_expansion,
                fetch_websites=fetch_websites,
                batch_size=batch_size
            )
            logger.info(f"Created batch session: {session_id} with {len(locations)} locations")
        
        # Validate batch index
        if batch_index >= session.total_batches:
            return jsonify({
                "error": f"Invalid batch index {batch_index}. Total batches: {session.total_batches}"
            }), 400
        
        # Set current batch to requested index
        session.current_batch_index = batch_index
        
        # Get locations for this batch
        batch_locations = session.get_current_batch()
        logger.info(
            f"Processing batch {batch_index + 1}/{session.total_batches} "
            f"({len(batch_locations)} locations)"
        )
        
        # Execute searches for this batch
        def search_location(location):
            try:
                if search_mode == "without_api":
                    result_data = search_without_api(keyword, location, max_results=50)
                elif use_expansion:
                    result_data = scraper_engine.search_with_expansion(
                        keyword, location, fetch_websites
                    ).to_dict()
                else:
                    result_data = scraper_engine.search_single_location(
                        keyword, location, fetch_websites
                    ).to_dict()

                batch_processor.mark_location_completed(session_id, location)
                result_data = _apply_result_filters(result_data, website_issue_only)
                result_data = _apply_websites_only_filter(result_data, websites_only)
                return (location, result_data)
            except Exception as e:
                logger.error(f"Error searching {location}: {str(e)}")
                batch_processor.mark_location_failed(session_id, location)
                return (location, {"error": str(e), "results": []})
        
        # Execute batch searches with timeout
        batch_results = {}
        start_time = time.time()
        timeout_seconds = 40  # 40 seconds per batch (safe on free tier)
        
        try:
            max_workers = 1 if search_mode == "without_api" else min(batch_size, 3)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(search_location, loc): loc for loc in batch_locations
                }
                
                for future in as_completed(futures, timeout=timeout_seconds):
                    try:
                        location, result_data = future.result()
                        batch_results[location] = result_data
                    except Exception as e:
                        location = futures[future]
                        logger.error(f"Batch search error: {str(e)}")
                        batch_results[location] = {"error": str(e), "results": []}
        
        except Exception as e:
            logger.warning(f"Batch timeout or error: {str(e)}")
            # Return partial results if available
        
        elapsed = time.time() - start_time
        logger.info(f"Batch {batch_index + 1} completed in {elapsed:.1f}s with {len(batch_results)} results")
        
        # Build response
        response_data = {
            "session_id": session_id,
            "batch_index": batch_index,
            "batch_results": batch_results,
            "batch_results_count": len(batch_results),
            "progress": session.get_progress(),
            "next_batch_index": batch_index + 1 if session.has_next_batch() else None,
            "has_next_batch": session.has_next_batch(),
            "mode": search_mode,
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        log_error(f"Batch search error: {str(e)}")
        return jsonify({
            "error": "Batch search failed. Please try again.",
            "details": str(e) if config.DEBUG_MODE else None
        }), 500


@app.route("/batch-status/<session_id>", methods=["GET"])
def batch_status(session_id: str):
    """
    Get status of a batch processing session.
    """
    try:
        batch_processor = get_batch_processor()
        session = batch_processor.get_session(session_id)
        
        if not session:
            return jsonify({
                "error": "Session not found",
                "session_id": session_id
            }), 404
        
        return jsonify({
            "session_id": session_id,
            "progress": session.get_progress(),
            "metadata": session.to_dict(),
        }), 200
    
    except Exception as e:
        log_error(f"Error getting batch status: {str(e)}")
        return jsonify({
            "error": "Failed to get batch status",
            "details": str(e) if config.DEBUG_MODE else None
        }), 500


@app.route("/search-multiple", methods=["POST"])
def search_multiple():
    """
    Search across multiple locations in parallel.
    
    Request JSON:
    {
        "keyword": "restaurants",
        "locations": "Delhi, Mumbai, Bangalore",
        "use_expansion": false,
        "fetch_websites": true
    }
    """
    try:
        if not request.json:
            return jsonify({"error": "Invalid JSON request"}), 400
        
        keyword = request.json.get("keyword", "").strip()
        locations_str = request.json.get("locations", "").strip()
        use_expansion = request.json.get("use_expansion", False)
        fetch_websites = request.json.get("fetch_websites", True)
        websites_only = bool(request.json.get("websites_only", False))
        search_mode = _normalize_search_mode(request.json)
        website_issue_only = bool(request.json.get("website_issue_only", False))
        
        if not keyword or not locations_str:
            return jsonify({"error": "Keyword and locations are required"}), 400
        
        # Parse locations
        location_list = [
            loc.strip() for loc in locations_str.split(",") if loc.strip()
        ]
        
        if not location_list:
            return jsonify({"error": "At least one location is required"}), 400

        if search_mode == "with_api":
            # Check if scraper is initialized
            if scraper_engine is None:
                return jsonify({
                    "error": "Search service not available",
                    "details": "Google API Key not configured. Set GOOGLE_MAPS_API_KEY environment variable, or switch to WITHOUT API mode."
                }), 503

            # Check if API key is configured
            if not config.GOOGLE_API_KEY:
                return jsonify({
                    "error": "API Key not configured",
                    "details": "Set GOOGLE_MAPS_API_KEY environment variable or switch to WITHOUT API mode"
                }), 503
        
        logger.info(
            f"Multi-location search: '{keyword}' in {len(location_list)} locations (mode={search_mode})"
        )
        
        # Define search function for location execution
        def search_location(location):
            try:
                if search_mode == "without_api":
                    result_data = search_without_api(keyword, location, max_results=50)
                elif use_expansion:
                    result_data = scraper_engine.search_with_expansion(
                        keyword, location, fetch_websites
                    ).to_dict()
                else:
                    result_data = scraper_engine.search_single_location(
                        keyword, location, fetch_websites
                    ).to_dict()
                result_data = _apply_result_filters(result_data, website_issue_only)
                return (location, result_data)
            except Exception as e:
                logger.error(f"Error searching {location}: {str(e)}")
                return (location, {"error": str(e), "results": []})

        # Run without_api sequentially to avoid public endpoint timeouts/partial returns.
        if search_mode == "without_api":
            all_results = {}
            for loc in location_list:
                location, result_data = search_location(loc)
                result_data = _apply_websites_only_filter(result_data, websites_only)
                all_results[location] = result_data

            response_data = {
                "keyword": keyword,
                "locations_requested": len(location_list),
                "locations_completed": len(all_results),
                "results": all_results,
                "metrics": scraper_engine.get_metrics() if scraper_engine else None,
                "mode": search_mode,
            }

            return jsonify(response_data), 200
        
        # Execute parallel searches with early timeout
        start_time = time.time()
        all_results = {}
        
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            futures = [
                executor.submit(search_location, loc) for loc in location_list
            ]
            
            try:
                for future in as_completed(futures, timeout=90):  # 90 second limit to avoid worker timeout
                    try:
                        location, result_data = future.result()
                        result_data = _apply_websites_only_filter(result_data, websites_only)
                        all_results[location] = result_data
                    except Exception as e:
                        log_error(f"Future error: {str(e)}")
                        continue
                    
                    # Safety check: if we're taking too long, warn and return early
                    elapsed = time.time() - start_time
                    if elapsed > 100:
                        logger.warning(f"Search is taking too long ({elapsed:.1f}s), returning partial results")
                        break
            except Exception as e:
                log_error(f"Parallel search timeout: {str(e)}")
                logger.warning(f"Returning partial results. Completed: {len(all_results)}/{len(location_list)}")
        
        
        response_data = {
            "keyword": keyword,
            "locations_requested": len(location_list),
            "locations_completed": len(all_results),
            "results": all_results,
            "metrics": scraper_engine.get_metrics() if scraper_engine else None,
            "mode": search_mode,
        }
        
        return jsonify(response_data), 200
    
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error: {str(e)}")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        log_error(f"Search-multiple error: {str(e)}")
        return jsonify({
            "error": "Search failed. Please try again.",
            "details": str(e) if config.DEBUG_MODE else None
        }), 500


@app.route("/metrics", methods=["GET"])
def metrics():
    """Get system metrics and performance stats."""
    # Check if scraper is initialized
    if scraper_engine is None:
        return jsonify({
            "error": "Metrics unavailable",
            "details": "Scraper engine not initialized. Check GOOGLE_MAPS_API_KEY."
        }), 503
    
    return jsonify(scraper_engine.get_metrics()), 200


@app.route("/cache/clear", methods=["POST"])
def clear_cache():
    """Clear all caches (admin endpoint)."""
    try:
        # Check if scraper is initialized
        if scraper_engine is None:
            return jsonify({
                "error": "Cache clear failed",
                "details": "Scraper engine not initialized. Check GOOGLE_MAPS_API_KEY."
            }), 503
        
        scraper_engine.clear_caches()
        return jsonify({"message": "Caches cleared successfully"}), 200
    except Exception as e:
        log_error(f"Error clearing cache: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/config", methods=["GET"])
def get_config():
    """Get current configuration."""
    return jsonify({
        "max_workers": config.MAX_WORKERS,
        "max_concurrent_api_calls": config.MAX_CONCURRENT_API_CALLS,
        "max_pages_per_search": config.MAX_PAGES_PER_SEARCH,
        "max_results_per_location": config.MAX_RESULTS_PER_LOCATION,
        "request_timeout": config.REQUEST_TIMEOUT,
        "cache_enabled": config.CACHE_ENABLED,
        "fetch_websites_by_default": config.FETCH_WEBSITES_BY_DEFAULT,
        "api_key_configured": bool(config.GOOGLE_API_KEY),
        "search_modes": ["with_api", "without_api"],
    }), 200


if __name__ == "__main__":
    app.run(debug=config.DEBUG_MODE)