"""
user_flow.py -- Buyer ka poora experience.
Start (banner+caption) -> Courses -> Items(Batches) -> Banner+Caption -> Buy Now
-> QR (5-min window, koi DONE button nahi) -> jab bhi screenshot aaye capture -> Admin ko log

Har user ka apna alag context.user_data hota hai, isliye "har user ka panel alag" apne aap ho jaata hai.
"""

import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import db
import utils
import keyboards as kb
import log

ORDER_TIMEOUT_SECONDS = 300  # 5 minute


async def _send_welcome(chat_id, context: ContextTypes.DEFAULT_TYPE):
    settings = db.get_settings()
    markup = kb.courses_kb()
    if not markup:
        await context.bot.send_message(chat_id, "Filhaal koi course available nahi hai. Thodi der baad try karo.")
        return
    caption = settings.get("welcome_caption") or "👋 <b>Welcome!</b>\nNeeche diye gaye courses me se select karo:"
    media_type = settings.get("welcome_media_type")
    file_id = settings.get("welcome_media_file_id")
    if media_type == "photo" and file_id:
        await utils.safe_send_photo(context.bot, chat_id, file_id, caption, reply_markup=markup)
    elif media_type == "video" and file_id:
        await utils.safe_send_video(context.bot, chat_id, file_id, caption, reply_markup=markup)
    else:
        await utils.safe_send_message(context.bot, chat_id, caption, reply_markup=markup)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user
    await _send_welcome(update.effective_chat.id, context)
    await log.log(context, f"▶️ /start — {user.full_name} (<code>{user.id}</code>)")


async def show_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        await q.message.delete()
    except Exception:
        pass
    await _send_welcome(q.message.chat_id, context)


async def show_items(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: str):
    q = update.callback_query
    course = db.get_course(course_id)
    if not course:
        await q.answer("Yeh course ab available nahi hai.", show_alert=True)
        return
    markup = kb.items_kb(course_id)
    await q.edit_message_text(f"📚 <b>{course['name']}</b>\nNeeche se select karo:", parse_mode=ParseMode.HTML, reply_markup=markup)


async def show_item_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
    q = update.callback_query
    item = db.get_item(item_id)
    if not item:
        await q.answer("Yeh item ab available nahi hai.", show_alert=True)
        return
    caption = (item.get("caption") or f"<b>{item['name']}</b>") + f"\n\n💰 Price: ₹{item['price']}"
    markup = kb.item_detail_kb(item_id, item["course_id"])

    await q.answer()
    try:
        await q.message.delete()
    except Exception:
        pass
    if item.get("media_file_id") and item.get("media_type") == "photo":
        await utils.safe_send_photo(context.bot, q.message.chat_id, item["media_file_id"], caption, reply_markup=markup)
    elif item.get("media_file_id") and item.get("media_type") == "video":
        await utils.safe_send_video(context.bot, q.message.chat_id, item["media_file_id"], caption, reply_markup=markup)
    else:
        await utils.safe_send_message(context.bot, q.message.chat_id, caption, reply_markup=markup)


async def _expire_order_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    order_id = job.data["order_id"]
    order = db.get_order(order_id)
    if not order or order["status"] != "awaiting_payment":
        return  # already screenshot bhej diya ya already processed, kuch nahi karna
    db.update_order_status(order_id, "expired")
    await utils.safe_send_message(
        context.bot, order["user_id"],
        "⏰ <b>Time khatam!</b> Yeh transaction 5 minute me confirm nahi hua isliye close ho gaya.\n"
        "Agar payment kar chuke ho to turant support se contact karo, warna naya order banane ke liye course dubara select karo.",
    )


async def start_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
    q = update.callback_query
    user = q.from_user
    item = db.get_item(item_id)
    if not item:
        await q.answer("Yeh item ab available nahi hai.", show_alert=True)
        return
    if not db.get_setting("upi_id"):
        await q.answer("Payment abhi setup nahi hua, admin se contact karo.", show_alert=True)
        return

    final_amount = utils.generate_unique_amount(item["price"])
    order_id = db.create_order(
        user_id=user.id, username=user.username, full_name=user.full_name,
        item_id=item_id, item_name=item["name"],
        base_amount=item["price"], final_amount=final_amount,
    )

    upi_link = utils.build_upi_link(final_amount, note=f"Order{order_id[-6:]}")
    qr_bytes = utils.generate_qr_bytes(upi_link)

    support = db.get_setting("support_contact", "")
    instructions = db.get_setting("done_instructions", "")
    caption = (
        f"🧾 <b>{item['name']}</b>\n"
        f"💰 Amount to Pay: <b>₹{final_amount}</b>\n\n"
        f"{instructions}\n"
    )
    if support:
        caption += f"\nNeed help? Contact: {support}"

    await q.answer()
    await utils.safe_send_photo(context.bot, q.message.chat_id, qr_bytes, caption)

    if context.job_queue:
        context.job_queue.run_once(
            _expire_order_job, when=ORDER_TIMEOUT_SECONDS,
            data={"order_id": order_id}, name=f"expire_{order_id}",
        )

    await log.log(context, f"🛒 Buy: {user.full_name} (<code>{user.id}</code>) → {item['name']} ₹{final_amount}")


async def on_screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Payment window (5 min) ke andar user jo bhi photo bheje, uski koi bhi photo ise capture
    kar leti hai -- alag se DONE dabane ki zarurat nahi hai."""
    user = update.effective_user
    order = db.find_awaiting_payment_order(user.id)
    if not order:
        return  # koi active awaiting-payment order nahi hai, ignore

    order_id = str(order["_id"])

    if time.time() - order["created_at"] > ORDER_TIMEOUT_SECONDS:
        db.update_order_status(order_id, "expired")
        await update.message.reply_text("⏰ Time khatam ho chuka hai, yeh order expire ho gaya. Dubara Buy Now se try karo.")
        return

    photo = update.message.photo[-1]
    db.set_order_screenshot(order_id, photo.file_id)

    pending_msg = db.get_setting("pending_message", "Aapka payment verify ho raha hai ✅")
    await update.message.reply_text(pending_msg)

    caption = utils.build_order_caption(db.get_order(order_id), status_label="Pending")
    for admin_id in utils.ADMIN_IDS:
        msg = await utils.safe_send_photo(context.bot, admin_id, photo.file_id, caption, reply_markup=kb.admin_review_kb(order_id))
        if msg:
            db.append_admin_msg_ref(order_id, msg.chat_id, msg.message_id)

    await log.log(context, f"📸 Screenshot: {user.full_name} (<code>{user.id}</code>) → order <code>{order_id}</code>")
