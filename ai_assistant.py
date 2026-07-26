# AI Smart Assistant & Energy Advisory Engine for Bangladesh Power Bot
# Supports Google Gemini API (Primary), Groq Cloud (Secondary), and OpenRouter (Tertiary) failover

import os
import requests

SYSTEM_PROMPT = """You are 'EnergyBuddy AI', an expert Bangladesh electricity assistant embedded in a Telegram Bot.
You assist customers of DESCO, BPDB, Palli Bidyut (BREB), DPDC, WZPDCL, and NESCO.

Your capabilities:
1. Explain Bangladesh electricity tariff slabs (LT-A residential: Slab 1 0-50u @ ৳3.75, Slab 2 51-75u @ ৳5.14, Slab 3 76-200u @ ৳5.72, Slab 4 201-300u @ ৳6.01, Slab 5 301-400u @ ৳6.30, Slab 6 >400u @ ৳10.70).
2. Give actionable energy-saving advice for Bangladesh climate (AC temperature set to 25°C, inverter vs non-inverter ACs, Off-Peak usage 11 PM - 5 PM).
3. Answer questions about prepaid meter codes (Hexing 801, Intech 00, Sanxing 00), USSD *727#, and bKash missing token recovery.
4. Reply in the same language as the user (Bangla or English). Keep answers concise, clear, and friendly with helpful Markdown formatting.
"""

def query_gemini(full_prompt: str) -> str | None:
    """Queries Google AI Studio (Gemini Flash) API."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=10)
        res = r.json()
        candidates = res.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text")
    except Exception:
        pass
    return None

def query_groq(full_prompt: str) -> str | None:
    """Queries Groq Cloud API (Llama 3 8B/70B)."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full_prompt}],
        "temperature": 0.5,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        res = r.json()
        choices = res.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content")
    except Exception:
        pass
    return None

def query_openrouter(full_prompt: str) -> str | None:
    """Queries OpenRouter API (Free Tier Models)."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full_prompt}],
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        res = r.json()
        choices = res.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content")
    except Exception:
        pass
    return None

def query_ai_assistant(user_prompt: str, context_data: dict = None, lang: str = "en") -> str:
    """Queries AI Assistant with automatic failover (Gemini -> Groq -> OpenRouter)."""
    context_str = ""
    if context_data:
        context_str = (
            f"\n[User Live Account Context]\n"
            f"Provider: {context_data.get('provider', 'DESCO')}\n"
            f"Account: {context_data.get('account_no', 'N/A')}\n"
            f"Current Balance: ৳{context_data.get('balance', 0)}\n"
            f"Month Consumption: {context_data.get('month_units', 0)} kWh\n"
        )

    full_prompt = f"{context_str}\nUser Question: {user_prompt}"

    # 1. Try Gemini (Primary)
    answer = query_gemini(full_prompt)
    if answer:
        return answer

    # 2. Try Groq (Secondary)
    answer = query_groq(full_prompt)
    if answer:
        return answer

    # 3. Try OpenRouter (Tertiary)
    answer = query_openrouter(full_prompt)
    if answer:
        return answer

    # Fallback response if no keys provided or all fail
    if lang == "bn":
        return (
            "🤖 *এআই স্মার্ট অ্যাসিস্ট্যান্ট*\n\n"
            "এআই সেবা ব্যবহারের জন্য `.env` ফাইলে `GEMINI_API_KEY` অথবা `GROQ_API_KEY` যুক্ত করুন।\n\n"
            "💡 *দ্রুত উত্তর:* বিদ্যুৎ সাশ্রয় করতে এসি ২৫ ডিগ্রি সেলসিয়াসে চালান এবং রাত ১১টা থেকে বিকেল ৫টার মধ্যে (Off-Peak) ভারী যন্ত্রপাতি ব্যবহার করুন।"
        )
    return (
        "🤖 *AI Smart Assistant*\n\n"
        "To activate full AI natural language chat, add `GEMINI_API_KEY` or `GROQ_API_KEY` in your `.env` file.\n\n"
        "💡 *Quick Tip:* Set your AC to 25°C and operate heavy appliances during Off-Peak hours (11 PM – 5 PM) to save electricity!"
    )
