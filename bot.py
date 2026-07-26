import asyncio
import os
import requests
import urllib3

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
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
# KEYBOARDS
# =====================================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Check Balance", callback_data="balance")],
        [InlineKeyboardButton("❓ Help",          callback_data="help")],
    ])

# =====================================
# COMMANDS
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "👋 Welcome to *DESCO Info Bot*!\n\n"
        "I can check your prepaid electricity balance "
        "from DESCO instantly.\n\n"
        "Choose an option below or use the menu:"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "📖 *DESCO Info Bot — Help*\n\n"
        "Available commands:\n"
        "• /start — Show main menu\n"
        "• /balance — Check your prepaid balance\n"
        "• /help — Show this help message\n\n"
        "To check your balance, send /balance and "
        "enter your DESCO account number when prompted.\n\n"
        "You can find your account number on your "
        "electricity bill or meter card."
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


# =====================================
# BALANCE CONVERSATION
# =====================================

async def balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Works from both /balance command and inline button
    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.message.reply_text
    else:
        send = update.message.reply_text

    await send(
        "🔢 Please enter your *DESCO account number*:\n\n"
        "_Tip: You can find it on your bill or meter card._",
        parse_mode="Markdown",
    )

    return WAITING_FOR_ACCOUNT


async def balance_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):

    account_no = update.message.text.strip()

    if not account_no.isdigit():

        await update.message.reply_text(
            "❌ *Invalid account number.*\n"
            "Please enter digits only.\n\n"
            "Try /balance again.",
            parse_mode="Markdown",
        )

        return ConversationHandler.END

    await update.message.reply_text("⏳ Fetching your balance...")

    try:

        data = get_balance_data(account_no)

        if not data:

            await update.message.reply_text(
                "❌ *No data found* for that account number.\n"
                "Please check and try /balance again.",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(),
            )

            return ConversationHandler.END

        balance_amount = data.get("balance", 0)
        monthly_usage  = data.get("currentMonthConsumption", 0)
        meter_no       = data.get("meterNo", "N/A")
        reading_time   = data.get("readingTime", "N/A")

        msg = (
            f"⚡ *DESCO Info*\n\n"
            f"🔑 Account: `{account_no}`\n"
            f"💰 Balance: *৳{balance_amount}*\n"
            f"📊 Monthly Usage: `{float(monthly_usage):.2f} Unit`\n"
            f"🔌 Meter: `{meter_no}`\n"
            f"🕒 Reading: `{reading_time}`"
        )

        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ *Error fetching data:*\n`{e}`",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "❌ Cancelled.",
        reply_markup=main_menu_keyboard(),
    )

    return ConversationHandler.END

# =====================================
# INLINE BUTTON HANDLER
# =====================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "help":

        text = (
            "📖 *DESCO Info Bot — Help*\n\n"
            "Available commands:\n"
            "• /start — Show main menu\n"
            "• /balance — Check your prepaid balance\n"
            "• /help — Show this help message\n\n"
            "To check your balance, send /balance and "
            "enter your DESCO account number when prompted.\n\n"
            "You can find your account number on your "
            "electricity bill or meter card."
        )

        await query.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

# =====================================
# REGISTER BOT COMMANDS (/ MENU)
# =====================================

async def setup_commands(app):

    await app.bot.set_my_commands([
        BotCommand("start",   "🏠 Main menu"),
        BotCommand("balance", "⚡ Check prepaid balance"),
        BotCommand("help",    "❓ Help & instructions"),
    ])

# =====================================
# MAIN
# =====================================

def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Inline button handler (must be before ConversationHandler)
    app.add_handler(
        CallbackQueryHandler(button_handler, pattern="^help$")
    )

    # Balance conversation (inline button "balance" as entry point too)
    balance_conv = ConversationHandler(
        entry_points=[
            CommandHandler("balance", balance_start),
            CallbackQueryHandler(balance_start, pattern="^balance$"),
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

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(balance_conv)

    app.post_init = setup_commands

    print("DESCO Info Running (webhook)...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )


if __name__ == "__main__":
    main()