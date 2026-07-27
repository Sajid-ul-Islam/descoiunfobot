# CSV Data Exporter Engine for DESCO & Bangladesh Utility Accounts

import io
import csv

def generate_csv_report(monthly_data: list, recharge_data: list, account_no: str, system: str) -> io.BytesIO:
    """Generates a downloadable CSV spreadsheet containing 12-month consumption & recharge history."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["DESCO & BANGLADESH POWER UTILITY REPORT"])
    writer.writerow(["Account Number", account_no])
    writer.writerow(["System / Provider", system])
    writer.writerow([])

    writer.writerow(["--- 12-MONTH CONSUMPTION HISTORY ---"])
    writer.writerow(["Month (YYYY-MM)", "Consumed Units (kWh)", "Bill Amount (Taka ৳)"])
    for m in sorted(monthly_data, key=lambda x: str(x.get("month", ""))):
        writer.writerow([m.get("month", ""), m.get("consumedUnit", 0), m.get("consumedTaka", 0)])

    writer.writerow([])
    writer.writerow(["--- RECHARGE TRANSACTION HISTORY ---"])
    writer.writerow(["Recharge Date", "Total Amount (Taka ৳)", "Energy Amount (Taka ৳)", "Token Number"])
    
    records = recharge_data if isinstance(recharge_data, list) else [recharge_data]
    for r in sorted(records, key=lambda x: str(x.get("rechargeDate") or x.get("date", ""))):
        writer.writerow([
            r.get("rechargeDate") or r.get("date", ""),
            r.get("totalAmount") or r.get("amount", 0),
            r.get("energyAmount", 0),
            r.get("tokenNo", "OTA Direct")
        ])

    buf = io.BytesIO()
    buf.write(output.getvalue().encode("utf-8-sig"))  # UTF-8 with BOM for Excel compatibility
    buf.seek(0)
    return buf


def generate_text_statement(monthly_data: list, recharge_data: list, account_no: str, system: str, lang: str = "en") -> str:
    """Generates a structured executive visual statement report card."""
    sorted_mo = sorted(monthly_data or [], key=lambda x: str(x.get("month") or x.get("readingMonth", "")))
    mo_units  = [float(m.get("consumedUnit") or m.get("consumption") or m.get("unit") or 0) for m in sorted_mo]
    mo_taka   = [float(m.get("consumedTaka") or m.get("amount") or m.get("billAmount") or 0) for m in sorted_mo]

    total_units = sum(mo_units)
    total_bill  = sum(mo_taka)
    count_mo    = len(mo_units) if mo_units else 1
    avg_mo_units = total_units / count_mo
    avg_mo_taka  = total_bill / count_mo

    recharge_recs = recharge_data if isinstance(recharge_data, list) else [recharge_data] if recharge_data else []
    total_recharge = sum(float(r.get("totalAmount") or r.get("rechargeAmount") or r.get("amount") or 0) for r in recharge_recs)

    if lang == "bn":
        return (
            f"📄 *বাংলাদেশ ইলেকট্রিসিটি অ্যানুয়াল ইউটিলিটি স্টেটমেন্ট*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 *অ্যাকাউন্ট:* `{account_no}`\n"
            f"🏢 *সিস্টেম / প্রোভাইডার:* `{system}`\n"
            f"🗓 *পরিসংখ্যান সময়কাল:* গত ১২ মাস\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 *মাসিক ব্যবহারের সামারি*\n"
            f"⚡ *মোট বিদ্যুৎ ব্যবহার:* `{total_units:.2f} kWh`\n"
            f"💰 *মোট বিদ্যুৎ খরচ:* *৳{total_bill:.2f}*\n"
            f"📉 *গড় মাসিক ব্যবহার:* `{avg_mo_units:.1f} kWh/মাস` (~৳{avg_mo_taka:.2f}/মাস)\n\n"
            f"💳 *রিচার্জ ট্রানজাকশন*\n"
            f"💵 *মোট রিচার্জ জমা:* *৳{total_recharge:.2f}*\n"
            f"🔄 *মোট লেনদেন সংখ্যা:* `{len(recharge_recs)} টি`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *পরামর্শ:* বিদ্যুৎ বিল কমাতে এসি ২৫° সে. এ রাখুন ও রাত ১১টা-বিকেল ৫টা (অফ-পিক) ভারী লোড ব্যবহার করুন।"
        )

    return (
        f"📄 *UTILITY CONSUMPTION & FINANCIAL STATEMENT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 *Account Number:* `{account_no}`\n"
        f"🏢 *System / Provider:* `{system}`\n"
        f"🗓 *Report Period:* Past 12 Months\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 *CONSUMPTION SUMMARY*\n"
        f"⚡ *Total Energy Consumed:* `{total_units:.2f} kWh`\n"
        f"💰 *Total Energy Billed:* *৳{total_bill:.2f}*\n"
        f"📉 *Average Monthly Usage:* `{avg_mo_units:.1f} kWh/mo` (~৳{avg_mo_taka:.2f}/mo)\n\n"
        f"💳 *RECHARGE & PAYMENT METRICS*\n"
        f"💵 *Total Recharged:* *৳{total_recharge:.2f}*\n"
        f"🔄 *Total Transactions:* `{len(recharge_recs)} recharges`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Efficiency Tip:* Keep AC set to 25°C and shift high-wattage loads to Off-Peak (11 PM - 5 PM) to reduce monthly bills."
    )
