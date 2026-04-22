from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime

import database as db
from config import PACKAGES, SUPPORT_USERNAME, FOREX_VIP_PACKAGES, PACKAGE_TIP_HTML
from keyboards import (
    join_options_kb, paid_menu_kb, refer_join_kb,
    packages_kb, proceed_payment_kb, forex_join_kb, forex_proceed_payment_kb,
    member_start_kb,
)
from user_msg_tracker import pop_all as _pop_user_msgs, add_id as _track_user_msg

router = Router()


async def _wipe_chat(callback: CallbackQuery) -> None:
    """Delete all tracked bot messages in this chat plus the current one."""
    chat_id = callback.message.chat.id
    ids = _pop_user_msgs(chat_id)
    ids.append(callback.message.message_id)
    seen: set[int] = set()
    for mid in ids:
        if mid in seen:
            continue
        seen.add(mid)
        try:
            await callback.bot.delete_message(chat_id, mid)
        except Exception:
            pass

def get_pkg(pkg_id: int):
    return next((p for p in PACKAGES if p["id"] == pkg_id), None)

# ── Start screen text ──────────────────────────────────────
def start_text(first_name: str, sub: dict | None, username: str | None = None) -> str:
    display = f"@{username}" if username else f"*{first_name}*"

    if sub:
        end = datetime.fromisoformat(sub["end_date"])
        days_left = max(0, (end - datetime.now()).days)
        status = (
            f"✅ *Active:* {sub['package_name']}\n"
            f"📅 *Expires:* {end.strftime('%d %b %Y')}  ⏳ *{days_left}d left*"
        )
    else:
        status = "❌ *No active subscription*"

    return (
        f"☪️ *Assalamu Walaikum* {display} 👋\n\n"
        f"{status}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌟 *SVIP JOIN — OPTIONS AVAILABLE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 *PAID JOIN* — MTG / NON-MTG SVIP plans\n"
        f"💹 *FOREX VIP JOIN* — GOLDZILA SVIP plans\n"
        f"🔗 *REFER JOIN* — Join via referral link\n\n"
        f"👇 Choose an option below:"
    )

# ── Package list text (HTML) ───────────────────────────────
def build_packages_text() -> str:
    svip_pkgs  = [p for p in PACKAGES if "SVIP" in p["name"]]
    other_pkgs = [p for p in PACKAGES if "SVIP" not in p["name"]]

    lines = ["💎 <b>Subscription Plans</b>\n"]

    if svip_pkgs:
        lines.append("🏆 <b>MTG Future Signal — SVIP</b>")
        lines.append("━━━━━━━━━━━━━━━━")
        for p in svip_pkgs:
            duration = p["name"].split("·")[-1].strip()
            original = p["price"] * 4
            lines.append(f"  {duration:<12}  <s>${original}</s> ➜  <b>${p['price']}</b>")
        lines.append("")

    if other_pkgs:
        lines.append("📈 <b>NON-MTG Future Signal</b>")
        lines.append("━━━━━━━━━━━━━━━━")
        for p in other_pkgs:
            duration = p["name"].split("·")[-1].strip()
            original = p["price"] * 4
            lines.append(f"  {duration:<12}  <s>${original}</s> ➜  <b>${p['price']}</b>")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━\n",
        "🌐 <b>VIP FUTURE Signal Info</b>",
        "🕐 <b>Timezone:</b> UTC +6:00",
        "📅 <b>Daily Signal Post:</b> 12 PM – 1 PM\n",
        "💡 <b>Different timezone?</b>",
        "Pay an extra <b>$20</b> for <b>custom signals</b> — I'll create a signal list "
        "according to your timezone and send it to your chat every day.",
        "<i>(Please inform admin first, then pay the $20 extra)</i>\n",
        "👇 <b>Tap a plan below to subscribe:</b>",
    ]
    return "\n".join(lines)

# ── FOREX VIP packages text (HTML) ────────────────────────
def build_forex_text() -> str:
    lines = [
        "💹 <b>FOREX VIP JOIN</b>\n",
        "🚀 <b>BOOST YOUR CAPITAL 100x</b>",
        "with our tools and Signals\n",
        "🤑 <b>GOLDZILA SVIP PAID JOIN</b>",
        "<i>(IB change — MOST IF YOUR EXNESS USER)</i>\n",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for p in FOREX_VIP_PACKAGES:
        original = p["price"] * 4
        lines.append(f"  {p['label']:<22}  <s>${original}</s>  ➜  <b>${p['price']}</b>")
    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━\n",
        "💳 <b>Payment methods accepted:</b>",
        "₿ Bitcoin  |  🔷 USDT TRC20  |  💛 Binance Pay\n",
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "♻️ <b>Lifetime Access available with partner link.</b>\n"
        "To get this please contact 👉 Support",
        "\n👇 Select a plan below to pay:",
    ]
    return "\n".join(lines)

def _is_admin(user_id: int) -> bool:
    try:
        return user_id == db.get_admin_id()
    except Exception:
        return False

def _start_keyboard(sub, user_id: int = 0):
    if sub and "FOREX" in sub.get("package_name", ""):
        return member_start_kb(is_forex_sub=True, is_admin=_is_admin(user_id))
    elif sub:
        return member_start_kb(is_forex_sub=False, is_admin=_is_admin(user_id))
    return join_options_kb(is_admin=_is_admin(user_id))

# ── /start ─────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    db.upsert_user(user.id, user.username, user.full_name)
    sub = db.get_active_subscription(user.id)
    await message.answer(
        start_text(user.first_name, sub, user.username),
        parse_mode="Markdown",
        reply_markup=_start_keyboard(sub, user.id)
    )

# ── Back to start ──────────────────────────────────────────
@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    sub  = db.get_active_subscription(user.id)
    await callback.message.edit_text(
        start_text(user.first_name, sub, user.username),
        parse_mode="Markdown",
        reply_markup=_start_keyboard(sub, user.id)
    )
    await callback.answer()

# ── 📋 MANU button (member dashboard) ──────────────────────
@router.callback_query(F.data == "start_refresh")
async def start_refresh(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    sub  = db.get_active_subscription(user.id)
    await _wipe_chat(callback)
    await callback.bot.send_message(
        callback.message.chat.id,
        start_text(user.first_name, sub, user.username),
        parse_mode="Markdown",
        reply_markup=_start_keyboard(sub, user.id),
    )
    await callback.answer()

# ── 🔄 Renew → PAID JOIN ───────────────────────────────────
@router.callback_query(F.data == "renew_paid")
async def renew_paid(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _wipe_chat(callback)
    await callback.bot.send_message(
        callback.message.chat.id,
        "💎 *PAID JOIN*\n\nChoose what you'd like to do below:",
        parse_mode="Markdown",
        reply_markup=paid_menu_kb(),
    )
    await callback.answer()

# ── 🔄 Renew → FOREX VIP JOIN ──────────────────────────────
@router.callback_query(F.data == "renew_forex")
async def renew_forex(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _wipe_chat(callback)
    await callback.bot.send_message(
        callback.message.chat.id,
        build_forex_text(),
        parse_mode="HTML",
        reply_markup=forex_join_kb(),
    )
    await callback.answer()

# ── PAID JOIN ──────────────────────────────────────────────
@router.callback_query(F.data == "paid_join")
async def paid_join(callback: CallbackQuery):
    await callback.message.edit_text(
        "💎 *PAID JOIN*\n\n"
        "Choose what you'd like to do below:",
        parse_mode="Markdown",
        reply_markup=paid_menu_kb()
    )
    await callback.answer()

# ── Back to paid menu ──────────────────────────────────────
@router.callback_query(F.data == "back_paid")
async def back_paid(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "💎 *PAID JOIN*\n\n"
        "Choose what you'd like to do below:",
        parse_mode="Markdown",
        reply_markup=paid_menu_kb()
    )
    await callback.answer()

# ── FOREX VIP JOIN ─────────────────────────────────────────
@router.callback_query(F.data == "forex_join")
async def forex_join(callback: CallbackQuery):
    await callback.message.edit_text(
        build_forex_text(),
        parse_mode="HTML",
        reply_markup=forex_join_kb()
    )
    await callback.answer()

# ── REFER JOIN ─────────────────────────────────────────────
@router.callback_query(F.data == "refer_join")
async def refer_join(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔗 *REFER JOIN*\n\n"
        "To join via referral, contact our admin directly:\n\n"
        "👤 *@OAWHIDSHAKIB*\n\n"
        "Send a DM and mention you want to join via referral.",
        parse_mode="Markdown",
        reply_markup=refer_join_kb()
    )
    await callback.answer()

# ── Show packages ──────────────────────────────────────────
@router.callback_query(F.data == "show_packages")
@router.callback_query(F.data == "renew")
async def show_packages(callback: CallbackQuery):
    await callback.message.edit_text(
        build_packages_text(),
        parse_mode="HTML",
        reply_markup=packages_kb()
    )
    await callback.answer()

# ── Package selected ───────────────────────────────────────
@router.callback_query(F.data.startswith("pkg_"))
async def package_selected(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg    = get_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    await state.update_data(selected_pkg_id=pkg_id)
    original = pkg["price"] * 4

    text = (
        f"✅ <b>You selected:</b>\n\n"
        f"📦 {pkg['name']}\n"
        f"💰 Amount: <s>${original}</s>  <b>${pkg['price']}</b>\n"
        f"⏱ Duration: <b>{pkg['description']}</b>\n\n"
        f"Click below to proceed to payment."
    )

    if pkg["days"] < 30:
        text += f"\n\n{PACKAGE_TIP_HTML}"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=proceed_payment_kb(pkg_id)
    )
    await callback.answer()

# ── My subscription ────────────────────────────────────────
@router.callback_query(F.data == "my_sub")
async def my_subscription(callback: CallbackQuery):
    sub = db.get_active_subscription(callback.from_user.id)
    if sub:
        end       = datetime.fromisoformat(sub["end_date"])
        start     = datetime.fromisoformat(sub["start_date"])
        days_left = max(0, (end - datetime.now()).days)
        text = (
            f"📊 *Your Subscription*\n\n"
            f"📦 Package: *{sub['package_name']}*\n"
            f"📅 Started: {start.strftime('%d %b %Y')}\n"
            f"📅 Expires: *{end.strftime('%d %b %Y')}*\n"
            f"⏳ Remaining: *{days_left} days*\n\n"
            f"{'🟢 Status: Active' if days_left > 0 else '🔴 Status: Expiring today!'}"
        )
    else:
        text = (
            "❌ *No Active Subscription*\n\n"
            "You don't have an active subscription.\n"
            "Choose a package to get started! 👇"
        )

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=paid_menu_kb())
    await callback.answer()

# ── No-op (section header buttons) ─────────────────────────
@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
