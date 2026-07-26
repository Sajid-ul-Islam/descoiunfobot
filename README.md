# ⚡ DESCO Info Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-v20+-0088cc.svg)](https://core.telegram.org/bots/api)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ed.svg)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deploy%20Ready-46E3B7.svg)](https://render.com/)

A feature-rich Telegram Bot for checking **DESCO (Dhaka Electric Supply Company Limited)** prepaid electricity balance, customer details, daily usage breakdowns, monthly consumption, and 12-month recharge histories.

---

## ✨ Features

- **🔍 Dual-System Auto-Detection**: Automatically detects whether an account/meter uses DESCO's `unified` or `tkdes` backend system.
- **🔢 Account or Meter No. Input**: Accepts either your **Customer Account Number** (e.g. `41032243`) or **Meter Number** (e.g. `030310015159`).
- **💾 Smart Account Memory**: Remembers your account per-user so you don't have to re-enter it every time.
- **⚡ Balance & Current Reading**: Instant balance (৳), monthly consumption (Units), meter number, and last reading timestamp.
- **👤 Customer & Meter Profile**: Full connection info including Customer Name, Address, Phase, Sanction Load, Transformer, Feeder, and Sub-Division.
- **📊 Usage Statistics & Bill Projection**:
  - Daily average unit consumption.
  - Projected end-of-month unit usage.
  - Estimated days balance will last.
  - Estimated bill calculation based on DESCO LT-A tariff slabs.
  - Connection age & load utilization percentage.
- **📆 Daily Usage & Cost Breakdown**: Day-by-day delta calculations showing daily units, daily cost (৳), and effective rate (@৳/unit).
- **📅 12-Month Consumption History**: Month-by-month breakdown of unit consumption and bill amounts.
- **💳 12-Month Recharge History**: Complete transaction history with recharge amounts and token numbers.
- **🎛 Interactive Navigation**: Inline buttons, back buttons, and full Telegram command menu support (`/` menu).

---

## 🤖 Commands Reference

| Command | Button | Description |
|---|---|---|
| `/start` | 🏠 Main Menu | Shows welcome card, saved account, and main navigation buttons |
| `/balance` | ⚡ Balance | Checks current prepaid balance and monthly units |
| `/info` | 👤 Customer Info | Displays full customer profile and meter technical details |
| `/stats` | 📊 Stats | Shows usage statistics, daily average, and projected bill |
| `/summary` | 📋 Summary | Complete combined snapshot card |
| `/daily` | 📆 Daily Usage | Day-by-day unit usage, daily cost, and unit price breakdown |
| `/monthly` | 📅 Monthly Usage | 12-month historical monthly consumption |
| `/recharge` | 💳 Recharge History | 12-month recharge transaction history & token numbers |
| `/forget` | 🗑 Clear Account | Clears saved account details from user memory |
| `/help` | ❓ Help | Instructions and user guide |
| `/cancel` | ❌ Cancel | Cancels active prompts |

---

## 🏗 Tech Stack & Dependencies

- **Language**: Python 3.11+
- **Framework**: `python-telegram-bot[webhooks]`
- **HTTP Client**: `requests` / `urllib3`
- **Utilities**: `python-dotenv`, `python-dateutil`
- **Deployment**: Docker container on Render Web Service (Free Tier compliant)

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the repository
```bash
git clone https://github.com/khanistiak/descobuddy.git
cd descobuddy
```

### 2. Create a virtual environment & install dependencies
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

## 🐳 Docker Setup

Build and run locally with Docker:

```bash
# Build Docker image
docker build -t desco-info-bot .

# Run container
docker run -d --name desco-bot \
  -e BOT_TOKEN="your_telegram_bot_token" \
  -e WEBHOOK_URL="https://your-public-domain.com" \
  -e PORT="10000" \
  -p 10000:10000 \
  desco-info-bot
```

---

## 🌐 Deploying to Render (Free Tier)

This repository includes a `render.yaml` blueprint configured as a **Web Service** using Docker.

1. Push your repository to **GitHub**.
2. Go to [render.com](https://render.com) → **New → Blueprint**.
3. Connect your repository (`descobuddy`). Render will auto-detect `render.yaml`.
4. Add the following **Environment Variables** in the Render Dashboard:
   - `BOT_TOKEN`: Your Telegram Bot token from [@BotFather](https://t.me/BotFather).
   - `WEBHOOK_URL`: Your Render app URL (e.g. `https://descoinfo.onrender.com`).
   - `PORT`: `10000`
5. Click **Deploy**.

---

## 🛡 Disclaimer

This is an unofficial community project created for public convenience. It connects to publicly accessible DESCO web endpoints. It is not affiliated with, endorsed by, or connected to Dhaka Electric Supply Company Limited (DESCO).
