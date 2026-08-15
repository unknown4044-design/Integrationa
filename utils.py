"""
utils.py -- Helper functions:
- unique payment amount generate karna (base price + random variation)
- UPI deep-link QR code generate karna (bot khud banata hai, koi manual upload nahi)
"""

import asyncio
import io
import os
import random
import re
import urllib.parse

import qrcode
from telegram.constants import ParseMode

import db

ADMIN_IDS = set(
    int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()
)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def generate_unique_amount(base_price: float) -> float:
    """
    Base price me chhota unique variation add karta hai (configurable range)
    taaki har order ka amount alag ho aur screenshot se easily match ho sake.
    """
    vmin = float(db.get_setting("variation_min", 0.11))
    vmax = float(db.get_setting("variation_max", 0.99))
    variation = round(random.uniform(vmin, vmax), 2)
    return round(base_price + variation, 2)


def build_upi_link(amount: float, note: str) -> str:
    upi_id = db.get_setting("upi_id", "")
    upi_name = db.get_setting("upi_name", "Merchant")
    params = {
        "pa": upi_id,
        "pn": upi_name,
        "am": f"{amount:.2f}",
        "cu": "INR",
        "tn": note,
    }
    return f"upi://pay?{urllib.parse.urlencode(params)}"


def generate_qr_bytes(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    buf.name = "payment_qr.png"
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------------- Safe senders ----------------
# Kabhi kabhi HTML caption me kisi special/premium emoji ya tag ki wajah se
# Telegram error de sakta hai. Yeh wrappers pehle formatted (HTML) try karte hain,
# fail hone par bina formatting ke plain text bhej dete hain -- bot kabhi crash
# nahi hota, message hamesha deliver hota hai.

def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


async def safe_send_message(bot, chat_id, text, **kwargs):
    try:
        return await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, **kwargs)
    except Exception:
        try:
            return await bot.send_message(chat_id, _strip_html(text), **kwargs)
        except Exception:
            return None


async def safe_send_photo(bot, chat_id, photo, caption, **kwargs):
    try:
        return await bot.send_photo(chat_id, photo, caption=caption, parse_mode=ParseMode.HTML, **kwargs)
    except Exception:
        if hasattr(photo, "seek"):
            try:
                photo.seek(0)
            except Exception:
                pass
        try:
            return await bot.send_photo(chat_id, photo, caption=_strip_html(caption), **kwargs)
        except Exception:
            return None


async def safe_send_video(bot, chat_id, video, caption, **kwargs):
    try:
        return await bot.send_video(chat_id, video, caption=caption, parse_mode=ParseMode.HTML, **kwargs)
    except Exception:
        try:
            return await bot.send_video(chat_id, video, caption=_strip_html(caption), **kwargs)
        except Exception:
            return None


def build_order_caption(order, status_label="Pending") -> str:
    return (
        f"🆕 <b>Payment Request</b>\n"
        f"👤 {order.get('full_name', '-')} (@{order.get('username') or '-'}) | ID: <code>{order['user_id']}</code>\n"
        f"📦 Item: {order['item_name']}\n"
        f"💰 Base: ₹{order['base_amount']} → Paid: ₹{order['final_amount']}\n"
        f"🆔 Order: <code>{order['_id']}</code>\n"
        f"Status: <b>{status_label}</b>"
    )


def build_timer_bar(remaining, total, bar_len=8):
    """5-min countdown ke saath dikhne wala shrinking progress bar, e.g. ▰▰▰▰▱▱▱▱ (patla, ek line me)."""
    filled = max(0, min(bar_len, round(bar_len * remaining / total)))
    return "▰" * filled + "▱" * (bar_len - filled)


# ---------------- Fake premium progress bar (cosmetic) ----------------
# Telegram me real progress bar widget nahi hota, isliye ek text bar (████░░░░)
# ko baar-baar edit karke "loading" jaisa animation dikhaya jaata hai.
# Purely visual hai -- QR/link generation ke asli logic ko yeh chhuta nahi.

async def animate_progress(bot, chat_id, label="Loading", steps=5, delay=0.3, bar_len=10):
    try:
        msg = await bot.send_message(chat_id, f"{label}\n[{'░' * bar_len}] 0%")
    except Exception:
        return
    for i in range(1, steps + 1):
        await asyncio.sleep(delay)
        filled = int(bar_len * i / steps)
        bar = "█" * filled + "░" * (bar_len - filled)
        pct = int(100 * i / steps)
        try:
            await bot.edit_message_text(f"{label}\n[{bar}] {pct}%", chat_id=chat_id, message_id=msg.message_id)
        except Exception:
            pass
    try:
        await bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass
