# Palli Bidyut (BREB) Module — Information, Meter Keypad Codes, USSD, MFS Payment & Missing Token Recovery Guide

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
            "📞 *জরুরি হটলাইন:* *১৬৮৯৯* (BREB ২৪/৭ কল সেন্টার)\n"
            "📱 *ইউএসএসডি ডায়াল:* `*৭২৭#` (ব্যালেন্স ও সেবার জন্য)\n\n"
            "📟 *মিটারে ব্যালেন্স দেখার কিপ্যাড কোড:*\n"
            "• *Hexing Meter:* `801` চাপুন\n"
            "• *Intech Meter:* `00` চাপুন\n"
            "• *Sanxing Meter:* `00` চাপুন\n"
            "• *Shenzhen Meter:* `801` চাপুন\n\n"
            "📱 *মোবাইল অ্যাপের মাধ্যমে রিচার্জ ও বিল:* \n"
            "• *বিকাশ:* Pay Bill → Electricity (Prepaid/Postpaid) → Palli Bidyut\n"
            "• *নগদ:* Bill Pay → Palli Bidyut\n"
            "• *রকেট:* Utility Pay → Palli Bidyut (Code: 200/201)"
        )
    return (
        "🌾 *Palli Bidyut (BREB) Service & Guide*\n\n"
        "📞 *Emergency Hotline:* *16899* (BREB 24/7 Call Center)\n"
        "📱 *USSD Dial:* `*727#` (Balance & Service Menu)\n\n"
        "📟 *Meter Keypad Codes (Press on Meter):*\n"
        "• *Hexing Meter:* Press `801` → Check Balance (৳)\n"
        "• *Intech Meter:* Press `00` → Check Balance (৳)\n"
        "• *Sanxing Meter:* Press `00` → Check Balance (৳)\n"
        "• *Shenzhen Meter:* Press `801` → Check Balance (৳)\n\n"
        "📱 *Recharge & Bill Pay via Mobile Financial Services (MFS):*\n"
        "• *bKash:* Pay Bill → Electricity (Prepaid/Postpaid) → Palli Bidyut\n"
        "• *Nagad:* Bill Pay → Palli Bidyut\n"
        "• *Rocket:* Utility Pay → Palli Bidyut (Biller ID: 200/201)"
    )

def get_token_help_text(lang: str = "en") -> str:
    if lang == "bn":
        return (
            "🔑 *টাকা কেটেছে কিন্তু টোকেন পাননি? সমাধানের উপায়:*\n\n"
            "1️⃣ *বিকাশ অ্যাপ থেকে টোকেন দেখুন (সবচেয়ে সহজ):*\n"
            "• বিকাশ অ্যাপ ওপেন করুন → *ইনবক্স (Inbox)* বা *লেনদেন (Transactions)* এ যান।\n"
            "• বিদ্যুৎ বিলের লেনদেনটিতে ট্যাপ করুন → নিচে *২০ ডিজিটের টোকেন (Token No)* দেখতে পাবেন!\n\n"
            "2️⃣ *USSD ডায়াল করে টোকেন নিন:*\n"
            "• মোবাইল থেকে `*৭২৭#` ডায়াল করুন → *Token Inquiry* বা *Last Token* অপশন বেছে নিন।\n\n"
            "3️⃣ *স্মার্ট মিটারে অটো রিচার্জ:*\n"
            "• নতুন অনলাইন স্মার্ট মিটারে টোকেন হাতে টাইপ করতে হয় না। সার্ভার থেকে সরাসরি মিটারে ব্যালেন্স যোগ হয়ে যায়।\n\n"
            "4️⃣ *জরুরি হেল্পলাইন বা রিফান্ড:*\n"
            "• টোকেন না পেলে পল্লী বিদ্যুৎ হটলাইন *১৬৮৯৯* এ বিকাশ Transaction ID (TrxID) সহ জানান।\n"
            "• কোনো কারণে পেমেন্ট ব্যর্থ হলে বিকাশ ২৪-৪৮ ঘণ্টার মধ্যে টাকা আপনার অ্যাকাউন্টে রিফান্ড করে দেবে।"
        )
    return (
        "🔑 *Money Deducted but Token Not Received? Solution:*\n\n"
        "1️⃣ *Check Token in bKash App (Easiest):*\n"
        "• Open bKash App → Go to *Inbox* or *Transactions*.\n"
        "• Tap on the Electricity Pay Bill transaction → Your *20-digit Token Number* is listed right on the digital receipt!\n\n"
        "2️⃣ *Get Token via USSD Dial:*\n"
        "• Dial `*727#` on your mobile phone → Select *Token Inquiry* or *Last Token*.\n\n"
        "3️⃣ *Automatic Smart Metering:*\n"
        "• Modern online smart meters load the credit over-the-air (OTA) automatically without manual token entry.\n\n"
        "4️⃣ *Hotline & Auto-Refund:*\n"
        "• Call BREB Helpline *16899* with your bKash Transaction ID (TrxID).\n"
        "• If the utility server fails to process the order, bKash automatically refunds the money to your account within 24-48 hours."
    )
