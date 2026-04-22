import asyncio
import logging
from datetime import datetime
from aiogram import Bot

import database as db
from config import GROUP_ID, SUPPORT_USERNAME, PACKAGES

logger = logging.getLogger(__name__)

# ── Reminder rules: (days_before, min_pkg_days, max_pkg_days) ──
# monthly+ (30d+) → member reminder 7 days before
# weekly   (14d)  → member reminder 5 days before
# 6-day           → member reminder 3 days before
# 3-day or less   → no member reminder
REMINDER_RULES = [
    (7, 30, 9999),
    (5, 14, 29),
    (3,  6, 13),
]

REMINDER_TEXT = (
    "⚠️ *QUICK VIP UPDATE* ⚠️\n\n"
    "Your VIP subscription is about to expire in just a few days.\n\n"
    "Before it ends, ask yourself one simple question:\n"
    "👉 Do you want to start the new year calm, focused, and stress-free, "
    "or go back to guessing trades again?\n\n"
    "Then Renewing in advance :\nmeans:-\n"
    "✅ No interruption\n"
    "✅ No last-minute stress\n"
    "✅ Smooth, structured trading from Day 1 of the new year\n\n"
    "Smart traders prepare early.\n"
    "Let me know when you're ready to renew and lock your access.\n\n"
    "⏰ Don't wait till it expires."
)

def get_pkg_days(package_id: int) -> int:
    pkg = next((p for p in PACKAGES if p["id"] == package_id), None)
    return pkg["days"] if pkg else 30

async def check_expiring_subscriptions(bot: Bot):
    """Send smart reminders to members based on subscription duration."""
    from keyboards import packages_kb

    for (remind_days, min_days, max_days) in REMINDER_RULES:
        subs = db.get_subscriptions_expiring_in_days(remind_days)
        for sub in subs:
            pkg_days = get_pkg_days(sub["package_id"])
            if not (min_days <= pkg_days <= max_days):
                continue
            if db.already_reminded(sub["user_id"], sub["id"], remind_days):
                continue
            try:
                await bot.send_message(
                    sub["user_id"],
                    REMINDER_TEXT,
                    parse_mode="Markdown",
                    reply_markup=packages_kb()
                )
                db.log_reminder(sub["user_id"], sub["id"], remind_days)
                logger.info(f"Sent {remind_days}-day reminder to user {sub['user_id']}")
            except Exception as e:
                logger.error(f"Failed to remind user {sub['user_id']}: {e}")

async def alert_admin_expiring_soon(bot: Bot):
    """Send admin a 1-day-before alert for every subscription expiring tomorrow."""
    admin_id = db.get_admin_id()
    subs = db.get_subscriptions_expiring_in_days(1)
    for sub in subs:
        # Use days_before=1 as the admin-alert marker (separate from member reminders)
        if db.already_reminded(sub["user_id"], sub["id"], 1):
            continue
        end   = datetime.fromisoformat(sub["end_date"])
        uname = f"@{sub['username']}" if sub.get("username") else sub.get("full_name", "Unknown")
        try:
            await bot.send_message(
                admin_id,
                f"⏰ *Subscription Expiring Tomorrow — Admin Alert*\n\n"
                f"👤 Member: *{sub.get('full_name', 'Unknown')}* ( {uname} )\n"
                f"📦 Package: *{sub.get('package_name', 'N/A')}*\n"
                f"📅 *Expires:* {end.strftime('%d %b %Y')}\n\n"
                f"Please follow up with this member if needed.",
                parse_mode="Markdown"
            )
            db.log_reminder(sub["user_id"], sub["id"], 1)
            logger.info(f"Sent 1-day admin alert for user {sub['user_id']}")
        except Exception as e:
            logger.error(f"Failed to send admin 1-day alert for {sub['user_id']}: {e}")

async def remove_expired_members(bot: Bot):
    """Expire subscriptions, remove from group, and alert admin."""
    admin_id = db.get_admin_id()
    expired  = db.expire_subscriptions()

    for record in expired:
        user_id = record["user_id"]
        uname   = f"@{record['username']}" if record.get("username") else f"ID {user_id}"
        fname   = record.get("full_name", "Unknown")

        # Notify member
        try:
            await bot.send_message(
                user_id,
                "❌ <b>Subscription Expired</b>\n\n"
                "Your subscription has ended and you have been removed from the group.\n\n"
                "To rejoin, please purchase a new subscription 👇",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Could not notify expired user {user_id}: {e}")

        # Remove from group
        try:
            await bot.ban_chat_member(GROUP_ID, user_id)
            await bot.unban_chat_member(GROUP_ID, user_id)
            logger.info(f"Removed expired user {user_id} from group")
        except Exception as e:
            logger.error(f"Could not remove user {user_id} from group: {e}")

        # Alert admin
        try:
            await bot.send_message(
                admin_id,
                f"🔴 *Member Subscription Expired — Admin Alert*\n\n"
                f"👤 Member: *{fname}* ( {uname} )\n"
                f"📦 Package: *{record.get('package_name', 'N/A')}*\n\n"
                f"Member has been auto-removed from the group.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Could not send admin expiry alert: {e}")

async def send_scheduled_alerts(bot: Bot):
    """Send admin-scheduled broadcast alerts to all active members."""
    admin_id = db.get_admin_id()
    alerts   = db.get_pending_alerts()

    for alert in alerts:
        subs       = db.get_all_active_subscriptions()
        sent_count = alert["sent_count"] + 1
        success    = 0

        for sub in subs:
            try:
                await bot.send_message(
                    sub["user_id"],
                    f"📢 *{alert['title']}*\n\n{alert['message']}\n\n"
                    f"💬 Need help? Contact {SUPPORT_USERNAME}",
                    parse_mode="Markdown"
                )
                success += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Alert send failed for {sub['user_id']}: {e}")

        db.mark_alert_sent(alert["id"], sent_count, alert["repeat_times"], alert["interval_hours"])
        logger.info(f"Alert '{alert['title']}' sent to {success}/{len(subs)} members")

        try:
            await bot.send_message(
                admin_id,
                f"✅ *Alert Sent*\n\n"
                f"📌 {alert['title']}\n"
                f"👥 Delivered to {success} members\n"
                f"🔁 Send count: {sent_count}/{alert['repeat_times']}",
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def scheduler_loop(bot: Bot):
    while True:
        try:
            await check_expiring_subscriptions(bot)
            await alert_admin_expiring_soon(bot)
            await remove_expired_members(bot)
            await send_scheduled_alerts(bot)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(60)

async def start_scheduler(bot: Bot):
    asyncio.create_task(scheduler_loop(bot))
    logger.info("✅ Scheduler started.")
