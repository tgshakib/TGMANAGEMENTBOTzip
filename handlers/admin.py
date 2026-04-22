from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

import database as db
from config import PACKAGES, FOREX_VIP_PACKAGES, GROUP_ID
from keyboards import (
    admin_panel_kb, back_admin_kb, transfer_confirm_kb,
    active_members_actions_kb, ban_member_list_kb, ban_confirm_kb,
)
from admin_msg_tracker import add_id as track_admin_msg, pop_all as pop_admin_msgs

router = Router()


# Outer middleware: track every incoming message from the admin so we can wipe
# their side too when CLOSE ADMIN PANEL is pressed. Runs before handlers and
# always continues propagation.
@router.message.outer_middleware()
async def _track_admin_incoming_mw(handler, event: Message, data):
    try:
        if event.from_user and event.from_user.id == db.get_admin_id():
            track_admin_msg(event.message_id)
    except Exception:
        pass
    return await handler(event, data)

def get_pkg(pkg_id: int):
    return next((p for p in PACKAGES if p["id"] == pkg_id), None)

def get_forex_pkg_by_name(name: str):
    return next((p for p in FOREX_VIP_PACKAGES if p["name"] == name), None)

def is_forex_payment(package_name: str) -> bool:
    return "FOREX" in package_name

def is_admin(user_id: int) -> bool:
    return user_id == db.get_admin_id()

def pkg_type_label(pkg) -> str:
    if pkg and "SVIP" in pkg.get("name", ""):
        return "MTG SVIP"
    if pkg and "NON-MTG" in pkg.get("name", ""):
        return "NON-MTG"
    return pkg["name"] if pkg else "SVIP"

def pkg_duration_label(days: int) -> str:
    if days >= 30:
        months = days // 30
        return f"{months} Month{'s' if months > 1 else ''}"
    return f"{days} Days"

# ── FSM States ─────────────────────────────────────────────
class AlertStates(StatesGroup):
    title        = State()
    message      = State()
    send_date    = State()
    repeat_times = State()
    interval     = State()

class ApprovalStates(StatesGroup):
    waiting_invite_link = State()

class TransferStates(StatesGroup):
    waiting_new_admin = State()

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
        broker = p.get("broker_name") or "—"
        ss     = "✅" if p.get("screenshot_file_id") else "❌"
        text += (
            f"🔹 *{p['full_name']}* (@{p['username'] or 'N/A'})\n"
            f"📦 *Package:* {p['package_name']}\n"
            f"💰 *Amount:* *${p['amount']}*\n"
            f"🏦 *Broker:* {broker}\n"
            f"📸 *Screenshot:* {ss}\n"
            f"🕐 *Submitted:* {p['submitted_at'][:16]}\n\n"
        )

    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown", reply_markup=back_admin_kb()
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="Markdown", reply_markup=back_admin_kb()
        )

    for p in payments:
        broker = p.get("broker_name") or "—"
        caption = (
            f"💳 *New Payment*\n"
            f"👤 *{p['full_name']}* (@{p['username'] or 'N/A'})\n"
            f"📦 *{p['package_name']}*\n"
            f"💰 *${p['amount']}*\n"
            f"🏦 *Broker:* {broker}"
        )
        if p.get("screenshot_file_id"):
            await callback.message.answer_photo(
                photo=p["screenshot_file_id"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=admin_payment_kb(p["id"])
            )
        else:
            await callback.message.answer(
                caption + "\n_(No screenshot attached)_",
                parse_mode="Markdown",
                reply_markup=admin_payment_kb(p["id"])
            )
    await callback.answer()

# ── Alhamdulillah Receive Payment ──────────────────────────
@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, state: FSMContext, bot):
    if not is_admin(callback.from_user.id):
        return
    payment_id = int(callback.data.split("_")[1])
    payment = db.approve_payment(payment_id)
    if not payment:
        await callback.answer("Payment not found!", show_alert=True)
        return

    pkg_name = payment.get("package_name", "")
    forex    = is_forex_payment(pkg_name)

    if forex:
        pkg  = get_forex_pkg_by_name(pkg_name)
        days = pkg["days"] if pkg else 30
    else:
        pkg  = get_pkg(payment["package_id"])
        days = pkg["days"] if pkg else 30

    sub_id = db.create_subscription(payment["user_id"], payment["package_id"], payment["package_name"])
    db.activate_subscription(sub_id, days)

    raw_username = payment.get("username") or ""
    uname        = f"@{raw_username}" if raw_username else payment.get("full_name", "User")
    user_info    = f"{payment.get('full_name', 'User')} ({uname})"

    # Delete the old payment message
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Store context and ask admin for invite link
    await state.set_state(ApprovalStates.waiting_invite_link)
    await state.update_data(
        user_id=payment["user_id"],
        payment_id=payment_id,
        package_name=payment["package_name"],
        package_id=payment["package_id"],
        days=days,
        user_info=user_info,
        uname=uname,
        is_forex=forex,
    )

    fname = payment.get("full_name", "User")

    await callback.message.answer(
        f"🤲 *Alhamdulillah! Payment Received!*\n\n"
        f"👤 *{fname}* ( {uname} )\n"
        f"📦 *{payment['package_name']}*\n"
        f"✅ Subscription activated.\n\n"
        f"🔗 Now please send the VIP invite link 👇",
        parse_mode="Markdown"
    )
    await callback.answer("🤲 Alhamdulillah!")

# ── Receive invite link from admin ─────────────────────────
@router.message(ApprovalStates.waiting_invite_link)
async def receive_invite_link(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id):
        return

    data         = await state.get_data()
    invite_link  = message.text.strip() if message.text else ""
    user_id      = data["user_id"]
    package_id   = data["package_id"]
    days         = data["days"]
    package_name = data["package_name"]
    uname        = data.get("uname", "Member")
    forex        = data.get("is_forex", False)

    await state.clear()

    duration = pkg_duration_label(days)

    if forex:
        congrats = (
            f"🎉 <b>Payment Received! Congratulations!</b>\n"
            f"🟢 Your account is now active.\n\n"
            f"🔮 GOLDZILA SVIP : approved\n"
            f"⏳ Duration : {duration}\n\n"
            f"👉 To join our GOLDZILA SVIP please click the link below:\n"
            f"{invite_link}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Once you've joined:\n"
            f"Please Read pin post Patiently FOLLOW Our Guidelines &amp; Trade Rules "
            f"To Get Started Smoothly.\n\n"
            f"For Exness broker user : DM here @JAYITAUTOBO CHANGE IB GET 1:unlimited leverages\n"
            f'Send message: <b>"CHANGE IB VIP MEMBER"</b>'
        )
    else:
        pkg       = get_pkg(package_id)
        svip_type = pkg_type_label(pkg)
        congrats  = (
            f"🎉 <b>Payment Received! Congratulations!</b>\n"
            f"🟢 Your account is now active.\n\n"
            f"🔮 SVIP Types : {svip_type}\n"
            f"⏳ Duration : {duration}\n\n"
            f"👉 To join our exclusive community, please click the link below:\n"
            f"{invite_link}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Once you've joined:\n"
            f"Please Wait Patiently For Our Guidelines &amp; Trade Rules "
            f"To Get Started Smoothly.\n\n"
            f"For guidelines DM here @OAWHIDSHAKIB\n"
            f'Send message: <b>"SVIP GUIDE"</b>'
        )

    try:
        await bot.send_message(user_id, congrats, parse_mode="HTML")
        await message.answer(
            f"✅ *Invite link sent successfully Member {uname}*\n\n"
            f"⏳ *WORK WORK WORK Waiting for next payment, sir!*",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(
            f"❌ Could not send message to user: {e}\n\n"
            f"Please contact them manually.\n\n"
            f"⏳ *WORK WORK WORK Waiting for next payment, sir!*",
            parse_mode="Markdown"
        )

    await message.answer(
        "🛠 *Admin Panel*",
        parse_mode="Markdown",
        reply_markup=admin_panel_kb()
    )

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

    # Notify the user of rejection
    try:
        await bot.send_message(
            payment["user_id"],
            f"❌ <b>Payment Rejected</b>\n\n"
            f"Unfortunately, your payment for <b>{payment['package_name']}</b> was rejected.\n\n"
            f"Please contact support if you believe this is a mistake.\n"
            f"👤 @OAWHIDSHAKIB",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Delete the old payment message
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.answer("❌ Payment rejected.")

    await callback.message.answer(
        f"❌ *Payment Rejected.*\n\n"
        f"⏳ *WORK WORK WORK Waiting for next payment, sir!*",
        parse_mode="Markdown"
    )
    await callback.message.answer(
        "🛠 *Admin Panel*",
        parse_mode="Markdown",
        reply_markup=admin_panel_kb()
    )

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
            f"• *{s['full_name']}* (@{s['username'] or 'N/A'})\n"
            f"  📦 {s['package_name']} | ⏳ *{days_left}d left* | 📅 {end.strftime('%d %b %Y')}\n"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n...(truncated)"

    await callback.message.edit_text(
        text, parse_mode="Markdown", reply_markup=active_members_actions_kb()
    )
    await callback.answer()

# ── Ban list: show all active members with remove buttons ───
@router.callback_query(F.data == "admin_ban_list")
async def admin_ban_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    subs = db.get_all_active_subscriptions()
    if not subs:
        await callback.message.edit_text(
            "✅ *No active members to remove.*",
            parse_mode="Markdown",
            reply_markup=active_members_actions_kb()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🚫 *Ban / Remove Member*\n\n"
        f"Select a member below to remove them from the group and expire their subscription:\n\n"
        f"*{len(subs)} active member(s)*",
        parse_mode="Markdown",
        reply_markup=ban_member_list_kb(subs)
    )
    await callback.answer()

# ── Ban: show confirm for one member ───────────────────────
@router.callback_query(F.data.startswith("banrem_"))
async def ban_member_prompt(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split("_")[1])
    sub = db.get_active_subscription(user_id)
    user = db.get_user(user_id)
    if not sub or not user:
        await callback.answer("Member not found.", show_alert=True)
        return

    uname    = f"@{user['username']}" if user.get("username") else user.get("full_name", "Unknown")
    end      = datetime.fromisoformat(sub["end_date"])
    days_left = max(0, (end - datetime.now()).days)

    await callback.message.edit_text(
        f"🚫 *Confirm Member Removal*\n\n"
        f"👤 *{user['full_name']}* ( {uname} )\n"
        f"📦 *{sub['package_name']}*\n"
        f"⏳ *{days_left} days remaining*\n"
        f"📅 Expires: {end.strftime('%d %b %Y')}\n\n"
        f"⚠️ This will:\n"
        f"• Expire their subscription immediately\n"
        f"• Remove them from the group\n"
        f"• Send them a removal notification\n\n"
        f"Are you sure?",
        parse_mode="Markdown",
        reply_markup=ban_confirm_kb(user_id)
    )
    await callback.answer()

# ── Ban confirm: execute removal ────────────────────────────
@router.callback_query(F.data.startswith("banyes_"))
async def ban_member_execute(callback: CallbackQuery, bot):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split("_")[1])
    sub  = db.get_active_subscription(user_id)
    user = db.get_user(user_id)

    if not sub:
        await callback.answer("No active subscription found.", show_alert=True)
        return

    uname = f"@{user['username']}" if user and user.get("username") else f"ID {user_id}"
    fname = user.get("full_name", "User") if user else "User"

    # Expire subscription in DB
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE subscriptions SET status='expired' WHERE user_id=? AND status='active'",
            (user_id,)
        )

    # Remove from group
    try:
        await bot.ban_chat_member(GROUP_ID, user_id)
        await bot.unban_chat_member(GROUP_ID, user_id)
    except Exception as e:
        pass

    # Notify member
    try:
        await bot.send_message(
            user_id,
            f"🚫 <b>You have been removed by Admin</b>\n\n"
            f"Your subscription has been ended by the admin.\n\n"
            f"If you believe this is a mistake, please contact support.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        f"✅ *Member Removed Successfully*\n\n"
        f"👤 *{fname}* ( {uname} )\n"
        f"📦 {sub['package_name']}\n\n"
        f"Subscription expired and removed from group.",
        parse_mode="Markdown",
        reply_markup=active_members_actions_kb()
    )
    await callback.answer("✅ Member removed.")

# ── Stats ──────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    subs    = db.get_all_active_subscriptions()
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
        "⏰ *Schedule an Alert*\n\nStep 1/5: Enter a *title* for this alert:",
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
    await message.answer("Step 2/5: Enter the *message* to send to all members:", parse_mode="Markdown")

@router.message(AlertStates.message)
async def alert_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(message=message.text)
    await state.set_state(AlertStates.send_date)
    await message.answer(
        "Step 3/5: Enter *date and time* to send (format: `DD-MM-YYYY HH:MM`)\nExample: `25-12-2024 09:00`",
        parse_mode="Markdown"
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
            "Step 4/5: How many times should this alert be sent? (e.g. `1`, `2`, `3`)",
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer("❌ Invalid format. Use `DD-MM-YYYY HH:MM`", parse_mode="Markdown")

@router.message(AlertStates.repeat_times)
async def alert_repeat(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        n = int(message.text.strip())
        await state.update_data(repeat_times=n)
        if n > 1:
            await state.set_state(AlertStates.interval)
            await message.answer("Step 5/5: How many hours between each alert? (e.g. `24`)")
        else:
            data = await state.get_data()
            db.create_alert(data["title"], data["message"], data["send_at"], 1, 24)
            await state.clear()
            await message.answer(
                f"✅ *Alert Scheduled!*\n\n📌 {data['title']}\n📅 {data['send_at'][:16]}\n🔁 1 time",
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
        data  = await state.get_data()
        db.create_alert(data["title"], data["message"], data["send_at"], data["repeat_times"], hours)
        await state.clear()
        await message.answer(
            f"✅ *Alert Scheduled!*\n\n📌 {data['title']}\n📅 {data['send_at'][:16]}\n🔁 {data['repeat_times']}x every {hours}h",
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
        icon = "✅" if a["status"] == "done" else "⏳"
        lines.append(
            f"{icon} *{a['title']}*\n"
            f"  Msg: {a['message'][:40]}...\n"
            f"  Next: {a['send_at'][:16]} | Sent: {a['sent_count']}/{a['repeat_times']}\n"
        )

    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=back_admin_kb())
    await callback.answer()

# ── Manual activate ────────────────────────────────────────
@router.message(Command("activate"))
async def manual_activate(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("Usage: /activate <user_id> <pkg_id> <days>")
        return
    try:
        uid, pkg_id, days = int(parts[1]), int(parts[2]), int(parts[3])
        pkg    = get_pkg(pkg_id)
        sub_id = db.create_subscription(uid, pkg_id, pkg["name"] if pkg else f"Package {pkg_id}")
        db.activate_subscription(sub_id, days)
        await message.answer(f"✅ Activated subscription for user {uid} ({days} days)")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

# ── Transfer Admin ──────────────────────────────────────────
@router.callback_query(F.data == "admin_transfer")
async def admin_transfer_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(TransferStates.waiting_new_admin)
    current_id = db.get_admin_id()
    await callback.message.edit_text(
        f"🔄 *Transfer Admin Access*\n\n"
        f"📌 *Current Admin ID:* `{current_id}`\n\n"
        f"To transfer admin rights, send the new admin's details in this format:\n\n"
        f"`@username 123456789`\n\n"
        f"_(username and Chat ID, separated by a space)_\n\n"
        f"⚠️ You will *lose admin access* after confirming the transfer.",
        parse_mode="Markdown",
        reply_markup=back_admin_kb()
    )
    await callback.answer()

@router.message(TransferStates.waiting_new_admin)
async def admin_transfer_receive(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()
    new_username = None
    new_id       = None

    for part in parts:
        part_clean = part.lstrip("@")
        try:
            new_id = int(part_clean)
        except ValueError:
            new_username = part_clean

    if not new_id:
        await message.answer(
            "❌ *Could not read a valid Chat ID.*\n\n"
            "Please send in this format:\n`@username 123456789`\n\n"
            "The Chat ID must be a number.",
            parse_mode="Markdown",
            reply_markup=back_admin_kb()
        )
        return

    await state.update_data(new_admin_id=new_id, new_username=new_username)

    display = f"@{new_username}" if new_username else f"ID `{new_id}`"
    await message.answer(
        f"🔄 *Confirm Admin Transfer*\n\n"
        f"👤 *New Admin:* {display}\n"
        f"🆔 *Chat ID:* `{new_id}`\n\n"
        f"⚠️ After transfer:\n"
        f"• They will receive full admin access\n"
        f"• *You will no longer be admin*\n\n"
        f"Are you sure you want to proceed?",
        parse_mode="Markdown",
        reply_markup=transfer_confirm_kb(new_id)
    )

@router.callback_query(F.data.startswith("transfer_confirm_"))
async def admin_transfer_confirm(callback: CallbackQuery, state: FSMContext, bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("You are no longer the admin.", show_alert=True)
        return

    new_admin_id  = int(callback.data.split("_")[2])
    old_admin_id  = db.get_admin_id()
    data          = await state.get_data()
    new_username  = data.get("new_username")
    display       = f"@{new_username}" if new_username else f"ID {new_admin_id}"

    await state.clear()

    # Execute the transfer
    from datetime import datetime as dt
    db.set_admin_id(new_admin_id)

    # Update the message for old admin
    await callback.message.edit_text(
        f"✅ *Admin Transfer Complete*\n\n"
        f"👤 New Admin: *{display}*\n"
        f"🆔 Chat ID: `{new_admin_id}`\n"
        f"🕐 Time: {dt.now().strftime('%d %b %Y %H:%M')}\n\n"
        f"You have *relinquished admin access*.",
        parse_mode="Markdown"
    )
    await callback.answer("✅ Transfer complete.")

    # Notify new admin
    try:
        await bot.send_message(
            new_admin_id,
            f"🎉 *You are now the Bot Admin!*\n\n"
            f"Admin access has been transferred to you by the previous admin.\n\n"
            f"Use /admin to open your admin panel.",
            parse_mode="Markdown"
        )
    except Exception as e:
        try:
            await bot.send_message(
                old_admin_id,
                f"⚠️ *Could not notify new admin ({new_admin_id}):*\n`{e}`\n\n"
                f"Make sure they have started the bot first.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

# ── CLOSE ADMIN PANEL — wipe entire admin chat history ─────
@router.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery, state: FSMContext, bot):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.answer("🧹 Closing admin panel…")

    admin_id = db.get_admin_id()
    ids = pop_admin_msgs()
    # Also include the current callback message itself
    try:
        ids.append(callback.message.message_id)
    except Exception:
        pass

    # Deduplicate while preserving order
    seen = set()
    unique_ids = []
    for mid in ids:
        if mid not in seen:
            seen.add(mid)
            unique_ids.append(mid)

    for mid in unique_ids:
        try:
            await bot.delete_message(admin_id, mid)
        except Exception:
            # Already deleted, too old (>48h), or not deletable — ignore
            pass
