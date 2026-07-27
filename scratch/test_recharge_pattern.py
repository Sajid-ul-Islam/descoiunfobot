from datetime import date, timedelta
from collections import Counter

def analyze_recharge_pattern(recharge_data: list, lang: str = "en") -> dict:
    """
    Analyzes recharge history to detect:
    1. Average days between recharges
    2. Average recharge amount
    3. Most probable recharge day range of the month (e.g. 1st–5th)
    4. Most probable day of week
    5. Estimated next recharge date & days remaining
    """
    if not recharge_data:
        return {"has_pattern": False, "formatted_text": ""}

    records = recharge_data if isinstance(recharge_data, list) else [recharge_data]
    parsed = []

    for r in records:
        raw_dt = str(r.get("rechargeDate") or r.get("date", "") or "").strip()
        amt = float(r.get("totalAmount") or r.get("rechargeAmount") or r.get("amount") or 0)
        if not raw_dt:
            continue
        # Extract YYYY-MM-DD
        dt_part = raw_dt[:10]
        try:
            d_obj = date.fromisoformat(dt_part)
            parsed.append({"date": d_obj, "amount": amt, "raw_dt": raw_dt})
        except ValueError:
            pass

    if not parsed:
        return {"has_pattern": False, "formatted_text": ""}

    # Sort chronologically (oldest first)
    parsed.sort(key=lambda x: x["date"])
    dates = [p["date"] for p in parsed]
    amounts = [p["amount"] for p in parsed if p["amount"] > 0]

    total_recharges = len(parsed)
    total_spent = sum(amounts)
    avg_amount = round(total_spent / len(amounts), 0) if amounts else 0.0

    # 1. Average days between recharges
    unique_dates = sorted(list(set(dates)))
    gaps = [(unique_dates[i] - unique_dates[i-1]).days for i in range(1, len(unique_dates))]
    valid_gaps = [g for g in gaps if g > 0]
    avg_days_between = round(sum(valid_gaps) / len(valid_gaps), 1) if valid_gaps else 0.0

    # 2. Most probable day of month range
    day_brackets = {
        "1st–5th": 0,
        "6th–10th": 0,
        "11th–15th": 0,
        "16th–20th": 0,
        "21st–25th": 0,
        "26th–31st": 0,
    }
    day_numbers = []
    weekdays = []

    weekday_names_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_names_bn = ["সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার", "রবিবার"]

    for d in dates:
        day_num = d.day
        day_numbers.append(day_num)
        weekdays.append(d.weekday())

        if 1 <= day_num <= 5:
            day_brackets["1st–5th"] += 1
        elif 6 <= day_num <= 10:
            day_brackets["6th–10th"] += 1
        elif 11 <= day_num <= 15:
            day_brackets["11th–15th"] += 1
        elif 16 <= day_num <= 20:
            day_brackets["16th–20th"] += 1
        elif 21 <= day_num <= 25:
            day_brackets["21st–25th"] += 1
        else:
            day_brackets["26th–31st"] += 1

    top_bracket = max(day_brackets.items(), key=lambda x: x[1])[0]

    # Most common day of week
    weekday_counts = Counter(weekdays)
    most_common_wd_idx = weekday_counts.most_common(1)[0][0] if weekday_counts else 4
    most_common_wd_en = weekday_names_en[most_common_wd_idx]
    most_common_wd_bn = weekday_names_bn[most_common_wd_idx]

    # Most common exact day of month
    day_counts = Counter(day_numbers)
    most_common_day = day_counts.most_common(1)[0][0] if day_counts else dates[-1].day

    # 3. Next probable recharge prediction
    last_date = dates[-1]
    today = date.today()
    predicted_next_date = last_date + timedelta(days=max(int(round(avg_days_between)), 1)) if avg_days_between > 0 else today + timedelta(days=15)
    days_remaining = (predicted_next_date - today).days

    # 4. Formatted text output
    EN = (lang == "en")
    if avg_days_between > 0:
        freq_str = f"Every ~`{avg_days_between} days`" if EN else f"প্রতি ~`{avg_days_between} দিন` পর"
    else:
        freq_str = f"`{total_recharges} times` total" if EN else f"মোট `{total_recharges} বার`"

    wd_name = most_common_wd_en if EN else most_common_wd_bn
    
    if days_remaining > 0:
        rem_str = f"(~`{days_remaining} days` remaining)" if EN else f"(আনুমানিক ~`{days_remaining} দিন` বাকি)"
    elif days_remaining == 0:
        rem_str = f"(*Today!*)" if EN else f"(*আজকে!*)"
    else:
        rem_str = f"(`{abs(days_remaining)} days` overdue)" if EN else f"(`{abs(days_remaining)} দিন` অতিবাহিত)"

    if EN:
        formatted_text = (
            f"📊 *Recharge Pattern & Analytics:*\n"
            f"• 🔁 *Top-up Frequency:* {freq_str} (Avg: `৳{avg_amount:,.0f}`)\n"
            f"• 📅 *Most Common Period:* `{top_bracket}` of the month ({wd_name}s)\n"
            f"• 🔮 *Predicted Next Top-up:* `{predicted_next_date.strftime('%Y-%m-%d')}` {rem_str}"
        )
    else:
        # Convert numbers for Bangla if needed
        formatted_text = (
            f"📊 *রিচার্জ প্যাটার্ন ও বিশ্লেষণ:*\n"
            f"• 🔁 *রিচার্জের সময়সীমা:* {freq_str} (গড় পরিমাণ: `৳{avg_amount:,.0f}`)\n"
            f"• 📅 *সবচেয়ে সম্ভাব্য সময়:* মাসের `{top_bracket}` তারিখ ({wd_name})\n"
            f"• 🔮 *পরবর্তী সম্ভাব্য রিচার্জ:* `{predicted_next_date.strftime('%Y-%m-%d')}` {rem_str}"
        )

    return {
        "has_pattern": True,
        "total_recharges": total_recharges,
        "total_spent": total_spent,
        "avg_amount": avg_amount,
        "avg_days_between": avg_days_between,
        "top_bracket": top_bracket,
        "most_common_day": most_common_day,
        "most_common_weekday": most_common_wd_en,
        "predicted_next_date": str(predicted_next_date),
        "days_remaining": days_remaining,
        "formatted_text": formatted_text,
    }


# Test with sample DESCO recharge records
if __name__ == "__main__":
    sample_records = [
        {"rechargeDate": "2026-01-02 10:00:00", "totalAmount": 1000},
        {"rechargeDate": "2026-01-20 14:30:00", "totalAmount": 1000},
        {"rechargeDate": "2026-02-05 11:15:00", "totalAmount": 1500},
        {"rechargeDate": "2026-02-22 09:00:00", "totalAmount": 1000},
        {"rechargeDate": "2026-03-10 16:45:00", "totalAmount": 1000},
        {"rechargeDate": "2026-03-28 12:00:00", "totalAmount": 2000},
        {"rechargeDate": "2026-04-14 18:20:00", "totalAmount": 1000},
        {"rechargeDate": "2026-05-02 10:10:00", "totalAmount": 1000},
        {"rechargeDate": "2026-05-19 13:00:00", "totalAmount": 1000},
        {"rechargeDate": "2026-06-05 15:30:00", "totalAmount": 1500},
        {"rechargeDate": "2026-06-23 11:00:00", "totalAmount": 1000},
        {"rechargeDate": "2026-07-10 09:15:00", "totalAmount": 1000},
    ]

    res_en = analyze_recharge_pattern(sample_records, lang="en")
    print("=== ENGLISH PATTERN ===")
    print(res_en["formatted_text"])
    print("\nRaw metrics:", res_en)

    res_bn = analyze_recharge_pattern(sample_records, lang="bn")
    print("\n=== BANGLA PATTERN ===")
    print(res_bn["formatted_text"])
