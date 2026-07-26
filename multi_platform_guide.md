# Multi-Platform Guide: Expanding DESCO Info Bot to WhatsApp, Facebook & Instagram

This guide details how to extend your **DESCO Info Bot** from Telegram to **WhatsApp**, **Facebook Messenger**, and **Instagram Direct**.

---

## 🏗 System Architecture Overview

To support multiple platforms cleanly without duplicating code, split your application into **2 layers**:

```
 ┌─────────────────┐ ┌──────────────────┐ ┌───────────────────┐ ┌──────────────────┐
 │  Telegram Bot   │ │  WhatsApp Cloud  │ │    FB Messenger   │ │ Instagram Direct │
 └────────┬────────┘ └────────┬─────────┘ └─────────┬─────────┘ └────────┬─────────┘
          │                   │                     │                    │
 ─────────┼───────────────────┼─────────────────────┼────────────────────┼──────────
          └───────────────────┴──────────┬──────────┴────────────────────┘
                                         ▼
                            ┌────────────────────────┐
                            │    Core DESCO Engine   │
                            │  (desco_get, calc, etc)│
                            └────────────────────────┘
```

1. **Core Engine**: Pure Python module containing DESCO API calls, auto-system detection (`unified` / `tkdes`), daily deltas, stats calculations, and LT-A bill estimates.
2. **Platform Handlers**: Platform-specific adapters that format responses for each channel's UI (Telegram Inline Keyboards, WhatsApp Interactive Messages, Facebook Quick Replies, Instagram Buttons).

---

## 🟢 1. WhatsApp Integration

### Option A: Meta WhatsApp Business Cloud API (Official & Free Tier Available)
Meta offers 1,000 free service conversations per month via the **WhatsApp Business Cloud API**.

1. **Setup Meta Developer Account**:
   - Go to [developers.facebook.com](https://developers.facebook.com) → Create App → Select **Business** type.
   - Add **WhatsApp** product to your app.
   - Obtain a **Phone Number ID**, **WhatsApp Business Account ID**, and a **Permanent Access Token**.
2. **Webhook Setup**:
   - Add a `/webhook/whatsapp` endpoint to a FastAPI or Flask app.
   - Meta sends HTTP POST requests whenever a user messages your WhatsApp number.
   - Send replies using Meta's REST endpoint: `https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages`

### Option B: Twilio for WhatsApp (Easiest Setup)
1. Sign up on [Twilio](https://www.twilio.com) and enable WhatsApp Sandbox.
2. Set Twilio Webhook URL to `https://your-app.onrender.com/webhook/twilio`.
3. Use Twilio Python SDK (`twilio.rest`) to send and receive messages.

---

## 🔵 2. Facebook Messenger Integration

Facebook Messenger uses the **Meta Messenger Platform**.

1. **Setup Facebook Page & App**:
   - Create a Facebook Page for your bot (e.g. *DESCO Info Bot*).
   - In Meta Developer Console, add the **Messenger** product to your Meta App.
   - Link your Facebook Page and generate a **Page Access Token**.
2. **Webhook Verification & Reception**:
   - Subscribe your webhook endpoint (e.g. `/webhook/facebook`) to the `messages` event.
   - When users message your Page, Meta posts JSON to your webhook containing `sender.id` and `message.text`.
3. **Replying**:
   - POST to `https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}` with quick-reply buttons (Balance, Info, Stats, Recharge, Monthly).

---

## 🟣 3. Instagram Direct Integration

Instagram Messaging uses the **Instagram Messaging API** (part of Meta Graph API).

1. **Requirements**:
   - Convert your Instagram account to an **Instagram Professional / Business Account**.
   - Connect the Instagram Professional Account to your Facebook Page.
2. **Meta Developer App Setup**:
   - Enable **Instagram Graph API** in your Meta Developer Console.
   - Turn on "Allow Access to Messages" in Instagram app settings (*Settings → Privacy → Messages → Allow Access to Messages*).
3. **Webhook Setup**:
   - Uses the exact same webhook infrastructure as Facebook Messenger (under `entry[].messaging[]`).
   - Deliveries arrive at `/webhook/instagram` or unified Meta webhook.

---

## 🛠 Recommended Unified Code Approach (FastAPI + Telegram + Meta)

By adding a `FastAPI` or `Flask` web server alongside `python-telegram-bot`, you can run a single web service on Render that handles:
- Telegram Webhook (`/telegram`)
- WhatsApp / Meta Webhook (`/webhook/meta`)

### Modular Folder Structure:
```
descobuddy/
├── core/
│   └── desco_api.py      # Core logic (desco_get, detect_system, calc_stats)
├── adapters/
│   ├── telegram_bot.py   # Telegram UI & commands
│   ├── whatsapp.py       # WhatsApp Cloud API handler
│   └── messenger.py      # Facebook & Instagram handler
├── main.py               # Combined FastAPI / Flask server
├── Dockerfile
└── render.yaml
```

---

## 📋 Summary Comparison Table

| Platform | Official API | Free Tier? | Best For |
|---|---|---|---|
| **Telegram** | Telegram Bot API | 100% Free | Instant setup, rich buttons & inline menus |
| **WhatsApp** | Meta WhatsApp Cloud API | 1,000 conversations/mo free | Mass reach in Bangladesh |
| **Facebook** | Messenger Platform | 100% Free | Page followers & direct social messaging |
| **Instagram** | Instagram Messaging API | 100% Free | Mobile audience & social discovery |
