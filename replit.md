# Telegram Subscription Bot

A Python-based Telegram bot for managing paid subscriptions to a Telegram group or channel. Built with aiogram 3.x.

## Features

- Subscription packages with configurable pricing and durations
- Payment flow: users select a package, send payment proof (screenshot), admin approves/rejects
- Automated subscription expiry: removes users from group when subscription ends
- Reminder notifications: sends messages 3 days and 1 day before expiry
- Admin panel: manage pending payments, view active members, schedule broadcast alerts
- Scheduled alerts: broadcast messages to all active subscribers

## Architecture

```
bot.py           — Entry point, initializes bot and dispatcher
config.py        — All configuration via environment variables
database.py      — SQLite database (subscriptions.db auto-created)
keyboards.py     — All inline keyboard layouts
scheduler.py     — Background tasks (reminders, expiry, alerts)
handlers/
  user.py        — /start, packages, subscription views
  admin.py       — Admin panel, approve/reject payments, alerts
  payment.py     — Payment flow (package → payment → screenshot upload)
```

## Environment Variables / Secrets

| Key | Description |
|-----|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather (secret) |
| `ADMIN_ID` | Your Telegram user ID from @userinfobot (secret) |
| `GROUP_ID` | Your group/channel ID, negative number (secret) |
| `SUPPORT_USERNAME` | Support contact username e.g. @YourUsername (env var) |

## Running

The bot runs via the "Start Bot" workflow:
```bash
python bot.py
```

## Database

SQLite file `subscriptions.db` is auto-created on first run. Tables:
- `users` — registered users
- `subscriptions` — subscription records (pending/active/expired/rejected)
- `payments` — payment submissions with screenshot file IDs
- `scheduled_alerts` — admin-scheduled broadcast messages
- `reminder_log` — tracks which reminders have been sent

## Dependencies

- aiogram==3.13.1 (Telegram bot framework)
- aiosqlite==0.20.0 (async SQLite support)
