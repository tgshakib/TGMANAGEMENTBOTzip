from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import PACKAGES, PAYMENT_INSTRUCTIONS, ADMIN_ID
from keyboards import cancel_kb, main_menu_kb

router = Router()

class PaymentStates(StatesGroup):
    waiting_screenshot = State()

def get_pkg(pkg_id: int):
    return next((p for p in PACKAGES if p["id"] == pkg_id), None)

# ── Pay Now (from main menu, needs package selected first) ─
@router.callback_query(F.data == "pay_now")
async def pay_now_redirect(callback: CallbackQuery):
    from keyboards import packages_kb
    await callback.message.edit_text(
        "📦 *First, select a package to pay for:*",
        parse_mode="Markdown",
        reply_markup=packages_kb()
    )
    await callback.answer()

# ── Proceed payment after package selected ─────────────────
@router.callback_query(F.data.startswith("pay_"))
async def proceed_payment(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg = get_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    # Create a pending payment record
    payment_id = db.create_payment(
        callback.from_user.id, pkg["id"], pkg["name"], pkg["price"]
    )
    await state.update_data(payment_id=payment_id, pkg_id=pkg_id)
    await state.set_state(PaymentStates.waiting_screenshot)

    await callback.message.edit_text(
        f"💳 *Payment Instructions*\n\n"
        f"📦 Package: *{pkg['name']}*\n"
        f"💰 Amount: *৳{pkg['price']}*\n\n"
        f"{PAYMENT_INSTRUCTIONS}\n\n"
        f"📸 *After payment, please send your payment screenshot here.*",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    await callback.answer()

# ── Receive screenshot ─────────────────────────────────────
@router.message(PaymentStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    payment_id = data.get("payment_id")
    pkg_id = data.get("pkg_id")

    if not payment_id:
        await message.answer("❌ Session expired. Please start again.", reply_markup=main_menu_kb())
        await state.clear()
        return

    pkg = get_pkg(pkg_id)
    file_id = message.photo[-1].file_id
    db.attach_screenshot(payment_id, file_id)

    user = message.from_user
    await state.clear()

    # Confirm to user
    await message.answer(
        "✅ *Screenshot received!*\n\n"
        "Your payment is under review. You'll be notified once approved.\n\n"
        "⏱ Usually takes 5–30 minutes during working hours.",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

    # Forward to admin
    from keyboards import admin_payment_kb
    caption = (
        f"💳 *New Payment Request* #{payment_id}\n\n"
        f"👤 User: {user.full_name} (@{user.username or 'N/A'})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📦 Package: *{pkg['name'] if pkg else 'Unknown'}*\n"
        f"💰 Amount: ৳{pkg['price'] if pkg else '?'}\n\n"
        f"✅ Approve or ❌ Reject below:"
    )
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=admin_payment_kb(payment_id)
    )

# ── Non-photo sent when screenshot expected ────────────────
@router.message(PaymentStates.waiting_screenshot)
async def wrong_file_type(message: Message):
    await message.answer(
        "📸 Please send a *photo/screenshot* of your payment.\n"
        "Make sure to send it as a photo, not a file.",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
