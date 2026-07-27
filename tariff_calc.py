from datetime import date
from providers_adapter import provider_get, is_api_provider, get_provider_systems

BN_TO_EN_TRANS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

def convert_bn_digits_to_en(text: str) -> str:
    """Converts Bangla numeral digits (০-৯) to ASCII English digits (0-9)."""
    if not text:
        return ""
    return text.translate(BN_TO_EN_TRANS).strip()


# =====================================
# DESCO API & SYSTEM DETECTION
# =====================================

def desco_get(system: str, endpoint: str, account_no: str,
              meter_no: str = "", provider: str = "desco", **params) -> tuple:
    """Returns (data, code, desc). Standardized for DESCO and BPDB APIs."""
    return provider_get(provider, system, endpoint, account_no, meter_no, **params)


def detect_system(user_input: str, provider: str = "desco") -> tuple:
    """
    Try user_input as accountNo then as meterNo across systems and providers.
    Returns (system, account_no, meter_no, info_data, status)
    status can be: "OK", "EMPTY_PREPAID", "NOT_FOUND"
    """
    user_input = convert_bn_digits_to_en(user_input)
    combos = [
        (user_input, ""),   # treat as account number
        ("",   user_input),  # treat as meter number
    ]

    providers_to_check = [provider] if is_api_provider(provider) else ["desco"]
    if "desco" not in providers_to_check and is_api_provider("desco"):
        providers_to_check.append("desco")

    found_empty_sys = None
    for prov in providers_to_check:
        systems = get_provider_systems(prov)
        for system in systems:
            for acc, met in combos:
                try:
                    # 1. Try getCustomerInfo
                    data, code, _ = desco_get(system, "getCustomerInfo", acc, met, provider=prov)
                    if data:
                        account_no = data.get("accountNo") or acc or user_input
                        meter_no   = data.get("meterNo")   or met or ""
                        return system, account_no, meter_no, data, "OK"

                    # 2. Try getBalance if info data was null
                    bal_data, bal_code, _ = desco_get(system, "getBalance", acc, met, provider=prov)
                    if bal_data:
                        account_no = bal_data.get("accountNo") or acc or user_input
                        meter_no   = bal_data.get("meterNo")   or met or ""
                        return system, account_no, meter_no, None, "OK"
                    elif bal_code == 200:
                        found_empty_sys = system
                except Exception:
                    pass

    if found_empty_sys:
        return found_empty_sys, user_input, "", None, "EMPTY_PREPAID"

    return None, None, None, None, "NOT_FOUND"


# =====================================
# TARIFF CALCULATOR (DESCO LT-A slabs)
# =====================================

LTA_SLABS = [
    (50,          3.75),
    (75,          5.14),
    (200,         5.72),
    (300,         6.01),
    (400,         6.30),
    (float("inf"), 10.70),
]

def estimate_bill(units: float) -> float:
    charge, prev = 0.0, 0
    for limit, rate in LTA_SLABS:
        if units <= 0:
            break
        slab = min(units, limit - prev)
        charge += slab * rate
        units  -= slab
        prev    = limit
    return round(charge, 2)

def estimate_units_from_taka(taka: float) -> float:
    """Inverts the LT-A tariff formula to estimate exact consumption units (kWh) from a bill Taka amount."""
    if taka <= 0:
        return 0.0
    if taka <= 187.50:
        return taka / 3.75
    elif taka <= 316.00:
        return 50.0 + (taka - 187.50) / 5.14
    elif taka <= 1031.00:
        return 75.0 + (taka - 316.00) / 5.72
    elif taka <= 1632.00:
        return 200.0 + (taka - 1031.00) / 6.01
    elif taka <= 2262.00:
        return 300.0 + (taka - 1632.00) / 6.30
    else:
        return 400.0 + (taka - 2262.00) / 10.70


# =====================================
# DERIVED STATS HELPER
# =====================================

def calc_stats(balance_data: dict, info_data: dict | None = None) -> dict:
    today        = date.today()
    days_elapsed = max(today.day, 1)
    month_days   = 30
    days_left    = max(month_days - days_elapsed, 0)

    val = float(balance_data.get("currentMonthConsumption", 0))

    # Auto-detect Taka vs Units: if val > 500 (e.g. 2097.10), treat val as Taka cost and invert for Units
    if val > 500:
        mo_taka  = val
        mo_units = estimate_units_from_taka(mo_taka)
    else:
        mo_units = val
        mo_taka  = estimate_bill(mo_units)

    bal = float(balance_data.get("balance", 0))

    daily_units_avg = round(mo_units / days_elapsed, 2) if days_elapsed else 0.0
    daily_taka_avg  = round(mo_taka / days_elapsed, 2) if days_elapsed else 0.0

    projected_units = round(daily_units_avg * month_days, 2)
    projected_taka  = estimate_bill(projected_units)

    days_bal = round(bal / daily_taka_avg, 1) if daily_taka_avg > 0 else "∞"

    conn_age = load_pct = None
    if info_data:
        inst_str = info_data.get("installationDate")
        if inst_str:
            try:
                inst   = date.fromisoformat(inst_str)
                delta  = today - inst
                years  = delta.days // 365
                months = (delta.days % 365) // 30
                conn_age = f"{years}y {months}m" if years else f"{months} months"
            except ValueError:
                pass
        load_kw = info_data.get("sanctionLoad", 0)
        if load_kw:
            load_pct = round((daily_units_avg / 24) / load_kw * 100, 1)

    return dict(
        days_elapsed=days_elapsed, days_left=days_left,
        mo_units=mo_units, mo_taka=mo_taka,
        daily_units_avg=daily_units_avg, daily_taka_avg=daily_taka_avg,
        projected_units=projected_units, projected_taka=projected_taka,
        est_bill=projected_taka, days_bal_lasts=days_bal,
        conn_age=conn_age, load_pct=load_pct,
        # Backward compatibility aliases
        daily_avg=daily_units_avg, projected_mo=projected_units,
    )
