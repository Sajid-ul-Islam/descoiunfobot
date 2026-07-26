import asyncio
import os
import requests
import urllib3

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

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

BOT_TOKEN   = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT        = int(os.getenv("PORT", 10000))

# =====================================
# CONVERSATION STATES
# =====================================

WAITING_FOR_ACCOUNT = 0

# =====================================
# DESCO API
# =====================================

def get_balance_data(account_no: str):

    url = (
        "https://prepaid.desco.org.bd/api/unified/"
        f"customer/getBalance?accountNo={account_no}"
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
        "⚡ DESCO Info\n\n"
        "Commands:\n"
        "/balance — Check your prepaid balance"
    )


async def balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🔢 Please enter your DESCO account number:"
    )

    return WAITING_FOR_ACCOUNT


async def balance_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):

    account_no = update.message.text.strip()

    if not account_no.isdigit():

        await update.message.reply_text(
            "❌ Invalid account number. Please enter digits only.\n"
            "Try /balance again."
        )

        return ConversationHandler.END

    await update.message.reply_text("⏳ Fetching balance...")

    try:

        data = get_balance_data(account_no)

        if not data:

            await update.message.reply_text(
                "❌ No data found for that account number.\n"
                "Please check and try /balance again."
            )

            return ConversationHandler.END

        balance_amount = data.get("balance", 0)
        monthly_usage  = data.get("currentMonthConsumption", 0)
        meter_no       = data.get("meterNo", "N/A")
        reading_time   = data.get("readingTime", "N/A")

        msg = (
            f"⚡ DESCO Info\n\n"
            f"🔑 Account: {account_no}\n"
            f"💰 Balance: ৳{balance_amount}\n"
            f"📊 Monthly Usage: {float(monthly_usage):.2f} Unit\n"
            f"🔌 Meter: {meter_no}\n"
            f"🕒 Reading: {reading_time}"
        )

        await update.message.reply_text(msg)

    except Exception as e:

        await update.message.reply_text(
            f"❌ Error fetching data:\n{e}"
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("❌ Cancelled.")

    return ConversationHandler.END

# =====================================
# MAIN
# =====================================

def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))

    balance_conv = ConversationHandler(
        entry_points=[
            CommandHandler("balance", balance_start)
        ],
        states={
            WAITING_FOR_ACCOUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    balance_fetch
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel)
        ],
    )

    app.add_handler(balance_conv)

    print("DESCO Info Running (webhook)...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )


if __name__ == "__main__":
    main()