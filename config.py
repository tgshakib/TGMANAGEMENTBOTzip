import os

# ============================================================
#  CONFIG — Values are loaded from environment variables/secrets
# ============================================================

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
ADMIN_ID   = int(os.environ.get("ADMIN_ID", "0"))
GROUP_ID   = int(os.environ.get("GROUP_ID", "0"))

SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "@JAYITAUTOBO")

PAYMENT_INSTRUCTIONS = os.environ.get("PAYMENT_INSTRUCTIONS", """
💛 *Binance Pay (Business Official):*
Pay ID: `582355370`

🔷 *Crypto (USDT — TRC20):*
`TYudgrH88fCWzNqthy6tXQAieeNcCBYmER`

📌 After payment, send your screenshot proof to:
👤 @Oawhidshakib
""")

# ── MTG / NON-MTG SVIP Packages ────────────────────────────
PACKAGES = [
    # MTG Future Signal Compounding SVIP
    {"id": 1, "name": "🎀 SVIP · 3 Days",    "price": 5,  "days": 3,  "description": "MTG Future Signal Compounding SVIP"},
    {"id": 2, "name": "💠 SVIP · 6 Days",    "price": 10, "days": 6,  "description": "MTG Future Signal Compounding SVIP"},
    {"id": 3, "name": "🏅 SVIP · 14 Days",   "price": 20, "days": 14, "description": "MTG Future Signal Compounding SVIP"},
    {"id": 4, "name": "👑 SVIP · 30 Days",   "price": 52, "days": 30, "description": "MTG Future Signal Compounding SVIP"},
    {"id": 5, "name": "💎 SVIP · 60 Days",   "price": 66, "days": 60, "description": "MTG Future Signal Compounding SVIP"},
    # NON-MTG Future Signal Compounding
    {"id": 6, "name": "💠 NON-MTG · 6 Days",    "price": 15, "days": 6,  "description": "NON-MTG Future Signal Compounding"},
    {"id": 7, "name": "🏅 NON-MTG · 1 Month",   "price": 58, "days": 30, "description": "NON-MTG Future Signal Compounding"},
    {"id": 8, "name": "👑 NON-MTG · 3 Months",  "price": 99, "days": 90, "description": "NON-MTG Future Signal Compounding"},
]

# ── GOLDZILA / FOREX VIP Packages ──────────────────────────
FOREX_VIP_PACKAGES = [
    {"id": 1, "name": "🎯 FOREX SVIP · 10 Days",   "price": 30,  "days": 10,   "label": "10 Days"},
    {"id": 2, "name": "💠 FOREX SVIP · 15 Days",   "price": 48,  "days": 15,   "label": "15 Days"},
    {"id": 3, "name": "🔥 FOREX SVIP · 1 Month",   "price": 119, "days": 30,   "label": "1 Month"},
    {"id": 4, "name": "🏅 FOREX SVIP · 3 Months",  "price": 170, "days": 90,   "label": "3 Months"},
    {"id": 5, "name": "💎 FOREX SVIP · 12 Months", "price": 599, "days": 365,  "label": "12 Months"},
    {"id": 6, "name": "♾️ FOREX SVIP · UNLIMITED", "price": 899, "days": 3650, "label": "UNLIMITED"},
]

FOREX_LIFETIME_NOTE = (
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "♻️ *Lifetime Access available with partner link.*\n"
    "To get this please contact 👉 Support"
)

FOREX_PAYMENT_INSTRUCTIONS = os.environ.get("FOREX_PAYMENT_INSTRUCTIONS", """
💛 *Binance Pay (Business Official):*
Pay ID: `582355370`

🔷 *Crypto (USDT — TRC20):*
`TYudgrH88fCWzNqthy6tXQAieeNcCBYmER`

📌 After payment, send your screenshot proof below.
""")

# ── Tip shown for non-monthly packages (HTML) ──────────────
PACKAGE_TIP_HTML = (
    "💡 <b>Tips:</b>\n\n"
    "❒ নিজের account কে ভালো একটা boost up ভালো একটা রিজাল্ট দেখতে চাইলে, "
    "আমি personally suggested করবো ১/২মাসের জন্যে SVIP join করেন। "
    "সাথে আমি প্রতেকদিন কত ডলার profit করে market থেকে বের হইয়া যাবেন তার একটা "
    "DAILY target sheet দিয়া দিবো এবং ওইটা follow করলে মাস শেষে ৭০০/৮০০$+ profit "
    "থাকবে ইনশাল্লাহ। 💯💞\n\n"
    "〔 English 〕\n"
    "❒ NEED GOOD RESULT — BOOST YOUR Capital? I will personally suggest to join "
    "SVIP for 1/2 month. Also, I will give you a DAILY target sheet of how many "
    "dollars profit you will get out of the market every day and if you follow that, "
    "you will have 700/800$+ profit at the end of the month, in sha Allah. 💯💞"
)

# ── Scheduler reminder windows (handled internally in scheduler.py) ─
REMINDER_DAYS_BEFORE = [7, 5, 3]
