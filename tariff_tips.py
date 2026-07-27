# Tariff Slab Smart Tip Generator & Low Balance Alert Module

def get_tariff_tip(units: float, lang: str = "en") -> str:
    """Calculates current slab and gives actionable tip to avoid higher slab rate."""
    if units <= 50:
        slab_name = "Slab 1 (0-50 kWh @ ৳3.75/unit)" if lang == "en" else "ধাপ ১ (০-৫০ ইউনিট @ ৳৩.৭৫/ইউনিট)"
        rem = 50 - units
        tip = f"💡 Keep usage under 50 units ({rem:.1f} kWh left) to maintain the lowest lifeline tariff!" if lang == "en" else f"💡 ৫০ ইউনিটের নিচে ব্যবহার বজায় রাখলে সর্বনিম্নে জীবনযাত্রা ট্যারিফ সুবিধা পাবেন! (আরও {rem:.1f} ইউনিট বাকি)"
    elif units <= 75:
        slab_name = "Slab 2 (51-75 kWh @ ৳5.14/unit)" if lang == "en" else "ধাপ ২ (৫১-৭৫ ইউনিট @ ৳৫.১৪/ইউনিট)"
        rem = 75 - units
        tip = f"💡 Keep usage under 75 units ({rem:.1f} kWh left) to avoid jumping to ৳5.72/unit!" if lang == "en" else f"💡 ৭৫ ইউনিটের মধ্যে রাখলে ৳৫.৭২ ধাপে যাওয়া থেকে বাঁচবেন! (আরও {rem:.1f} ইউনিট বাকি)"
    elif units <= 200:
        slab_name = "Slab 3 (76-200 kWh @ ৳5.72/unit)" if lang == "en" else "ধাপ ৩ (৭৬-২০০ ইউনিট @ ৳৫.৭২/ইউনিট)"
        rem = 200 - units
        tip = f"💡 Keep usage under 200 units ({rem:.1f} kWh left) to avoid jumping to ৳6.01/unit!" if lang == "en" else f"💡 ২০০ ইউনিটের নিচে থাকলে পরবর্তী উচ্চতর ধাপ এড়ানো সম্ভব! (আরও {rem:.1f} ইউনিট বাকি)"
    elif units <= 300:
        slab_name = "Slab 4 (201-300 kWh @ ৳6.01/unit)" if lang == "en" else "ধাপ ৪ (২০১-৩০০ ইউনিট @ ৳৬.০১/ইউনিট)"
        rem = 300 - units
        tip = f"💡 Stay under 300 units ({rem:.1f} kWh left) to prevent stepping into ৳6.30/unit!" if lang == "en" else f"💡 ৩০০ ইউনিটের মধ্যে রাখার চেষ্টা করুন। (আরও {rem:.1f} ইউনিট বাকি)"
    elif units <= 400:
        slab_name = "Slab 5 (301-400 kWh @ ৳6.30/unit)" if lang == "en" else "ধাপ ৫ (৩০১-৪০০ ইউনিট @ ৳৬.৩০/ইউনিট)"
        rem = 400 - units
        tip = f"💡 Stay under 400 units ({rem:.1f} kWh left) to avoid the maximum ৳10.70/unit slab!" if lang == "en" else f"💡 ৪০০ ইউনিটের নিচে রাখলে সর্বোচ্চ ৳১০.৭০ ধাপ এড়ানো যাবে! (আরও {rem:.1f} ইউনিট বাকি)"
    else:
        slab_name = "Slab 6 (>400 kWh @ ৳10.70/unit)" if lang == "en" else "ধাপ ৬ (>৪০০ ইউনিট @ ৳১০.৭০/ইউনিট)"
        tip = "⚠️ You are in the highest tariff slab (৳10.70/unit). Turn off non-essential AC/appliances to save bill!" if lang == "en" else "⚠️ আপনি সর্বোচ্চ বিদ্যুৎ ধাপে আছেন (৳১০.৭০/ইউনিট)। অতিরিক্ত এসি/হিটার ব্যবহারে সতর্ক হোন!"

    lbl = "📋 *Tariff Slab Monitor:*" if lang == "en" else "📋 *ট্যারিফ ধাপ মনিটর:*"
    return f"{lbl}\n• {slab_name}\n• {tip}"

def get_low_balance_warning(balance: float, daily_avg: float = 0, lang: str = "en") -> str:
    """Returns low balance warning banner if balance < 100 or < 3 days remaining."""
    days_left = balance / daily_avg if daily_avg > 0 else 999
    if balance <= 100 or days_left <= 3:
        if lang == "bn":
            return f"\n\n🚨 *সতর্কতা: প্রিপেইড ব্যালেন্স কম!*\nবর্তমান ব্যালেন্স মাত্র *৳{balance:.2f}*। বিদ্যুৎ বিচ্ছেদ এড়াতে এখনই বিকাশ বা নগদ দিয়ে রিচার্জ করুন।"
        else:
            return f"\n\n🚨 *CRITICAL LOW BALANCE ALERT!*\nCurrent balance is only *৳{balance:.2f}*. Recharge now via bKash/Nagad to prevent disconnection!"
    return ""


def get_tariff_slab_warning(mo_use: float, projected_mo: float, days_elapsed: int, days_left: int, lang: str = "en") -> str:
    """Predicts if month-end consumption will cross expensive slab thresholds (300 or 400 kWh) and calculates exact reduction targets and taka savings."""
    if days_left <= 0:
        return ""

    curr_daily = mo_use / max(days_elapsed, 1)

    # 1. Warning for crossing 400 kWh (Slab 6 Jump to ৳10.70/unit)
    if projected_mo > 400 and mo_use < 400:
        rem_units = 400 - mo_use
        target_daily = rem_units / days_left
        reduction = max(curr_daily - target_daily, 0)
        over_units = projected_mo - 400
        extra_cost = over_units * 10.70

        if lang == "bn":
            return (
                f"\n\n🚨 *স্মার্ট ট্যারিফ সতর্কতা (৪০০ ইউনিট থ্রেশহোল্ড)*\n"
                f"বর্তমান ব্যবহারের হারে আপনার মাস শেষে আনুমানিক ব্যবহার দাঁড়াবে *{projected_mo:.1f} Unit*। "
                f"৪০০ ইউনিট অতিক্রম করলে প্রতি ইউনিটে *৳১০.৭০* (সর্বোচ্চ রেট) চার্জ প্রযোজ্য হবে!\n\n"
                f"💡 *সাশ্রয়ের লক্ষ্য:* দৈনিক ব্যবহার মাত্র `{reduction:.1f} Unit` কমালে (লক্ষ্য: `{target_daily:.1f} Unit/দিন`) "
                f"আপনি প্রায় *~৳{extra_cost:.0f}* অতিরিক্ত বিদ্যুৎ বিল সাশ্রয় করতে পারবেন!"
            )
        else:
            return (
                f"\n\n🚨 *SMART TARIFF WARNING (400 kWh Threshold)*\n"
                f"At your current run-rate, your projected month-end usage will hit *{projected_mo:.1f} kWh*. "
                f"Crossing 400 units shifts extra units to the maximum *৳10.70/unit* tariff (+70% jump)!\n\n"
                f"💡 *Money Saving Target:* Reduce daily usage by `{reduction:.1f} kWh/day` (target: `{target_daily:.1f} kWh/day`) "
                f"to stay under 400 units and save *~৳{extra_cost:.0f}* this month!"
            )

    # 2. Warning for crossing 300 kWh (Slab 5 Jump to ৳6.30/unit)
    elif projected_mo > 300 and mo_use < 300:
        rem_units = 300 - mo_use
        target_daily = rem_units / days_left
        reduction = max(curr_daily - target_daily, 0)
        over_units = projected_mo - 300
        extra_cost = over_units * 6.30

        if lang == "bn":
            return (
                f"\n\n⚠️ *ট্যারিফ সতর্কতা (৩০০ ইউনিট থ্রেশহোল্ড)*\n"
                f"মাস শেষে আনুমানিক ব্যবহার: *{projected_mo:.1f} Unit*। "
                f"দৈনিক ব্যবহার `{reduction:.1f} Unit` কমিয়ে ৩০০ ইউনিটের মধ্যে রাখলে প্রায় *~৳{extra_cost:.0f}* সাশ্রয় হবে।"
            )
        else:
            return (
                f"\n\n⚠️ *TARIFF WARNING (300 kWh Threshold)*\n"
                f"Projected month-end usage: *{projected_mo:.1f} kWh*. "
                f"Reduce daily usage by `{reduction:.1f} kWh/day` to stay under 300 units and save *~৳{extra_cost:.0f}*!"
            )

    return ""
