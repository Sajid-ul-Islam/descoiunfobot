# Complete Bangladesh Electricity Distribution Network & Providers Guide
# Covers: DESCO, DPDC, BPDB, BREB (Palli Bidyut), WZPDCL, NESCO

ALL_PROVIDERS = {
    "desco": {
        "name_en": "⚡ DESCO — Dhaka North",
        "name_bn": "⚡ ডেসকো — ঢাকা উত্তর",
        "coverage_en": "Mirpur, Gulshan, Uttara, Tongi, Banani, Baridhara, Kafrul, Airport, Nikunja.",
        "coverage_bn": "মিরপুর, গুলশান, উত্তরা, টঙ্গী, বনানী, বারিধারা, কাফরুল, বিমানবন্দর, নিকুঞ্জ।",
        "helpline": "16120",
        "portal": "https://prepaid.desco.org.bd/",
    },
    "dpdc": {
        "name_en": "🌆 DPDC — Dhaka South & Narayanganj",
        "name_bn": "🌆 ডিপিডিসি — ঢাকা দক্ষিণ ও নারায়ণগঞ্জ",
        "coverage_en": "Dhanmondi, Lalbagh, Motijheel, Ramna, Azimpur, Tejgaon, Narayanganj.",
        "coverage_bn": "ধানমন্ডি, লালবাগ, মতিঝিল, রমনা, আজিমপুর, তেজগাঁও, নারায়ণগঞ্জ।",
        "helpline": "16116",
        "portal": "https://dpdc.org.bd/",
    },
    "bpdb": {
        "name_en": "🏢 BPDB — Chattogram & Regional Urban Zones",
        "name_bn": "🏢 বিপিডিবি — চট্টগ্রাম ও আঞ্চলিক শহর জোন",
        "coverage_en": "Chattogram City (Agrabad, Halishahar, Khulshi, Chandgaon), Sylhet, Mymensingh.",
        "coverage_bn": "চট্টগ্রাম শহর (আগ্রাবাদ, হালিশহর, খুলশী, চান্দগাঁও), সিলেট, ময়মনসিংহ।",
        "helpline": "16200 / 16131",
        "portal": "https://prepaid.bpdb.gov.bd/",
    },
    "breb": {
        "name_en": "🌾 Palli Bidyut (BREB) — All Rural & Suburbs (64 Districts)",
        "name_bn": "🌾 পল্লী বিদ্যুৎ (বিআরইবি) — দেশের সকল গ্রাম ও উপজেলা (৬৪ জেলা)",
        "coverage_en": "80 Palli Bidyut Samity (PBS) units across rural Bangladesh & district outskirts.",
        "coverage_bn": "দেশের ৮০টি পল্লী বিদ্যুৎ সমিতি (পিবিএস) ও উপজেলা সমূহ।",
        "helpline": "16899",
        "portal": "http://www.reb.gov.bd/",
    },
    "wzpdcl": {
        "name_en": "🌊 WZPDCL — West Zone (Khulna, Barishal, Greater Faridpur)",
        "name_bn": "🌊 ওজোপাডিকো — পশ্চিম জোন (খুলনা, বরিশাল, বৃহত্তর ফরিদপুর)",
        "coverage_en": "Khulna division, Barishal division, Faridpur, Jessore, Kushtia urban areas.",
        "coverage_bn": "খুলনা বিভাগ, বরিশাল বিভাগ, ফরিদপুর, যশোর, কুষ্টিয়া শহর অঞ্চল।",
        "helpline": "16117",
        "portal": "https://wzpdcl.gov.bd/",
    },
    "nesco": {
        "name_en": "❄️ NESCO — North Zone (Rajshahi & Rangpur Divisions)",
        "name_bn": "❄️ নেসকো — উত্তর জোন (রাজশাহী ও রংপুর বিভাগ)",
        "coverage_en": "Rajshahi, Rangpur, Bogura, Pabna, Dinajpur, Naogaon urban centers.",
        "coverage_bn": "রাজশাহী, রংপুর, বগুড়া, পাবনা, দিনাজপুর, নওগাঁ শহর জোন।",
        "helpline": "16603",
        "portal": "https://nesco.gov.bd/",
    }
}

def get_all_coverage_text(lang: str = "en") -> str:
    if lang == "bn":
        lines = [
            "🇧🇩 *বাংলাদেশের পূর্ণাঙ্গ বিদ্যুৎ সরবরাহকারী ডিরেক্টরি*\n",
            "বাংলাদেশের বিদ্যুৎ বিতরণ ব্যবস্থা ৬টি প্রধান প্রতিষ্ঠানে বিভক্ত:\n"
        ]
        for key, p in ALL_PROVIDERS.items():
            lines.append(
                f"*{p['name_bn']}*\n"
                f"📍 *কভারেজ:* {p['coverage_bn']}\n"
                f"📞 *হটলাইন:* **{p['helpline']}**\n"
                f"🌐 *ওয়েবসাইট:* [পোর্টাল দেখুন]({p['portal']})\n"
            )
        return "\n".join(lines)
    else:
        lines = [
            "🇧🇩 *Complete Bangladesh Power Grid Directory*\n",
            "Electricity in Bangladesh is distributed by 6 primary power entities:\n"
        ]
        for key, p in ALL_PROVIDERS.items():
            lines.append(
                f"*{p['name_en']}*\n"
                f"📍 *Coverage:* {p['coverage_en']}\n"
                f"📞 *Hotline:* **{p['helpline']}**\n"
                f"🌐 *Portal:* [Visit Portal]({p['portal']})\n"
            )
        return "\n".join(lines)

def get_bpdb_text(lang: str = "en") -> str:
    p = ALL_PROVIDERS["bpdb"]
    if lang == "bn":
        return (
            f"🏢 *{p['name_bn']}*\n\n"
            f"📍 *কভারেজ:* {p['coverage_bn']}\n"
            "• বিপিডিবি সরাসরি এসব এলাকায় বিদ্যুৎ সরবরাহ বিষয়াবলী পরিচালনা করে।\n\n"
            f"🌐 *প্রিপেইড পোর্টাল:* [prepaid.bpdb.gov.bd]({p['portal']})\n"
            f"📞 *হেল্পলাইন:* **{p['helpline']}**\n\n"
            "📱 *মোবাইল পেমেন্ট:* বিকাশ / নগদ → পে বিল → বিপিডিবি"
        )
    return (
        f"🏢 *{p['name_en']}*\n\n"
        f"📍 *Coverage:* {p['coverage_en']}\n"
        "• BPDB directly manages retail electricity distribution to homes and commercial spaces.\n\n"
        f"🌐 *Prepaid Portal:* [prepaid.bpdb.gov.bd]({p['portal']})\n"
        f"📞 *Helpline:* **{p['helpline']}**\n\n"
        "📱 *MFS Bill Pay:* bKash / Nagad → Pay Bill → BPDB"
    )
