"""
utils.py -- Helper functions:
- unique payment amount generate karna (base price + random variation)
- UPI deep-link QR code generate karna (bot khud banata hai, koi manual upload nahi)
"""

import io
import os
import random
import urllib.parse

import qrcode

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
