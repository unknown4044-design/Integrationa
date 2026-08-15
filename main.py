"""
main.py -- Bot yahan se start hota hai. Render Web Service ke liye webhook mode.

ENV chahiye: BOT_TOKEN, ADMIN_IDS, MONGO_URI, WEBHOOK_SECRET
(WEBHOOK_URL Render khud RENDER_EXTERNAL_URL se de deta hai)
"""

import logging
import os

from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ChatMemberHandler, filters

import db
import utils
import user_flow
import admin_panel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "webhook")
WEBHOOK_BASE = os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL", "")


async def cmd_start(update: Update, context):
    await user_flow.cmd_start(update, context)


async def callback_router(update: Update, context):
    q = update.callback_query
    data = q.data or ""

    if data == "back:courses":
        await user_flow.show_courses(update, context)
    elif data.startswith("course:"):
        await user_flow.show_items(update, context, data.split(":", 1)[1])
    elif data.startswith("item:"):
        await user_flow.show_item_detail(update, context, data.split(":", 1)[1])
    elif data.startswith("buy:"):
        await user_flow.start_purchase(update, context, data.split(":", 1)[1])
    elif data.startswith("accept:"):
        await admin_panel.review_accept(update, context, data.split(":", 1)[1])
    elif data.startswith("reject:"):
        await admin_panel.review_reject(update, context, data.split(":", 1)[1])
    elif data.startswith("grp:"):
        _, order_id, group_id = data.split(":")
        await admin_panel.review_group_selected(update, context, order_id, group_id)
    elif data.startswith("adm:"):
        await admin_panel.admin_callback(update, context, data.split(":", 1)[1])
    else:
        await q.answer()


async def text_router(update: Update, context):
    consumed = await admin_panel.handle_admin_text(update, context)
    if not consumed:
        return  # buyer se free text expected nahi hai, chup chaap ignore


async def media_router(update: Update, context):
    consumed = await admin_panel.handle_admin_media(update, context)
    if consumed:
        return
    if update.message.photo:
        await user_flow.on_screenshot_received(update, context)


async def on_bot_chat_membership_changed(update: Update, context):
    """Bot ko kisi group/channel me Admin/Member banate hi ya hataate hi, group list
    khud-ba-khud update ho jaati hai -- manual forward karne ki zarurat nahi."""
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    joined = old_status in ("left", "kicked") and new_status in ("member", "administrator")
    left = old_status in ("member", "administrator") and new_status in ("left", "kicked")

    if joined:
        existing = db.get_group_by_chat_id(chat.id)
        if not existing:
            db.add_group(chat.title or str(chat.id), chat.id)
            for admin_id in utils.ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"✅ Naya group/channel add ho gaya:\n<b>{chat.title}</b>\n"
                        f"Yeh ab Manage Groups me dikhega aur order-accept ke waqt select kar sakte ho.\n\n"
                        f"⚠️ Invite-link banane ke liye bot ko yahan <b>Admin</b> rakho (invite permission ke saath).",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass
    elif left:
        existing = db.get_group_by_chat_id(chat.id)
        if existing:
            db.delete_group(str(existing["_id"]))
            for admin_id in utils.ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id, f"⚠️ Bot ko <b>{chat.title}</b> se hata diya gaya, group list se bhi hata diya gaya hai.",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass


async def post_init(application: Application):
    db.init_db()
    await application.bot.set_my_commands(
        [BotCommand("start", "Courses dekho / shuru karo")], scope=BotCommandScopeDefault()
    )
    for admin_id in utils.ADMIN_IDS:
        try:
            await application.bot.set_my_commands(
                [
                    BotCommand("start", "Courses dekho"),
                    BotCommand("admin", "Admin Panel kholo"),
                ],
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception:
            pass
    log.info("Bot ready.")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", admin_panel.cmd_admin))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(ChatMemberHandler(on_bot_chat_membership_changed, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, media_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    if WEBHOOK_BASE:
        url_path = WEBHOOK_SECRET
        webhook_url = f"{WEBHOOK_BASE.rstrip('/')}/{url_path}"
        log.info(f"Starting webhook on port {PORT} -> {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=url_path,
            webhook_url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        log.warning("WEBHOOK_URL/RENDER_EXTERNAL_URL set nahi hai — polling mode me chal raha hai.")
        app.run_polling()


if __name__ == "__main__":
    main()
