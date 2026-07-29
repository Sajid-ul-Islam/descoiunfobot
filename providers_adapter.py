# Unified Multi-Provider API Adapter Engine
# Standardizes requests across DESCO, BPDB, BREB, DPDC, WZPDCL, NESCO

import os
import time
import requests
import urllib3
from portal_scraper import scrape_portal_data

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROVIDERS = {
    "desco": {
        "name": "DESCO (Dhaka North)",
        "type": "api",
        "systems": ["unified", "tkdes", "desco_postpaid", "postpaid"],
        "base_url": os.getenv("DESCO_API_URL", "https://prepaid.desco.org.bd/api"),
        "portal_url": "https://ebill.desco.org.bd/",
    },
    "bpdb": {
        "name": "BPDB (Chattogram & Zones)",
        "type": "api",
        "systems": ["unified", "cgp"],
        "base_url": os.getenv("BPDB_API_URL", "https://billonweb.bpdb.gov.bd/api"),
        "portal_url": "https://billonweb.bpdb.gov.bd/",
    },
    "dpdc": {
        "name": "DPDC (Dhaka South)",
        "type": "api",
        "systems": ["unified", "dpdc_prepaid"],
        "base_url": os.getenv("DPDC_API_URL", "https://prepaid.dpdc.org.bd/api"),
        "portal_url": "https://dpdc.org.bd/",
    },
    "breb": {
        "name": "Palli Bidyut (BREB)",
        "type": "api",
        "systems": ["unified", "pbs"],
        "base_url": os.getenv("BREB_API_URL", "https://prepaid.breb.gov.bd/api"),
        "ussd": "*727#",
        "hotline": "16899",
    },
    "wzpdcl": {
        "name": "WZPDCL (West Zone)",
        "type": "api",
        "systems": ["unified", "wz_prepaid"],
        "base_url": os.getenv("WZPDCL_API_URL", "https://prepaid.wzpdcl.gov.bd/api"),
        "portal_url": "https://wzpdcl.gov.bd/",
    },
    "nesco": {
        "name": "NESCO (North Zone)",
        "type": "api",
        "systems": ["unified", "nesco_prepaid"],
        "base_url": os.getenv("NESCO_API_URL", "https://prepaid.nesco.gov.bd/api"),
        "portal_url": "https://nesco.gov.bd/",
    }
}


def is_api_provider(provider_id: str) -> bool:
    """Returns True if the provider supports direct API or portal queries."""
    p_info = PROVIDERS.get(provider_id)
    return p_info.get("type") == "api" if p_info else False


def get_provider_systems(provider_id: str) -> list:
    """Returns supported system identifiers for the given provider."""
    p_info = PROVIDERS.get(provider_id, {})
    return p_info.get("systems", ["unified"])


_CACHE = {}
_CACHE_TTL = 30  # seconds

def _clean_expired_cache():
    """Prunes expired cache keys to prevent memory leaks."""
    now = time.time()
    expired = [k for k, (t, _) in _CACHE.items() if now - t > _CACHE_TTL]
    for k in expired:
        _CACHE.pop(k, None)

def _desco_get(system: str, endpoint: str, account_no: str = "", meter_no: str = "", **extra_params) -> tuple:
    _clean_expired_cache()
    base_url = PROVIDERS["desco"]["base_url"]
    url = f"{base_url}/{system}/customer/{endpoint}"

    params = {}
    if account_no:
        params["accountNo"] = account_no
    if meter_no:
        params["meterNo"] = meter_no
    params.update(extra_params)

    # Check cache
    cache_key = ("desco", system, endpoint, account_no, meter_no, tuple(sorted(params.items())))
    now = time.time()
    if cache_key in _CACHE:
        cached_time, cached_result = _CACHE[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_result

    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=12, verify=False)
            if r.status_code == 429:
                time.sleep(1.5)
                continue
            raw = r.json()
            data = raw.get("data")
            code = raw.get("code", 0)
            desc = raw.get("desc", "Unknown response")

            if "simpleRateLimit" in str(desc) or code == 429:
                time.sleep(1.5)
                continue

            result = (data, code, desc)
            if data is not None and code == 200:
                _CACHE[cache_key] = (now, result)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                return None, 500, str(e)
            time.sleep(1.0)

    return None, 429, "DESCO server rate limit reached ('simpleRateLimit'). Please wait 10 seconds before trying again."


def _generic_provider_get(provider_id: str, system: str, endpoint: str, account_no: str = "", meter_no: str = "", **extra_params) -> tuple:
    _clean_expired_cache()
    p_info = PROVIDERS.get(provider_id, {})
    base_url = p_info.get("base_url")
    url = f"{base_url}/{system}/{endpoint}"

    headers = {
        "User-Agent": "EnergyAssistantMobileApp/2.1 (Android)",
        "Accept": "application/json",
    }
    app_token = os.getenv(f"{provider_id.upper()}_APP_TOKEN")
    if app_token:
        headers["Authorization"] = f"Bearer {app_token}"

    params = {}
    if account_no:
        params["accountNo"] = account_no
    if meter_no:
        params["meterNo"] = meter_no
    params.update(extra_params)

    cache_key = (provider_id, system, endpoint, account_no, meter_no, tuple(sorted(params.items())))
    now = time.time()
    if cache_key in _CACHE:
        cached_time, cached_result = _CACHE[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_result

    # 1. Try Direct REST API endpoint
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5, verify=False)
        if r.status_code == 200:
            try:
                raw = r.json()
                data = raw.get("data", raw)
                code = raw.get("code", 200)
                desc = raw.get("desc", "OK")
                result = (data, code, desc)
                _CACHE[cache_key] = (now, result)
                return result
            except Exception:
                pass
    except Exception:
        pass

    # 2. Seamless Fallback to Automated Portal Scraper
    p_data, p_code, p_desc = scrape_portal_data(provider_id, account_no, meter_no)
    result = (p_data, p_code, p_desc)
    _CACHE[cache_key] = (now, result)
    return result


def provider_get(provider_id: str, system: str, endpoint: str, account_no: str = "", meter_no: str = "", **extra_params) -> tuple:
    """
    Standardized provider API call. Returns (data, code, desc).
    Dispatches to provider-specific adapters while guaranteeing standard dictionary structures.
    """
    if provider_id == "desco" and system in ("desco_postpaid", "postpaid"):
        return scrape_portal_data("desco_postpaid", account_no, meter_no)
    elif provider_id == "desco":
        return _desco_get(system, endpoint, account_no, meter_no, **extra_params)
    else:
        return _generic_provider_get(provider_id, system, endpoint, account_no, meter_no, **extra_params)

