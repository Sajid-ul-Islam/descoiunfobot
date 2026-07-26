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

from db import init_db, track_user, get_admin_stats, get_user_language, set_user_language, get_user_provider, set_user_provider
from chart_gen import generate_daily_chart, generate_monthly_chart, generate_recharge_chart, generate_usage_chart
from i18n import get_msg
from palli_bidyut import get_palli_text, get_token_help_text
from power_bd import get_bpdb_text, get_nesco_text, get_all_coverage_text
from providers_adapter import provider_get
from tariff_tips import get_tariff_tip, get_low_balance_warning
from report_gen import generate_csv_report
from appliance_calc import get_calc_text, get_tariff_guide_text

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
ACTION_CHART    = "chart"
ACTION_EXPORT   = "export"

# =====================================
# DESCO API
# =====================================

def desco_get(system: str, endpoint: str, account_no: str,
              meter_no: str = "", provider: str = "desco", **params) -> tuple:
    """Returns (data, code, desc). Standardized for DESCO and BPDB APIs."""
    return provider_get(provider, system, endpoint, account_no, meter_no, **params)


def detect_system(user_input: str, provider: str = "desco") -> tuple:
    """
    Try user_input as accountNo then as meterNo across systems and providers.
    Returns (system, account_no, meter_no, info_data, status)
    status can be: "OK", "EMPTY_PREPAID", "NOT_FOUND"
    """
    combos = [
        (user_input, ""),   # treat as account number
        ("",   user_input),  # treat as meter number
    ]

    providers_to_check = [provider] + [p for p in ["desco", "bpdb"] if p != provider]

    found_empty_sys = None
    for prov in providers_to_check:
        systems = ["unified", "tkdes"] if prov == "desco" else ["unified"]
        for system in systems:
            for acc, met in combos:
                try:
                    # 1. Try getCustomerInfo
                    data, code, _ = desco_get(system, "getCustomerInfo", acc, met, provider=prov)
                    if data:
                        account_no = data.get("accountNo") or acc or user_input
                        meter_no   = data.get("meterNo")   or met or ""
                        return system, account_no, meter_no, data, "OK"

                    # 2. Try getBalance if info data was null
                    bal_data, bal_code, _ = desco_get(system, "getBalance", acc, met, provider=prov)
                    if bal_data:
                        account_no = bal_data.get("accountNo") or acc or user_input
                        meter_no   = bal_data.get("meterNo")   or met or ""
                        return system, account_no, meter_no, None, "OK"
                    elif bal_code == 200:
                        found_empty_sys = system
                except Exception:
                    pass

    if found_empty_sys:
        return found_empty_sys, user_input, "", None, "EMPTY_PREPAID"

    return None, None, None, None, "NOT_FOUND"

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

def main_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(get_msg(lang, "balance_btn"), callback_data="balance"),
            InlineKeyboardButton(get_msg(lang, "info_btn"),    callback_data="info"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "stats_btn"),   callback_data="stats"),
            InlineKeyboardButton(get_msg(lang, "chart_btn"),   callback_data="chart"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "summary_btn"), callback_data="summary"),
            InlineKeyboardButton(get_msg(lang, "daily_btn"),   callback_data="daily"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "monthly_btn"),  callback_data="monthly"),
            InlineKeyboardButton(get_msg(lang, "recharge_btn"), callback_data="recharge"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "export_btn"),   callback_data="export"),
            InlineKeyboardButton(get_msg(lang, "other_btn"),    callback_data="other_menu"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "settings_btn"), callback_data="settings"),
            InlineKeyboardButton(get_msg(lang, "help_btn"),     callback_data="help"),
        ],
    ])

def back_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def daily_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(lang, "view_daily_chart"), callback_data="chart_daily")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"),    callback_data="start")],
    ])

def monthly_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(lang, "view_monthly_chart"), callback_data="chart_monthly")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"),      callback_data="start")],
    ])

def chart_range_keyboard(lang: str = "en", days: int = 15):
    btn_7  = "✅ 7 Days" if days == 7 else "7 Days"
    btn_15 = "✅ 15 Days" if days == 15 else "15 Days"
    btn_30 = "✅ 30 Days" if days == 30 else "30 Days"
    btn_60 = "✅ 60 Days" if days == 60 else "60 Days"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(btn_7,  callback_data="range_7"),
            InlineKeyboardButton(btn_15, callback_data="range_15"),
            InlineKeyboardButton(btn_30, callback_data="range_30"),
            InlineKeyboardButton(btn_60, callback_data="range_60"),
        ],
        [
            InlineKeyboardButton("📅 Specific Date Lookup", callback_data="range_date"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start"),
        ],
    ])

def recharge_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(lang, "view_recharge_chart"), callback_data="chart_recharge")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"),       callback_data="start")],
    ])

def postpaid_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 DESCO E-Bill Portal", url="https://ebill.desco.org.bd/")],
        [InlineKeyboardButton("🌐 DESCO OCSMS Portal", url="https://ocsms.desco.org.bd/")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def palli_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 " + get_msg(lang, "token_btn"), callback_data="token_info")],
        [InlineKeyboardButton("🌐 BREB Official Portal", url="http://www.reb.gov.bd/")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def bpdb_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 BPDB Prepaid Portal", url="https://prepaid.bpdb.gov.bd/")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def providers_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def settings_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton("🇧🇩 বাংলা",  callback_data="set_lang_bn"),
        ],
        [InlineKeyboardButton("⚡ Change Utility Provider", callback_data="select_provider")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def other_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(get_msg(lang, "calc_btn"),   callback_data="calc_info"),
            InlineKeyboardButton(get_msg(lang, "tariff_btn"), callback_data="tariff_info"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "palli_btn"), callback_data="palli_info"),
            InlineKeyboardButton(get_msg(lang, "bpdb_btn"),  callback_data="bpdb_info"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "nesco_btn"),     callback_data="nesco_info"),
            InlineKeyboardButton(get_msg(lang, "postpaid_btn"),  callback_data="postpaid_info"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "providers_btn"), callback_data="providers_info"),
            InlineKeyboardButton(get_msg(lang, "token_btn"),     callback_data="token_info"),
        ],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def provider_selector_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ DESCO (Dhaka North)",  callback_data="set_prov_desco"),
            InlineKeyboardButton("🌾 Palli Bidyut (BREB)",   callback_data="set_prov_breb"),
        ],
        [
            InlineKeyboardButton("🏢 BPDB (Chattogram)",    callback_data="set_prov_bpdb"),
            InlineKeyboardButton("🌆 DPDC (Dhaka South)",    callback_data="set_prov_dpdc"),
        ],
        [
            InlineKeyboardButton("🌊 WZPDCL (West Zone)",   callback_data="set_prov_wzpdcl"),
            InlineKeyboardButton("❄️ NESCO (North Zone)",   callback_data="set_prov_nesco"),
        ],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("language")
    if not lang:
        user_id = update.effective_user.id if update and update.effective_user else 0
        lang = get_user_language(user_id) if user_id else "en"
        context.user_data["language"] = lang
    return lang

async def send_main_menu(send_fn, account_no=None, system=None, lang: str = "en"):
    saved = f"\n\n💾 Account: `{account_no}` _{system}_" if account_no else ""
    msg_text = get_msg(lang, "welcome", saved=saved)
    await send_fn(
        msg_text,
        parse_mode="Markdown",
        reply_markup=main_keyboard(lang),
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
    lang = get_lang(update, context)
    account_no = context.user_data.get("account_no")
    system     = context.user_data.get("system")
    await send_main_menu(update.message.reply_text, account_no, system, lang)


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/settings")
    lang = get_lang(update, context)
    msg_text = get_msg(lang, "settings_title")
    await update.message.reply_text(
        msg_text,
        parse_mode="Markdown",
        reply_markup=settings_keyboard(lang),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/help")
    await update.message.reply_text(
        "📖 *DESCO Info Bot — Help*\n\n"
        "*Commands:*\n"
        "• /start — Main menu\n"
        "• /balance — Prepaid balance\n"
        "• /info — Customer & meter details\n"
        "• /stats — Usage stats & bill estimate\n"
        "• /chart — Visual usage & trend charts\n"
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


async def postpaid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/postpaid")
    await update.message.reply_text(
        "📄 *DESCO Postpaid Electricity Bill Check*\n\n"
        "If you are a DESCO Postpaid customer (monthly bill user), access your bill through:\n\n"
        "1️⃣ *DESCO E-Bill Portal:* Download PDF monthly bill\n"
        "2️⃣ *bKash App:* Pay Bill → Electricity (Postpaid) → DESCO → Enter Account No.\n"
        "3️⃣ *Nagad App:* Bill Pay → DESCO Postpaid\n"
        "4️⃣ *Rocket App:* Utility Pay → DESCO Postpaid",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=postpaid_keyboard(),
    )


async def palli_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/palli")
    lang = get_lang(update, context)
    await update.message.reply_text(
        get_palli_text(lang),
        parse_mode="Markdown",
        reply_markup=palli_keyboard(lang),
    )


async def provider_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/provider")
    lang = get_lang(update, context)
    msg_text = get_msg(lang, "provider_title")
    await update.message.reply_text(
        msg_text,
        parse_mode="Markdown",
        reply_markup=provider_selector_keyboard(lang),
    )


async def token_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/token")
    lang = get_lang(update, context)
    await update.message.reply_text(
        get_token_help_text(lang),
        parse_mode="Markdown",
        reply_markup=back_keyboard(lang),
    )


async def other_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/other")
    lang = get_lang(update, context)
    await update.message.reply_text(
        get_msg(lang, "other_title"),
        parse_mode="Markdown",
        reply_markup=other_keyboard(lang),
    )


async def calc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/calc")
    lang = get_lang(update, context)
    await update.message.reply_text(
        get_calc_text(lang),
        parse_mode="Markdown",
        reply_markup=back_keyboard(lang),
    )


async def tariff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/tariff")
    lang = get_lang(update, context)
    await update.message.reply_text(
        get_tariff_guide_text(lang),
        parse_mode="Markdown",
        reply_markup=back_keyboard(lang),
    )


async def bpdb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/bpdb")
    lang = get_lang(update, context)
    await update.message.reply_text(
        get_bpdb_text(lang),
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=bpdb_keyboard(lang),
    )


async def nesco_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/nesco")
    lang = get_lang(update, context)
    await update.message.reply_text(
        get_nesco_text(lang),
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=back_keyboard(lang),
    )


async def providers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/providers")
    lang = get_lang(update, context)
    await update.message.reply_text(
        get_all_coverage_text(lang),
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=providers_keyboard(lang),
    )

# =====================================
# ACCOUNT NUMBER COLLECTION
# =====================================

async def account_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    send = update.message.reply_text

    pending = context.user_data.get("pending_action")
    account_no = context.user_data.get("account_no")
    system     = context.user_data.get("system", "unified")
    meter_no   = context.user_data.get("meter_no", "")

    if pending == "date_lookup" or "-" in user_input:
        if account_no and system:
            context.user_data.pop("pending_action", None)
            await send("🔍 Searching date records...")
            await lookup_specific_date(send, account_no, system, meter_no, user_input, context)
            return ConversationHandler.END

    if not user_input.isdigit():
        await send(
            "❌ *Invalid.* Enter digits only (account or meter number), or /cancel.",
            parse_mode="Markdown",
        )
        return ASK_ACCOUNT

    await send("🔍 Detecting account...")
    system, account_no, meter_no, info_data, status = detect_system(user_input)

    if status == "EMPTY_PREPAID":
        context.user_data["account_no"] = user_input
        context.user_data["system"]     = system
        context.user_data["meter_no"]   = ""
        track_user(update.effective_user, "account_submit_empty", user_input)
        await send(
            f"⚠️ *Prepaid Account Recognized (`{system}` system)*\n\n"
            f"🔑 Account: `{user_input}`\n\n"
            "This account is registered on DESCO's prepaid system, but DESCO currently has no meter balance or consumption data synced for it yet.\n\n"
            "_(This typically occurs for newly installed smart meters or accounts undergoing DESCO server sync)._",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
        return ConversationHandler.END

    if status == "NOT_FOUND" or not system:
        if len(user_input) == 8:
            await send(
                f"ℹ️ Account `{user_input}` is not active on Prepaid.\n\n"
                "If this is a Postpaid connection, check your bill via:\n\n"
                "📄 *DESCO E-Bill Portal:* [ebill.desco.org.bd](https://ebill.desco.org.bd/)\n"
                "🌐 *DESCO OCSMS:* [ocsms.desco.org.bd](https://ocsms.desco.org.bd/)\n"
                "📱 *bKash:* Pay Bill → Electricity (Postpaid) → DESCO",
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=postpaid_keyboard(),
            )
        else:
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
    prov = context.user_data.get("provider", "desco")
    if prov in ["breb", "dpdc", "wzpdcl", "nesco"]:
        lang = get_lang(None, context)
        await send_fn(get_palli_text(lang) if prov == "breb" else get_all_coverage_text(lang), parse_mode="Markdown", reply_markup=main_keyboard(lang))
        return

    await send_fn("⏳ Fetching balance...")
    try:
        data, code, desc = desco_get(system, "getBalance", account_no, meter_no, provider=prov)
        if not data:
            msg = ("⚠️ *Account found but no balance data.*"
                   if code == 200 else f"❌ *{desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return
        bal_val = float(data.get('balance', 0))
        mo_use  = float(data.get('currentMonthConsumption', 0))
        lang    = get_lang(None, context)
        warn_banner = get_low_balance_warning(bal_val, daily_avg=mo_use/30, lang=lang)

        await send_fn(
            f"⚡ *Balance Info*\n\n"
            f"🔑 Account: `{account_no}` _{system}_\n"
            f"💰 Balance: *৳{bal_val:.2f}*\n"
            f"📊 This Month: `{mo_use:.2f} Unit`\n"
            f"🔌 Meter: `{data.get('meterNo', 'N/A')}`\n"
            f"🕒 Last Reading: `{data.get('readingTime', 'N/A')}`"
            f"{warn_banner}",
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_info(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if prov in ["breb", "dpdc", "wzpdcl", "nesco"]:
        lang = get_lang(None, context)
        await send_fn(get_palli_text(lang) if prov == "breb" else get_all_coverage_text(lang), parse_mode="Markdown", reply_markup=main_keyboard(lang))
        return

    await send_fn("⏳ Fetching customer info...")
    try:
        data, code, desc = desco_get(system, "getCustomerInfo", account_no, meter_no, provider=prov)
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
    prov = context.user_data.get("provider", "desco")
    if prov in ["breb", "dpdc", "wzpdcl", "nesco"]:
        lang = get_lang(None, context)
        await send_fn(get_palli_text(lang) if prov == "breb" else get_all_coverage_text(lang), parse_mode="Markdown", reply_markup=main_keyboard(lang))
        return

    await send_fn("⏳ Calculating stats...")
    try:
        bal_data,  bal_code,  bal_desc  = desco_get(system, "getBalance",      account_no, meter_no, provider=prov)
        info_data, info_code, info_desc = desco_get(system, "getCustomerInfo", account_no, meter_no, provider=prov)
        if not bal_data:
            msg = ("⚠️ No balance data." if bal_code == 200 else f"❌ *{bal_desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return
        s = calc_stats(bal_data, info_data)
        load_line = f"⚡ Load Utilisation: `{s['load_pct']}%`\n" if s["load_pct'] is not None else ""
        conn_line = f"🏗 Connection Age: `{s['conn_age']}`\n"  if s["conn_age"]            else ""
        
        lang = get_lang(None, context)
        tariff_tip = get_tariff_tip(float(bal_data.get('currentMonthConsumption', 0)), lang=lang)
        
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
    prov = context.user_data.get("provider", "desco")
    if prov in ["breb", "dpdc", "wzpdcl", "nesco"]:
        lang = get_lang(None, context)
        await send_fn(get_palli_text(lang) if prov == "breb" else get_all_coverage_text(lang), parse_mode="Markdown", reply_markup=main_keyboard(lang))
        return

    await send_fn("⏳ Fetching full summary...")
    try:
        bal_data,  _, _  = desco_get(system, "getBalance",      account_no, meter_no, provider=prov)
        info_data, _, _  = desco_get(system, "getCustomerInfo", account_no, meter_no, provider=prov)
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
    prov = context.user_data.get("provider", "desco")
    if prov in ["breb", "dpdc", "wzpdcl", "nesco"]:
        lang = get_lang(None, context)
        await send_fn(get_palli_text(lang) if prov == "breb" else get_all_coverage_text(lang), parse_mode="Markdown", reply_markup=main_keyboard(lang))
        return

    await send_fn("⏳ Fetching recharge history...")
    try:
        today     = date.today()
        date_from = (today - timedelta(days=350)).strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")
        data, code, desc = desco_get(
            system, "getRechargeHistory", account_no, meter_no, provider=prov,
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
            reply_markup=recharge_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_monthly(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if prov in ["breb", "dpdc", "wzpdcl", "nesco"]:
        lang = get_lang(None, context)
        await send_fn(get_palli_text(lang) if prov == "breb" else get_all_coverage_text(lang), parse_mode="Markdown", reply_markup=main_keyboard(lang))
        return

    await send_fn("⏳ Fetching monthly consumption...")
    try:
        today      = date.today()
        month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
        month_to   = today.strftime("%Y-%m")
        data, code, desc = desco_get(
            system, "getCustomerMonthlyConsumption", account_no, meter_no, provider=prov,
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
            reply_markup=monthly_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def fetch_and_send_daily(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if prov in ["breb", "dpdc", "wzpdcl", "nesco"]:
        lang = get_lang(None, context)
        await send_fn(get_palli_text(lang) if prov == "breb" else get_all_coverage_text(lang), parse_mode="Markdown", reply_markup=main_keyboard(lang))
        return

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
            reply_markup=daily_keyboard(),
        )
    except Exception as e:
        await send_fn(f"❌ Error: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())

async def fetch_and_send_chart(send_fn, account_no, system, meter_no, context, update: Update = None, days: int = 7):
    msg_target = update.effective_message if update else None
    if msg_target:
        await msg_target.reply_text(f"⏳ Generating visual analytics chart ({days} Days)...")
    else:
        await send_fn(f"⏳ Generating visual analytics chart ({days} Days)...")

    try:
        today = date.today()

        # 1. Fetch daily data for up to 60 days
        date_from = (today - timedelta(days=max(days + 10, 65))).strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")
        prov = context.user_data.get("provider", "desco")
        daily_data, _, _ = desco_get(
            system, "getCustomerDailyConsumption", account_no, meter_no, provider=prov,
            dateFrom=date_from, dateTo=date_to,
        )

        # 2. Fetch monthly data
        month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
        month_to   = today.strftime("%Y-%m")
        monthly_data, _, _ = desco_get(
            system, "getCustomerMonthlyConsumption", account_no, meter_no, provider=prov,
            monthFrom=month_from, monthTo=month_to,
        )

        # 3. Fetch balance data for KPI card
        bal_data, _, _ = desco_get(system, "getBalance", account_no, meter_no, provider=prov)

        # 4. Render executive chart with days filter
        lang = get_lang(update, context) if update else "en"
        buf = generate_usage_chart(daily_data or [], monthly_data or [], account_no, system, bal_data=bal_data, lang=lang, days=days)

        # 5. Send photo with timeline range keyboard
        if msg_target:
            await msg_target.reply_photo(
                photo=buf,
                caption=f"📈 *DESCO Analytics Dashboard ({days} Days)*\n🔑 Account: `{account_no}` _{system}_",
                parse_mode="Markdown",
                reply_markup=chart_range_keyboard(lang, days=days),
            )
        else:
            await send_fn("📈 Chart generated.", reply_markup=chart_range_keyboard(lang, days=days))

    except Exception as e:
        await send_fn(f"❌ Error generating chart: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard())


async def lookup_specific_date(send_fn, account_no, system, meter_no, target_date_str, context):
    today = date.today()
    date_from = (today - timedelta(days=65)).strftime("%Y-%m-%d")
    date_to   = today.strftime("%Y-%m-%d")
    prov = context.user_data.get("provider", "desco")
    daily_data, _, _ = desco_get(system, "getCustomerDailyConsumption", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)

    if not daily_data or len(daily_data) < 2:
        await send_fn("⚠️ No daily usage data available for date lookup.", reply_markup=back_keyboard())
        return

    sorted_daily = sorted(daily_data, key=lambda x: str(x.get("date", "")))
    match_rec = None
    prev_rec = None

    for i in range(1, len(sorted_daily)):
        curr_d = str(sorted_daily[i].get("date", ""))
        if target_date_str in curr_d:
            match_rec = sorted_daily[i]
            prev_rec  = sorted_daily[i-1]
            break

    if not match_rec:
        await send_fn(f"❌ No consumption record found for date `{target_date_str}`.\n\nPlease check that the date is within the last 60 days.", parse_mode="Markdown", reply_markup=back_keyboard())
        return

    u_curr = float(match_rec.get("consumedUnit") or 0)
    u_prev = float(prev_rec.get("consumedUnit") or 0) if prev_rec else 0
    units  = max(u_curr - u_prev, 0)

    t_curr = float(match_rec.get("consumedTaka") or 0)
    t_prev = float(prev_rec.get("consumedTaka") or 0) if prev_rec else 0
    taka   = max(t_curr - t_prev, 0)
    rate   = taka / units if units > 0 else 0

    await send_fn(
        f"📅 *Specific Date Usage Info — {match_rec.get('date', target_date_str)}*\n\n"
        f"🔑 Account: `{account_no}` _{system}_\n"
        f"⚡ *Consumed Units:* `{units:.2f} kWh`\n"
        f"💰 *Daily Cost:* *৳{taka:.2f}*\n"
        f"📊 *Effective Unit Rate:* `@৳{rate:.2f} / kWh`\n"
        f"🔌 Meter: `{meter_no}`\n"
        f"🕒 Meter Reading Date: `{match_rec.get('date', 'N/A')}`",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

async def fetch_and_send_export(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    lang = get_lang(None, context)
    if prov in ["breb", "dpdc", "wzpdcl", "nesco"]:
        await send_fn(get_palli_text(lang) if prov == "breb" else get_all_coverage_text(lang), parse_mode="Markdown", reply_markup=main_keyboard(lang))
        return

    await send_fn(get_msg(lang, "exporting"))
    try:
        today = date.today()
        month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
        month_to   = today.strftime("%Y-%m")
        monthly_data, _, _ = desco_get(system, "getCustomerMonthlyConsumption", account_no, meter_no, provider=prov, monthFrom=month_from, monthTo=month_to)

        date_from = (today - timedelta(days=350)).strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")
        recharge_data, _, _ = desco_get(system, "getRechargeHistory", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)

        csv_buf = generate_csv_report(monthly_data or [], recharge_data or [], account_no, system)
        filename = f"DESCO_Report_{account_no}_{today.strftime('%Y%m%d')}.csv"

        if hasattr(send_fn, "__self__") and hasattr(send_fn.__self__, "reply_document"):
            await send_fn.__self__.reply_document(
                document=csv_buf,
                filename=filename,
                caption=f"📥 *Utility Consumption & Recharge Report*\n🔑 Account: `{account_no}` _{system}_",
                parse_mode="Markdown",
                reply_markup=main_keyboard(lang),
            )
        else:
            await send_fn("📥 Report generated.", reply_markup=main_keyboard(lang))
    except Exception as e:
        await send_fn(f"❌ Error exporting report: `{e}`", parse_mode="Markdown", reply_markup=back_keyboard(lang))

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
        ACTION_EXPORT:   fetch_and_send_export,
        ACTION_CHART:    lambda send_fn, acc, sys, met, ctx: fetch_and_send_chart(send_fn, acc, sys, met, ctx, update=update),
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
async def chart_cmd(u, c):    return await _cmd(ACTION_CHART,    u, c)
async def export_cmd(u, c):   return await _cmd(ACTION_EXPORT,   u, c)
async def nesco_cmd(u, c):    return await _cmd(ACTION_NESCO,    u, c)

# =====================================
# INLINE BUTTON HANDLER
# =====================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    send = query.message.reply_text
    data = query.data

    if data == "select_provider":
        lang = get_lang(update, context)
        await send(
            get_msg(lang, "provider_title"),
            parse_mode="Markdown",
            reply_markup=provider_selector_keyboard(lang),
        )
        return

    if data == "other_menu":
        lang = get_lang(update, context)
        await send(
            get_msg(lang, "other_title"),
            parse_mode="Markdown",
            reply_markup=other_keyboard(lang),
        )
        return

    if data == "calc_info":
        lang = get_lang(update, context)
        await send(
            get_calc_text(lang),
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang),
        )
        return

    if data == "tariff_info":
        lang = get_lang(update, context)
        await send(
            get_tariff_guide_text(lang),
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang),
        )
        return

    if data in ["range_7", "range_15", "range_30", "range_60"]:
        target_days = int(data.replace("range_", ""))
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system", "unified")
        meter_no   = context.user_data.get("meter_no", "")
        if account_no and system:
            await fetch_and_send_chart(send, account_no, system, meter_no, context, update=update, days=target_days)
        else:
            await send("❌ Please submit an account number first.", reply_markup=main_keyboard())
        return

    if data == "range_date":
        context.user_data["pending_action"] = "date_lookup"
        await send(
            "📅 *Specific Date Usage Lookup*\n\n"
            "Please type the date you want to inspect in `YYYY-MM-DD` or `MM-DD` format:\n"
            "_(Example: `2026-07-25` or `07-25`)_\n\n"
            "Or type /cancel to go back.",
            parse_mode="Markdown",
        )
        return ASK_ACCOUNT

    if data.startswith("set_prov_"):
        prov_code = data.replace("set_prov_", "")
        set_user_provider(update.effective_user.id, prov_code)
        context.user_data["provider"] = prov_code
        lang = get_lang(update, context)
        prov_names = {
            "desco": "DESCO (Dhaka North)",
            "breb": "Palli Bidyut (BREB)",
            "bpdb": "BPDB (Chattogram)",
            "dpdc": "DPDC (Dhaka South)",
            "wzpdcl": "WZPDCL (West Zone)",
            "nesco": "NESCO (North Zone)",
        }
        name = prov_names.get(prov_code, prov_code.upper())
        await send(
            get_msg(lang, "provider_saved", name=name),
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang),
        )
        return

    if data == "postpaid_info":
        await send(
            "📄 *DESCO Postpaid Electricity Bill Check*\n\n"
            "Access your postpaid bill through:\n\n"
            "1️⃣ *DESCO E-Bill Portal:* [ebill.desco.org.bd](https://ebill.desco.org.bd/)\n"
            "2️⃣ *bKash App:* Pay Bill → Electricity (Postpaid) → DESCO\n"
            "3️⃣ *Nagad App:* Bill Pay → DESCO Postpaid",
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=postpaid_keyboard(),
        )
        return

    if data == "palli_info":
        lang = get_lang(update, context)
        await send(
            get_palli_text(lang),
            parse_mode="Markdown",
            reply_markup=palli_keyboard(lang),
        )
        return

    if data == "nesco_info":
        lang = get_lang(update, context)
        await send(
            get_nesco_text(lang),
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=back_keyboard(lang),
        )
        return

    if data == "token_info":
        lang = get_lang(update, context)
        await send(
            get_token_help_text(lang),
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang),
        )
        return

    if data == "bpdb_info":
        lang = get_lang(update, context)
        await send(
            get_bpdb_text(lang),
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=bpdb_keyboard(lang),
        )
        return

    if data == "providers_info":
        lang = get_lang(update, context)
        await send(
            get_all_coverage_text(lang),
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=providers_keyboard(lang),
        )
        return

    if data == "set_lang_en":
        set_user_language(update.effective_user.id, "en")
        context.user_data["language"] = "en"
        await send(get_msg("en", "lang_saved"), parse_mode="Markdown", reply_markup=main_keyboard("en"))
        return

    if data == "set_lang_bn":
        set_user_language(update.effective_user.id, "bn")
        context.user_data["language"] = "bn"
        await send(get_msg("bn", "lang_saved"), parse_mode="Markdown", reply_markup=main_keyboard("bn"))
        return

    if data == "help":
        await send(
            "📖 *Help*\n\n"
            "• /balance — Balance\n"
            "• /info — Customer & meter info\n"
            "• /stats — Usage stats\n"
            "• /chart — Plotly analytics chart\n"
            "• /summary — Full summary\n"
            "• /daily — Daily usage breakdown\n"
            "• /monthly — Monthly consumption\n"
            "• /recharge — Recharge history\n"
            "• /forget — Clear saved account",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
        return

    if data == "chart_daily":
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system")
        meter_no   = context.user_data.get("meter_no", "")
        if account_no and system:
            await query.message.reply_text("⏳ Generating daily Plotly chart...")
            today = date.today()
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            date_to   = today.strftime("%Y-%m-%d")
            daily_data, _, _ = desco_get(system, "getCustomerDailyConsumption", account_no, meter_no, dateFrom=date_from, dateTo=date_to)
            buf = generate_daily_chart(daily_data or [], account_no, system)
            if buf:
                await query.message.reply_photo(photo=buf, caption=f"📆 *Daily Consumption Chart* — `{account_no}`", parse_mode="Markdown", reply_markup=daily_keyboard())
            else:
                await send("⚠️ Daily chart data unavailable.", reply_markup=back_keyboard())
        else:
            await send("🔢 Enter your *account number* or *meter number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_DAILY
            return ASK_ACCOUNT
        return

    if data == "chart_monthly":
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system")
        meter_no   = context.user_data.get("meter_no", "")
        if account_no and system:
            await query.message.reply_text("⏳ Generating monthly Plotly chart...")
            today = date.today()
            month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
            month_to   = today.strftime("%Y-%m")
            monthly_data, _, _ = desco_get(system, "getCustomerMonthlyConsumption", account_no, meter_no, monthFrom=month_from, monthTo=month_to)
            buf = generate_monthly_chart(monthly_data or [], account_no, system)
            if buf:
                await query.message.reply_photo(photo=buf, caption=f"📅 *Monthly Consumption Chart* — `{account_no}`", parse_mode="Markdown", reply_markup=monthly_keyboard())
            else:
                await send("⚠️ Monthly chart data unavailable.", reply_markup=back_keyboard())
        else:
            await send("🔢 Enter your *account number* or *meter number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_MONTHLY
            return ASK_ACCOUNT
        return

    if data == "chart_recharge":
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system")
        meter_no   = context.user_data.get("meter_no", "")
        if account_no and system:
            await query.message.reply_text("⏳ Generating recharge Plotly chart...")
            today     = date.today()
            date_from = (today - timedelta(days=350)).strftime("%Y-%m-%d")
            date_to   = today.strftime("%Y-%m-%d")
            recharge_data, _, _ = desco_get(system, "getRechargeHistory", account_no, meter_no, dateFrom=date_from, dateTo=date_to)
            buf = generate_recharge_chart(recharge_data or [], account_no, system)
            if buf:
                await query.message.reply_photo(photo=buf, caption=f"💳 *Recharge History Chart* — `{account_no}`", parse_mode="Markdown", reply_markup=recharge_keyboard())
            else:
                await send("⚠️ Recharge chart data unavailable.", reply_markup=back_keyboard())
        else:
            await send("🔢 Enter your *account number* or *meter number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_RECHARGE
            return ASK_ACCOUNT
        return

    ACTION_MAP = {
        "balance":  (ACTION_BALANCE,  fetch_and_send_balance),
        "info":     (ACTION_INFO,     fetch_and_send_info),
        "stats":    (ACTION_STATS,    fetch_and_send_stats),
        "summary":  (ACTION_SUMMARY,  fetch_and_send_summary),
        "recharge": (ACTION_RECHARGE, fetch_and_send_recharge),
        "monthly":  (ACTION_MONTHLY,  fetch_and_send_monthly),
        "daily":    (ACTION_DAILY,    fetch_and_send_daily),
        "export":   (ACTION_EXPORT,   fetch_and_send_export),
        "chart":    (ACTION_CHART,    lambda send, acc, sys, met, ctx: fetch_and_send_chart(send, acc, sys, met, ctx, update=update)),
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
        BotCommand("start",    "🏠 Main menu"),
        BotCommand("balance",  "⚡ Prepaid balance"),
        BotCommand("info",     "👤 Customer & meter info"),
        BotCommand("stats",    "📊 Usage stats & bill estimate"),
        BotCommand("chart",    "📈 Visual analytics chart"),
        BotCommand("summary",  "📋 Full account summary"),
        BotCommand("daily",    "📆 Daily usage & cost breakdown"),
        BotCommand("monthly",  "📅 Monthly consumption history"),
        BotCommand("recharge", "💳 Recharge history (12 months)"),
        BotCommand("export",   "📥 Download Excel CSV report"),
        BotCommand("calc",     "🧮 Appliance energy calculator"),
        BotCommand("tariff",   "⚡ Peak vs Off-Peak tariff schedule"),
        BotCommand("provider", "⚡ Select electricity provider"),
        BotCommand("other",    "🌐 Other providers & services"),
        BotCommand("palli",    "🌾 Palli Bidyut (BREB) info & codes"),
        BotCommand("bpdb",     "🏢 BPDB (Chattogram & Zones) info"),
        BotCommand("nesco",    "❄️ NESCO (Rajshahi & Rangpur) info"),
        BotCommand("token",    "🔑 Missing token recovery guide"),
        BotCommand("providers","🇧🇩 All Bangladesh power providers"),
        BotCommand("settings", "⚙️ Language & bot settings"),
        BotCommand("postpaid", "📄 Postpaid bill guidance & links"),
        BotCommand("forget",   "🗑 Clear saved account"),
        BotCommand("help",     "❓ Help"),
        BotCommand("cancel",   "❌ Cancel"),
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
        ("chart",    chart_cmd),
        ("export",   export_cmd),
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

    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("help",     help_command))
    app.add_handler(CommandHandler("forget",   forget_command))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("provider", provider_cmd))
    app.add_handler(CommandHandler("other",    other_cmd))
    app.add_handler(CommandHandler("calc",     calc_cmd))
    app.add_handler(CommandHandler("tariff",   tariff_cmd))
    app.add_handler(CommandHandler("postpaid", postpaid_cmd))
    app.add_handler(CommandHandler("palli",    palli_cmd))
    app.add_handler(CommandHandler("bpdb",     bpdb_cmd))
    app.add_handler(CommandHandler("nesco",    nesco_cmd))
    app.add_handler(CommandHandler("token",    token_cmd))
    app.add_handler(CommandHandler("providers",providers_cmd))
    app.add_handler(CommandHandler("admin",    admin_cmd))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(start|help|other_menu|calc_info|tariff_info|postpaid_info|palli_info|token_info|bpdb_info|nesco_info|providers_info|settings|select_provider|set_prov_.*|set_lang_en|set_lang_bn|chart_daily|chart_monthly|chart_recharge|range_7|range_15|range_30|range_60|range_date)$"))
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