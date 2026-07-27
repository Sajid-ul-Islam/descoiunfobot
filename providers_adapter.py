# Unified Multi-Provider API Adapter Engine
# Standardizes requests across DESCO, BPDB, BREB, DPDC, WZPDCL, NESCO

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROVIDERS = {
    "desco": {
        "name": "DESCO (Dhaka North)",
        "type": "api",
        "systems": ["unified", "tkdes"],
        "base_url": "https://prepaid.desco.org.bd/api",
    },
    "bpdb": {
        "name": "BPDB (Chattogram & Zones)",
        "type": "portal",
        "portal_url": "https://billonweb.bpdb.gov.bd/",
    },
    "dpdc": {
        "name": "DPDC (Dhaka South)",
        "type": "portal",
        "portal_url": "https://dpdc.org.bd/",
    },
    "breb": {
        "name": "Palli Bidyut (BREB)",
        "type": "ussd_guide",
        "ussd": "*727#",
        "hotline": "16899",
    },
    "wzpdcl": {
        "name": "WZPDCL (West Zone)",
        "type": "portal",
        "portal_url": "https://wzpdcl.gov.bd/",
    },
    "nesco": {
        "name": "NESCO (North Zone)",
        "type": "portal",
        "portal_url": "https://nesco.gov.bd/",
    }
}


def is_api_provider(provider_id: str) -> bool:
    """Returns True if the provider supports direct API queries."""
    p_info = PROVIDERS.get(provider_id)
    return p_info.get("type") == "api" if p_info else False


def get_provider_systems(provider_id: str) -> list:
    """Returns supported system identifiers for the given provider."""
    p_info = PROVIDERS.get(provider_id, {})
    return p_info.get("systems", ["unified"])


import time

_CACHE = {}
_CACHE_TTL = 30  # seconds

def _desco_get(system: str, endpoint: str, account_no: str = "", meter_no: str = "", **extra_params) -> tuple:
    base_url = PROVIDERS["desco"]["base_url"]
    url = f"{base_url}/{system}/customer/{endpoint}"

    params = {}
    if account_no:
        params["accountNo"] = account_no
    if meter_no:
        params["meterNo"] = meter_no
    params.update(extra_params)

    # Check cache
    cache_key = (system, endpoint, account_no, meter_no, tuple(sorted(params.items())))
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


def provider_get(provider_id: str, system: str, endpoint: str, account_no: str = "", meter_no: str = "", **extra_params) -> tuple:
    """
    Standardized provider API call. Returns (data, code, desc).
    Dispatches to provider-specific adapters while guaranteeing standard dictionary structures.
    """
    p_info = PROVIDERS.get(provider_id, PROVIDERS["desco"])
    p_type = p_info.get("type")

    if p_type != "api":
        return None, 400, f"{p_info.get('name', 'Provider')} uses web portal or USSD gateway"

    if provider_id == "desco":
        return _desco_get(system, endpoint, account_no, meter_no, **extra_params)

    # Modular hooks for future API adapters can be added here
    return None, 400, f"Live API adapter for {provider_id} not configured"
