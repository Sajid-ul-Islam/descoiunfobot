from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from telegram import Update
from telegram.ext import ContextTypes

from db import get_user_language
from tariff_calc import desco_get, calc_stats, estimate_bill, estimate_units_from_taka
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
)
from chart_gen import generate_usage_chart, generate_custom_date_range_chart, generate_daily_chart
from palli_bidyut import get_palli_text
from power_bd import get_bpdb_text, get_nesco_text, get_all_coverage_text
from providers_adapter import is_api_provider
from tariff_tips import get_low_balance_warning, get_tariff_slab_warning
from ai_assistant import generate_ai_error_explanation


def get_lang(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> str:
    if context and hasattr(context, "user_data") and context.user_data:
        lang = context.user_data.get("language")
        if lang:
            return lang
    user_id = update.effective_user.id if update and hasattr(update, "effective_user") and update.effective_user else None
    if user_id:
        lang = get_user_language(user_id)
        if context and hasattr(context, "user_data"):
            context.user_data["language"] = lang
        return lang or "en"
    return "en"


def get_non_desco_reply(prov: str, lang: str, account_no: str = ""):
    acc_str = f"\n\n🔑 *Saved Account:* `{account_no}`" if account_no else ""
    if prov == "breb":
        return get_palli_text(lang) + acc_str, palli_keyboard(lang)
    elif prov == "bpdb":
        return get_bpdb_text(lang) + acc_str, bpdb_keyboard(lang)
    elif prov == "nesco":
        return get_nesco_text(lang) + acc_str, back_keyboard(lang)
    else:
        return get_all_coverage_text(lang) + acc_str, main_keyboard(lang)


async def fetch_and_send_balance(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if not is_api_provider(prov):
        lang = get_lang(None, context)
        msg_text, markup = get_non_desco_reply(prov, lang, account_no=account_no)
        await send_fn(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
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
        raw_val = float(data.get('currentMonthConsumption', 0))
        if raw_val > 500:
            mo_taka  = raw_val
            mo_units = estimate_units_from_taka(mo_taka)
        else:
            mo_units = raw_val
            mo_taka  = estimate_bill(mo_units)

        lang = get_lang(None, context)
        warn_banner = get_low_balance_warning(bal_val, daily_avg=mo_units/30, lang=lang)

        await send_fn(
            f"⚡ *Prepaid Balance Info*\n\n"
            f"🔑 Account: `{account_no}` _{system}_\n"
            f"💵 *Prepaid Balance:* *৳{bal_val:.2f}*\n"
            f"⚡ *This Month Usage:* `{mo_units:.2f} kWh` (*৳{mo_taka:.2f}*)\n"
            f"🔌 Meter: `{data.get('meterNo', 'N/A')}`\n"
            f"🕒 Last Reading: `{data.get('readingTime', 'N/A')}`"
            f"{warn_banner}",
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang),
        )
    except Exception as e:
        lang = get_lang(None, context)
        err_msg = generate_ai_error_explanation(str(e), action_name="Command", provider=prov, lang=lang)
        await send_fn(err_msg, parse_mode="Markdown", reply_markup=back_keyboard(lang))


async def fetch_and_send_info(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if not is_api_provider(prov):
        lang = get_lang(None, context)
        msg_text, markup = get_non_desco_reply(prov, lang, account_no=account_no)
        await send_fn(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
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
        lang = get_lang(None, context)
        err_msg = generate_ai_error_explanation(str(e), action_name="Command", provider=prov, lang=lang)
        await send_fn(err_msg, parse_mode="Markdown", reply_markup=back_keyboard(lang))


async def fetch_and_send_stats(send_fn, account_no, system, meter_no, context, update: Update = None):
    prov = context.user_data.get("provider", "desco")
    if not is_api_provider(prov):
        lang = get_lang(None, context)
        msg_text, markup = get_non_desco_reply(prov, lang, account_no=account_no)
        await send_fn(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
        return

    # Resolve the best available message object for sending photos
    msg_target = None
    if update:
        msg_target = update.effective_message
    # Fallback: extract message from send_fn if it's a bound method of a Message
    if not msg_target and hasattr(send_fn, "__self__"):
        obj = send_fn.__self__
        if hasattr(obj, "reply_photo"):
            msg_target = obj

    await send_fn("⏳ Processing stats & generating visual dashboard...")

    try:
        today = date.today()
        bal_data,  bal_code,  bal_desc  = desco_get(system, "getBalance",      account_no, meter_no, provider=prov)
        info_data, info_code, info_desc = desco_get(system, "getCustomerInfo", account_no, meter_no, provider=prov)
        
        date_from = (today - timedelta(days=65)).strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")
        daily_data, _, _ = desco_get(system, "getCustomerDailyConsumption", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)

        month_from = (today - relativedelta(months=11)).strftime("%Y-%m")
        month_to   = today.strftime("%Y-%m")
        monthly_data, _, _ = desco_get(system, "getCustomerMonthlyConsumption", account_no, meter_no, provider=prov, monthFrom=month_from, monthTo=month_to)

        if not bal_data:
            msg = ("⚠️ No balance data." if bal_code == 200 else f"❌ *{bal_desc}*")
            await send_fn(msg, parse_mode="Markdown", reply_markup=back_keyboard())
            return

        s = calc_stats(bal_data, info_data)
        load_line = f"🔌 Sanctioned load: `{info_data.get('sanctionLoad','N/A')} kW` (Peak load: ~{s['load_pct']}%)\n" if s["load_pct"] else ""
        lang = get_lang(update, context) if update else "en"
        
        slab_warning = get_tariff_slab_warning(s['mo_units'], s['projected_units'], s['days_elapsed'], s['days_left'], lang=lang)

        caption_text = (
            f"📊 *Usage Statistics & Analytics Dashboard*\n\n"
            f"🔑 Account: `{account_no}` _{system}_\n"
            f"⚡ *Month Consumption:* `{s['mo_units']:.2f} kWh` (*৳{s['mo_taka']:.2f}*)\n"
            f"📉 *Daily Avg:* `{s['daily_units_avg']:.2f} kWh/day` (~৳{s['daily_taka_avg']:.2f}/day)\n"
            f"🔮 *Projected Month:* `{s['projected_units']:.2f} kWh` (~৳{s['projected_taka']:.2f})\n"
            f"💵 *Prepaid Balance:* *৳{bal_data.get('balance', 0)}* (lasts ~`{s['days_bal_lasts']} days`)\n"
            f"{load_line}{slab_warning}"
        )

        buf = generate_usage_chart(daily_data or [], monthly_data or [], account_no, system, bal_data=bal_data, lang=lang, days=7, stats=s)

        if buf and msg_target:
            await msg_target.reply_photo(
                photo=buf,
                caption=caption_text,
                parse_mode="Markdown",
                reply_markup=chart_range_keyboard(lang, days=7),
            )
        elif buf:
            # send_fn cannot send photos — send text stats + note about chart
            await send_fn(
                caption_text + "\n\n_📊 Open Stats & Dashboard from the menu to see the visual chart._",
                parse_mode="Markdown",
                reply_markup=chart_range_keyboard(lang, days=7),
            )
        else:
            await send_fn(caption_text, parse_mode="Markdown", reply_markup=chart_range_keyboard(lang, days=7))
    except Exception as e:
        lang = get_lang(None, context)
        err_msg = generate_ai_error_explanation(str(e), action_name="Stats & Dashboard", provider=prov, lang=lang)
        await send_fn(err_msg, parse_mode="Markdown", reply_markup=back_keyboard(lang))


async def fetch_and_send_summary(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if not is_api_provider(prov):
        lang = get_lang(None, context)
        msg_text, markup = get_non_desco_reply(prov, lang, account_no=account_no)
        await send_fn(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
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
        lang = get_lang(None, context)
        slab_warning = get_tariff_slab_warning(s['mo_units'], s['projected_units'], s['days_elapsed'], s['days_left'], lang=lang)
        await send_fn(
            f"📋 *Full Account Summary*\n\n"
            f"👤 *{info_data.get('customerName','N/A')}*\n"
            f"🔑 Account: `{account_no}` _{system}_\n"
            f"📍 {info_data.get('installationAddress','N/A')}\n\n"
            f"💰 *Balance & Consumption*\n"
            f"💵 Balance: *৳{bal_data.get('balance',0)}*\n"
            f"⚡ This Month: `{s['mo_units']:.2f} kWh` (*৳{s['mo_taka']:.2f}*)\n"
            f"📉 Daily Avg: `{s['daily_units_avg']:.2f} kWh/day` (~৳{s['daily_taka_avg']:.2f}/day)\n"
            f"🔮 Projected Month: `{s['projected_units']:.2f} kWh` (*~৳{s['projected_taka']:.2f}*)\n"
            f"🕐 Balance lasts ~`{s['days_bal_lasts']} days`\n\n"
            f"🔌 *Meter & Connection*\n"
            f"🔌 Meter: `{info_data.get('meterNo','N/A')}` | "
            f"{info_data.get('phaseType','N/A')} | "
            f"`{info_data.get('sanctionLoad','N/A')} kW`\n"
            f"🌐 Feeder: `{info_data.get('feederName','N/A')}`\n"
            f"📋 Tariff: `{info_data.get('tariffSolution','N/A')}`\n"
            f"{conn_line}"
            f"{slab_warning}",
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang),
        )
    except Exception as e:
        lang = get_lang(None, context)
        err_msg = generate_ai_error_explanation(str(e), action_name="Command", provider=prov, lang=lang)
        await send_fn(err_msg, parse_mode="Markdown", reply_markup=back_keyboard(lang))


async def fetch_and_send_recharge(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if not is_api_provider(prov):
        lang = get_lang(None, context)
        msg_text, markup = get_non_desco_reply(prov, lang, account_no=account_no)
        await send_fn(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
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
        lang = get_lang(None, context)
        err_msg = generate_ai_error_explanation(str(e), action_name="Command", provider=prov, lang=lang)
        await send_fn(err_msg, parse_mode="Markdown", reply_markup=back_keyboard(lang))


async def fetch_and_send_monthly(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if not is_api_provider(prov):
        lang = get_lang(None, context)
        msg_text, markup = get_non_desco_reply(prov, lang, account_no=account_no)
        await send_fn(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
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
        lang = get_lang(None, context)
        err_msg = generate_ai_error_explanation(str(e), action_name="Command", provider=prov, lang=lang)
        await send_fn(err_msg, parse_mode="Markdown", reply_markup=back_keyboard(lang))


async def fetch_and_send_daily(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    if not is_api_provider(prov):
        lang = get_lang(None, context)
        msg_text, markup = get_non_desco_reply(prov, lang, account_no=account_no)
        await send_fn(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
        return

    await send_fn("⏳ Fetching daily usage & cost breakdown...")
    try:
        today = date.today()
        # Fetch current month (from 1st of month to today)
        date_from = today.replace(day=1).strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")
        data, code, desc = desco_get(
            system, "getCustomerDailyConsumption", account_no, meter_no, provider=prov,
            dateFrom=date_from, dateTo=date_to,
        )
        if not data or len(data) < 2:
            # Fallback to last 30 days
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            data, code, desc = desco_get(
                system, "getCustomerDailyConsumption", account_no, meter_no, provider=prov,
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
        lang = get_lang(None, context)
        err_msg = generate_ai_error_explanation(str(e), action_name="Command", provider=prov, lang=lang)
        await send_fn(err_msg, parse_mode="Markdown", reply_markup=back_keyboard(lang))


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


async def lookup_date_range(send_fn, account_no, system, meter_no, start_date_str, end_date_str, context, update: Update = None):
    today = date.today()
    date_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    date_to   = today.strftime("%Y-%m-%d")
    prov = context.user_data.get("provider", "desco")
    daily_data, _, _ = desco_get(system, "getCustomerDailyConsumption", account_no, meter_no, provider=prov, dateFrom=date_from, dateTo=date_to)

    if not daily_data or len(daily_data) < 2:
        await send_fn("⚠️ No daily usage data available for range lookup.", reply_markup=back_keyboard())
        return

    sorted_daily = sorted(daily_data, key=lambda x: str(x.get("date", "")))
    filtered = []

    for i in range(1, len(sorted_daily)):
        curr_d = str(sorted_daily[i].get("date", ""))
        if start_date_str <= curr_d[-len(start_date_str):] and curr_d[-len(end_date_str):] <= end_date_str:
            u_curr = float(sorted_daily[i].get("consumedUnit") or 0)
            u_prev = float(sorted_daily[i-1].get("consumedUnit") or 0)
            units  = max(u_curr - u_prev, 0)

            t_curr = float(sorted_daily[i].get("consumedTaka") or 0)
            t_prev = float(sorted_daily[i-1].get("consumedTaka") or 0)
            taka   = max(t_curr - t_prev, 0)

            filtered.append({"date": curr_d, "units": round(units, 2), "taka": round(taka, 2)})

    if not filtered:
        await send_fn(f"❌ No records found between `{start_date_str}` and `{end_date_str}`.\n\nPlease check dates and try again.", parse_mode="Markdown", reply_markup=back_keyboard())
        return

    total_units = sum(r["units"] for r in filtered)
    total_taka  = sum(r["taka"] for r in filtered)
    num_days    = len(filtered)
    avg_units   = total_units / num_days if num_days > 0 else 0
    avg_taka    = total_taka / num_days if num_days > 0 else 0
    avg_rate    = total_taka / total_units if total_units > 0 else 0

    lang = get_lang(update, context) if update else "en"
    buf  = generate_custom_date_range_chart(filtered, account_no, system, start_date_str, end_date_str, lang=lang)

    summary_text = (
        f"📅 *Custom Date Range Usage Summary*\n"
        f"🗓 *Range:* `{start_date_str}` to `{end_date_str}` ({num_days} Days)\n"
        f"🔑 Account: `{account_no}` _{system}_\n\n"
        f"⚡ *Total Units Consumed:* `{total_units:.2f} kWh`\n"
        f"💰 *Total Cost:* *৳{total_taka:.2f}*\n"
        f"📉 *Daily Average:* `{avg_units:.2f} kWh/day` (~৳{avg_taka:.2f}/day)\n"
        f"📊 *Effective Avg Rate:* `@৳{avg_rate:.2f} / kWh`"
    )

    msg_target = update.effective_message if update else None
    if buf and msg_target:
        await msg_target.reply_photo(
            photo=buf,
            caption=summary_text,
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang),
        )
    else:
        await send_fn(summary_text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def fetch_and_send_export(send_fn, account_no, system, meter_no, context):
    prov = context.user_data.get("provider", "desco")
    lang = get_lang(None, context)
    if not is_api_provider(prov):
        msg_text, markup = get_non_desco_reply(prov, lang, account_no=account_no)
        await send_fn(msg_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=markup)
        return

    await send_fn(
        "📥 *Utility Report & Financial Statement*\n\n"
        "Select your preferred report format below:",
        parse_mode="Markdown",
        reply_markup=export_keyboard(lang),
    )
