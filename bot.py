import os
import logging
import urllib3
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from telegram import Update, BotCommand, BotCommandScopeChat
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

from db import init_db, track_user, set_user_language, set_user_provider
from chart_gen import generate_daily_chart, generate_monthly_chart, generate_recharge_chart
from i18n import get_msg
from palli_bidyut import get_palli_text, get_token_help_text
from power_bd import get_bpdb_text, get_nesco_text, get_all_coverage_text
from providers_adapter import is_api_provider, PROVIDERS
from tariff_tips import get_low_balance_warning, get_tariff_slab_warning
from report_gen import generate_csv_report, generate_text_statement
from appliance_calc import get_calc_text, get_tariff_guide_text
from ai_assistant import generate_ai_error_explanation

from tariff_calc import (
    desco_get,
    detect_system,
    convert_bn_digits_to_en,
    estimate_bill,
    estimate_units_from_taka,
    calc_stats,
    analyze_recharge_pattern,
)
from keyboards import (
    main_keyboard,
    back_keyboard,
    daily_keyboard,
    monthly_keyboard,
    chart_range_keyboard,
    export_keyboard,
    recharge_keyboard,
    postpaid_keyboard,
    palli_keyboard,
    bpdb_keyboard,
    providers_keyboard,
    settings_keyboard,
    other_keyboard,
    provider_selector_keyboard,
)
from fetch_handlers import (
    get_lang,
    fetch_and_send_balance,
    fetch_and_send_info,
    fetch_and_send_stats,
    fetch_and_send_summary,
    fetch_and_send_recharge,
    fetch_and_send_monthly,
    fetch_and_send_daily,
    fetch_and_send_chart,
    fetch_and_send_export,
)
from commands import (
    ASK_ACCOUNT,
    ACTION_BALANCE,
    ACTION_INFO,
    ACTION_STATS,
    ACTION_SUMMARY,
    ACTION_RECHARGE,
    ACTION_MONTHLY,
    ACTION_DAILY,
    ACTION_CHART,
    ACTION_EXPORT,
    send_main_menu,
    start,
    settings_cmd,
    help_command,
    forget_command,
    postpaid_cmd,
    palli_cmd,
    providers_cmd,
    token_cmd,
    other_cmd,
    calc_cmd,
    tariff_cmd,
    ai_cmd,
    bpdb_cmd,
    nesco_cmd,
    admin_cmd,
    account_received,
    cancel,
    balance_cmd,
    info_cmd,
    stats_cmd,
    summary_cmd,
    recharge_cmd,
    monthly_cmd,
    daily_cmd,
    chart_cmd,
    export_cmd,
)

# =====================================
# CONFIG
# =====================================

load_dotenv()

BOT_TOKEN   = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT        = int(os.getenv("PORT", 10000))
ADMIN_ID    = int(os.getenv("ADMIN_ID", 0)) if os.getenv("ADMIN_ID") else None


# =====================================
# INLINE BUTTON HANDLER
# =====================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()  # Acknowledge the button press; may fail if query is stale (>30s)
    except Exception:
        pass  # Stale query — continue processing anyway
    send = query.message.reply_text
    data = query.data

    if data == "start":
        context.user_data.pop("pending_action", None)
        lang = get_lang(update, context)
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system")
        await send_main_menu(send, account_no, system, lang)
        return ConversationHandler.END

    if data == "settings":
        lang = get_lang(update, context)
        msg_text = get_msg(lang, "settings_title")
        await send(
            msg_text,
            parse_mode="Markdown",
            reply_markup=settings_keyboard(lang),
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

    if data == "range_custom_dates":
        context.user_data["pending_action"] = "date_range_lookup"
        await send(
            "📆 *Custom Date Range Lookup*\n\n"
            "Please type your desired date range in `YYYY-MM-DD to YYYY-MM-DD` or `MM-DD to MM-DD` format:\n"
            "_(Example: `2026-07-01 to 2026-07-20` or `07-01 to 07-20`)_\n\n"
            "Or type /cancel to go back.",
            parse_mode="Markdown",
        )
        return ASK_ACCOUNT

    if data.startswith("set_prov_"):
        prov_code = data.replace("set_prov_", "")
        set_user_provider(update.effective_user.id, prov_code)
        context.user_data["provider"] = prov_code
        context.user_data.pop("account_no", None)
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
        context.user_data["pending_action"] = ACTION_BALANCE
        await send(
            f"⚡ *Provider set to {name}*\n\n"
            "🔢 Enter your *account number* or *meter number*:\n\n"
            "_(Both are printed on your electricity bill or meter card. Type /cancel to return)_",
            parse_mode="Markdown",
        )
        return ASK_ACCOUNT

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

    if data == "ai_info":
        lang = get_lang(update, context)
        context.user_data["pending_action"] = "ask_ai"
        await send(
            "🤖 *AI Smart Assistant*\n\n"
            "Ask me any question in English or Bangla about your electricity bill, meter codes, or tariff rates!\n\n"
            "_(Example: `এসি বেশি চালালে বিল কমানোর উপায় কি?` or `How do I check balance on Hexing meter?`)_\n\n"
            "Type your question below (or /cancel to return):",
            parse_mode="Markdown",
        )
        return ASK_ACCOUNT

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
        prov       = context.user_data.get("provider", "desco")
        lang       = get_lang(update, context)
        if account_no and system:
            status_msg = await query.message.reply_text("⏳ Generating daily Plotly chart...")
            today = date.today()
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            date_to   = today.strftime("%Y-%m-%d")
            daily_data, code, desc = desco_get(system, "getCustomerDailyConsumption", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)
            if not daily_data or len(daily_data) < 1:
                date_from = (today - timedelta(days=60)).strftime("%Y-%m-%d")
                daily_data, code, desc = desco_get(system, "getCustomerDailyConsumption", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)

            try:
                buf = generate_daily_chart(daily_data or [], account_no, system, lang=lang) if daily_data else None
            except Exception as e:
                buf = None
                desc = str(e)

            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass

            if buf:
                await query.message.reply_photo(photo=buf, caption=f"📆 *Daily Consumption Chart* — `{account_no}`", parse_mode="Markdown", reply_markup=daily_keyboard(lang))
            else:
                err_text = generate_ai_error_explanation(desc or "Daily usage records unavailable on provider server", action_name="Daily Chart Generation", provider=prov, lang=lang)
                await send(err_text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        else:
            await send("🔢 Enter your *account number* or *meter number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_DAILY
            return ASK_ACCOUNT
        return

    if data == "chart_monthly":
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system")
        meter_no   = context.user_data.get("meter_no", "")
        prov       = context.user_data.get("provider", "desco")
        lang       = get_lang(update, context)
        if account_no and system:
            status_msg = await query.message.reply_text("⏳ Generating monthly Plotly chart...")
            today = date.today()
            month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
            month_to   = today.strftime("%Y-%m")
            monthly_data, code, desc = desco_get(system, "getCustomerMonthlyConsumption", account_no, meter_no, provider=prov, monthFrom=month_from, monthTo=month_to)

            try:
                buf = generate_monthly_chart(monthly_data or [], account_no, system, lang=lang) if monthly_data else None
            except Exception as e:
                buf = None
                desc = str(e)

            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass

            if buf:
                await query.message.reply_photo(photo=buf, caption=f"📅 *Monthly Consumption Chart* — `{account_no}`", parse_mode="Markdown", reply_markup=monthly_keyboard(lang))
            else:
                err_text = generate_ai_error_explanation(desc or "Monthly consumption records unavailable", action_name="Monthly Chart Generation", provider=prov, lang=lang)
                await send(err_text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        else:
            await send("🔢 Enter your *account number* or *meter number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_MONTHLY
            return ASK_ACCOUNT
        return

    if data == "chart_recharge":
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system")
        meter_no   = context.user_data.get("meter_no", "")
        prov       = context.user_data.get("provider", "desco")
        lang       = get_lang(update, context)
        if account_no and system:
            status_msg = await query.message.reply_text("⏳ Generating recharge Plotly chart...")
            today     = date.today()
            date_from = (today - timedelta(days=350)).strftime("%Y-%m-%d")
            date_to   = today.strftime("%Y-%m-%d")
            recharge_data, code, desc = desco_get(system, "getRechargeHistory", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)

            try:
                buf = generate_recharge_chart(recharge_data or [], account_no, system, lang=lang) if recharge_data else None
            except Exception as e:
                buf = None
                desc = str(e)

            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass

            if buf:
                await query.message.reply_photo(photo=buf, caption=f"💳 *Recharge History Chart* — `{account_no}`", parse_mode="Markdown", reply_markup=recharge_keyboard(lang))
            else:
                err_text = generate_ai_error_explanation(desc or "Recharge history records unavailable", action_name="Recharge Chart Generation", provider=prov, lang=lang)
                await send(err_text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        else:
            await send("🔢 Enter your *account number* or *meter number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_RECHARGE
            return ASK_ACCOUNT
        return

    if data == "export_csv":
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system", "unified")
        meter_no   = context.user_data.get("meter_no", "")
        prov       = context.user_data.get("provider", "desco")
        lang       = get_lang(update, context)
        if account_no and system:
            await query.message.reply_text(get_msg(lang, "exporting"))
            today = date.today()
            month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
            month_to   = today.strftime("%Y-%m")
            monthly_data, _, _ = desco_get(system, "getCustomerMonthlyConsumption", account_no, meter_no, provider=prov, monthFrom=month_from, monthTo=month_to)

            date_from = (today - timedelta(days=350)).strftime("%Y-%m-%d")
            date_to   = today.strftime("%Y-%m-%d")
            recharge_data, _, _ = desco_get(system, "getRechargeHistory", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)

            csv_buf = generate_csv_report(monthly_data or [], recharge_data or [], account_no, system)
            filename = f"Utility_Report_{account_no}_{today.strftime('%Y%m%d')}.csv"

            if hasattr(query.message, "reply_document"):
                await query.message.reply_document(
                    document=csv_buf,
                    filename=filename,
                    caption=f"📥 *Utility Consumption & Recharge CSV Report*\n🔑 Account: `{account_no}` _{system}_",
                    parse_mode="Markdown",
                    reply_markup=export_keyboard(lang),
                )
            else:
                await send("📥 CSV Report generated.", reply_markup=export_keyboard(lang))
        else:
            await send("🔢 Enter your *account number* or *meter number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_EXPORT
            return ASK_ACCOUNT
        return

    if data == "export_statement":
        account_no = context.user_data.get("account_no")
        system     = context.user_data.get("system", "unified")
        meter_no   = context.user_data.get("meter_no", "")
        prov       = context.user_data.get("provider", "desco")
        lang       = get_lang(update, context)
        if account_no and system:
            await query.message.reply_text("⏳ Generating annual statement report...")
            today = date.today()
            month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
            month_to   = today.strftime("%Y-%m")
            monthly_data, _, _ = desco_get(system, "getCustomerMonthlyConsumption", account_no, meter_no, provider=prov, monthFrom=month_from, monthTo=month_to)

            date_from = (today - timedelta(days=350)).strftime("%Y-%m-%d")
            date_to   = today.strftime("%Y-%m-%d")
            recharge_data, _, _ = desco_get(system, "getRechargeHistory", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)

            stmt_text = generate_text_statement(monthly_data or [], recharge_data or [], account_no, system, lang=lang)
            await send(stmt_text, parse_mode="Markdown", reply_markup=export_keyboard(lang))
        else:
            await send("🔢 Enter your *account number* or *meter number*:", parse_mode="Markdown")
            context.user_data["pending_action"] = ACTION_EXPORT
            return ASK_ACCOUNT
        return

    ACTION_MAP = {
        "balance":  (ACTION_BALANCE,  fetch_and_send_balance),
        "info":     (ACTION_INFO,     fetch_and_send_info),
        "stats":    (ACTION_STATS,    lambda s, a, sys, m, c: fetch_and_send_stats(s, a, sys, m, c, update=update)),
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
# REGISTER BOT COMMANDS
# =====================================

async def setup_commands(app):
    # Public command menu for normal users (NO /admin)
    await app.bot.set_my_commands([
        BotCommand("start",    "🏠 Main menu"),
        BotCommand("balance",  "⚡ Prepaid balance"),
        BotCommand("info",     "👤 Customer & meter info"),
        BotCommand("stats",    "📊 Usage stats & visual dashboard"),
        BotCommand("summary",  "📋 Full account summary"),
        BotCommand("daily",    "📆 Daily usage & cost breakdown"),
        BotCommand("monthly",  "📅 Monthly consumption history"),
        BotCommand("recharge", "💳 Recharge history (12 months)"),
        BotCommand("export",   "📥 Download Excel CSV report"),
        BotCommand("calc",     "🧮 Appliance energy calculator"),
        BotCommand("tariff",   "⚡ Peak vs Off-Peak tariff schedule"),
        BotCommand("ask",      "🤖 Ask AI Assistant natural question"),
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

    if ADMIN_ID:
        try:
            await app.bot.set_my_commands(
                [
                    BotCommand("start",   "🏠 Main menu"),
                    BotCommand("balance", "⚡ Prepaid balance"),
                    BotCommand("info",    "👤 Customer & meter info"),
                    BotCommand("stats",   "📊 Usage stats & visual dashboard"),
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
            logger.info("Admin command scope registered for ADMIN_ID=%s", ADMIN_ID)
        except Exception as e:
            err_str = str(e).lower()
            if "chat not found" in err_str or "not found" in err_str:
                logger.info(
                    "Admin command scope skipped (admin has not started the bot yet). "
                    "Send /start to the bot as admin to activate the /admin command menu."
                )
            else:
                logger.warning("Admin command scope registration failed: %s", e)

# =====================================
# MAIN
# =====================================

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    # Silently ignore stale callback query errors — not actionable
    if "Query is too old" in str(err) or "query id is invalid" in str(err):
        logger.warning("Ignored stale callback query: %s", err)
        return
    logger.error("Exception while handling update:", exc_info=err)
    if isinstance(update, Update) and update.effective_message:
        lang = get_lang(update, context)
        prov = context.user_data.get("provider", "DESCO") if hasattr(context, "user_data") and context.user_data else "DESCO"
        err_text = str(err) if err else "Server processing exception"
        reply = generate_ai_error_explanation(err_text, action_name="Command Handler", provider=prov, lang=lang)
        try:
            await update.effective_message.reply_text(reply, parse_mode="Markdown", reply_markup=main_keyboard(lang))
        except Exception:
            try:
                # Fallback without parse_mode if Markdown parsing fails
                await update.effective_message.reply_text(reply.replace("*", "").replace("_", "").replace("`", ""), reply_markup=main_keyboard(lang))
            except Exception:
                pass

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(global_error_handler)

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

    conv = ConversationHandler(
        entry_points=[
            *[CommandHandler(name, fn) for name, fn in CMDS],
            CallbackQueryHandler(button_handler),
        ],
        states={
            ASK_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, account_received),
                CallbackQueryHandler(button_handler),
                CommandHandler("start", start),
                CommandHandler("cancel", cancel),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("help",     help_command))
    app.add_handler(CommandHandler("forget",   forget_command))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("provider", providers_cmd))
    app.add_handler(CommandHandler("providers",providers_cmd))
    app.add_handler(CommandHandler("provides", providers_cmd))
    app.add_handler(CommandHandler("other",    other_cmd))
    app.add_handler(CommandHandler("calc",     calc_cmd))
    app.add_handler(CommandHandler("tariff",   tariff_cmd))
    app.add_handler(CommandHandler("ask",      ai_cmd))
    app.add_handler(CommandHandler("ai",       ai_cmd))
    app.add_handler(CommandHandler("postpaid", postpaid_cmd))
    app.add_handler(CommandHandler("palli",    palli_cmd))
    app.add_handler(CommandHandler("bpdb",     bpdb_cmd))
    app.add_handler(CommandHandler("nesco",    nesco_cmd))
    app.add_handler(CommandHandler("token",    token_cmd))
    app.add_handler(CommandHandler("admin",    admin_cmd))
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