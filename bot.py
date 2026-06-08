import asyncio
import requests
import urllib3

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# =====================================
# SSL WARNING DISABLE
# =====================================

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

# =====================================
# CONFIG
# =====================================

BOT_TOKEN = "8847321807:AAGnUzsJhdFDsf3Y6VpuE6Scof0tO7nsCvQ"
ACCOUNT_NO = "41032243"

CHAT_ID = 150746841
LOW_BALANCE_LIMIT = 100

# =====================================
# DESCO API
# =====================================

def get_balance_data():

    url = (
        "https://prepaid.desco.org.bd/api/unified/"
        f"customer/getBalance?accountNo={ACCOUNT_NO}"
    )

    response = requests.get(
        url,
        timeout=15,
        verify=False
    )

    result = response.json()

    return result.get("data")

# =====================================
# COMMANDS
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "⚡ DESCO Buddy Online\n\n"
        "Commands:\n"
        "/balance"
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        data = get_balance_data()

        if not data:

            await update.message.reply_text(
                "❌ Account data পাওয়া যায়নি"
            )
            return

        balance_amount = data.get("balance", 0)
        monthly_usage = data.get(
            "currentMonthConsumption",
            0
        )
        meter_no = data.get(
            "meterNo",
            "N/A"
        )
        reading_time = data.get(
            "readingTime",
            "N/A"
        )

        msg = (
            f"⚡ DESCO Balance\n\n"
            f"💰 Balance: ৳{balance_amount}\n"
            f"📊 Monthly Usage: "
            f"{float(monthly_usage):.2f} Unit\n"
            f"🔌 Meter: {meter_no}\n"
            f"🕒 Reading: {reading_time}"
        )

        await update.message.reply_text(msg)

    except Exception as e:

        await update.message.reply_text(
            f"❌ Error:\n{e}"
        )

# =====================================
# LOW BALANCE ALERT
# =====================================

async def low_balance_checker(app):

    alert_sent = False

    while True:

        try:

            data = get_balance_data()

            if data:

                current_balance = float(
                    data["balance"]
                )

                if current_balance <= LOW_BALANCE_LIMIT:

                    if not alert_sent:

                        await app.bot.send_message(
                            chat_id=CHAT_ID,
                            text=(
                                "⚠️ LOW BALANCE ALERT\n\n"
                                f"Current Balance: "
                                f"৳{current_balance}"
                            )
                        )

                        alert_sent = True

                else:

                    alert_sent = False

        except Exception as e:

            print("Check Error:", e)

        await asyncio.sleep(1800)

# =====================================
# STARTUP
# =====================================

async def startup(app):

    asyncio.create_task(
        low_balance_checker(app)
    )

# =====================================
# MAIN
# =====================================

def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "balance",
            balance
        )
    )

    app.post_init = startup

    print(
        "DESCO Buddy Running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()