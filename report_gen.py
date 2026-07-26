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
