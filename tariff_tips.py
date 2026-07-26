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
