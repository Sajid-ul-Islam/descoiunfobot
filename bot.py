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

BASE_URL = "https://prepaid.desco.org.bd/api/unified/customer"

# =====================================
# CONVERSATION STATES
# =====================================

ASK_ACCOUNT = 0

# What to do after collecting the account number
ACTION_BALANCE  = "balance"
ACTION_INFO     = "info"

# =====================================
# DESCO API
# =====================================

def desco_get(endpoint: str, account_no: str) -> dict | None:
    url = f"{BASE_URL}/{endpoint}?accountNo={account_no}"
    response = requests.get(url, timeout=15, verify=False)
    result = response.json()
    return result.get("data")

# =====================================
# KEYBOARDS
# =====================================

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Balance",       callback_data="balance"),
            InlineKeyboardButton("👤 Customer Info", callback_data="info"),
        ],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="start")],
    ])

# =====================================
# HELPERS
# =====================================

async def send_main_menu(send_fn, account_no: str | None = None):
    saved = f"\n\n💾 Saved account: `{account_no}`" if account_no else ""
    await send_fn(
        f"👋 *Welcome to DESCO Info Bot!*{saved}\n\n"
        "Choose an option:",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

async def ask_for_account(send_fn, action: str, context: ContextTypes.DEFAULT_TYPE):
    """Ask the user for their account number if not saved."""
    saved = context.user_data.get("account_no")
    if saved:
        # Use saved account directly without asking
        return saved
    await send_fn(
        f"🔢 Enter your *DESCO account number*:\n\n"
        f"_Tip: found on your bill or meter card._",
        parse_mode="Markdown",
    )
    context.user_data["pending_action"] = action
    return None  # Signal: waiting for input

# =====================================
# COMMANDS — START & HELP
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    send = update.message.reply_text
    account_no = context.user_data.get("account_no")
    await send_main_menu(send, account_no)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *DESCO Info Bot — Help*\n\n"
        "*Commands:*\n"
        "• /start — Main menu\n"
        "• /balance — Check prepaid balance\n"
        "• /info — Customer & meter details\n"
        "• /forget — Clear saved account number\n"
        "• /help — This message\n"
        "• /cancel — Cancel current action\n\n"
        "*How it works:*\n"
        "The bot remembers your account number after first use, "
        "so you don\'t have to enter it every time.\n\n"
        "Use /forget to clear the saved number.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("account_no", None)
    await update.message.reply_text(
        "🗑 Saved account number cleared.\n"
        "You\'ll be asked again on next use.",
        reply_markup=main_keyboard(),
    )

# =====================================
# COMMANDS — BALANCE
# =====================================

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    send = update.message.reply_text
    result = await ask_for_account(send, ACTION_BALANCE, context)
    if result:
        await fetch_and_send_balance(send, result, context)
    else:
        return ASK_ACCOUNT
    return ConversationHandler.END


async def fetch_and_send_balance(send_fn, account_no: str, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["account_no"] = account_no
    await send_fn("⏳ Fetching balance...")
    try:
        data = desco_get("getBalance", account_no)
        if not data:
            await send_fn(
                "❌ *No data found* for that account number.",
                parse_mode="Markdown",
                reply_markup=back_keyboard(),
            )
            return

        balance  = data.get("balance", 0)
        usage    = data.get("currentMonthConsumption", 0)
        meter    = data.get("meterNo", "N/A")
        reading  = data.get("readingTime", "N/A")

        await send_fn(
            f"⚡ *Balance Info*\n\n"
            f"🔑 Account: `{account_no}`\n"
            f"💰 Balance: *৳{balance}*\n"
            f"📊 This Month: `{float(usage):.2f} Unit`\n"
            f"🔌 Meter No: `{meter}`\n"
            f"🕒 Last Reading: `{reading}`",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())

# =====================================
# COMMANDS — CUSTOMER INFO
# =====================================

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    send = update.message.reply_text
    result = await ask_for_account(send, ACTION_INFO, context)
    if result:
        await fetch_and_send_info(send, result, context)
    else:
        return ASK_ACCOUNT
    return ConversationHandler.END


async def fetch_and_send_info(send_fn, account_no: str, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["account_no"] = account_no
    await send_fn("⏳ Fetching customer info...")
    try:
        data = desco_get("getCustomerInfo", account_no)
        if not data:
            await send_fn(
                "❌ *No data found* for that account number.",
                parse_mode="Markdown",
                reply_markup=back_keyboard(),
            )
            return

        name     = data.get("customerName", "N/A")
        phone    = data.get("contactNo", "N/A")
        address  = data.get("installationAddress", "N/A")
        feeder   = data.get("feederName", "N/A")
        sd       = data.get("SDName", "N/A")
        tariff   = data.get("tariffSolution", "N/A")
        phase    = data.get("phaseType", "N/A")
        load     = data.get("sanctionLoad", "N/A")
        meter    = data.get("meterNo", "N/A")
        model    = data.get("meterModel", "N/A")
        inst_dt  = data.get("installationDate", "N/A")
        trafo    = data.get("transformer", "N/A")

        await send_fn(
            f"👤 *Customer Info*\n\n"
            f"🔑 Account: `{account_no}`\n"
            f"👤 Name: *{name}*\n"
            f"📞 Phone: `{phone}`\n"
            f"📍 Address: {address}\n\n"
            f"⚡ *Meter Details*\n"
            f"🔌 Meter No: `{meter}`\n"
            f"📦 Model: `{model}`\n"
            f"📅 Installed: `{inst_dt}`\n"
            f"🔧 Phase: `{phase}` | Load: `{load} kW`\n\n"
            f"🏗 *Supply Info*\n"
            f"🌐 Feeder: `{feeder}`\n"
            f"🏢 Sub-Division: `{sd}`\n"
            f"🔄 Transformer: `{trafo}`\n"
            f"📋 Tariff: `{tariff}`",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())

# =====================================
# CONVERSATION — ACCOUNT NUMBER INPUT
# =====================================

async def account_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    account_no = update.message.text.strip()
    send = update.message.reply_text

    if not account_no.isdigit():
        await send(
            "❌ *Invalid account number.* Digits only.\n\nTry again or /cancel.",
            parse_mode="Markdown",
        )
        return ASK_ACCOUNT  # Stay in state, let them retry

    action = context.user_data.get("pending_action", ACTION_BALANCE)

    if action == ACTION_BALANCE:
        await fetch_and_send_balance(send, account_no, context)
    elif action == ACTION_INFO:
        await fetch_and_send_info(send, account_no, context)

    context.user_data.pop("pending_action", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_action", None)
    await update.message.reply_text("❌ Cancelled.", reply_markup=main_keyboard())
    return ConversationHandler.END

# =====================================
# INLINE BUTTON HANDLER
# =====================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    send = query.message.reply_text
    data = query.data

    if data == "start":
        account_no = context.user_data.get("account_no")
        await send_main_menu(send, account_no)

    elif data == "help":
        await send(
            "📖 *DESCO Info Bot — Help*\n\n"
            "*Commands:*\n"
            "• /start — Main menu\n"
            "• /balance — Prepaid balance\n"
            "• /info — Customer & meter details\n"
            "• /forget — Clear saved account\n"
            "• /help — Help\n"
            "• /cancel — Cancel action",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )

    elif data == "balance":
        account_no = context.user_data.get("account_no")
        if account_no:
            await fetch_and_send_balance(send, account_no, context)
        else:
            await send(
                "🔢 Enter your *DESCO account number*:",
                parse_mode="Markdown",
            )
            context.user_data["pending_action"] = ACTION_BALANCE
            return ASK_ACCOUNT

    elif data == "info":
        account_no = context.user_data.get("account_no")
        if account_no:
            await fetch_and_send_info(send, account_no, context)
        else:
            await send(
                "🔢 Enter your *DESCO account number*:",
                parse_mode="Markdown",
            )
            context.user_data["pending_action"] = ACTION_INFO
            return ASK_ACCOUNT

# =====================================
# REGISTER BOT COMMANDS (/ MENU)
# =====================================

async def setup_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start",   "🏠 Main menu"),
        BotCommand("balance", "⚡ Check prepaid balance"),
        BotCommand("info",    "👤 Customer & meter info"),
        BotCommand("forget",  "🗑 Clear saved account number"),
        BotCommand("help",    "❓ Help & instructions"),
        BotCommand("cancel",  "❌ Cancel current action"),
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

    # Shared conversation handler covering all commands that need an account no
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("balance",  balance_cmd),
            CommandHandler("info",     info_cmd),
            CallbackQueryHandler(button_handler, pattern="^(balance|info)$"),
        ],
        states={
            ASK_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, account_received),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
    )

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("forget", forget_command))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(start|help)$"))
    app.add_handler(conv)

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