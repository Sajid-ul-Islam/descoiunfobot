# Bangladesh Electricity Utility Providers Guide — BPDB, BREB/Palli Bidyut, DESCO, DPDC, WZPDCL, NESCO

PROVIDERS_DATA = {
    "bpdb": {
        "name_en": "BPDB (Chattogram & Regional Zones)",
        "name_bn": "বিপিডিবি (চট্টগ্রাম ও আঞ্চলিক জোন)",
        "desc_en": (
            "🏢 *BPDB (Bangladesh Power Development Board)*\n\n"
            "📍 *Chattogram City Zone Coverage:*\n"
            "• Agrabad, Halishahar, Chandgaon, Khulshi, Nasirabad, Chawkbazar.\n"
            "• BPDB directly manages retail electricity distribution to homes and commercial spaces here.\n\n"
            "🌐 *Prepaid Portal:* [prepaid.bpdb.gov.bd](https://prepaid.bpdb.gov.bd/)\n"
            "📞 *Chattogram Helpline:* **16200** / Central: **16131**\n\n"
            "📱 *MFS Bill Pay:* bKash / Nagad → Pay Bill → BPDB Prepaid/Postpaid"
        ),
        "desc_bn": (
            "🏢 *বিপিডিবি (বাংলাদেশ বিদ্যুৎ উন্নয়ন বোর্ড)*\n\n"
            "📍 *চট্টগ্রাম সিটি জোন কভারেজ:*\n"
            "• আগ্রাবাদ, হালিশহর, চান্দগাঁও, খুলশী, নাসিরাবাদ, চকবাজার।\n"
            "• বিপিডিবি সরাসরি এসব এলাকায় বিদ্যুৎ সরবরাহ নিয়ন্ত্রণ করে।\n\n"
            "🌐 *প্রিপেইড পোর্টাল:* [prepaid.bpdb.gov.bd](https://prepaid.bpdb.gov.bd/)\n"
            "📞 *চট্টগ্রাম হেল্পলাইন:* **১৬২০০** / সেন্ট্রাল: **১৬১৩১**\n\n"
            "📱 *মোবাইল পেমেন্ট:* বিকাশ / নগদ → পে বিল → বিপিডিবি প্রিপেইড/পোস্টপেইড"
        ),
    },
    "breb": {
        "name_en": "Chattogram Palli Bidyut (PBS-1, 2, 3) & BREB",
        "name_bn": "চট্টগ্রাম পল্লী বিদ্যুৎ (পিবিএস ১, ২, ৩) ও বিআরইবি",
        "desc_en": (
            "🌾 *Chattogram Palli Bidyut Samity (PBS-1, PBS-2, PBS-3)*\n\n"
            "📍 *Suburban & Industrial Zone Coverage:*\n"
            "• Sitakunda, Hathazari, Mirsharai, Patiya, Boalkhali, Anwara, Raozan.\n"
            "• Operated under Bangladesh Rural Electrification Board (BREB).\n\n"
            "📞 *Emergency Hotline:* **16899** (BREB 24/7 Call Center)\n"
            "📱 *USSD Service:* Dial `*727#` on any phone\n\n"
            "📟 *Meter Keypad Codes:*\n"
            "• *Hexing:* `801` (Balance ৳)\n"
            "• *Intech:* `00` (Balance ৳)\n"
            "• *Sanxing:* `00` (Balance ৳)\n"
            "• *Shenzhen:* `801` (Balance ৳)\n\n"
            "📱 *MFS Pay:* bKash/Nagad/Rocket → Pay Bill → Palli Bidyut"
        ),
        "desc_bn": (
            "🌾 *চট্টগ্রাম পল্লী বিদ্যুৎ সমিতি (পিবিএস-১, পিবিএস-২, পিবিএস-৩)*\n\n"
            "📍 *উপজেলা ও শিল্পাঞ্চল কভারেজ:*\n"
            "• সীতাকুণ্ড, হাঠহাজারী, মীরসরাই, পটিয়া, বোয়ালখালী, আনোয়ারা, রাউজান।\n"
            "• বাংলাদেশ পল্লী বিদ্যুতায়ন বোর্ডের (বিআরইবি) অধীনে পরিচালিত।\n\n"
            "📞 *জরুরি হটলাইন:* **১৬৮৯৯** (বিআরইবি ২৪/৭ কল সেন্টার)\n"
            "📱 *ইউএসএসডি সেবা:* যে কোনো ফোনে `*৭২৭#` ডায়াল করুন\n\n"
            "📟 *মিটার কিপ্যাড কোড:*\n"
            "• *Hexing:* `801` (ব্যালেন্স ৳)\n"
            "• *Intech:* `00` (ব্যালেন্স ৳)\n"
            "• *Sanxing:* `00` (ব্যালেন্স ৳)\n"
            "• *Shenzhen:* `801` (ব্যালেন্স ৳)\n\n"
            "📱 *মোবাইল পেমেন্ট:* বিকাশ/নগদ/রকেট → পে বিল → পল্লী বিদ্যুৎ"
        ),
    }
}

def get_bpdb_text(lang: str = "en") -> str:
    return PROVIDERS_DATA["bpdb"]["desc_bn" if lang == "bn" else "desc_en"]

def get_chattogram_pbs_text(lang: str = "en") -> str:
    return PROVIDERS_DATA["breb"]["desc_bn" if lang == "bn" else "desc_en"]
