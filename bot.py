import asyncio
import os
import requests
import urllib3

from dotenv import load_dotenv
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

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ACCOUNT_NO = os.getenv("ACCOUNT_NO")
CHAT_ID = int(os.getenv("CHAT_ID"))
LOW_BALANCE_LIMIT = int(os.getenv("LOW_BALANCE_LIMIT", 100))

ALLOWED_USERS = {CHAT_ID}

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
# ACCESS CONTROL
# =====================================

def is_allowed(update: Update) -> bool:
    return update.effective_user.id in ALLOWED_USERS

# =====================================
# COMMANDS
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_allowed(update):
        await update.message.reply_text("⛔ Unauthorized")
        return

    await update.message.reply_text(
        "⚡ DESCO Info Online\n\n"
        "Commands:\n"
        "/balance"
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_allowed(update):
        await update.message.reply_text("⛔ Unauthorized")
        return

    try:

        data = get_balance_data()

        if not data:

            await update.message.reply_text(
                "❌ Account data পাওয়া যায়নি"
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
            f"⚡ DESCO Info\n\n"
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
        "DESCO Info Running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()