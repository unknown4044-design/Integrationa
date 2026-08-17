"""
main.py -- Multi-bot entry point.

Ek hi Render service par MULTIPLE Telegram bots chalte hain:
- MASTER bot (BOT_TOKEN env se) -- sirf /admin panel, buyer-flow band.
- CLONE bots (MongoDB "clones" collection se, Master ke "Manage Clone Bots" se add hote hain)
  -- sirf buyer-flow (courses/payment), /admin bilkul kaam nahi karta.

Sab bots SAME MongoDB (courses/items/groups/settings) share karte hain, isliye
Master me jo bhi set karo woh turant har clone me "as-it-is" dikhta hai.

Ek hi aiohttp web-server sabke webhooks handle karta hai (path = token ka hash),
isliye clone add/remove karte waqt Render redeploy karne ki zarurat nahi padti.
"""

import logging
import os

from aiohttp import web
from telegram import BotCommand, BotCommandScopeChat, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ChatMemberHandler, filters

import db
import utils
import user_flow
import admin_panel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]  # Master bot -- tumhara existing bot token
PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "webhook")
WEBHOOK_BASE = (os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL", "")).rstrip("/")

applications: dict[str, Application] = {}  # path_id -> Application


# ---------------- Shared handlers ----------------

async def cmd_start(update: Update, context):
    if context.bot_data.get("is_master"):
        if not utils.is_admin(update.effective_user.id):
            return  # Master bot -- sirf admin ko response, baaki sabko silence
        await admin_panel.cmd_admin(update, context)
        return
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
    await admin_panel.handle_admin_text(update, context)


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
                        f"⚠️ Invite-link banane ke liye bot ko yahan <b>Admin</b> rakho.",
                        parse_mode="HTML",
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
                        admin_id, f"⚠️ Bot ko <b>{chat.title}</b> se hata diya gaya, group list se bhi hata diya gaya.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass


# ---------------- Bot builders ----------------

def build_master_app(token: str) -> Application:
    """Master = tumhara existing bot, POORI functionality (buyer flow + admin panel dono)."""
    app = Application.builder().token(token).build()
    app.bot_data["is_master"] = True
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", admin_panel.cmd_admin))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(ChatMemberHandler(on_bot_chat_membership_changed, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, media_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    return app


def build_clone_app(token: str) -> Application:
    """Buyers Bot = SIRF buyer-flow (courses/payment). /admin yahan kaam nahi karta."""
    app = Application.builder().token(token).build()
    app.bot_data["is_master"] = False
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(ChatMemberHandler(on_bot_chat_membership_changed, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, media_router))
    return app


async def _register(app: Application):
    await app.initialize()
    await app.start()
    path_id = utils.clone_path_id(app.bot.token)
    applications[path_id] = app
    await app.bot.set_webhook(
        url=f"{WEBHOOK_BASE}/webhook/{path_id}", secret_token=WEBHOOK_SECRET, allowed_updates=Update.ALL_TYPES,
    )
    return path_id


async def start_clone_fn(token: str):
    app = build_clone_app(token)
    await _register(app)
    await app.bot.set_my_commands([BotCommand("start", "Courses dekho")])
    log.info(f"Clone bot started: @{(await app.bot.get_me()).username}")


async def stop_clone_fn(token: str):
    path_id = utils.clone_path_id(token)
    app = applications.pop(path_id, None)
    if not app:
        return
    try:
        await app.bot.delete_webhook()
    except Exception:
        pass
    await app.stop()
    await app.shutdown()
    log.info("Clone bot stopped.")


# ---------------- aiohttp webhook server ----------------

async def webhook_handler(request: web.Request):
    path_id = request.match_info["path_id"]
    app = applications.get(path_id)
    if not app:
        return web.Response(status=404, text="unknown bot")
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return web.Response(status=403, text="forbidden")
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.update_queue.put(update)
    return web.Response(text="OK")


async def health(request: web.Request):
    return web.Response(text=f"Bots running: {len(applications)}")


async def run():
    db.init_db()

    master_app = build_master_app(BOT_TOKEN)
    master_app.bot_data["start_clone_fn"] = start_clone_fn
    master_app.bot_data["stop_clone_fn"] = stop_clone_fn
    master_app.bot_data["all_bots"] = applications  # Broadcast/Pending-Orders ke liye -- kisi bhi bot ko find karke uske through message bhej sakte hain
    await _register(master_app)
    for admin_id in utils.ADMIN_IDS:
        try:
            await master_app.bot.set_my_commands(
                [BotCommand("admin", "Admin Panel kholo")],
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception:
            pass
    log.info(f"Master bot started: @{(await master_app.bot.get_me()).username}")

    for clone in db.list_clones():
        try:
            await start_clone_fn(clone["token"])
        except Exception as e:
            log.error(f"Clone start fail ({clone.get('label')}): {e}")

    aio_app = web.Application()
    aio_app.router.add_post("/webhook/{path_id}", webhook_handler)
    aio_app.router.add_get("/", health)
    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"Webhook server listening on port {PORT}. Total bots: {len(applications)}")

    import asyncio
    await asyncio.Event().wait()  # hamesha chalte raho


def main():
    import asyncio
    if not WEBHOOK_BASE:
        raise RuntimeError("WEBHOOK_URL / RENDER_EXTERNAL_URL set nahi hai -- webhook mode chahiye.")
    asyncio.run(run())


if __name__ == "__main__":
    main()
