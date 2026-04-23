import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import (
    PACKAGES, FOREX_VIP_PACKAGES, PAYMENT_INSTRUCTIONS, FOREX_PAYMENT_INSTRUCTIONS, ADMIN_ID,
    PAID_OFFER_TIER3, PAID_OFFER_TIER6, FOREX_OFFER_TIER3, FOREX_OFFER_TIER6,
)
from keyboards import (
    payment_instructions_kb, cancel_only_kb, paid_menu_kb,
    forex_join_kb, forex_proceed_payment_kb, forex_payment_instructions_kb, forex_cancel_kb,
    paid_offer_proceed_kb, paid_offer_payment_instructions_kb, paid_offer_cancel_kb,
    forex_offer_proceed_kb, forex_offer_payment_instructions_kb, forex_offer_cancel_kb,
)

router = Router()

class PaymentStates(StatesGroup):
    waiting_screenshot  = State()
    waiting_broker_name = State()

class ForexPaymentStates(StatesGroup):
    waiting_screenshot  = State()
    waiting_broker_name = State()

def get_pkg(pkg_id: int):
    return next((p for p in PACKAGES if p["id"] == pkg_id), None)

def get_forex_pkg(pkg_id: int):
    return next((p for p in FOREX_VIP_PACKAGES if p["id"] == pkg_id), None)

# ── Pay Now (from paid menu) ───────────────────────────────
@router.callback_query(F.data == "pay_now")
async def pay_now_redirect(callback: CallbackQuery):
    from keyboards import packages_kb
    await callback.message.edit_text(
        "📦 *First, select a package to pay for:*",
        parse_mode="Markdown",
        reply_markup=packages_kb()
    )
    await callback.answer()

# ── Proceed to payment after package selected ──────────────
@router.callback_query(F.data.startswith("pay_"))
async def proceed_payment(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg = get_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    # Do NOT create the payment row yet — only when user clicks "Check my Screenshot"
    await state.update_data(pkg_id=pkg_id)

    await callback.message.edit_text(
        f"💳 *Payment Instructions*\n\n"
        f"📦 Package: *{pkg['name']}*\n"
        f"💰 Amount: *${pkg['price']}*\n\n"
        f"{PAYMENT_INSTRUCTIONS}",
        parse_mode="Markdown",
        reply_markup=payment_instructions_kb()
    )
    await callback.answer()

# ── CHECK MY SCREENSHOT button ─────────────────────────────
@router.callback_query(F.data == "check_screenshot")
async def check_screenshot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pkg_id = data.get("pkg_id")
    pkg = get_pkg(pkg_id) if pkg_id else None
    if not pkg:
        await callback.answer("Session expired. Please start again.", show_alert=True)
        return

    # Create the pending payment row NOW so it appears in admin's pending review
    payment_id = db.create_payment(
        callback.from_user.id, pkg["id"], pkg["name"], pkg["price"]
    )
    await state.update_data(payment_id=payment_id)
    await state.set_state(PaymentStates.waiting_screenshot)

    await callback.message.edit_text(
        "📸 *Please send your payment screenshot now.*\n\n"
        "Take a screenshot of your completed payment and send it here as a photo.",
        parse_mode="Markdown",
        reply_markup=cancel_only_kb()
    )
    await callback.answer()

# ── Receive screenshot photo → ask for broker name ─────────
@router.message(PaymentStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get("payment_id")

    if not payment_id:
        await message.answer("❌ Session expired. Please start again.", reply_markup=paid_menu_kb())
        await state.clear()
        return

    file_id = message.photo[-1].file_id
    db.attach_screenshot(payment_id, file_id)

    await state.update_data(file_id=file_id)
    await state.set_state(PaymentStates.waiting_broker_name)
    # Note: payment is now visible in admin "Pending Payment Review" with screenshot.

    await message.answer(
        "✅ *Screenshot received!*\n\n"
        "📝 Now please type your *broker's name* and send it:",
        parse_mode="Markdown",
        reply_markup=cancel_only_kb()
    )

# ── Receive broker name → finalize submission ──────────────
@router.message(PaymentStates.waiting_broker_name, F.text)
async def receive_broker_name(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    payment_id  = data.get("payment_id")
    pkg_id      = data.get("pkg_id")
    file_id     = data.get("file_id")
    broker_name = message.text.strip()

    if not payment_id:
        await message.answer("❌ Session expired. Please start again.", reply_markup=paid_menu_kb())
        await state.clear()
        return

    pkg  = get_pkg(pkg_id)
    user = message.from_user
    db.attach_broker_name(payment_id, broker_name)
    await state.clear()

    # ── Pending animation ──────────────────────────────────
    pending = await message.answer("⏳ *Submitting your payment...*", parse_mode="Markdown")
    await asyncio.sleep(2)
    await pending.edit_text(
        "🔄 *Payment Under Review*\n\n"
        "✅ Your screenshot and broker name have been received.\n"
        "Our team will review and approve it shortly.\n\n"
        "⏱ Usually takes 5–30 minutes during working hours.\n"
        "You will be notified once approved.",
        parse_mode="Markdown",
        reply_markup=paid_menu_kb()
    )

    # ── Notify admin ───────────────────────────────────────
    from keyboards import admin_payment_kb
    caption = (
        f"💳 *New Payment Request*\n\n"
        f"👤 User: {user.full_name} (@{user.username or 'N/A'})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📦 Package: *{pkg['name'] if pkg else 'Unknown'}*\n"
        f"💰 Amount: ${pkg['price'] if pkg else '?'}\n"
        f"🏦 Broker: *{broker_name}*\n\n"
        f"Choose an action below:"
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
        "Make sure to send it as a photo, not as a file.",
        parse_mode="Markdown",
        reply_markup=cancel_only_kb()
    )

# ── Non-text sent when broker name expected ────────────────
@router.message(PaymentStates.waiting_broker_name)
async def wrong_broker_input(message: Message):
    await message.answer(
        "📝 Please *type and send your broker's name* as a text message.",
        parse_mode="Markdown",
        reply_markup=cancel_only_kb()
    )

# ════════════════════════════════════════════════════════════
#  FOREX VIP PAYMENT FLOW
# ════════════════════════════════════════════════════════════

# ── Forex package selected ─────────────────────────────────
@router.callback_query(F.data.startswith("fpkg_"))
async def forex_package_selected(callback: CallbackQuery):
    pkg_id = int(callback.data.split("_")[1])
    pkg = get_forex_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    original = pkg["price"] * 4
    await callback.message.edit_text(
        f"💹 <b>FOREX VIP — Package Selected</b>\n\n"
        f"📦 {pkg['name']}\n"
        f"💰 Amount: <s>${original}</s>  <b>${pkg['price']}</b>\n"
        f"⏱ Duration: <b>{pkg['label']}</b>\n\n"
        f"Tap below to proceed to payment.",
        parse_mode="HTML",
        reply_markup=forex_proceed_payment_kb(pkg_id)
    )
    await callback.answer()

# ── Forex proceed to payment ───────────────────────────────
@router.callback_query(F.data.startswith("fpay_"))
async def forex_proceed_payment(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg = get_forex_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    # Do NOT create payment row yet — only on "Check my Screenshot"
    await state.update_data(forex_pkg_id=pkg_id)

    await callback.message.edit_text(
        f"💳 *FOREX VIP — Payment Instructions*\n\n"
        f"📦 Package: *{pkg['name']}*\n"
        f"💰 Amount: *${pkg['price']}*\n\n"
        f"{FOREX_PAYMENT_INSTRUCTIONS}",
        parse_mode="Markdown",
        reply_markup=forex_payment_instructions_kb()
    )
    await callback.answer()

# ── Forex: CHECK MY SCREENSHOT button ─────────────────────
@router.callback_query(F.data == "forex_check_screenshot")
async def forex_check_screenshot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pkg_id = data.get("forex_pkg_id")
    pkg = get_forex_pkg(pkg_id) if pkg_id else None
    if not pkg:
        await callback.answer("Session expired. Please start again.", show_alert=True)
        return

    payment_id = db.create_payment(
        callback.from_user.id, pkg["id"], pkg["name"], pkg["price"]
    )
    await state.update_data(forex_payment_id=payment_id)
    await state.set_state(ForexPaymentStates.waiting_screenshot)

    await callback.message.edit_text(
        "📸 *Please send your FOREX payment screenshot now.*\n\n"
        "Take a screenshot of your completed payment and send it here as a photo.",
        parse_mode="Markdown",
        reply_markup=forex_cancel_kb()
    )
    await callback.answer()

# ── Forex: receive screenshot → ask broker name ────────────
@router.message(ForexPaymentStates.waiting_screenshot, F.photo)
async def forex_receive_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get("forex_payment_id")

    if not payment_id:
        await message.answer("❌ Session expired. Please start again.")
        await state.clear()
        return

    file_id = message.photo[-1].file_id
    db.attach_screenshot(payment_id, file_id)
    await state.update_data(forex_file_id=file_id)
    await state.set_state(ForexPaymentStates.waiting_broker_name)

    await message.answer(
        "✅ *Screenshot received!*\n\n"
        "📝 Now please type your *broker's name* and send it:",
        parse_mode="Markdown",
        reply_markup=forex_cancel_kb()
    )

# ── Forex: receive broker name → finalize ─────────────────
@router.message(ForexPaymentStates.waiting_broker_name, F.text)
async def forex_receive_broker_name(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    payment_id  = data.get("forex_payment_id")
    pkg_id      = data.get("forex_pkg_id")
    file_id     = data.get("forex_file_id")
    broker_name = message.text.strip()

    if not payment_id:
        await message.answer("❌ Session expired. Please start again.")
        await state.clear()
        return

    pkg  = get_forex_pkg(pkg_id)
    user = message.from_user
    db.attach_broker_name(payment_id, broker_name)
    await state.clear()

    pending = await message.answer("⏳ *Submitting your FOREX VIP payment...*", parse_mode="Markdown")
    await asyncio.sleep(2)
    await pending.edit_text(
        "🔄 *FOREX VIP Payment Under Review*\n\n"
        "✅ Your screenshot and broker name have been received.\n"
        "Our team will review and approve it shortly.\n\n"
        "⏱ Usually takes 5–30 minutes during working hours.\n"
        "You will be notified once approved.",
        parse_mode="Markdown",
    )

    from keyboards import admin_payment_kb
    caption = (
        f"💹 *New FOREX VIP Payment*\n\n"
        f"👤 User: {user.full_name} (@{user.username or 'N/A'})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📦 Package: *{pkg['name'] if pkg else 'Unknown'}*\n"
        f"💰 Amount: ${pkg['price'] if pkg else '?'}\n"
        f"🏦 Broker: *{broker_name}*\n\n"
        f"Choose an action below:"
    )
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=admin_payment_kb(payment_id)
    )

# ── Forex: non-photo when screenshot expected ──────────────
@router.message(ForexPaymentStates.waiting_screenshot)
async def forex_wrong_file_type(message: Message):
    await message.answer(
        "📸 Please send a *photo/screenshot* of your FOREX payment.\n"
        "Make sure to send it as a photo, not as a file.",
        parse_mode="Markdown",
        reply_markup=forex_cancel_kb()
    )

# ── Forex: non-text when broker name expected ──────────────
@router.message(ForexPaymentStates.waiting_broker_name)
async def forex_wrong_broker_input(message: Message):
    await message.answer(
        "📝 Please *type and send your broker's name* as a text message.",
        parse_mode="Markdown",
        reply_markup=forex_cancel_kb()
    )


# ════════════════════════════════════════════════════════════
#  MY OFFER — PAID VIP PAYMENT FLOW
# ════════════════════════════════════════════════════════════

class OfferPaymentStates(StatesGroup):
    waiting_screenshot  = State()
    waiting_broker_name = State()

class ForexOfferPaymentStates(StatesGroup):
    waiting_screenshot  = State()
    waiting_broker_name = State()


def _get_paid_offer_pkg(pkg_id: int):
    for p in PAID_OFFER_TIER6 + PAID_OFFER_TIER3:
        if p["id"] == pkg_id:
            return p
    return None


def _get_forex_offer_pkg(pkg_id: int):
    for p in FOREX_OFFER_TIER6 + FOREX_OFFER_TIER3:
        if p["id"] == pkg_id:
            return p
    return None


# ── Paid Offer: package selected ───────────────────────────
@router.callback_query(F.data.startswith("opkg_"))
async def offer_package_selected(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg = _get_paid_offer_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    await state.update_data(offer_pkg_id=pkg_id)
    text = (
        f"✅ <b>You selected (Loyalty Offer):</b>\n\n"
        f"📦 {pkg['name']}\n"
        f"💰 Amount: <b>${pkg['price']}</b>\n"
        f"⏱ Duration: <b>{pkg['description']}</b>\n\n"
        f"Click below to proceed to payment."
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=paid_offer_proceed_kb(pkg_id)
    )
    await callback.answer()


# ── Paid Offer: proceed to payment ─────────────────────────
@router.callback_query(F.data.startswith("opay_"))
async def offer_proceed_payment(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg = _get_paid_offer_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    await state.update_data(offer_pkg_id=pkg_id)
    await callback.message.edit_text(
        f"💳 *Payment Instructions (Loyalty Offer)*\n\n"
        f"📦 Package: *{pkg['name']}*\n"
        f"💰 Amount: *${pkg['price']}*\n\n"
        f"{PAYMENT_INSTRUCTIONS}",
        parse_mode="Markdown",
        reply_markup=paid_offer_payment_instructions_kb()
    )
    await callback.answer()


# ── Paid Offer: CHECK MY SCREENSHOT ────────────────────────
@router.callback_query(F.data == "ocheck_screenshot")
async def offer_check_screenshot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pkg_id = data.get("offer_pkg_id")
    pkg = _get_paid_offer_pkg(pkg_id) if pkg_id else None
    if not pkg:
        await callback.answer("Session expired. Please start again.", show_alert=True)
        return

    payment_id = db.create_payment(
        callback.from_user.id, pkg["id"], pkg["name"], pkg["price"]
    )
    await state.update_data(offer_payment_id=payment_id)
    await state.set_state(OfferPaymentStates.waiting_screenshot)

    await callback.message.edit_text(
        "📸 *Please send your payment screenshot now.*\n\n"
        "Take a screenshot of your completed payment and send it here as a photo.",
        parse_mode="Markdown",
        reply_markup=paid_offer_cancel_kb()
    )
    await callback.answer()


@router.message(OfferPaymentStates.waiting_screenshot, F.photo)
async def offer_receive_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get("offer_payment_id")
    if not payment_id:
        await message.answer("❌ Session expired. Please start again.")
        await state.clear()
        return
    file_id = message.photo[-1].file_id
    db.attach_screenshot(payment_id, file_id)
    await state.update_data(offer_file_id=file_id)
    await state.set_state(OfferPaymentStates.waiting_broker_name)
    await message.answer(
        "✅ *Screenshot received!*\n\n"
        "📝 Now please type your *broker's name* and send it:",
        parse_mode="Markdown",
        reply_markup=paid_offer_cancel_kb()
    )


@router.message(OfferPaymentStates.waiting_broker_name, F.text)
async def offer_receive_broker_name(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    payment_id  = data.get("offer_payment_id")
    pkg_id      = data.get("offer_pkg_id")
    file_id     = data.get("offer_file_id")
    broker_name = message.text.strip()
    if not payment_id:
        await message.answer("❌ Session expired. Please start again.")
        await state.clear()
        return

    pkg  = _get_paid_offer_pkg(pkg_id)
    user = message.from_user
    db.attach_broker_name(payment_id, broker_name)
    await state.clear()

    pending = await message.answer("⏳ *Submitting your loyalty-offer payment...*", parse_mode="Markdown")
    await asyncio.sleep(2)
    await pending.edit_text(
        "🔄 *Payment Under Review*\n\n"
        "✅ Your screenshot and broker name have been received.\n"
        "Our team will review and approve it shortly.\n\n"
        "⏱ Usually takes 5–30 minutes during working hours.\n"
        "You will be notified once approved.",
        parse_mode="Markdown",
    )

    from keyboards import admin_payment_kb
    caption = (
        f"🎁 *New LOYALTY OFFER Payment*\n\n"
        f"👤 User: {user.full_name} (@{user.username or 'N/A'})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📦 Package: *{pkg['name'] if pkg else 'Unknown'}*\n"
        f"💰 Amount: ${pkg['price'] if pkg else '?'}\n"
        f"🏦 Broker: *{broker_name}*\n\n"
        f"Choose an action below:"
    )
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=admin_payment_kb(payment_id)
    )


@router.message(OfferPaymentStates.waiting_screenshot)
async def offer_wrong_file_type(message: Message):
    await message.answer(
        "📸 Please send a *photo/screenshot* of your payment.",
        parse_mode="Markdown",
        reply_markup=paid_offer_cancel_kb()
    )


@router.message(OfferPaymentStates.waiting_broker_name)
async def offer_wrong_broker_input(message: Message):
    await message.answer(
        "📝 Please *type and send your broker's name* as a text message.",
        parse_mode="Markdown",
        reply_markup=paid_offer_cancel_kb()
    )


# ════════════════════════════════════════════════════════════
#  MY OFFER — FOREX VIP PAYMENT FLOW
# ════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("ofpkg_"))
async def forex_offer_package_selected(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg = _get_forex_offer_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    await state.update_data(forex_offer_pkg_id=pkg_id)
    await callback.message.edit_text(
        f"💹 <b>FOREX VIP — Loyalty Offer Selected</b>\n\n"
        f"📦 {pkg['name']}\n"
        f"💰 Amount: <b>${pkg['price']}</b>\n"
        f"⏱ Duration: <b>{pkg['label']}</b>\n\n"
        f"Tap below to proceed to payment.",
        parse_mode="HTML",
        reply_markup=forex_offer_proceed_kb(pkg_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ofpay_"))
async def forex_offer_proceed_payment(callback: CallbackQuery, state: FSMContext):
    pkg_id = int(callback.data.split("_")[1])
    pkg = _get_forex_offer_pkg(pkg_id)
    if not pkg:
        await callback.answer("Package not found!", show_alert=True)
        return

    await state.update_data(forex_offer_pkg_id=pkg_id)
    await callback.message.edit_text(
        f"💳 *FOREX VIP — Payment Instructions (Loyalty Offer)*\n\n"
        f"📦 Package: *{pkg['name']}*\n"
        f"💰 Amount: *${pkg['price']}*\n\n"
        f"{FOREX_PAYMENT_INSTRUCTIONS}",
        parse_mode="Markdown",
        reply_markup=forex_offer_payment_instructions_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "ofcheck_screenshot")
async def forex_offer_check_screenshot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pkg_id = data.get("forex_offer_pkg_id")
    pkg = _get_forex_offer_pkg(pkg_id) if pkg_id else None
    if not pkg:
        await callback.answer("Session expired. Please start again.", show_alert=True)
        return

    payment_id = db.create_payment(
        callback.from_user.id, pkg["id"], pkg["name"], pkg["price"]
    )
    await state.update_data(forex_offer_payment_id=payment_id)
    await state.set_state(ForexOfferPaymentStates.waiting_screenshot)

    await callback.message.edit_text(
        "📸 *Please send your FOREX payment screenshot now.*",
        parse_mode="Markdown",
        reply_markup=forex_offer_cancel_kb()
    )
    await callback.answer()


@router.message(ForexOfferPaymentStates.waiting_screenshot, F.photo)
async def forex_offer_receive_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get("forex_offer_payment_id")
    if not payment_id:
        await message.answer("❌ Session expired. Please start again.")
        await state.clear()
        return
    file_id = message.photo[-1].file_id
    db.attach_screenshot(payment_id, file_id)
    await state.update_data(forex_offer_file_id=file_id)
    await state.set_state(ForexOfferPaymentStates.waiting_broker_name)
    await message.answer(
        "✅ *Screenshot received!*\n\n"
        "📝 Now please type your *broker's name* and send it:",
        parse_mode="Markdown",
        reply_markup=forex_offer_cancel_kb()
    )


@router.message(ForexOfferPaymentStates.waiting_broker_name, F.text)
async def forex_offer_receive_broker_name(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    payment_id  = data.get("forex_offer_payment_id")
    pkg_id      = data.get("forex_offer_pkg_id")
    file_id     = data.get("forex_offer_file_id")
    broker_name = message.text.strip()
    if not payment_id:
        await message.answer("❌ Session expired. Please start again.")
        await state.clear()
        return

    pkg  = _get_forex_offer_pkg(pkg_id)
    user = message.from_user
    db.attach_broker_name(payment_id, broker_name)
    await state.clear()

    pending = await message.answer("⏳ *Submitting your FOREX loyalty-offer payment...*", parse_mode="Markdown")
    await asyncio.sleep(2)
    await pending.edit_text(
        "🔄 *FOREX VIP Payment Under Review*\n\n"
        "✅ Your screenshot and broker name have been received.\n"
        "Our team will review and approve it shortly.\n\n"
        "⏱ Usually takes 5–30 minutes during working hours.\n"
        "You will be notified once approved.",
        parse_mode="Markdown",
    )

    from keyboards import admin_payment_kb
    caption = (
        f"🎁 *New FOREX LOYALTY OFFER Payment*\n\n"
        f"👤 User: {user.full_name} (@{user.username or 'N/A'})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📦 Package: *{pkg['name'] if pkg else 'Unknown'}*\n"
        f"💰 Amount: ${pkg['price'] if pkg else '?'}\n"
        f"🏦 Broker: *{broker_name}*\n\n"
        f"Choose an action below:"
    )
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=admin_payment_kb(payment_id)
    )


@router.message(ForexOfferPaymentStates.waiting_screenshot)
async def forex_offer_wrong_file_type(message: Message):
    await message.answer(
        "📸 Please send a *photo/screenshot* of your payment.",
        parse_mode="Markdown",
        reply_markup=forex_offer_cancel_kb()
    )


@router.message(ForexOfferPaymentStates.waiting_broker_name)
async def forex_offer_wrong_broker_input(message: Message):
    await message.answer(
        "📝 Please *type and send your broker's name* as a text message.",
        parse_mode="Markdown",
        reply_markup=forex_offer_cancel_kb()
    )
