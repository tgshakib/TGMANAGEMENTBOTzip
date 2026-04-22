# 📖 Telegram Subscription Bot — Complete Setup Guide

## 📁 Project Structure

```
telegram_bot/
├── bot.py           ← Main entry point
├── config.py        ← ⚡ YOUR SETTINGS GO HERE
├── database.py      ← SQLite database (auto-created)
├── keyboards.py     ← All buttons and menus
├── scheduler.py     ← Background tasks (reminders, expiry, alerts)
├── requirements.txt ← Dependencies
├── handlers/
│   ├── user.py      ← User commands (/start, packages, subscription)
│   ├── admin.py     ← Admin panel (approve/reject, schedule alerts)
│   └── payment.py   ← Payment flow (package → payment → screenshot)
└── README.md        ← This file
```

---

## ⚡ Step-by-Step Setup (Beginner Friendly)

### Step 1: Install Python
- Download Python 3.10+ from https://python.org
- During install, check ✅ "Add Python to PATH"

### Step 2: Get your Bot Token
1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Follow instructions, copy the **token** (looks like: `123456:ABC-DEF...`)

### Step 3: Get your Admin ID
1. Open Telegram, search for **@userinfobot**
2. Send `/start`
3. Copy your **Id** number (e.g., `987654321`)

### Step 4: Get your Group/Channel ID
1. Add **@userinfobot** to your group/channel
2. It will show the group ID (negative number like `-1001234567890`)
3. Remove the bot after getting the ID

### Step 5: Add your bot as Admin to your group/channel
- Go to your group/channel → Admins → Add Admin
- Add your bot
- Give permissions: **Ban users**, **Delete messages**

### Step 6: Edit config.py
Open `config.py` and fill in:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"    # From Step 2
ADMIN_ID = 987654321                  # From Step 3
GROUP_ID = -1001234567890             # From Step 4
SUPPORT_USERNAME = "@YourUsername"    # Your support contact
```
Also customize:
- `PAYMENT_INSTRUCTIONS` — your bank/bKash/Nagad details
- `PACKAGES` — your subscription plans and prices

### Step 7: Install dependencies
Open terminal/command prompt in the `telegram_bot/` folder and run:
```bash
pip install -r requirements.txt
```

### Step 8: Run the bot
```bash
python bot.py
```

You should see:
```
✅ Database initialized.
✅ Scheduler started.
🤖 Bot is starting...
```

---

## 🤖 Bot Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Show main menu with subscription status |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Open admin panel |
| `/activate <user_id> <pkg_id> <days>` | Manually activate subscription |

---

## 🔄 How the Bot Works

### User Flow
```
/start → Main Menu
         ├── 📦 Packages → Select Package → 💳 Pay → Send Screenshot → Pending
         ├── 🔄 Renew → Same as Packages
         ├── 📊 My Subscription → View status & expiry
         └── 💬 Support → Opens support chat
```

### Admin Flow
```
/admin → Admin Panel
         ├── 📋 Pending Payments → See screenshots → ✅ Approve / ❌ Reject
         ├── 👥 Active Members → List all active subscribers
         ├── ⏰ Schedule Alert → Send broadcast at specific time
         ├── 📢 View Alerts → See all scheduled alerts
         └── 📊 Stats → Quick stats
```

### Automation
- ✅ Every **60 seconds**, the bot checks:
  - Subscriptions expiring in 1 day → sends reminder
  - Subscriptions expiring in 3 days → sends reminder
  - Expired subscriptions → removes user from group
  - Scheduled alerts → sends broadcast

---

## 🔧 Customization

### Change reminder timing
In `config.py`:
```python
REMINDER_DAYS_BEFORE = [3, 1]  # 3 days before, then 1 day before
```

### Add more packages
In `config.py`:
```python
PACKAGES = [
    {"id": 1, "name": "⭐ Basic", "price": 299, "days": 30, "description": "1 Month"},
    # Add more here...
]
```

### Change check interval
In `scheduler.py`, change the sleep time:
```python
await asyncio.sleep(60)  # 60 = every minute, 3600 = every hour
```

---

## 🚀 Running 24/7 (on a server)

### On Linux (VPS):
```bash
# Install screen
sudo apt install screen

# Start a screen session
screen -S mybot

# Run bot
python bot.py

# Detach: press Ctrl+A then D
# Reattach: screen -r mybot
```

### Using systemd service:
Create `/etc/systemd/system/telegrambot.service`:
```ini
[Unit]
Description=Telegram Subscription Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/telegram_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable telegrambot
sudo systemctl start telegrambot
sudo systemctl status telegrambot
```

---

## 🛡️ Common Issues

| Problem | Solution |
|---------|----------|
| Bot not removing users | Make sure bot has **admin** rights in group with **Ban users** permission |
| "Unauthorized" error | Check your `BOT_TOKEN` in config.py |
| Bot not responding | Make sure bot is running (`python bot.py`) |
| Can't find group ID | Add @userinfobot to your group temporarily |

---

## 📝 Notes
- Database (`subscriptions.db`) is created automatically on first run
- All data is stored locally — no cloud needed
- For production use, consider running on a VPS (DigitalOcean, Hetzner, etc.)
