from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import PACKAGES, FOREX_VIP_PACKAGES, SUPPORT_USERNAME

# ── Start / Join Options ───────────────────────────────────
def join_options_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="💎 PAID JOIN",       callback_data="paid_join"),
            InlineKeyboardButton(text="💹 FOREX VIP JOIN",  callback_data="forex_join"),
        ],
        [
            InlineKeyboardButton(text="🎁 MONTHLY JOIN OFFERS", callback_data="monthly_offers"),
        ],
        [
            InlineKeyboardButton(text="🔗 REFER JOIN",      callback_data="refer_join"),
            InlineKeyboardButton(text="🏢 OFFLINE VIP JOIN", url="https://t.me/OAWHIDSHAKIB"),
        ],
        [
            InlineKeyboardButton(text="🤖 SOFTWARE & AI SIGNAL BOT BUY", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"),
        ],
    ]
    if is_admin:
        rows.append([
            InlineKeyboardButton(text="🛡️ ADMINISTRATION ACCESS", callback_data="admin_panel"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ── Paid Join Menu ─────────────────────────────────────────
def paid_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Packages",         callback_data="show_packages"),
            InlineKeyboardButton(text="💬 Support",          url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton(text="💳 Pay Now",          callback_data="pay_now"),
            InlineKeyboardButton(text="📊 My Subscription",  callback_data="my_sub"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back",             callback_data="back_main"),
        ],
    ])

# ── FOREX VIP section ─────────────────────────────────────
def forex_join_kb() -> InlineKeyboardMarkup:
    buttons = []
    for p in FOREX_VIP_PACKAGES:
        buttons.append([InlineKeyboardButton(
            text=f"{p['label']}  ·  ${p['price']}",
            callback_data=f"fpkg_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text="💬 Support",
        url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"
    )])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ── Forex: after package selected ─────────────────────────
def forex_proceed_payment_kb(pkg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Proceed to Payment",    callback_data=f"fpay_{pkg_id}")],
        [InlineKeyboardButton(text="⬅️ Back to Forex Plans",   callback_data="forex_join")],
    ])

# ── Forex: payment instructions screen ────────────────────
def forex_payment_instructions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 CHECK MY SCREENSHOT",   callback_data="forex_check_screenshot")],
        [InlineKeyboardButton(text="💬 Support",                url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="❌ Cancel",                 callback_data="back_main")],
    ])

# ── Forex: cancel only ─────────────────────────────────────
def forex_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="back_main")]
    ])

# ── Refer Join ─────────────────────────────────────────────
def refer_join_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 DM @OAWHIDSHAKIB", url="https://t.me/OAWHIDSHAKIB")],
        [InlineKeyboardButton(text="⬅️ Back",             callback_data="back_main")],
    ])

# ── Package Selection ──────────────────────────────────────
def packages_kb() -> InlineKeyboardMarkup:
    svip_pkgs  = [p for p in PACKAGES if "SVIP" in p["name"]]
    other_pkgs = [p for p in PACKAGES if "SVIP" not in p["name"]]

    buttons = []
    buttons.append([
        InlineKeyboardButton(text="━━━ 🏆 MTG FUTURE SVIP ━━━", callback_data="noop")
    ])
    for i in range(0, len(svip_pkgs), 2):
        row = []
        for pkg in svip_pkgs[i:i+2]:
            duration = pkg["name"].split("·")[-1].strip()
            row.append(InlineKeyboardButton(
                text=f"{duration}  ·  ${pkg['price']}",
                callback_data=f"pkg_{pkg['id']}"
            ))
        buttons.append(row)

    if other_pkgs:
        buttons.append([
            InlineKeyboardButton(text="━━━ 📈 NON-MTG SIGNAL ━━━", callback_data="noop")
        ])
        for i in range(0, len(other_pkgs), 2):
            row = []
            for pkg in other_pkgs[i:i+2]:
                duration = pkg["name"].split("·")[-1].strip()
                row.append(InlineKeyboardButton(
                    text=f"{duration}  ·  ${pkg['price']}",
                    callback_data=f"pkg_{pkg['id']}"
                ))
            buttons.append(row)

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_paid")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ── After package selected ─────────────────────────────────
def proceed_payment_kb(pkg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Proceed to Payment",  callback_data=f"pay_{pkg_id}")],
        [InlineKeyboardButton(text="⬅️ Back to Packages",    callback_data="show_packages")],
    ])

# ── Payment instructions screen ────────────────────────────
def payment_instructions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 CHECK MY SCREENSHOT", callback_data="check_screenshot")],
        [InlineKeyboardButton(text="❌ Cancel",               callback_data="back_paid")],
    ])

# ── Waiting for screenshot photo ──────────────────────────
def cancel_only_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="back_paid")]
    ])

# ── Admin: approve / reject ────────────────────────────────
def admin_payment_kb(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🤲 Alhamdulillah Receive Payment",
            callback_data=f"approve_{payment_id}"
        )],
        [InlineKeyboardButton(text="❌ Rejected", callback_data=f"reject_{payment_id}")],
    ])

# ── Admin main panel ───────────────────────────────────────
def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Pending Payments",  callback_data="admin_pending"),
            InlineKeyboardButton(text="👥 Active Members",    callback_data="admin_members"),
        ],
        [
            InlineKeyboardButton(text="⏰ Schedule Alert",    callback_data="admin_schedule"),
            InlineKeyboardButton(text="📢 View Alerts",       callback_data="admin_alerts"),
        ],
        [
            InlineKeyboardButton(text="📊 Stats",             callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton(text="🔄 Transfer Admin",    callback_data="admin_transfer"),
        ],
        [
            InlineKeyboardButton(text="🧹 CLOSE ADMIN PANEL", callback_data="admin_close"),
        ],
    ])

# ── Active members page actions ────────────────────────────
def active_members_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Ban / Remove Member",  callback_data="admin_ban_list")],
        [InlineKeyboardButton(text="⬅️ Back to Admin Panel",  callback_data="admin_panel")],
    ])

# ── Ban member: list all active members ────────────────────
def ban_member_list_kb(members: list) -> InlineKeyboardMarkup:
    buttons = []
    for m in members:
        uname = f"@{m['username']}" if m.get("username") else m.get("full_name", "Unknown")
        pkg   = m.get("package_name", "")
        buttons.append([InlineKeyboardButton(
            text=f"🚫 {uname} — {pkg}",
            callback_data=f"banrem_{m['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="admin_members")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ── Ban confirm ────────────────────────────────────────────
def ban_confirm_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, Remove Now",  callback_data=f"banyes_{user_id}")],
        [InlineKeyboardButton(text="❌ Cancel",           callback_data="admin_ban_list")],
    ])

# ── Transfer confirm ───────────────────────────────────────
def transfer_confirm_kb(new_admin_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, Transfer Now", callback_data=f"transfer_confirm_{new_admin_id}")],
        [InlineKeyboardButton(text="❌ Cancel",            callback_data="admin_panel")],
    ])

# ── Back to admin panel ────────────────────────────────────
def back_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel")]
    ])

# ── Member dashboard (active sub) — 2 buttons only ────────
def member_start_kb(is_forex_sub: bool = False, is_admin: bool = False) -> InlineKeyboardMarkup:
    renew_data = "renew_forex" if is_forex_sub else "renew_paid"
    rows = [
        [
            InlineKeyboardButton(text="🔄 Renew",  callback_data=renew_data),
            InlineKeyboardButton(text="📋 MANU",   callback_data="start_refresh"),
        ],
    ]
    if is_admin:
        rows.append([
            InlineKeyboardButton(text="🛡️ ADMINISTRATION ACCESS", callback_data="admin_panel"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ── Aliases ────────────────────────────────────────────────
def cancel_kb() -> InlineKeyboardMarkup:
    return cancel_only_kb()

def main_menu_kb() -> InlineKeyboardMarkup:
    return paid_menu_kb()
