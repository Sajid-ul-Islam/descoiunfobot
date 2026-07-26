# Appliance Energy & Monthly Cost Estimator Engine for Bangladesh Tariffs

APPLIANCES = [
    ("❄️ 1.5 Ton AC (Non-Inverter)", 1500),
    ("❄️ 1.5 Ton AC (Inverter Avg)", 800),
    ("🧊 Refrigerator (200-300L)", 150),
    ("🌀 Ceiling Fan", 75),
    ("💡 LED Light Bulb", 12),
    ("💧 1 HP Water Pump", 746),
    ("📺 43-inch LED TV", 80),
    ("💻 Laptop / Computer", 65),
    ("👔 Electric Iron", 1000),
    ("🍲 Microwave Oven", 1200),
]

def calculate_appliance_cost(appliance_idx: int, hours_per_day: float, rate_per_unit: float = 6.01) -> dict:
    """Calculates daily kWh, monthly kWh, and estimated monthly cost (৳)."""
    if appliance_idx < 0 or appliance_idx >= len(APPLIANCES):
        appliance_idx = 0

    name, watts = APPLIANCES[appliance_idx]
    daily_kwh = (watts * hours_per_day) / 1000.0
    monthly_kwh = daily_kwh * 30.0
    monthly_cost = monthly_kwh * rate_per_unit

    return {
        "name": name,
        "watts": watts,
        "hours": hours_per_day,
        "daily_kwh": round(daily_kwh, 2),
        "monthly_kwh": round(monthly_kwh, 1),
        "monthly_cost": round(monthly_cost, 2),
    }

def get_calc_text(lang: str = "en") -> str:
    if lang == "bn":
        return (
            "🧮 *গৃহস্থালী বিদ্যুৎ খরচ ক্যালকুলেটর*\n\n"
            "বিভিন্ন যন্ত্রপাতির আনুমানিক বিদ্যুৎ ব্যবহার ও খরচের হিসাব:\n\n"
            "• **১.৫ টন এসি (ইনভার্টার):** ৮ ঘণ্টা/দিন ➔ ~১৯২ ইউনিট/মাস (~৳১,১৫৩)\n"
            "• **রেফ্রিজারেটর (২৫০ লিটার):** ২৪ ঘণ্টা ➔ ~১০৮ ইউনিট/মাস (~৳৬৪৯)\n"
            "• **সিএসি সিলিং ফ্যান:** ১২ ঘণ্টা/দিন ➔ ~২৭ ইউনিট/মাস (~৳১৬২)\n"
            "• **এলইডি লাইট (১২ ওয়াট):** ১০ ঘণ্টা/দিন ➔ ~৩.৬ ইউনিট/মাস (~৳২২)\n"
            "• **১ এইচপি ওয়াটার পাম্প:** ১ ঘণ্টা/দিন ➔ ~২২.৪ ইউনিট/মাস (~৳১৩৫)\n\n"
            "💡 *টিপ:* রাত ১১টা থেকে বিকেল ৫টার মধ্যে (Off-Peak) ভারী যন্ত্রপাতি ব্যবহার করলে বিদ্যুৎ সাশ্রয় হয়।"
        )
    return (
        "🧮 *Home Appliance Energy & Cost Estimator*\n\n"
        "Estimated monthly energy consumption and cost for common appliances:\n\n"
        "• **1.5 Ton Inverter AC:** 8 hrs/day ➔ ~192 kWh/month (~৳1,153)\n"
        "• **Refrigerator (250L):** 24 hrs ➔ ~108 kWh/month (~৳649)\n"
        "• **Ceiling Fan:** 12 hrs/day ➔ ~27 kWh/month (~৳162)\n"
        "• **LED Bulb (12W):** 10 hrs/day ➔ ~3.6 kWh/month (~৳22)\n"
        "• **1 HP Water Pump:** 1 hr/day ➔ ~22.4 kWh/month (~৳135)\n\n"
        "💡 *Tip:* Operating heavy appliances during Off-Peak hours (11 PM – 5 PM) helps optimize load."
    )

def get_tariff_guide_text(lang: str = "en") -> str:
    if lang == "bn":
        return (
            "⚡ *বাংলাদেশ বিদ্যুৎ ট্যারিফ ও পিক-আওয়ার সময়সূচী*\n\n"
            "🕒 *সময়সূচী (Time-of-Use Schedule):*\n"
            "• 🔴 **পিক আওয়ার (Peak Hours):** বিকেল ৫:০০ - রাত ১১:০০ (সর্বোচ্চ রেট)\n"
            "• 🟢 **অফ-পিক আওয়ার (Off-Peak Hours):** রাত ১১:০০ - বিকেল ৫:০০ (কম রেট)\n\n"
            "📊 *আবাসিক এলটি-এ (LT-A) ধাপভিত্তিক ট্যারিফ:* \n"
            "১. ০ – ৫০ ইউনিট: ৳৩.৭৫/ইউনিট\n"
            "২. ৫১ – ৭৫ ইউনিট: ৳৫.১৪/ইউনিট\n"
            "৩. ৭৬ – ২০০ ইউনিট: ৳৫.৭২/ইউনিট\n"
            "৪. ২০১ – ৩০০ ইউনিট: ৳৬.০১/ইউনিট\n"
            "৫. ৩০১ – ৪০০ ইউনিট: ৳৬.৩০/ইউনিট\n"
            "৬. >৪০০ ইউনিট: ৳১০.৭০/ইউনিট"
        )
    return (
        "⚡ *Official Bangladesh Electricity Tariff & Time-of-Use Schedule*\n\n"
        "🕒 *Peak vs Off-Peak Schedule:*\n"
        "• 🔴 **Peak Hours:** 5:00 PM – 11:00 PM (Highest Rate)\n"
        "• 🟢 **Off-Peak Hours:** 11:00 PM – 5:00 PM (Lower Rate)\n\n"
        "📊 *Residential LT-A Step Tariff Slabs:*\n"
        "1. 0 – 50 kWh: ৳3.75 / unit\n"
        "2. 51 – 75 kWh: ৳5.14 / unit\n"
        "3. 76 – 200 kWh: ৳5.72 / unit\n"
        "4. 201 – 300 kWh: ৳6.01 / unit\n"
        "5. 301 – 400 kWh: ৳6.30 / unit\n"
        "6. >400 kWh: ৳10.70 / unit"
    )
