# Palli Bidyut (BREB) Module — Information, Meter Keypad Codes, USSD, and MFS Payment Guide

METER_CODES = {
    "Hexing": [
        ("801", "Current Balance (৳) / বর্তমান ব্যালেন্স"),
        ("802", "Total Units Used (kWh) / মোট ব্যবহৃত ইউনিট"),
        ("800", "Meter Number / মিটার নম্বর"),
    ],
    "Intech": [
        ("00", "Current Balance (৳) / বর্তমান ব্যালেন্স"),
        ("01", "Current Month Usage / চলতি মাসের ব্যবহার"),
    ],
    "Sanxing": [
        ("00", "Current Balance (৳) / বর্তমান ব্যালেন্স"),
        ("02", "Total Consumed Energy / মোট ব্যবহৃত বিদ্যুৎ"),
    ],
    "Shenzhen": [
        ("801", "Current Balance (৳) / বর্তমান ব্যালেন্স"),
        ("802", "Total KWh / মোট ইউনিট"),
    ]
}

def get_palli_text(lang: str = "en") -> str:
    if lang == "bn":
        return (
            "🌾 *পল্লী বিদ্যুৎ (BREB) সেবা ও গাইড*\n\n"
            "📞 *জরুরি হটলাইন:* **১৬৮৯৯** (BREB ২৪/৭ কল সেন্টার)\n"
            "📱 *ইউএসএসডি ডায়াল:* `*৭২৭#` (ব্যালেন্স ও সেবার জন্য)\n\n"
            "📟 *মিটারে ব্যালেন্স দেখার কিপ্যাড কোড:*\n"
            "• *Hexing Meter:* `801` চাপুন\n"
            "• *Intech Meter:* `00` চাপুন\n"
            "• *Sanxing Meter:* `00` চাপুন\n"
            "• *Shenzhen Meter:* `801` চাপুন\n\n"
            "📱 *মোবাইল অ্যাপের মাধ্যমে রিচার্জ ও বিল:* \n"
            "• **বিকাশ:** Pay Bill → Electricity (Prepaid/Postpaid) → Palli Bidyut\n"
            "• **নগদ:** Bill Pay → Palli Bidyut\n"
            "• **রকেট:** Utility Pay → Palli Bidyut (Code: 200/201)"
        )
    return (
        "🌾 *Palli Bidyut (BREB) Service & Guide*\n\n"
        "📞 *Emergency Hotline:* **16899** (BREB 24/7 Call Center)\n"
        "📱 *USSD Dial:* `*727#` (Balance & Service Menu)\n\n"
        "📟 *Meter Keypad Codes (Press on Meter):*\n"
        "• *Hexing Meter:* Press `801` → Check Balance (৳)\n"
        "• *Intech Meter:* Press `00` → Check Balance (৳)\n"
        "• *Sanxing Meter:* Press `00` → Check Balance (৳)\n"
        "• *Shenzhen Meter:* Press `801` → Check Balance (৳)\n\n"
        "📱 *Recharge & Bill Pay via Mobile Financial Services (MFS):*\n"
        "• **bKash:** Pay Bill → Electricity (Prepaid/Postpaid) → Palli Bidyut\n"
        "• **Nagad:** Bill Pay → Palli Bidyut\n"
        "• **Rocket:** Utility Pay → Palli Bidyut (Biller ID: 200/201)"
    )
