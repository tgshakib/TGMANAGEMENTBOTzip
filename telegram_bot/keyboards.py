from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import PACKAGES, SUPPORT_USERNAME

# ── Main Menu ──────────────────────────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Packages", callback_data="show_packages"),
            InlineKeyboardButton(text="🔄 Renew", callback_data="renew"),
        ],
        [
            InlineKeyboardButton(text="📊 My Subscription", callback_data="my_sub"),
            InlineKeyboardButton(text="💬 Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton(text="💳 Pay Now", callback_data="pay_now"),
        ]
    ])

# ── Package Selection ──────────────────────────────────────
def packages_kb() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in PACKAGES:
        buttons.append([
            InlineKeyboardButton(
                text=f"{pkg['name']}  —  ৳{pkg['price']} / {pkg['description']}",
                callback_data=f"pkg_{pkg['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ── After package selected ─────────────────────────────────
def proceed_payment_kb(pkg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Proceed to Payment", callback_data=f"pay_{pkg_id}")],
        [InlineKeyboardButton(text="⬅️ Back to Packages", callback_data="show_packages")],
    ])

# ── Payment screenshot ─────────────────────────────────────
def send_screenshot_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Send Screenshot", callback_data="send_screenshot")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="back_main")],
    ])

# ── Admin: approve/reject ──────────────────────────────────
def admin_payment_kb(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton(text="❌ Reject",  callback_data=f"reject_{payment_id}"),
        ]
    ])

# ── Admin main panel ───────────────────────────────────────
def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Pending Payments", callback_data="admin_pending"),
            InlineKeyboardButton(text="👥 Active Members",   callback_data="admin_members"),
        ],
        [
            InlineKeyboardButton(text="⏰ Schedule Alert",   callback_data="admin_schedule"),
            InlineKeyboardButton(text="📢 View Alerts",      callback_data="admin_alerts"),
        ],
        [
            InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
        ]
    ])

# ── Cancel ─────────────────────────────────────────────────
def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="back_main")]
    ])

def back_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel")]
    ])
