# AI Smart Assistant & Energy Advisory Engine for Bangladesh Power Bot
# Supports Google Gemini API (gemini-1.5-flash / gemini-2.5-flash) with graceful fallback

import os
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """You are 'EnergyBuddy AI', an expert Bangladesh electricity assistant embedded in a Telegram Bot.
You assist customers of DESCO, BPDB, Palli Bidyut (BREB), DPDC, WZPDCL, and NESCO.

Your capabilities:
1. Explain Bangladesh electricity tariff slabs (LT-A residential: Slab 1 0-50u @ ৳3.75, Slab 2 51-75u @ ৳5.14, Slab 3 76-200u @ ৳5.72, Slab 4 201-300u @ ৳6.01, Slab 5 301-400u @ ৳6.30, Slab 6 >400u @ ৳10.70).
2. Give actionable energy-saving advice for Bangladesh climate (AC temperature set to 25°C, inverter vs non-inverter ACs, Off-Peak usage 11 PM - 5 PM).
3. Answer questions about prepaid meter codes (Hexing 801, Intech 00, Sanxing 00), USSD *727#, and bKash missing token recovery.
4. Reply in the same language as the user (Bangla or English). Keep answers concise, clear, and friendly with helpful Markdown formatting.
"""

def query_ai_assistant(user_prompt: str, context_data: dict = None, lang: str = "en") -> str:
    """Queries Gemini REST API to answer energy questions with user account context."""
    if not GEMINI_API_KEY:
        if lang == "bn":
            return (
                "🤖 *এআই স্মার্ট অ্যাসিস্ট্যান্ট*\n\n"
                "এআই সেবা ব্যবহারের জন্য `.env` ফাইলে `GEMINI_API_KEY` যুক্ত করুন।\n\n"
                "💡 *দ্রুত উত্তর:* বিদ্যুৎ সাশ্রয় করতে এসি ২৫ ডিগ্রি সেলসিয়াসে চালান এবং রাত ১১টা থেকে বিকেল ৫টার মধ্যে (Off-Peak) ভারী যন্ত্রপাতি ব্যবহার করুন।"
            )
        return (
            "🤖 *AI Smart Assistant*\n\n"
            "To activate full AI natural language chat, add `GEMINI_API_KEY` in your `.env` file.\n\n"
            "💡 *Quick Tip:* Set your AC to 25°C and operate heavy appliances during Off-Peak hours (11 PM – 5 PM) to save electricity!"
        )

    # Build prompt with user account context if available
    context_str = ""
    if context_data:
        context_str = (
            f"\n[User Live Account Context]\n"
            f"Provider: {context_data.get('provider', 'DESCO')}\n"
            f"Account: {context_data.get('account_no', 'N/A')}\n"
            f"Current Balance: ৳{context_data.get('balance', 0)}\n"
            f"Month Consumption: {context_data.get('month_units', 0)} kWh\n"
        )

    full_prompt = f"{SYSTEM_PROMPT}\n{context_str}\nUser Question: {user_prompt}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [{"text": full_prompt}]
            }
        ]
    }

    try:
        r = requests.post(url, json=payload, timeout=12)
        res = r.json()
        candidates = res.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "Sorry, I couldn't generate a response.")
        return "⚠️ AI service returned an empty response."
    except Exception as e:
        return f"❌ AI Assistant Error: `{e}`"
