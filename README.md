# ⚡ Bangladesh Unified Power & DESCO Telegram Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-v20+-0088cc.svg)](https://core.telegram.org/bots/api)
[![Plotly Analytics](https://img.shields.io/badge/Plotly-Visual%20Analytics-3F4F75.svg)](https://plotly.com/python/)
[![Multi-Language](https://img.shields.io/badge/Language-English%20%7C%20Bangla%20%F0%9F%87%A7%F0%9F%87%A9-green.svg)](https://github.com/Sajid-ul-Islam/descoiunfobot)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ed.svg)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deploy%20Ready-46E3B7.svg)](https://render.com/)

A state-of-the-art, feature-rich Telegram Bot for tracking prepaid & postpaid electricity balance, customer details, daily usage breakdowns, 12-month recharge histories, visual analytics dashboards, and Excel report exports across **all 6 power utility providers in Bangladesh**:

1. **⚡ DESCO (Dhaka North)**
2. **🏢 BPDB (Chattogram & Regional Urban Zones)**
3. **🌾 Palli Bidyut / BREB (Rural & Suburban Districts)**
4. **🌆 DPDC (Dhaka South & Narayanganj)**
5. **🌊 WZPDCL (West Zone — Khulna, Barishal, Greater Faridpur)**
6. **❄️ NESCO (North Zone — Rajshahi & Rangpur Divisions)**

---

## ✨ Key Features & Capabilities

### 🌐 1. Multi-Provider Gateway & Unified Interface (`/provider`)
- **Seamless Provider Selector**: Switch between **DESCO**, **BPDB**, **Palli Bidyut (BREB)**, **DPDC**, **WZPDCL**, and **NESCO** anytime.
- **Dual-System Auto-Detection**: Automatically detects whether an account/meter uses `unified` or `tkdes` backend systems.
- **Account Memory**: Remembers saved accounts per user in SQLite (`bot_data.db`).

### 🇧🇩 2. Complete Multi-Language Engine (`/settings`)
- **Full English 🇬🇧 & Bangla 🇧🇩 Support**: Toggle your preferred language from settings or `/settings` command.
- **Cross-Platform Font Rendering**: Engineered to render cleanly on Android, iOS, Windows, Mac, Linux, and Telegram Web without broken Unicode boxes.

### 📈 3. Executive 4-Card Plotly Analytics Dashboard (`/chart`)
- **Top KPI Metric Cards (`go.Indicator`)**: Current Balance (৳), Current Month Consumption (kWh), Daily Average (kWh/day), and Projected Usage (kWh).
- **Glowing Semi-Transparent Spline Area Chart**: 15-Day daily usage and cost trends.
- **Tealgrn / Viridis Gradient Bar Chart**: 12-Month historical unit consumption and bill amounts.
- **Server Font Stack**: Rendered via headless Chromium using Debian `Noto Sans Bengali` fonts.

### 📥 4. Excel CSV Ledger Exporter (`/export`)
- **Downloadable Account Ledger**: Instantly exports a UTF-8 Excel-compatible `.csv` document containing 12-month consumption history and full recharge transaction logs.

### 🧮 5. Home Appliance Energy Calculator & Tariff Schedule (`/calc` & `/tariff`)
- **Appliance Calculator (`/calc`)**: Estimates daily/monthly kWh and monthly cost (৳) for Inverter ACs, Refrigerators, Fans, LED bulbs, and Water Pumps.
- **Peak vs Off-Peak Schedule (`/tariff`)**: Interactive guide for Time-of-Use hours:
  - 🔴 **Peak Hours:** 5:00 PM – 11:00 PM (Highest Rate)
  - 🟢 **Off-Peak Hours:** 11:00 PM – 5:00 PM (Lower Rate)
  - All 6 residential LT-A tariff slabs (৳3.75/unit to ৳10.70/unit).

### 📋 6. Tariff Slab Smart Tips & Low Balance Alerts
- **Proactive Tariff Monitor**: Advises users how many units remain before stepping into a higher tariff rate.
- **Critical Low Balance Banner**: Warns users when balance drops below **৳100** or less than **3 days** of usage remain.

### 🔑 7. bKash Missing Token Recovery Guide (`/token`)
- Step-by-step instructions for recovering digital receipt tokens from bKash App Inbox, USSD `*727#` inquiry, or BREB Helpline **16899**.

---

## 🤖 Bot Command Reference

| Command | Button | Description |
|---|---|---|
| `/start` | 🏠 Main Menu | Welcome card, saved account, and main navigation |
| `/balance` | ⚡ Balance | Prepaid balance, current month units, and last reading |
| `/info` | 👤 Customer Info | Profile details, meter model, load, phase, and transformer |
| `/stats` | 📊 Stats | Daily average usage, projected bill, and tariff slab monitor |
| `/chart` | 📈 Dashboard | Generates 4-card Plotly PNG analytics dashboard |
| `/summary` | 📋 Summary | Complete combined account snapshot |
| `/daily` | 📆 Daily Usage | Day-by-day unit usage, daily cost (৳), and unit price |
| `/monthly` | 📅 Monthly Usage | 12-month historical consumption |
| `/recharge` | 💳 Recharge History | 12-month transaction history and token numbers |
| `/export` | 📥 Export CSV Report | Downloads Excel-compatible CSV account report |
| `/calc` | 🧮 Appliance Calculator | Home appliance energy and monthly cost estimator |
| `/tariff` | ⚡ Tariff & Peak Hours | LT-A tariff slabs and Peak/Off-Peak time schedule |
| `/provider` | ⚡ Select Provider | Switches active utility provider |
| `/other` | 🌐 Other Providers | Alternative providers, USSD guides, and portals |
| `/palli` | 🌾 Palli Bidyut | BREB USSD `*727#` guide, hotline 16899, & keypad codes |
| `/bpdb` | 🏢 BPDB | Chattogram & urban zone portal guide |
| `/token` | 🔑 Token Help | bKash missing token recovery guide |
| `/providers`| 🇧🇩 All BD Providers | Complete 6-entity Bangladesh power grid directory |
| `/settings` | ⚙️ Settings | Language (EN/BN) and provider preferences |
| `/forget` | 🗑 Clear Saved Account | Clears saved account details from user memory |
| `/help` | ❓ Help | Instructions and user guide |

---

## 🏗 Tech Stack & Architecture

- **Language**: Python 3.11+
- **Telegram Framework**: `python-telegram-bot[webhooks]` v20+
- **Data Visualization**: `plotly`, `kaleido` (Headless Chromium image generator)
- **Database Engine**: `sqlite3` (User language, provider, and account persistence)
- **Fonts Stack**: `Noto Sans Bengali` (`fonts-noto-extra`, `fonts-beng`)
- **HTTP Engine**: `requests`, `urllib3`
- **Deployment Container**: Docker on Render Web Service

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the Repository
```bash
git clone https://github.com/Sajid-ul-Islam/descoiunfobot.git
cd descoiunfobot
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
BOT_TOKEN=your_telegram_bot_token_from_botfather
WEBHOOK_URL=http://localhost
PORT=10000
```

### 4. Run the Bot
```bash
python bot.py
```

---

## 🐳 Docker Deployment

To build and run the bot locally inside Docker with full Bengali font support:

```bash
# Build Docker image
docker build -t desco-unified-bot .

# Run Docker container
docker run -d -p 10000:10000 --env-file .env desco-unified-bot
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.
