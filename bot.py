import os
import requests
import urllib3
from datetime import date

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
ACTION_STATS    = "stats"
ACTION_SUMMARY  = "summary"

# =====================================
# DESCO API
# =====================================

def desco_get(endpoint: str, account_no: str) -> tuple:
    """Returns (data, code, desc, raw)."""
    url = f"{BASE_URL}/{endpoint}?accountNo={account_no}"
    response = requests.get(url, timeout=15, verify=False)
    print(f"[DESCO] {endpoint} | status={response.status_code} | body={response.text[:300]}")
    raw  = response.json()
    data = raw.get("data")
    code = raw.get("code", 0)
    desc = raw.get("desc", "Unknown error")
    return data, code, desc, raw

# =====================================
# TARIFF CALCULATOR (DESCO LT-A slabs)
# =====================================

LTA_SLABS = [
    (50,  3.75),
    (75,  5.14),
    (200, 5.72),
    (300, 6.01),
    (400, 6.30),
    (float("inf"), 10.70),
]

def estimate_bill(units: float) -> float:
    """Estimate DESCO LT-A bill from units consumed (approx, excl. demand charge)."""
    charge = 0.0
    prev = 0
    for limit, rate in LTA_SLABS:
        if units <= 0:
            break
        slab_units = min(units, limit - prev)
        charge += slab_units * rate
        units -= slab_units
        prev = limit
    return round(charge, 2)

# =====================================
# DERIVED STATS HELPER
# =====================================

def calc_stats(balance_data: dict, info_data: dict | None = None) -> dict:
    today          = date.today()
    reading_str    = balance_data.get("readingTime", str(today))
    try:
        reading_date = date.fromisoformat(reading_str)
    except ValueError:
        reading_date = today

    days_elapsed   = max(today.day, 1)          # days into this month
    month_days     = 30                          # approx month length
    days_left      = max(month_days - days_elapsed, 0)

    usage          = float(balance_data.get("currentMonthConsumption", 0))
    bal            = float(balance_data.get("balance", 0))

    daily_avg      = round(usage / days_elapsed, 2) if days_elapsed else 0
    projected_mo   = round(daily_avg * month_days, 2)
    est_bill       = estimate_bill(projected_mo)
    days_bal_lasts = round(bal / (daily_avg * 8), 1) if daily_avg > 0 else "∞"  # ≈৳8/unit avg

    conn_age = None
    load_pct = None
    if info_data:
        inst_str = info_data.get("installationDate")
        if inst_str:
            try:
                inst = date.fromisoformat(inst_str)
                delta = today - inst
                years  = delta.days // 365
                months = (delta.days % 365) // 30
                conn_age = f"{years}y {months}m" if years else f"{months} months"
            except ValueError:
                pass
        load_kw = info_data.get("sanctionLoad", 0)
        if load_kw:
            load_pct = round((daily_avg / 24) / load_kw * 100, 1)  # kWh→kW avg

    return {
        "today":          today,
        "days_elapsed":   days_elapsed,
        "days_left":      days_left,
        "daily_avg":      daily_avg,
        "projected_mo":   projected_mo,
        "est_bill":       est_bill,
        "days_bal_lasts": days_bal_lasts,
        "conn_age":       conn_age,
        "load_pct":       load_pct,
    }

# =====================================
# KEYBOARDS
# =====================================

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Balance",       callback_data="balance"),
            InlineKeyboardButton("👤 Customer Info", callback_data="info"),
        ],
        [
            InlineKeyboardButton("📊 Stats",   callback_data="stats"),
            InlineKeyboardButton("📋 Summary", callback_data="summary"),
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
        "🔢 Enter your *DESCO account number*:\n\n"
        "_Found on your electricity bill or prepaid meter card._",
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
        data, code, desc, _ = desco_get("getBalance", account_no)
        if not data:
            if code == 200:
                msg = (
                    "⚠️ *Account found but no data available.*\n\n"
                    "This account may be newly registered or inactive."
                )
            else:
                msg = (
                    f"❌ *{desc}*\n\n"
                    "Please double-check your account number."
                )
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
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


# =====================================
# COMMANDS — STATS
# =====================================

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    send = update.message.reply_text
    result = await ask_for_account(send, ACTION_STATS, context)
    if result:
        await fetch_and_send_stats(send, result, context)
    else:
        return ASK_ACCOUNT
    return ConversationHandler.END


async def fetch_and_send_stats(send_fn, account_no: str, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["account_no"] = account_no
    await send_fn("⏳ Calculating stats...")
    try:
        bal_data, bal_code, bal_desc, _ = desco_get("getBalance",      account_no)
        info_data, _, _, _               = desco_get("getCustomerInfo", account_no)
        if not bal_data:
            if bal_code == 200:
                msg = "⚠️ *Account found but no data available yet.*"
            else:
                msg = f"❌ *{bal_desc}*\n\nPlease double-check your account number."
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return

        s = calc_stats(bal_data, info_data)
        load_line = f"⚡ Load Utilisation: `{s['load_pct']}%`\n" if s["load_pct"] is not None else ""
        conn_line = f"🏗 Connection Age: `{s['conn_age']}`\n" if s["conn_age"] else ""

        await send_fn(
            f"📊 *Usage Statistics*\n\n"
            f"🔑 Account: `{account_no}`\n"
            f"📅 Days into month: `{s['days_elapsed']}`\n"
            f"📆 Days remaining: `{s['days_left']}`\n\n"
            f"⚡ *Consumption*\n"
            f"📈 This month so far: `{bal_data.get('currentMonthConsumption', 0):.2f} Unit`\n"
            f"📉 Daily average: `{s['daily_avg']} Unit/day`\n"
            f"🔮 Projected this month: `{s['projected_mo']} Unit`\n\n"
            f"💰 *Balance*\n"
            f"💵 Current: *৳{bal_data.get('balance', 0)}*\n"
            f"🕐 Est. days balance lasts: `{s['days_bal_lasts']} days`\n\n"
            f"🧾 *Bill Estimate (LT-A)*\n"
            f"💳 Approx bill: *~৳{s['est_bill']}*\n"
            f"_(Based on projected {s['projected_mo']} units, excl. demand charge)_\n\n"
            f"{load_line}{conn_line}",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())

# =====================================
# COMMANDS — SUMMARY
# =====================================

async def summary_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    send = update.message.reply_text
    result = await ask_for_account(send, ACTION_SUMMARY, context)
    if result:
        await fetch_and_send_summary(send, result, context)
    else:
        return ASK_ACCOUNT
    return ConversationHandler.END


async def fetch_and_send_summary(send_fn, account_no: str, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["account_no"] = account_no
    await send_fn("⏳ Fetching full summary...")
    try:
        bal_data, bal_code, bal_desc, _ = desco_get("getBalance",      account_no)
        info_data, info_code, info_desc, _ = desco_get("getCustomerInfo", account_no)
        if not bal_data or not info_data:
            if bal_code == 200 or info_code == 200:
                msg = "⚠️ *Account found but no data available yet.*"
            else:
                msg = f"❌ *{bal_desc or info_desc}*\n\nPlease double-check your account number."
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return

        s    = calc_stats(bal_data, info_data)
        name = info_data.get("customerName", "N/A")
        addr = info_data.get("installationAddress", "N/A")
        tariff = info_data.get("tariffSolution", "N/A")
        phase  = info_data.get("phaseType", "N/A")
        load   = info_data.get("sanctionLoad", "N/A")
        meter  = info_data.get("meterNo", "N/A")
        feeder = info_data.get("feederName", "N/A")
        conn_line = f"🏗 Connection age: `{s['conn_age']}`\n" if s["conn_age"] else ""

        await send_fn(
            f"📋 *Full Account Summary*\n\n"
            f"👤 *{name}*\n"
            f"🔑 Account: `{account_no}`\n"
            f"📍 {addr}\n\n"
            f"💰 *Balance & Usage*\n"
            f"💵 Balance: *৳{bal_data.get('balance', 0)}*\n"
            f"📈 This month: `{bal_data.get('currentMonthConsumption', 0):.2f} Unit`\n"
            f"📉 Daily avg: `{s['daily_avg']} Unit/day`\n"
            f"🔮 Projected: `{s['projected_mo']} Unit`\n"
            f"💳 Est. bill: *~৳{s['est_bill']}*\n"
            f"🕐 Balance lasts ~`{s['days_bal_lasts']} days`\n\n"
            f"🔌 *Meter & Connection*\n"
            f"🔌 Meter: `{meter}` | {phase} | `{load} kW`\n"
            f"🌐 Feeder: `{feeder}`\n"
            f"📋 Tariff: `{tariff}`\n"
            f"{conn_line}",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())

async def fetch_and_send_info(send_fn, account_no: str, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["account_no"] = account_no
    await send_fn("⏳ Fetching customer info...")
    try:
        data, code, desc, _ = desco_get("getCustomerInfo", account_no)
        if not data:
            if code == 200:
                msg = (
                    "⚠️ *Account found but no customer info available.*\n\n"
                    "This account may be newly registered or inactive."
                )
            else:
                msg = (
                    f"❌ *{desc}*\n\n"
                    "Please double-check your account number."
                )
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
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
    elif action == ACTION_STATS:
        await fetch_and_send_stats(send, account_no, context)
    elif action == ACTION_SUMMARY:
        await fetch_and_send_summary(send, account_no, context)

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

    elif data == "stats":
        account_no = context.user_data.get("account_no")
        if account_no:
            await fetch_and_send_stats(send, account_no, context)
        else:
            await send("🔢 Enter your *DESCO account number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_STATS
            return ASK_ACCOUNT

    elif data == "summary":
        account_no = context.user_data.get("account_no")
        if account_no:
            await fetch_and_send_summary(send, account_no, context)
        else:
            await send("🔢 Enter your *DESCO account number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_SUMMARY
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
        BotCommand("stats",   "📊 Usage stats & bill estimate"),
        BotCommand("summary", "📋 Full account summary"),
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
            CommandHandler("stats",    stats_cmd),
            CommandHandler("summary",  summary_cmd),
            CallbackQueryHandler(button_handler, pattern="^(balance|info|stats|summary)$"),
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
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(stats|summary)$"))
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