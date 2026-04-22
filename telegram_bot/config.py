# ============================================================
#  CONFIG — Fill in your values before running the bot
# ============================================================

# 1. Get this from @BotFather on Telegram
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# 2. Your Telegram user ID (get from @userinfobot)
ADMIN_ID = 123456789  # Replace with your actual Telegram ID

# 3. Your group/channel ID (negative number for groups, e.g. -1001234567890)
GROUP_ID = -1001234567890  # Replace with your actual group/channel ID

# 4. Payment details shown to users
PAYMENT_INSTRUCTIONS = """
💳 *Payment Instructions*

Please send payment to one of the following:

🏦 *Bank Transfer:*
Account Name: Your Name
Account Number: 1234567890
Bank: Your Bank Name

📱 *Mobile Banking (bKash/Nagad):*
Number: 01XXXXXXXXX
Reference: Your Telegram Username

After payment, click the button below to send your screenshot.
"""

# 5. Support contact
SUPPORT_USERNAME = "@YourSupportUsername"

# 6. Subscription packages (name, price in BDT, duration in days)
PACKAGES = [
    {"id": 1, "name": "⭐ Basic",    "price": 299,  "days": 30,  "description": "1 Month Access"},
    {"id": 2, "name": "🔥 Standard", "price": 799,  "days": 90,  "description": "3 Months Access"},
    {"id": 3, "name": "👑 Premium",  "price": 1499, "days": 180, "description": "6 Months Access"},
    {"id": 4, "name": "💎 VIP",      "price": 2499, "days": 365, "description": "1 Year Access"},
]

# 7. Reminder settings (days before expiry to send reminders)
REMINDER_DAYS_BEFORE = [3, 1]  # Send reminders 3 days and 1 day before expiry
