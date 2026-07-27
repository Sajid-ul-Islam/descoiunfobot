import os
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from db import (
    track_user,
    get_user_language,
    set_user_language,
    set_user_provider,
    get_admin_stats,
)
from tariff_calc import convert_bn_digits_to_en, detect_system
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
    get_non_desco_reply,
    fetch_and_send_balance,
    fetch_and_send_info,
    fetch_and_send_stats,
    fetch_and_send_summary,
    fetch_and_send_recharge,
    fetch_and_send_monthly,
    fetch_and_send_daily,
    fetch_and_send_chart,
    lookup_specific_date,
    lookup_date_range,
    fetch_and_send_export,
)
from i18n import get_msg
from palli_bidyut import get_palli_text, get_token_help_text
from power_bd import get_bpdb_text, get_nesco_text, get_all_coverage_text
from providers_adapter import is_api_provider, PROVIDERS
from appliance_calc import get_calc_text, get_tariff_guide_text
from ai_assistant import query_ai_assistant, extract_ai_intent

ASK_ACCOUNT = 1

ACTION_BALANCE  = "balance"
ACTION_INFO     = "info"
ACTION_STATS    = "stats"
ACTION_SUMMARY  = "summary"
ACTION_RECHARGE = "recharge"
ACTION_MONTHLY  = "monthly"
ACTION_DAILY    = "daily"
ACTION_CHART    = "chart"
ACTION_EXPORT   = "export"

ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) if os.getenv("ADMIN_ID") else None


async def send_main_menu(send_fn, account_no=None, system=None, lang: str = "en"):
    saved = f"\n\n💾 Account: `{account_no}` _{system}_" if account_no else ""
    msg_text = get_msg(lang, "welcome", saved=saved)
    await send_fn(
        msg_text,
        parse_mode="Markdown",
        reply_markup=main_keyboard(lang),
    )


async def resolve_account(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
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
# COMMAND HANDLERS
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


async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user, "/ask")
    lang = get_lang(update, context)
    context.user_data["pending_action"] = "ask_ai"
    await update.message.reply_text(
        "🤖 *AI Smart Assistant*\n\n"
        "Ask me any question in English or Bangla about your electricity bill, meter codes, or tariff rates!\n\n"
        "_(Example: `এসি বেশি চালালে বিল কমানোর উপায় কি?` or `How do I check balance on Hexing meter?`)_\n\n"
        "Type your question below (or /cancel to return):",
        parse_mode="Markdown",
    )
    return ASK_ACCOUNT


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
    msg_text = (
        "⚡ *Select Electricity Provider / বিদ্যুৎ সরবরাহকারী প্রতিষ্ঠান*\n\n"
        "Choose your electricity distribution company from the 6 providers below to check balance, usage, and monthly bills:\n\n"
        "1️⃣ *DESCO* — Dhaka North, Uttara, Gulshan, Mirpur, Tongi\n"
        "2️⃣ *BPDB* — Chattogram, Sylhet, Mymensingh, Comilla\n"
        "3️⃣ *DPDC* — Dhaka South, Dhanmondi, Narayanganj\n"
        "4️⃣ *Palli Bidyut (BREB)* — Rural Subdivisions & Unions\n"
        "5️⃣ *WZPDCL* — Khulna, Barishal, Faridpur\n"
        "6️⃣ *NESCO* — Rajshahi, Rangpur, Bogura"
        if lang == "en"
        else "⚡ *বিদ্যুৎ সরবরাহকারী প্রতিষ্ঠান নির্বাচন করুন*\n\nব্যালেন্স, ব্যবহার এবং বিল দেখার জন্য নিচে দেওয়া ৬টি বিদ্যুৎ বিতরণ কোম্পানির মধ্যে থেকে আপনার প্রতিষ্ঠান নির্বাচন করুন:"
    )
    await update.message.reply_text(
        msg_text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=provider_selector_keyboard(lang),
    )


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
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


async def account_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text   = update.message.text.strip() if update.message and update.message.text else ""
    user_input = convert_bn_digits_to_en(raw_text)
    msg_target = update.effective_message or (update.callback_query.message if update.callback_query else None)
    send       = msg_target.reply_text if msg_target else update.message.reply_text

    pending = context.user_data.get("pending_action")
    account_no = context.user_data.get("account_no")
    system     = context.user_data.get("system", "unified")
    meter_no   = context.user_data.get("meter_no", "")

    if pending == "ask_ai":
        context.user_data.pop("pending_action", None)
        await send("🤖 Thinking...")
        lang = get_lang(update, context)
        account_no = context.user_data.get("account_no", "")
        system     = context.user_data.get("system", "unified")
        meter_no   = context.user_data.get("meter_no", "")
        ctx_data   = {"provider": context.user_data.get("provider", "DESCO"), "account_no": account_no}
        raw_reply  = query_ai_assistant(user_input, context_data=ctx_data, lang=lang)
        clean_text, intent = extract_ai_intent(raw_reply)

        kb_map = {
            "chart": chart_range_keyboard(lang),
            "daily": daily_keyboard(lang),
            "monthly": monthly_keyboard(lang),
            "recharge": recharge_keyboard(lang),
            "calc": back_keyboard(lang),
            "tariff": back_keyboard(lang),
            "stats": main_keyboard(lang),
            "summary": main_keyboard(lang),
            "balance": main_keyboard(lang),
        }
        reply_kb = kb_map.get(intent, main_keyboard(lang))
        await send(clean_text, parse_mode="Markdown", reply_markup=reply_kb)

        # Automatic Command Triggering if account is saved and intent matched
        if account_no and intent:
            dispatch_fn = {
                "balance":  fetch_and_send_balance,
                "info":     fetch_and_send_info,
                "stats":    fetch_and_send_stats,
                "chart":    lambda s, a, sys, m, c: fetch_and_send_stats(s, a, sys, m, c, update=update),
                "summary":  fetch_and_send_summary,
                "recharge": fetch_and_send_recharge,
                "monthly":  fetch_and_send_monthly,
                "daily":    fetch_and_send_daily,
                "export":   fetch_and_send_export,
            }.get(intent)
            if dispatch_fn:
                await dispatch_fn(send, account_no, system, meter_no, context)

        return ConversationHandler.END

    if pending in ["date_lookup", "date_range_lookup"] or " to " in user_input.lower() or " - " in user_input:
        if account_no and system:
            context.user_data.pop("pending_action", None)
            if " to " in user_input.lower() or " - " in user_input or pending == "date_range_lookup":
                parts = user_input.lower().replace(" to ", " - ").split(" - ")
                if len(parts) >= 2:
                    s_date = parts[0].strip()
                    e_date = parts[1].strip()
                    await send(f"🔍 Searching usage for date range `{s_date}` to `{e_date}`...", parse_mode="Markdown")
                    await lookup_date_range(send, account_no, system, meter_no, s_date, e_date, context, update=update)
                    return ConversationHandler.END
            await send("🔍 Searching date records...")
            await lookup_specific_date(send, account_no, system, meter_no, user_input, context)
            return ConversationHandler.END

    if not user_input.isdigit():
        await send(
            "❌ *Invalid.* Enter digits only (account or meter number), or /cancel.",
            parse_mode="Markdown",
        )
        return ASK_ACCOUNT

    prov = context.user_data.get("provider", "desco")

    if not is_api_provider(prov):
        context.user_data["account_no"] = user_input
        context.user_data["system"]     = "portal"
        context.user_data["meter_no"]   = ""
        track_user(update.effective_user, "account_submit_portal", user_input)

        p_name = PROVIDERS.get(prov, {}).get("name", prov.upper())
        await send(
            f"✅ Account `{user_input}` saved for *{p_name}*",
            parse_mode="Markdown",
        )
        action = context.user_data.pop("pending_action", ACTION_BALANCE)
        dispatch = {
            ACTION_BALANCE:  fetch_and_send_balance,
            ACTION_INFO:     fetch_and_send_info,
            ACTION_STATS:    lambda s, a, sys, m, c: fetch_and_send_stats(s, a, sys, m, c, update=update),
            ACTION_SUMMARY:  fetch_and_send_summary,
            ACTION_RECHARGE: fetch_and_send_recharge,
            ACTION_MONTHLY:  fetch_and_send_monthly,
            ACTION_DAILY:    fetch_and_send_daily,
            ACTION_EXPORT:   fetch_and_send_export,
            ACTION_CHART:    lambda send, acc, sys, met, ctx: fetch_and_send_chart(send, acc, sys, met, ctx, update=update),
        }
        if action in dispatch:
            await dispatch[action](send, user_input, "portal", "", context)
        else:
            lang = get_lang(update, context)
            msg_text, markup = get_non_desco_reply(prov, lang, account_no=user_input)
            await send(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
        return ConversationHandler.END

    await send("🔍 Detecting account...")
    system, account_no, meter_no, info_data, status = detect_system(user_input, provider=prov)

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
            p_name = PROVIDERS.get(prov, {}).get("name", "electricity provider")
            await send(
                f"❌ *Not found on {p_name} servers.*\n\n"
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
        ACTION_STATS:    lambda s, a, sys, m, c: fetch_and_send_stats(s, a, sys, m, c, update=update),
        ACTION_SUMMARY:  fetch_and_send_summary,
        ACTION_RECHARGE: fetch_and_send_recharge,
        ACTION_MONTHLY:  fetch_and_send_monthly,
        ACTION_DAILY:    fetch_and_send_daily,
        ACTION_EXPORT:   fetch_and_send_export,
        ACTION_CHART:    lambda send, acc, sys, met, ctx: fetch_and_send_chart(send, acc, sys, met, ctx, update=update),
    }
    if action in dispatch:
        await dispatch[action](send, account_no, system, meter_no, context)
    else:
        await fetch_and_send_balance(send, account_no, system, meter_no, context)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_action", None)
    await update.message.reply_text("❌ Cancelled.", reply_markup=main_keyboard())
    return ConversationHandler.END


async def _cmd(action: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    account_no, system, meter_no = await resolve_account(update, context, action)
    if not account_no:
        return ASK_ACCOUNT
    send = update.message.reply_text
    dispatch = {
        ACTION_BALANCE:  fetch_and_send_balance,
        ACTION_INFO:     fetch_and_send_info,
        ACTION_STATS:    lambda send_fn, acc, sys, met, ctx: fetch_and_send_stats(send_fn, acc, sys, met, ctx, update=update),
        ACTION_SUMMARY:  fetch_and_send_summary,
        ACTION_RECHARGE: fetch_and_send_recharge,
        ACTION_MONTHLY:  fetch_and_send_monthly,
        ACTION_DAILY:    fetch_and_send_daily,
        ACTION_EXPORT:   fetch_and_send_export,
        ACTION_CHART:    lambda send_fn, acc, sys, met, ctx: fetch_and_send_chart(send_fn, acc, sys, met, ctx, update=update),
    }
    if action in dispatch:
        await dispatch[action](send, account_no, system, meter_no, context)
    else:
        await fetch_and_send_balance(send, account_no, system, meter_no, context)
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
