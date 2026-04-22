from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

import database as db
from config import ADMIN_ID, PACKAGES, GROUP_ID
from keyboards import admin_panel_kb, back_admin_kb

router = Router()

def get_pkg(pkg_id: int):
    return next((p for p in PACKAGES if p["id"] == pkg_id), None)

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ── FSM States ─────────────────────────────────────────────
class AlertStates(StatesGroup):
    title        = State()
    message      = State()
    send_date    = State()
    repeat_times = State()
    interval     = State()

class ManualActivate(StatesGroup):
    user_id  = State()
    pkg_id   = State()
    days     = State()

# ── /admin ─────────────────────────────────────────────────
@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 *Admin Panel*\n\nWelcome back, Admin!",
        parse_mode="Markdown",
        reply_markup=admin_panel_kb()
    )

@router.callback_query(F.data == "admin_panel")
async def admin_panel_cb(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "🛠 *Admin Panel*",
        parse_mode="Markdown",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()

# ── Pending payments ───────────────────────────────────────
@router.callback_query(F.data == "admin_pending")
async def admin_pending(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    payments = db.get_pending_payments()
    if not payments:
        await callback.message.edit_text(
            "✅ No pending payments right now.",
            reply_markup=back_admin_kb()
        )
        await callback.answer()
        return

    from keyboards import admin_payment_kb
    text = f"💳 *{len(payments)} Pending Payment(s):*\n\n"
    for p in payments:
        text += (
            f"#{p['id']} — {p['full_name']} (@{p['username'] or 'N/A'})\n"
            f"Package: {p['package_name']} | ৳{p['amount']}\n"
            f"Submitted: {p['submitted_at'][:16]}\n\n"
        )

    # Show individual items with approve/reject buttons
    await callback.message.edit_text(
        text, parse_mode="Markdown", reply_markup=back_admin_kb()
    )
    # Send each payment separately with buttons
    for p in payments:
        if p.get("screenshot_file_id"):
            await callback.message.answer_photo(
                photo=p["screenshot_file_id"],
                caption=f"Payment #{p['id']} — {p['full_name']} | {p['package_name']} | ৳{p['amount']}",
                reply_markup=admin_payment_kb(p["id"])
            )
        else:
            await callback.message.answer(
                f"Payment #{p['id']} — {p['full_name']} | {p['package_name']} | ৳{p['amount']}\n(No screenshot)",
                reply_markup=admin_payment_kb(p["id"])
            )
    await callback.answer()

# ── Approve payment ────────────────────────────────────────
@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, bot):
    if not is_admin(callback.from_user.id):
        return
    payment_id = int(callback.data.split("_")[1])
    payment = db.approve_payment(payment_id)
    if not payment:
        await callback.answer("Payment not found!", show_alert=True)
        return

    pkg = get_pkg(payment["package_id"])
    days = pkg["days"] if pkg else 30

    # Create and activate subscription
    sub_id = db.create_subscription(payment["user_id"], payment["package_id"], payment["package_name"])
    db.activate_subscription(sub_id, days)
    db.attach_screenshot(payment_id, payment.get("screenshot_file_id", ""))

    # Notify user
    end_date = (datetime.now().replace(microsecond=0).isoformat())
    from datetime import timedelta
    end = datetime.now() + timedelta(days=days)

    try:
        await bot.send_message(
            payment["user_id"],
            f"🎉 *Payment Approved!*\n\n"
            f"✅ Your subscription is now *active*!\n"
            f"📦 Package: *{payment['package_name']}*\n"
            f"📅 Valid until: *{end.strftime('%d %b %Y')}*\n\n"
            f"Welcome to the community! 🚀",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Could not notify user {payment['user_id']}: {e}")

    await callback.message.edit_caption(
        f"✅ *Payment #{payment_id} APPROVED*\n"
        f"User: {payment['user_id']} | Package: {payment['package_name']}",
        parse_mode="Markdown"
    )
    await callback.answer("✅ Payment approved!")

# ── Reject payment ─────────────────────────────────────────
@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, bot):
    if not is_admin(callback.from_user.id):
        return
    payment_id = int(callback.data.split("_")[1])
    payment = db.get_payment(payment_id)
    if not payment:
        await callback.answer("Payment not found!", show_alert=True)
        return
    db.reject_payment(payment_id)

    try:
        await bot.send_message(
            payment["user_id"],
            f"❌ *Payment Rejected*\n\n"
            f"Unfortunately, your payment for *{payment['package_name']}* was rejected.\n\n"
            f"Please contact support if you believe this is a mistake.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        f"❌ *Payment #{payment_id} REJECTED*",
        parse_mode="Markdown"
    )
    await callback.answer("❌ Payment rejected.")

# ── Active members ─────────────────────────────────────────
@router.callback_query(F.data == "admin_members")
async def admin_members(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    subs = db.get_all_active_subscriptions()
    if not subs:
        await callback.message.edit_text("👥 No active members.", reply_markup=back_admin_kb())
        await callback.answer()
        return

    lines = [f"👥 *Active Members ({len(subs)}):*\n"]
    for s in subs:
        end = datetime.fromisoformat(s["end_date"])
        days_left = max(0, (end - datetime.now()).days)
        lines.append(
            f"• {s['full_name']} (@{s['username'] or 'N/A'})\n"
            f"  {s['package_name']} | ⏳ {days_left}d left | Exp: {end.strftime('%d %b %Y')}\n"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n...(truncated)"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_admin_kb())
    await callback.answer()

# ── Stats ──────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    subs = db.get_all_active_subscriptions()
    pending = db.get_pending_payments()

    await callback.message.edit_text(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Active Members: *{len(subs)}*\n"
        f"💳 Pending Payments: *{len(pending)}*\n"
        f"📅 Updated: {datetime.now().strftime('%d %b %Y %H:%M')}",
        parse_mode="Markdown",
        reply_markup=back_admin_kb()
    )
    await callback.answer()

# ── Schedule alert ─────────────────────────────────────────
@router.callback_query(F.data == "admin_schedule")
async def admin_schedule_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AlertStates.title)
    await callback.message.edit_text(
        "⏰ *Schedule an Alert*\n\n"
        "Step 1/5: Enter a *title* for this alert:",
        parse_mode="Markdown",
        reply_markup=back_admin_kb()
    )
    await callback.answer()

@router.message(AlertStates.title)
async def alert_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text)
    await state.set_state(AlertStates.message)
    await message.answer(
        "Step 2/5: Enter the *message* to send to all members:",
        parse_mode="Markdown",
        reply_markup=back_admin_kb()
    )

@router.message(AlertStates.message)
async def alert_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(message=message.text)
    await state.set_state(AlertStates.send_date)
    await message.answer(
        "Step 3/5: Enter *date and time* to send (format: `DD-MM-YYYY HH:MM`)\n"
        "Example: `25-12-2024 09:00`",
        parse_mode="Markdown",
        reply_markup=back_admin_kb()
    )

@router.message(AlertStates.send_date)
async def alert_date(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        dt = datetime.strptime(message.text.strip(), "%d-%m-%Y %H:%M")
        await state.update_data(send_at=dt.isoformat())
        await state.set_state(AlertStates.repeat_times)
        await message.answer(
            "Step 4/5: How many times should this alert be sent?\n"
            "Enter a number (e.g., `1`, `2`, `3`):",
            parse_mode="Markdown",
            reply_markup=back_admin_kb()
        )
    except ValueError:
        await message.answer(
            "❌ Invalid format. Use `DD-MM-YYYY HH:MM`\nExample: `25-12-2024 09:00`",
            parse_mode="Markdown"
        )

@router.message(AlertStates.repeat_times)
async def alert_repeat(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        n = int(message.text.strip())
        await state.update_data(repeat_times=n)
        if n > 1:
            await state.set_state(AlertStates.interval)
            await message.answer(
                "Step 5/5: How many hours between each alert?\n"
                "Enter hours (e.g., `24` for daily, `12` for twice daily):",
                parse_mode="Markdown"
            )
        else:
            data = await state.get_data()
            alert_id = db.create_alert(
                data["title"], data["message"], data["send_at"], 1, 24
            )
            await state.clear()
            await message.answer(
                f"✅ *Alert Scheduled!*\n\n"
                f"📌 Title: {data['title']}\n"
                f"📅 Send at: {data['send_at'][:16]}\n"
                f"🔁 Repeat: 1 time",
                parse_mode="Markdown",
                reply_markup=admin_panel_kb()
            )
    except ValueError:
        await message.answer("❌ Please enter a valid number.")

@router.message(AlertStates.interval)
async def alert_interval(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        hours = int(message.text.strip())
        data = await state.get_data()
        alert_id = db.create_alert(
            data["title"], data["message"], data["send_at"],
            data["repeat_times"], hours
        )
        await state.clear()
        await message.answer(
            f"✅ *Alert Scheduled!*\n\n"
            f"📌 Title: {data['title']}\n"
            f"📅 First send: {data['send_at'][:16]}\n"
            f"🔁 Repeat: {data['repeat_times']} times every {hours}h",
            parse_mode="Markdown",
            reply_markup=admin_panel_kb()
        )
    except ValueError:
        await message.answer("❌ Please enter a valid number of hours.")

# ── View alerts ────────────────────────────────────────────
@router.callback_query(F.data == "admin_alerts")
async def admin_view_alerts(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    alerts = db.get_all_alerts()
    if not alerts:
        await callback.message.edit_text("📢 No alerts scheduled.", reply_markup=back_admin_kb())
        await callback.answer()
        return

    lines = ["📢 *Scheduled Alerts:*\n"]
    for a in alerts:
        status_icon = "✅" if a["status"] == "done" else "⏳"
        lines.append(
            f"{status_icon} *{a['title']}*\n"
            f"  Msg: {a['message'][:40]}...\n"
            f"  Next: {a['send_at'][:16]} | Sent: {a['sent_count']}/{a['repeat_times']}\n"
        )

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=back_admin_kb()
    )
    await callback.answer()

# ── Manual activate (admin command) ───────────────────────
@router.message(Command("activate"))
async def manual_activate(message: Message):
    """Usage: /activate <user_id> <pkg_id> <days>"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("Usage: /activate <user_id> <pkg_id> <days>")
        return
    try:
        uid, pkg_id, days = int(parts[1]), int(parts[2]), int(parts[3])
        pkg = get_pkg(pkg_id)
        sub_id = db.create_subscription(uid, pkg_id, pkg["name"] if pkg else f"Package {pkg_id}")
        db.activate_subscription(sub_id, days)
        await message.answer(f"✅ Activated subscription for user {uid} ({days} days)")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
