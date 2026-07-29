from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from i18n import get_msg

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
            InlineKeyboardButton(get_msg(lang, "export_btn"),    callback_data="export"),
            InlineKeyboardButton(get_msg(lang, "providers_btn"), callback_data="select_provider"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "other_btn"),    callback_data="other_menu"),
            InlineKeyboardButton(get_msg(lang, "settings_btn"), callback_data="settings"),
        ],
        [
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

def chart_range_keyboard(lang: str = "en", days: int = 7):
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
            InlineKeyboardButton("📅 Specific Date", callback_data="range_date"),
            InlineKeyboardButton("📆 Date-to-Date Range", callback_data="range_custom_dates"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start"),
        ],
    ])

def export_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 CSV Excel Report", callback_data="export_csv"),
            InlineKeyboardButton("📄 Visual Statement", callback_data="export_statement"),
        ],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def recharge_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(lang, "view_recharge_chart"), callback_data="chart_recharge")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"),       callback_data="start")],
    ])

def postpaid_keyboard(lang: str = "en", pdf_url: str | None = None):
    buttons = []
    if pdf_url:
        buttons.append([InlineKeyboardButton("📥 Download Bill Copy (PDF)", url=pdf_url)])
    buttons.extend([
        [InlineKeyboardButton("📄 DESCO E-Bill Portal", url="https://ebill.desco.org.bd/")],
        [InlineKeyboardButton("🌐 DESCO OCSMS Portal", url="https://ocsms.desco.org.bd/")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])
    return InlineKeyboardMarkup(buttons)


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
        [
            InlineKeyboardButton("⚡ Switch Active Provider", callback_data="select_provider"),
            InlineKeyboardButton(get_msg(lang, "postpaid_btn"),    callback_data="postpaid_info"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "palli_btn"),  callback_data="palli_info"),
            InlineKeyboardButton(get_msg(lang, "bpdb_btn"),   callback_data="bpdb_info"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "nesco_btn"),  callback_data="nesco_info"),
            InlineKeyboardButton(get_msg(lang, "token_btn"),  callback_data="token_info"),
        ],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def settings_keyboard(lang: str = "en", has_account: bool = False):
    acc_btn = (
        InlineKeyboardButton(get_msg(lang, "clear_account_btn"), callback_data="confirm_clear_account")
        if has_account
        else InlineKeyboardButton(get_msg(lang, "set_account_btn"), callback_data="start")
    )
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton("🇧🇩 বাংলা",  callback_data="set_lang_bn"),
        ],
        [acc_btn],
        [InlineKeyboardButton("⚡ Change Utility Provider", callback_data="select_provider")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def confirm_clear_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(get_msg(lang, "confirm_clear_yes"), callback_data="do_clear_account"),
            InlineKeyboardButton(get_msg(lang, "confirm_clear_cancel"), callback_data="settings"),
        ]
    ])

def ai_quick_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(lang, "ai_chip_peak"),  callback_data="ai_prompt_peak")],
        [InlineKeyboardButton(get_msg(lang, "ai_chip_ac"),    callback_data="ai_prompt_ac")],
        [InlineKeyboardButton(get_msg(lang, "ai_chip_token"), callback_data="ai_prompt_token")],
        [InlineKeyboardButton(get_msg(lang, "main_menu_btn"), callback_data="start")],
    ])

def other_keyboard(lang: str = "en"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(get_msg(lang, "ai_btn"),     callback_data="ai_info"),
            InlineKeyboardButton(get_msg(lang, "calc_btn"),   callback_data="calc_info"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "tariff_btn"), callback_data="tariff_info"),
            InlineKeyboardButton(get_msg(lang, "token_btn"),  callback_data="token_info"),
        ],
        [
            InlineKeyboardButton(get_msg(lang, "providers_btn"), callback_data="select_provider"),
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
