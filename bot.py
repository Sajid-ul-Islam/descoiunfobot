import os
import requests
import urllib3
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from db import init_db, track_user, get_admin_stats

# =====================================
# CONFIG
# =====================================

load_dotenv()

BOT_TOKEN   = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT        = int(os.getenv("PORT", 10000))
ADMIN_ID    = int(os.getenv("ADMIN_ID", 0))

BASE_API = "https://prepaid.desco.org.bd/api"
SYSTEMS  = ["unified", "tkdes"]

# =====================================
# CONVERSATION STATES
# =====================================

ASK_ACCOUNT = 0

ACTION_BALANCE  = "balance"
ACTION_INFO     = "info"
ACTION_STATS    = "stats"
ACTION_SUMMARY  = "summary"
ACTION_RECHARGE = "recharge"
ACTION_MONTHLY  = "monthly"
ACTION_DAILY    = "daily"

# =====================================
# DESCO API
# =====================================

def desco_get(system: str, endpoint: str, account_no: str,
              meter_no: str = "", **params) -> tuple:
    """Returns (data, code, desc). Raises on network error."""
    url = (
        f"{BASE_API}/{system}/customer/{endpoint}"
        f"?accountNo={account_no}&meterNo={meter_no}"
    )
    for k, v in params.items():
        url += f"&{k}={v}"
    print(f"[DESCO] GET {url}")
    r = requests.get(url, timeout=15, verify=False)
    raw  = r.json()
    data = raw.get("data")
    code = raw.get("code", 0)
    desc = raw.get("desc", "Unknown error")
    return data, code, desc


def detect_system(user_input: str) -> tuple:
    """
    Try user_input as accountNo then as meterNo across both systems.
    Returns (system, account_no, meter_no, info_data) or (None, None, None, None).
    """
    combos = [
        (user_input, ""),   # treat as account number
        ("",   user_input),  # treat as meter number
    ]
    for system in SYSTEMS:
        for acc, met in combos:
            try:
                data, code, _ = desco_get(system, "getCustomerInfo", acc, met)
                if data:
                    account_no = data.get("accountNo") or acc or ""
                    meter_no   = data.get("meterNo")   or met or ""
                    return system, account_no, meter_no, data
            except Exception:
                pass
    return None, None, None, None

# =====================================
# TARIFF CALCULATOR (DESCO LT-A slabs)
# =====================================

LTA_SLABS = [
    (50,          3.75),
    (75,          5.14),
    (200,         5.72),
    (300,         6.01),
    (400,         6.30),
    (float("inf"), 10.70),
]

def estimate_bill(units: float) -> float:
    charge, prev = 0.0, 0
    for limit, rate in LTA_SLABS:
        if units <= 0:
            break
        slab = min(units, limit - prev)
        charge += slab * rate
        units  -= slab
        prev    = limit
    return round(charge, 2)

# =====================================
# DERIVED STATS HELPER
# =====================================

def calc_stats(balance_data: dict, info_data: dict | None = None) -> dict:
    today        = date.today()
    days_elapsed = max(today.day, 1)
    month_days   = 30
    days_left    = max(month_days - days_elapsed, 0)
    usage        = float(balance_data.get("currentMonthConsumption", 0))
    bal          = float(balance_data.get("balance", 0))
    daily_avg    = round(usage / days_elapsed, 2) if days_elapsed else 0
    projected_mo = round(daily_avg * month_days, 2)
    est_bill     = estimate_bill(projected_mo)
    days_bal     = round(bal / (daily_avg * 8), 1) if daily_avg > 0 else "∞"
    conn_age = load_pct = None
    if info_data:
        inst_str = info_data.get("installationDate")
        if inst_str:
            try:
                inst   = date.fromisoformat(inst_str)
                delta  = today - inst
                years  = delta.days // 365
                months = (delta.days % 365) // 30
                conn_age = f"{years}y {months}m" if years else f"{months} months"
            except ValueError:
                pass
        load_kw = info_data.get("sanctionLoad", 0)
        if load_kw:
            load_pct = round((daily_avg / 24) / load_kw * 100, 1)
    return dict(
        days_elapsed=days_elapsed, days_left=days_left,
        daily_avg=daily_avg, projected_mo=projected_mo,
        est_bill=est_bill, days_bal_lasts=days_bal,
        conn_age=conn_age, load_pct=load_pct,
    )

# =====================================
# KEYBOARDS
# =====================================

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Balance",        callback_data="balance"),
            InlineKeyboardButton("👤 Customer Info",  callback_data="info"),
        ],
        [
            InlineKeyboardButton("📊 Stats",          callback_data="stats"),
            InlineKeyboardButton("📋 Summary",        callback_data="summary"),
        ],
        [
            InlineKeyboardButton("📆 Daily Usage",     callback_data="daily"),
            InlineKeyboardButton("📅 Monthly Usage",   callback_data="monthly"),
        ],
        [
            InlineKeyboardButton("💳 Recharge History", callback_data="recharge"),
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

async def send_main_menu(send_fn, account_no=None, system=None):
    saved = f"\n\n💾 Account: `{account_no}` _{system}_" if account_no else ""
    await send_fn(
        f"👋 *Welcome to DESCO Info Bot!*{saved}\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def resolve_account(update, context, action):
    """Return (account_no, system, meter_no) from session or ask user."""
    account_no = context.user_data.get("account_no")
    system     = context.user_data.get("system")
    meter_no   = context.user_data.get("meter_no", "")
    if account_no and system:
        return account_no, system, meter_no
    send = (update.message or update.callback_query.message).reply_text
    await send(
        "🔢 Enter your *account number* or *meter number*:\n\n"
        "_Both are printed on your electricity bill or meter card._",
        parse_mode="Markdown",
    )
    context.user_data["pending_action"] = action
    return None, None, None

# =====================================
# COMMANDS — START & HELP
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/start")
    account_no = context.user_data.get("account_no")
    system     = context.user_data.get("system")
    await send_main_menu(update.message.reply_text, account_no, system)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/help")
    await update.message.reply_text(
        "📖 *DESCO Info Bot — Help*\n\n"
        "*Commands:*\n"
        "• /start — Main menu\n"
        "• /balance — Prepaid balance\n"
        "• /info — Customer & meter details\n"
        "• /stats — Usage stats & bill estimate\n"
        "• /summary — Full summary\n"
        "• /daily — Daily usage & cost breakdown\n"
        "• /recharge — Last 12 months recharge history\n"
        "• /monthly — Monthly consumption history\n"
        "• /forget — Clear saved account\n"
        "• /cancel — Cancel current action\n\n"
        "*Supported systems:* `unified` and `tkdes`\n"
        "The bot auto-detects which system your account is on.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🗑 Saved account cleared.",
        reply_markup=main_keyboard(),
    )

# =====================================
# ACCOUNT NUMBER COLLECTION
# =====================================

async def account_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    send = update.message.reply_text
    if not user_input.isdigit():
        await send(
            "❌ *Invalid.* Enter digits only (account or meter number), or /cancel.",
            parse_mode="Markdown",
        )
        return ASK_ACCOUNT

    await send("🔍 Detecting account...")
    system, account_no, meter_no, info_data = detect_system(user_input)

    if not system:
        await send(
            "❌ *Not found on DESCO servers.*\n\n"
            "Please double-check your account number or meter number.",
            parse_mode="Markdown",
            reply_markup=back_keyboard(),
        )
        return ConversationHandler.END

    context.user_data["account_no"] = account_no
    context.user_data["system"]     = system
    context.user_data["meter_no"]   = meter_no

    track_user(update.effective_user, "account_submit", account_no)

    await send(
        f"✅ Found on *{system}* system\n"
        f"🔑 Account: `{account_no}`\n"
        f"🔌 Meter: `{meter_no}`",
        parse_mode="Markdown",
    )

    action = context.user_data.pop("pending_action", ACTION_BALANCE)
    dispatch = {
        ACTION_BALANCE:  fetch_and_send_balance,
        ACTION_INFO:     fetch_and_send_info,
        ACTION_STATS:    fetch_and_send_stats,
        ACTION_SUMMARY:  fetch_and_send_summary,
        ACTION_RECHARGE: fetch_and_send_recharge,
        ACTION_MONTHLY:  fetch_and_send_monthly,
    }
    await dispatch[action](send, account_no, system, meter_no, context)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_action", None)
    await update.message.reply_text("❌ Cancelled.", reply_markup=main_keyboard())
    return ConversationHandler.END

# =====================================
# FETCH FUNCTIONS
# =====================================

async def fetch_and_send_balance(send_fn, account_no, system, meter_no, context):
    await send_fn("⏳ Fetching balance...")
    try:
        data, code, desc = desco_get(system, "getBalance", account_no, meter_no)
        if not data:
            msg = ("⚠️ *Account found but no balance data.*"
                   if code == 200 else f"❌ *{desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return
        await send_fn(
            f"⚡ *Balance Info*\n\n"
            f"🔑 Account: `{account_no}` _{system}_\n"
            f"💰 Balance: *৳{data.get('balance', 0)}*\n"
            f"📊 This Month: `{float(data.get('currentMonthConsumption', 0)):.2f} Unit`\n"
            f"🔌 Meter: `{data.get('meterNo', 'N/A')}`\n"
            f"🕒 Last Reading: `{data.get('readingTime', 'N/A')}`",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_info(send_fn, account_no, system, meter_no, context):
    await send_fn("⏳ Fetching customer info...")
    try:
        data, code, desc = desco_get(system, "getCustomerInfo", account_no, meter_no)
        if not data:
            msg = ("⚠️ *Account found but no info available.*"
                   if code == 200 else f"❌ *{desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return
        await send_fn(
            f"👤 *Customer Info*\n\n"
            f"🔑 Account: `{account_no}` _{system}_\n"
            f"👤 Name: *{data.get('customerName', 'N/A')}*\n"
            f"📞 Phone: `{data.get('contactNo', 'N/A')}`\n"
            f"📍 Address: {data.get('installationAddress', 'N/A')}\n\n"
            f"⚡ *Meter Details*\n"
            f"🔌 Meter: `{data.get('meterNo', 'N/A')}`\n"
            f"📦 Model: `{data.get('meterModel', 'N/A')}`\n"
            f"📅 Installed: `{data.get('installationDate', 'N/A')}`\n"
            f"🔧 Phase: `{data.get('phaseType', 'N/A')}` | Load: `{data.get('sanctionLoad', 'N/A')} kW`\n\n"
            f"🏗 *Supply Info*\n"
            f"🌐 Feeder: `{data.get('feederName', 'N/A')}`\n"
            f"🏢 Sub-Division: `{data.get('SDName', 'N/A')}`\n"
            f"🔄 Transformer: `{data.get('transformer', 'N/A')}`\n"
            f"📋 Tariff: `{data.get('tariffSolution', 'N/A')}`",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_stats(send_fn, account_no, system, meter_no, context):
    await send_fn("⏳ Calculating stats...")
    try:
        bal_data,  bal_code,  bal_desc  = desco_get(system, "getBalance",      account_no, meter_no)
        info_data, info_code, info_desc = desco_get(system, "getCustomerInfo", account_no, meter_no)
        if not bal_data:
            msg = ("⚠️ No balance data." if bal_code == 200 else f"❌ *{bal_desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return
        s = calc_stats(bal_data, info_data)
        load_line = f"⚡ Load Utilisation: `{s['load_pct']}%`\n" if s["load_pct"] is not None else ""
        conn_line = f"🏗 Connection Age: `{s['conn_age']}`\n"  if s["conn_age"]            else ""
        await send_fn(
            f"📊 *Usage Statistics*\n\n"
            f"🔑 Account: `{account_no}` _{system}_\n"
            f"📅 Days into month: `{s['days_elapsed']}`\n"
            f"📆 Days remaining: `{s['days_left']}`\n\n"
            f"⚡ *Consumption*\n"
            f"📈 This month: `{float(bal_data.get('currentMonthConsumption',0)):.2f} Unit`\n"
            f"📉 Daily average: `{s['daily_avg']} Unit/day`\n"
            f"🔮 Projected: `{s['projected_mo']} Unit`\n\n"
            f"💰 *Balance*\n"
            f"💵 Current: *৳{bal_data.get('balance', 0)}*\n"
            f"🕐 Est. days left: `{s['days_bal_lasts']} days`\n\n"
            f"🧾 *Bill Estimate (LT-A)*\n"
            f"💳 Approx: *~৳{s['est_bill']}*\n"
            f"_(Based on {s['projected_mo']} projected units, excl. demand charge)_\n\n"
            f"{load_line}{conn_line}",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_summary(send_fn, account_no, system, meter_no, context):
    await send_fn("⏳ Fetching full summary...")
    try:
        bal_data,  _, _  = desco_get(system, "getBalance",      account_no, meter_no)
        info_data, _, _  = desco_get(system, "getCustomerInfo", account_no, meter_no)
        if not bal_data or not info_data:
            await send_fn("⚠️ Incomplete data returned.", reply_markup=back_keyboard())
            return
        s = calc_stats(bal_data, info_data)
        conn_line = f"🏗 Connection age: `{s['conn_age']}`\n" if s["conn_age"] else ""
        await send_fn(
            f"📋 *Full Account Summary*\n\n"
            f"👤 *{info_data.get('customerName','N/A')}*\n"
            f"🔑 Account: `{account_no}` _{system}_\n"
            f"📍 {info_data.get('installationAddress','N/A')}\n\n"
            f"💰 *Balance & Usage*\n"
            f"💵 Balance: *৳{bal_data.get('balance',0)}*\n"
            f"📈 This month: `{float(bal_data.get('currentMonthConsumption',0)):.2f} Unit`\n"
            f"📉 Daily avg: `{s['daily_avg']} Unit/day`\n"
            f"🔮 Projected: `{s['projected_mo']} Unit`\n"
            f"💳 Est. bill: *~৳{s['est_bill']}*\n"
            f"🕐 Balance lasts ~`{s['days_bal_lasts']} days`\n\n"
            f"🔌 *Meter & Connection*\n"
            f"🔌 Meter: `{info_data.get('meterNo','N/A')}` | "
            f"{info_data.get('phaseType','N/A')} | "
            f"`{info_data.get('sanctionLoad','N/A')} kW`\n"
            f"🌐 Feeder: `{info_data.get('feederName','N/A')}`\n"
            f"📋 Tariff: `{info_data.get('tariffSolution','N/A')}`\n"
            f"{conn_line}",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_recharge(send_fn, account_no, system, meter_no, context):
    await send_fn("⏳ Fetching recharge history...")
    try:
        today     = date.today()
        date_from = (today - timedelta(days=350)).strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")
        data, code, desc = desco_get(
            system, "getRechargeHistory", account_no, meter_no,
            dateFrom=date_from, dateTo=date_to,
        )
        if not data:
            msg = ("⚠️ No recharge history found." if code == 200 else f"❌ *{desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return
        records = data if isinstance(data, list) else [data]
        lines   = []
        for r in records[:15]:  # max 15 entries
            dt  = r.get("rechargeDate") or r.get("date", "N/A")
            amt = r.get("totalAmount") or r.get("rechargeAmount") or r.get("amount", "N/A")
            tok = r.get("tokenNo", "")
            line = f"📆 `{dt}` — *৳{amt}*"
            if tok:
                line += f"\n   🔑 Token: `{tok}`"
            lines.append(line)
        await send_fn(
            f"💳 *Recharge History* (last 12 months)\n"
            f"🔑 Account: `{account_no}` _{system}_\n\n"
            + "\n\n".join(lines),
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_monthly(send_fn, account_no, system, meter_no, context):
    await send_fn("⏳ Fetching monthly consumption...")
    try:
        today      = date.today()
        month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
        month_to   = today.strftime("%Y-%m")
        data, code, desc = desco_get(
            system, "getCustomerMonthlyConsumption", account_no, meter_no,
            monthFrom=month_from, monthTo=month_to,
        )
        if not data:
            msg = ("⚠️ No consumption history found." if code == 200 else f"❌ *{desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return
        records = data if isinstance(data, list) else [data]
        records = sorted(records, key=lambda x: str(x.get("month", "")), reverse=True)
        lines   = []
        for r in records[:12]:
            month = r.get("month") or r.get("readingMonth", "N/A")
            units = r.get("consumedUnit") or r.get("consumption") or r.get("unit", "0")
            taka  = r.get("consumedTaka") or r.get("amount") or r.get("billAmount", "0")
            line  = f"📅 `{month}` — `{float(units):.2f} Unit` | *৳{float(taka):.2f}*"
            lines.append(line)
        await send_fn(
            f"📊 *Monthly Consumption* (last 12 months)\n"
            f"🔑 Account: `{account_no}` _{system}_\n\n"
            + "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_daily(send_fn, account_no, system, meter_no, context):
    await send_fn("⏳ Fetching daily usage & cost breakdown...")
    try:
        today = date.today()
        # Fetch current month (from 1st of month to today)
        date_from = today.replace(day=1).strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")
        data, code, desc = desco_get(
            system, "getCustomerDailyConsumption", account_no, meter_no,
            dateFrom=date_from, dateTo=date_to,
        )
        if not data or len(data) < 2:
            # Fallback to last 30 days
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            data, code, desc = desco_get(
                system, "getCustomerDailyConsumption", account_no, meter_no,
                dateFrom=date_from, dateTo=date_to,
            )

        if not data:
            msg = ("⚠️ No daily consumption history found." if code == 200 else f"❌ *{desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return

        records = data if isinstance(data, list) else [data]
        records = sorted(records, key=lambda x: str(x.get("date", "")))

        lines = []
        for i in range(1, len(records)):
            prev_rec = records[i-1]
            curr_rec = records[i]
            d_str    = curr_rec.get("date", "N/A")

            u_curr  = float(curr_rec.get("consumedUnit") or 0)
            u_prev  = float(prev_rec.get("consumedUnit") or 0)
            u_delta = max(u_curr - u_prev, 0)

            t_curr  = float(curr_rec.get("consumedTaka") or 0)
            t_prev  = float(prev_rec.get("consumedTaka") or 0)
            t_delta = max(t_curr - t_prev, 0)

            rate = (t_delta / u_delta) if u_delta > 0 else 0

            lines.append(
                f"📆 `{d_str}` — `{u_delta:.2f} Unit` | *৳{t_delta:.2f}* `(@৳{rate:.2f}/u)`"
            )

        if not lines and records:
            r = records[0]
            lines.append(f"📆 `{r.get('date')}` — `{float(r.get('consumedUnit',0)):.2f} Unit` | *৳{float(r.get('consumedTaka',0)):.2f}*")

        lines.reverse()

        await send_fn(
            f"📆 *Daily Usage & Cost Breakdown*\n"
            f"🔑 Account: `{account_no}` _{system}_\n\n"
            + "\n".join(lines[:25]),
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())

# =====================================
# COMMAND ENTRY POINTS
# =====================================

async def _cmd(action: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    send = update.message.reply_text
    account_no, system, meter_no = await resolve_account(update, context, action)
    track_user(update.effective_user, f"/{action}", account_no or "")
    if not account_no:
        return ASK_ACCOUNT
    dispatch = {
        ACTION_BALANCE:  fetch_and_send_balance,
        ACTION_INFO:     fetch_and_send_info,
        ACTION_STATS:    fetch_and_send_stats,
        ACTION_SUMMARY:  fetch_and_send_summary,
        ACTION_RECHARGE: fetch_and_send_recharge,
        ACTION_MONTHLY:  fetch_and_send_monthly,
        ACTION_DAILY:    fetch_and_send_daily,
    }
    await dispatch[action](send, account_no, system, meter_no, context)
    return ConversationHandler.END

async def balance_cmd(u, c):  return await _cmd(ACTION_BALANCE,  u, c)
async def info_cmd(u, c):     return await _cmd(ACTION_INFO,     u, c)
async def stats_cmd(u, c):    return await _cmd(ACTION_STATS,    u, c)
async def summary_cmd(u, c):  return await _cmd(ACTION_SUMMARY,  u, c)
async def recharge_cmd(u, c): return await _cmd(ACTION_RECHARGE, u, c)
async def monthly_cmd(u, c):  return await _cmd(ACTION_MONTHLY,  u, c)
async def daily_cmd(u, c):    return await _cmd(ACTION_DAILY,    u, c)

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
        system     = context.user_data.get("system")
        await send_main_menu(send, account_no, system)
        return

    if data == "help":
        await send(
            "📖 *Help*\n\n"
            "• /balance — Balance\n"
            "• /info — Customer & meter info\n"
            "• /stats — Usage stats\n"
            "• /summary — Full summary\n"
            "• /recharge — Recharge history\n"
            "• /monthly — Monthly consumption\n"
            "• /forget — Clear saved account",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
        return

    ACTION_MAP = {
        "balance":  (ACTION_BALANCE,  fetch_and_send_balance),
        "info":     (ACTION_INFO,     fetch_and_send_info),
        "stats":    (ACTION_STATS,    fetch_and_send_stats),
        "summary":  (ACTION_SUMMARY,  fetch_and_send_summary),
        "recharge": (ACTION_RECHARGE, fetch_and_send_recharge),
        "monthly":  (ACTION_MONTHLY,  fetch_and_send_monthly),
        "daily":    (ACTION_DAILY,    fetch_and_send_daily),
    }
    if data in ACTION_MAP:
        action, fetch_fn = ACTION_MAP[data]
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system")
        meter_no   = context.user_data.get("meter_no", "")
        track_user(update.effective_user, f"btn_{action}", account_no or "")
        if account_no and system:
            await fetch_fn(send, account_no, system, meter_no, context)
        else:
            await send("🔢 Enter your *DESCO account number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = action
            return ASK_ACCOUNT

# =====================================
# ADMIN COMMAND
# =====================================

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        # Completely silent for non-admin users
        return

    track_user(update.effective_user, "/admin")
    stats = get_admin_stats()

    users_list = []
    for u in stats["recent_users"]:
        name = u["first_name"] or u["username"] or str(u["user_id"])
        users_list.append(f"• `{u['user_id']}` ({name}) — {u['request_count']} reqs")

    recent_str = "\n".join(users_list) if users_list else "None"

    await update.message.reply_text(
        f"📊 *DESCO Bot Usage Statistics*\n\n"
        f"👥 *Total Unique Users:* `{stats['total_users']}`\n"
        f"🔥 *Active Today:* `{stats['active_today']}`\n"
        f"📆 *Active Past 7 Days:* `{stats['active_week']}`\n"
        f"⚡ *Total Requests Processed:* `{stats['total_requests']}`\n\n"
        f"👤 *Recent Active Users:*\n{recent_str}",
        parse_mode="Markdown"
    )

# =====================================
# REGISTER BOT COMMANDS
# =====================================

async def setup_commands(app):
    # Public command menu for normal users (NO /admin)
    await app.bot.set_my_commands([
        BotCommand("start",   "🏠 Main menu"),
        BotCommand("balance", "⚡ Prepaid balance"),
        BotCommand("info",    "👤 Customer & meter info"),
        BotCommand("stats",   "📊 Usage stats & bill estimate"),
        BotCommand("summary", "📋 Full account summary"),
        BotCommand("daily",   "📆 Daily usage & cost breakdown"),
        BotCommand("monthly", "📅 Monthly consumption history"),
        BotCommand("recharge","💳 Recharge history (12 months)"),
        BotCommand("forget",  "🗑 Clear saved account"),
        BotCommand("help",    "❓ Help"),
        BotCommand("cancel",  "❌ Cancel"),
    ])

    # Admin-only command menu (shows /admin only to ADMIN_ID)
    if ADMIN_ID:
        try:
            await app.bot.set_my_commands(
                [
                    BotCommand("start",   "🏠 Main menu"),
                    BotCommand("balance", "⚡ Prepaid balance"),
                    BotCommand("info",    "👤 Customer & meter info"),
                    BotCommand("stats",   "📊 Usage stats & bill estimate"),
                    BotCommand("summary", "📋 Full account summary"),
                    BotCommand("daily",   "📆 Daily usage & cost breakdown"),
                    BotCommand("monthly", "📅 Monthly consumption history"),
                    BotCommand("recharge","💳 Recharge history (12 months)"),
                    BotCommand("admin",   "📊 Admin analytics dashboard"),
                    BotCommand("forget",  "🗑 Clear saved account"),
                    BotCommand("help",    "❓ Help"),
                    BotCommand("cancel",  "❌ Cancel"),
                ],
                scope=BotCommandScopeChat(chat_id=ADMIN_ID)
            )
        except Exception as e:
            print("Admin command scope error:", e)

# =====================================
# MAIN
# =====================================

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    CMDS = [
        ("balance",  balance_cmd),
        ("info",     info_cmd),
        ("stats",    stats_cmd),
        ("summary",  summary_cmd),
        ("recharge", recharge_cmd),
        ("monthly",  monthly_cmd),
        ("daily",    daily_cmd),
    ]
    ALL_ACTIONS = "|".join(a for a, _ in CMDS)

    conv = ConversationHandler(
        entry_points=[
            *[CommandHandler(name, fn) for name, fn in CMDS],
            CallbackQueryHandler(button_handler, pattern=f"^({ALL_ACTIONS})$"),
        ],
        states={
            ASK_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, account_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("forget", forget_command))
    app.add_handler(CommandHandler("admin",  admin_cmd))
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