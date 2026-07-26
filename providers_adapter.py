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
        "type": "api",
        "systems": ["unified"],
        "base_url": "https://prepaid.bpdb.gov.bd/api",
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

def provider_get(provider_id: str, system: str, endpoint: str, account_no: str = "", meter_no: str = "", **extra_params) -> tuple:
    """
    Standardized provider API call. Returns (data, code, desc).
    """
    p_info = PROVIDERS.get(provider_id, PROVIDERS["desco"])
    if p_info.get("type") != "api":
        return None, 400, "Provider uses web portal or USSD gateway"

    base_url = p_info["base_url"]
    url = f"{base_url}/{system}/customer/{endpoint}"

    params = {}
    if account_no:
        params["accountNo"] = account_no
    if meter_no:
        params["meterNo"] = meter_no
    params.update(extra_params)

    try:
        r = requests.get(url, params=params, timeout=12, verify=False)
        raw = r.json()
        data = raw.get("data")
        code = raw.get("code", 0)
        desc = raw.get("desc", "Unknown response")
        return data, code, desc
    except Exception as e:
        return None, 500, str(e)
