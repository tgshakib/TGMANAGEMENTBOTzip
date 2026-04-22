from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from datetime import datetime

import database as db
from config import PACKAGES, SUPPORT_USERNAME
from keyboards import main_menu_kb, packages_kb, proceed_payment_kb

router = Router()

def get_pkg(pkg_id: int):
    return next((p for p in PACKAGES if p["id"] == pkg_id), None)

# ── /start ─────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    db.upsert_user(user.id, user.username, user.full_name)

    sub = db.get_active_subscription(user.id)
    if sub:
        end = datetime.fromisoformat(sub["end_date"])
        days_left = (end - datetime.now()).days
        status_text = (
            f"✅ *Active Subscription*\n"
            f"📦 Package: {sub['package_name']}\n"
            f"📅 Expires: {end.strftime('%d %b %Y')}\n"
            f"⏳ Days left: *{days_left}*"
        )
    else:
        status_text = "❌ You have no active subscription."

    await message.answer(
        f"👋 Welcome, *{user.first_name}*!\n\n"
        f"{status_text}\n\n"
        f"Use the buttons below to manage your subscription.",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

# ── Show packages ──────────────────────────────────────────
@router.callback_query(F.data == "show_packages")
@router.callback_query(F.data == "renew")
async def show_packages(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 *Choose a Subscription Package:*\n\n"
        "Select the plan that works best for you 👇",
        parse_mode="Markdown",
        reply_markup=packages_kb()
    )
    await callback.answer()

# ── Package selected ───────────────────────────────────────
@router.callback_query(F.data.startswith("pkg_"))
async def package_selected(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg = get_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    await state.update_data(selected_pkg_id=pkg_id)

    await callback.message.edit_text(
        f"✅ *You selected:*\n\n"
        f"{pkg['name']}\n"
        f"💰 Price: *৳{pkg['price']}*\n"
        f"⏱ Duration: *{pkg['description']}*\n\n"
        f"Click below to proceed to payment.",
        parse_mode="Markdown",
        reply_markup=proceed_payment_kb(pkg_id)
    )
    await callback.answer()

# ── My subscription ────────────────────────────────────────
@router.callback_query(F.data == "my_sub")
async def my_subscription(callback: CallbackQuery):
    sub = db.get_active_subscription(callback.from_user.id)
    if sub:
        end = datetime.fromisoformat(sub["end_date"])
        start = datetime.fromisoformat(sub["start_date"])
        days_left = max(0, (end - datetime.now()).days)
        text = (
            f"📊 *Your Subscription Details*\n\n"
            f"📦 Package: *{sub['package_name']}*\n"
            f"📅 Started: {start.strftime('%d %b %Y')}\n"
            f"📅 Expires: *{end.strftime('%d %b %Y')}*\n"
            f"⏳ Days Remaining: *{days_left} days*\n\n"
            f"{'🟢 Status: Active' if days_left > 0 else '🔴 Status: Expiring today!'}"
        )
    else:
        text = (
            "❌ *No Active Subscription*\n\n"
            "You don't have an active subscription.\n"
            "Choose a package to get started!"
        )

    from keyboards import main_menu_kb
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb())
    await callback.answer()

# ── Back to main ───────────────────────────────────────────
@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    sub = db.get_active_subscription(user.id)

    if sub:
        end = datetime.fromisoformat(sub["end_date"])
        days_left = (end - datetime.now()).days
        status_text = (
            f"✅ *Active Subscription*\n"
            f"📦 Package: {sub['package_name']}\n"
            f"⏳ Days left: *{days_left}*"
        )
    else:
        status_text = "❌ You have no active subscription."

    await callback.message.edit_text(
        f"🏠 *Main Menu*\n\n{status_text}",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )
    await callback.answer()
