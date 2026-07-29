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

    # Check DESCO Postpaid fallback if user_input looks like a DESCO Postpaid account (e.g. 8 digits)
    if len(user_input) == 8:
        try:
            post_data, post_code, _ = desco_get("desco_postpaid", "getCustomerInfo", user_input, provider="desco")
            if post_data and post_code == 200:
                acc_no = post_data.get("accountNo") or user_input
                return "desco_postpaid", acc_no, "", post_data, "OK"
        except Exception:
            pass

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


# =====================================
# RECHARGE PATTERN ANALYTICS ENGINE
# =====================================

EN_TO_BN_TRANS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

def to_bn_digits(val) -> str:
    return str(val).translate(EN_TO_BN_TRANS)

def analyze_recharge_pattern(recharge_data: list, lang: str = "en") -> dict:
    """
    Analyzes recharge history to detect:
    1. Average days between recharges
    2. Average recharge amount
    3. Most probable recharge day range of month (e.g. 1st–5th)
    4. Most probable day of week (e.g. Friday)
    5. Estimated next recharge date & days remaining
    """
    from datetime import timedelta
    from collections import Counter

    if not recharge_data:
        return {"has_pattern": False, "formatted_text": ""}

    records = recharge_data if isinstance(recharge_data, list) else [recharge_data]
    parsed = []

    for r in records:
        raw_dt = str(r.get("rechargeDate") or r.get("date", "") or "").strip()
        amt = float(r.get("totalAmount") or r.get("rechargeAmount") or r.get("amount") or 0)
        if not raw_dt:
            continue
        dt_part = raw_dt[:10]
        try:
            d_obj = date.fromisoformat(dt_part)
            parsed.append({"date": d_obj, "amount": amt, "raw_dt": raw_dt})
        except ValueError:
            pass

    if not parsed:
        return {"has_pattern": False, "formatted_text": ""}

    parsed.sort(key=lambda x: x["date"])
    dates = [p["date"] for p in parsed]
    amounts = [p["amount"] for p in parsed if p["amount"] > 0]

    total_recharges = len(parsed)
    total_spent = sum(amounts)
    avg_amount = round(total_spent / len(amounts), 0) if amounts else 0.0

    unique_dates = sorted(list(set(dates)))
    gaps = [(unique_dates[i] - unique_dates[i-1]).days for i in range(1, len(unique_dates))]
    valid_gaps = [g for g in gaps if g > 0]
    avg_days_between = round(sum(valid_gaps) / len(valid_gaps), 1) if valid_gaps else 0.0

    day_brackets_en = {
        "1st–5th": 0, "6th–10th": 0, "11th–15th": 0,
        "16th–20th": 0, "21st–25th": 0, "26th–31st": 0
    }
    day_brackets_bn = {
        "১ম–৫ম": 0, "৬ষ্ঠ–১০ম": 0, "১১শ–১৫শ": 0,
        "১৬শ–২০শ": 0, "২১শ–২৫শ": 0, "২৬শ–৩১শ": 0
    }

    weekdays = []
    weekday_names_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_names_bn = ["সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার", "রবিবার"]

    for d in dates:
        day_num = d.day
        weekdays.append(d.weekday())

        if 1 <= day_num <= 5:
            day_brackets_en["1st–5th"] += 1
            day_brackets_bn["১ম–৫ম"] += 1
        elif 6 <= day_num <= 10:
            day_brackets_en["6th–10th"] += 1
            day_brackets_bn["৬ষ্ঠ–১০ম"] += 1
        elif 11 <= day_num <= 15:
            day_brackets_en["11th–15th"] += 1
            day_brackets_bn["১১শ–১৫শ"] += 1
        elif 16 <= day_num <= 20:
            day_brackets_en["16th–20th"] += 1
            day_brackets_bn["১৬শ–২০শ"] += 1
        elif 21 <= day_num <= 25:
            day_brackets_en["21st–25th"] += 1
            day_brackets_bn["২১শ–২৫শ"] += 1
        else:
            day_brackets_en["26th–31st"] += 1
            day_brackets_bn["২৬শ–৩১শ"] += 1

    top_bracket_en = max(day_brackets_en.items(), key=lambda x: x[1])[0]
    top_bracket_bn = max(day_brackets_bn.items(), key=lambda x: x[1])[0]

    weekday_counts = Counter(weekdays)
    most_common_wd_idx = weekday_counts.most_common(1)[0][0] if weekday_counts else 4
    wd_en = weekday_names_en[most_common_wd_idx]
    wd_bn = weekday_names_bn[most_common_wd_idx]

    last_date = dates[-1]
    today = date.today()
    predicted_next_date = last_date + timedelta(days=max(int(round(avg_days_between)), 1)) if avg_days_between > 0 else today + timedelta(days=15)
    days_remaining = (predicted_next_date - today).days

    EN = (lang == "en")
    if EN:
        freq_str = f"Every ~`{avg_days_between} days`" if avg_days_between > 0 else f"`{total_recharges} times` total"
        rem_str = f"(~`{days_remaining} days` remaining)" if days_remaining > 0 else ("(*Today!*)" if days_remaining == 0 else f"(`{abs(days_remaining)} days` overdue)")
        formatted_text = (
            f"📊 *Recharge Pattern & Analytics:*\n"
            f"• 🔁 *Top-up Frequency:* {freq_str} (Avg: `৳{avg_amount:,.0f}`)\n"
            f"• 📅 *Most Common Period:* `{top_bracket_en}` of the month ({wd_en}s)\n"
            f"• 🔮 *Predicted Next Top-up:* `{predicted_next_date.strftime('%Y-%m-%d')}` {rem_str}"
        )
    else:
        avg_days_bn = to_bn_digits(avg_days_between)
        avg_amt_bn = to_bn_digits(f"{avg_amount:,.0f}")
        pred_date_bn = to_bn_digits(predicted_next_date.strftime('%Y-%m-%d'))
        rem_days_bn = to_bn_digits(abs(days_remaining))

        freq_str = f"প্রতি ~`{avg_days_bn} দিন` পর" if avg_days_between > 0 else f"মোট `{to_bn_digits(total_recharges)} বার`"
        rem_str = f"(আনুমানিক ~`{rem_days_bn} দিন` বাকি)" if days_remaining > 0 else ("(*আজকে!*)" if days_remaining == 0 else f"(`{rem_days_bn} দিন` অতিবাহিত)")
        formatted_text = (
            f"📊 *রিচার্জ প্যাটার্ন ও বিশ্লেষণ:*\n"
            f"• 🔁 *রিচার্জের সময়সীমা:* {freq_str} (গড় পরিমাণ: `৳{avg_amt_bn}`)\n"
            f"• 📅 *সবচেয়ে সম্ভাব্য সময়:* মাসের `{top_bracket_bn}` তারিখ ({wd_bn})\n"
            f"• 🔮 *পরবর্তী সম্ভাব্য রিচার্জ:* `{pred_date_bn}` {rem_str}"
        )

    return {
        "has_pattern": True,
        "total_recharges": total_recharges,
        "total_spent": total_spent,
        "avg_amount": avg_amount,
        "avg_days_between": avg_days_between,
        "top_bracket": top_bracket_en if EN else top_bracket_bn,
        "most_common_weekday": wd_en if EN else wd_bn,
        "predicted_next_date": str(predicted_next_date),
        "days_remaining": days_remaining,
        "formatted_text": formatted_text,
    }
