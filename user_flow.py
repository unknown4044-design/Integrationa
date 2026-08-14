"""
user_flow.py -- Buyer ka poora experience.
Start -> Courses -> Items(Batches) -> Banner+Caption -> Buy Now -> QR -> DONE -> Screenshot -> Admin ko log
Har user ka apna alag context.user_data hota hai (Telegram/PTB isko khud isolate karta hai per chat),
isliye "har user ka panel alag" apne aap ho jaata hai.
"""

from telegram import Update, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import db
import utils
import keyboards as kb


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    markup = kb.courses_kb()
    if not markup:
        await update.message.reply_text("Filhaal koi course available nahi hai. Thodi der baad try karo.")
        return
    await update.message.reply_text(
        "👋 <b>Welcome!</b>\nNeeche diye gaye courses me se select karo:",
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
    )


async def show_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    markup = kb.courses_kb()
    if not markup:
        await q.edit_message_text("Filhaal koi course available nahi hai.")
        return
    await q.edit_message_text("👋 <b>Courses:</b>", parse_mode=ParseMode.HTML, reply_markup=markup)


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

    await q.message.delete()
    if item.get("media_file_id") and item.get("media_type") == "photo":
        await context.bot.send_photo(q.message.chat_id, item["media_file_id"], caption=caption, parse_mode=ParseMode.HTML, reply_markup=markup)
    elif item.get("media_file_id") and item.get("media_type") == "video":
        await context.bot.send_video(q.message.chat_id, item["media_file_id"], caption=caption, parse_mode=ParseMode.HTML, reply_markup=markup)
    else:
        await context.bot.send_message(q.message.chat_id, caption, parse_mode=ParseMode.HTML, reply_markup=markup)


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
    await context.bot.send_photo(
        q.message.chat_id, qr_bytes, caption=caption,
        parse_mode=ParseMode.HTML, reply_markup=kb.done_kb(order_id),
    )


async def on_done_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
    q = update.callback_query
    order = db.get_order(order_id)
    if not order or order["user_id"] != q.from_user.id:
        await q.answer("Invalid request.", show_alert=True)
        return
    if order["status"] != "awaiting_payment":
        await q.answer("Yeh order already process ho chuka hai.", show_alert=True)
        return

    db.update_order_status(order_id, "awaiting_screenshot")
    context.user_data["awaiting_screenshot_for"] = order_id
    await q.answer()
    await q.edit_message_reply_markup(reply_markup=None)
    prompt = db.get_setting("screenshot_prompt", "Payment screenshot bhejo")
    await context.bot.send_message(q.message.chat_id, prompt)


async def on_screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("awaiting_screenshot_for")
    if not order_id:
        return  # yeh photo kisi aur cheez ke liye hai (jaise admin ka banner upload) — us handler ko chalne do
    order = db.get_order(order_id)
    if not order or order["status"] != "awaiting_screenshot":
        return

    photo = update.message.photo[-1]
    db.set_order_screenshot(order_id, photo.file_id)
    context.user_data.pop("awaiting_screenshot_for", None)

    pending_msg = db.get_setting("pending_message", "Aapka payment verify ho raha hai ✅")
    await update.message.reply_text(pending_msg)

    # Admin(s) ko log bhejo
    user = update.effective_user
    caption = (
        f"🆕 <b>New Payment Request</b>\n"
        f"👤 {user.full_name} (@{user.username or '-'}) | ID: <code>{user.id}</code>\n"
        f"📦 Item: {order['item_name']}\n"
        f"💰 Base: ₹{order['base_amount']} → Paid: ₹{order['final_amount']}\n"
        f"🆔 Order: <code>{order_id}</code>\n"
        f"Status: <b>Pending</b>"
    )
    for admin_id in utils.ADMIN_IDS:
        try:
            msg = await context.bot.send_photo(
                admin_id, photo.file_id, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=kb.admin_review_kb(order_id),
            )
            db.append_admin_msg_ref(order_id, msg.chat_id, msg.message_id)
        except Exception:
            pass
