import asyncio
import logging
from datetime import datetime
from aiogram import Bot

import database as db
from config import ADMIN_ID, GROUP_ID, REMINDER_DAYS_BEFORE, SUPPORT_USERNAME

logger = logging.getLogger(__name__)

async def check_expiring_subscriptions(bot: Bot):
    """Send reminder messages for subscriptions expiring soon."""
    for days in REMINDER_DAYS_BEFORE:
        subs = db.get_subscriptions_expiring_in_days(days)
        for sub in subs:
            # Avoid duplicate reminders
            if db.already_reminded(sub["user_id"], sub["id"], days):
                continue

            end = datetime.fromisoformat(sub["end_date"])
            try:
                from keyboards import packages_kb
                await bot.send_message(
                    sub["user_id"],
                    f"⚠️ *Subscription Expiring Soon!*\n\n"
                    f"Your subscription expires in *{days} day(s)* on {end.strftime('%d %b %Y')}.\n\n"
                    f"🔄 Do you want to renew?\n"
                    f"Please select a package below 👇",
                    parse_mode="Markdown",
                    reply_markup=packages_kb()
                )
                db.log_reminder(sub["user_id"], sub["id"], days)
                logger.info(f"Sent {days}-day reminder to user {sub['user_id']}")
            except Exception as e:
                logger.error(f"Failed to remind user {sub['user_id']}: {e}")

async def remove_expired_members(bot: Bot):
    """Expire subscriptions and remove users from group/channel."""
    expired = db.expire_subscriptions()
    for record in expired:
        user_id = record["user_id"]
        try:
            # Notify user
            await bot.send_message(
                user_id,
                f"❌ *Subscription Expired*\n\n"
                f"Your subscription has ended. You have been removed from the group.\n\n"
                f"To rejoin, please purchase a new subscription 👇",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Could not notify expired user {user_id}: {e}")

        try:
            # Ban (kick) from group/channel
            await bot.ban_chat_member(GROUP_ID, user_id)
            # Unban immediately so they can rejoin later
            await bot.unban_chat_member(GROUP_ID, user_id)
            logger.info(f"Removed expired user {user_id} from group {GROUP_ID}")
        except Exception as e:
            logger.error(f"Could not remove user {user_id} from group: {e}")

async def send_scheduled_alerts(bot: Bot):
    """Send admin-scheduled broadcast alerts to all active members."""
    alerts = db.get_pending_alerts()
    for alert in alerts:
        subs = db.get_all_active_subscriptions()
        sent_count = alert["sent_count"] + 1
        success = 0

        for sub in subs:
            try:
                await bot.send_message(
                    sub["user_id"],
                    f"📢 *{alert['title']}*\n\n{alert['message']}\n\n"
                    f"💬 Need help? Contact {SUPPORT_USERNAME}",
                    parse_mode="Markdown"
                )
                success += 1
                await asyncio.sleep(0.05)  # Avoid flood limits
            except Exception as e:
                logger.error(f"Alert send failed for {sub['user_id']}: {e}")

        db.mark_alert_sent(alert["id"], sent_count, alert["repeat_times"], alert["interval_hours"])
        logger.info(f"Alert '{alert['title']}' sent to {success}/{len(subs)} members")

        # Notify admin
        try:
            await bot.send_message(
                ADMIN_ID,
                f"✅ *Alert Sent*\n\n"
                f"📌 {alert['title']}\n"
                f"👥 Delivered to {success} members\n"
                f"🔁 Send count: {sent_count}/{alert['repeat_times']}",
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def scheduler_loop(bot: Bot):
    """Main scheduler loop — runs every 60 seconds."""
    while True:
        try:
            await check_expiring_subscriptions(bot)
            await remove_expired_members(bot)
            await send_scheduled_alerts(bot)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(60)  # Check every minute

async def start_scheduler(bot: Bot):
    """Launch scheduler as a background task."""
    asyncio.create_task(scheduler_loop(bot))
    logger.info("✅ Scheduler started.")
