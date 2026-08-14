
# Modified user_flow.py (safe upgrade)

from telegram import Update
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

    settings = db.get_settings()

    if settings.get("welcome_media_file_id"):
        if settings.get("welcome_media_type") == "photo":
            await update.message.reply_photo(
                settings["welcome_media_file_id"],
                caption=settings.get("welcome_caption"),
                reply_markup=markup,
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_video(
                settings["welcome_media_file_id"],
                caption=settings.get("welcome_caption"),
                reply_markup=markup,
                parse_mode=ParseMode.HTML
            )
    else:
        await update.message.reply_text(
            settings.get("welcome_caption"),
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )


async def show_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    markup = kb.courses_kb()
    await q.edit_message_text("👋 <b>Courses:</b>", parse_mode=ParseMode.HTML, reply_markup=markup)


async def show_items(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: str):
    q = update.callback_query
    markup = kb.items_kb(course_id)
    await q.edit_message_text("📚 Select batch:", parse_mode=ParseMode.HTML, reply_markup=markup)


async def show_item_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
    q = update.callback_query
    item = db.get_item(item_id)

    caption = (item.get("caption") or item["name"]) + f"\n\n💰 ₹{item['price']}"
    markup = kb.item_detail_kb(item_id, item["course_id"])

    await q.message.delete()

    if item.get("media_file_id"):
        if item.get("media_type") == "photo":
            await context.bot.send_photo(q.message.chat_id, item["media_file_id"], caption=caption, parse_mode=ParseMode.HTML, reply_markup=markup)
        else:
            await context.bot.send_video(q.message.chat_id, item["media_file_id"], caption=caption, parse_mode=ParseMode.HTML, reply_markup=markup)
    else:
        await context.bot.send_message(q.message.chat_id, caption, parse_mode=ParseMode.HTML, reply_markup=markup)


async def start_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
    q = update.callback_query
    user = q.from_user
    item = db.get_item(item_id)

    final_amount = utils.generate_unique_amount(item["price"])

    order_id = db.create_order(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        item_id=item_id,
        item_name=item["name"],
        base_amount=item["price"],
        final_amount=final_amount,
    )

    settings = db.get_settings()

    caption = settings.get("payment_caption") or f"🧾 {item['name']}\n💰 ₹{final_amount}"

    if settings.get("payment_media_file_id"):
        if settings.get("payment_media_type") == "photo":
            await context.bot.send_photo(q.message.chat_id, settings["payment_media_file_id"], caption=caption, parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_video(q.message.chat_id, settings["payment_media_file_id"], caption=caption, parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(q.message.chat_id, caption)


async def on_done_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
    q = update.callback_query
    db.update_order_status(order_id, "awaiting_screenshot")

    context.user_data["awaiting_screenshot_for"] = order_id

    settings = db.get_settings()

    if settings.get("screenshot_media_file_id"):
        if settings.get("screenshot_media_type") == "photo":
            await context.bot.send_photo(q.message.chat_id, settings["screenshot_media_file_id"], caption=settings.get("screenshot_caption"), parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_video(q.message.chat_id, settings["screenshot_media_file_id"], caption=settings.get("screenshot_caption"), parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(q.message.chat_id, db.get_setting("screenshot_prompt"))


async def on_screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("awaiting_screenshot_for")
    if not order_id:
        return

    photo = update.message.photo[-1]
    db.set_order_screenshot(order_id, photo.file_id)

    await update.message.reply_text("Payment sent for verification ✅")
