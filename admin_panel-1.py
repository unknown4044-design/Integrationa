"""
admin_panel.py -- Sirf ADMIN_IDS wale users yeh use kar sakte hain.
Content (courses/items/banner/caption/price), groups, welcome/accept banners,
aur saare text-messages yahin se runtime me configure hote hain.
"""

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import db
import utils
import keyboards as kb
import log


def _guard(update: Update) -> bool:
    return utils.is_admin(update.effective_user.id)


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    context.user_data.pop("adm_state", None)
    await update.message.reply_text("🛠 <b>Admin Panel</b>", parse_mode=ParseMode.HTML, reply_markup=kb.admin_main_kb())


def _set_state(context, state, **data):
    context.user_data["adm_state"] = state
    context.user_data["adm_data"] = data


def _clear_state(context):
    context.user_data.pop("adm_state", None)
    context.user_data.pop("adm_data", None)


# ---------------- Callback dispatcher ----------------

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    if not _guard(update):
        return
    q = update.callback_query
    parts = action.split(":")
    key = parts[0]

    if key == "main":
        _clear_state(context)
        await q.edit_message_text("🛠 <b>Admin Panel</b>", parse_mode=ParseMode.HTML, reply_markup=kb.admin_main_kb())

    elif key == "cancel":
        _clear_state(context)
        await q.edit_message_text("Cancelled.", reply_markup=kb.admin_main_kb())

    # ---- Courses ----
    elif key == "courses":
        await q.edit_message_text("📚 <b>Courses</b>", parse_mode=ParseMode.HTML, reply_markup=kb.admin_courses_kb())

    elif key == "addcourse":
        _set_state(context, "addcourse")
        await q.edit_message_text("Naye course ka naam type karo:", reply_markup=kb.cancel_kb())

    elif key == "course":
        course_id = parts[1]
        course = db.get_course(course_id)
        await q.edit_message_text(
            f"📚 <b>{course['name']}</b>\nItems/Batches manage karo:",
            parse_mode=ParseMode.HTML, reply_markup=kb.admin_course_manage_kb(course_id),
        )

    elif key == "delcourse":
        db.delete_course(parts[1])
        await q.edit_message_text("Course delete ho gaya.", reply_markup=kb.admin_courses_kb())

    elif key == "additem":
        course_id = parts[1]
        _set_state(context, "additem", course_id=course_id)
        await q.edit_message_text("Naye item/batch ka naam type karo:", reply_markup=kb.cancel_kb())

    elif key == "item":
        item_id = parts[1]
        item = db.get_item(item_id)
        await q.edit_message_text(
            f"🎯 <b>{item['name']}</b>\nPrice: ₹{item['price']}\nBanner: {'✅' if item.get('media_file_id') else '❌'}\nCaption: {'✅' if item.get('caption') else '❌'}",
            parse_mode=ParseMode.HTML, reply_markup=kb.admin_item_manage_kb(item_id, item["course_id"]),
        )

    elif key == "delitem":
        item_id, course_id = parts[1], parts[2]
        db.delete_item(item_id)
        await q.edit_message_text("Item delete ho gaya.", reply_markup=kb.admin_course_manage_kb(course_id))

    elif key == "setbanner":
        _set_state(context, "setbanner", item_id=parts[1])
        await q.edit_message_text("Photo ya Video banner bhejo:", reply_markup=kb.cancel_kb())

    elif key == "setcaption":
        _set_state(context, "setcaption", item_id=parts[1])
        await q.edit_message_text(
            "Caption type/bhejo (Bold text aur Telegram Premium emoji waise hi likh sakte ho, jaisa dikhega waisa hi save hoga):",
            reply_markup=kb.cancel_kb(),
        )

    elif key == "setprice":
        _set_state(context, "setprice", item_id=parts[1])
        await q.edit_message_text("Base price (sirf number, e.g. 499) type karo:", reply_markup=kb.cancel_kb())

    # ---- Groups ----
    elif key == "groups":
        await q.edit_message_text("👥 <b>Groups</b>\n(delete karne ke liye tap karo)", parse_mode=ParseMode.HTML, reply_markup=kb.admin_groups_kb())

    elif key == "addgroup":
        _set_state(context, "addgroup")
        await q.edit_message_text(
            "Group/Channel se koi bhi message yahan <b>forward</b> karo (bot us group me admin hona chahiye, invite-link create karne ki permission ke sath).\n\n"
            "Ya manually bhejo: <code>Group Name | -1001234567890</code>",
            parse_mode=ParseMode.HTML, reply_markup=kb.cancel_kb(),
        )

    elif key == "delgroup":
        db.delete_group(parts[1])
        await q.edit_message_text("Group hata diya gaya.", reply_markup=kb.admin_groups_kb())

    # ---- Settings ----
    elif key == "settings":
        await q.edit_message_text("⚙️ <b>Settings</b>", parse_mode=ParseMode.HTML, reply_markup=kb.admin_settings_kb())

    elif key == "set":
        setting_key = parts[1]
        if setting_key == "variation":
            _set_state(context, "setting", setting_key="variation")
            await q.edit_message_text("Range type karo (₹ min,max), e.g. <code>0.11,0.99</code>", parse_mode=ParseMode.HTML, reply_markup=kb.cancel_kb())
        else:
            _set_state(context, "setting", setting_key=setting_key)
            await q.edit_message_text(f"Naya value type karo ({setting_key}):", reply_markup=kb.cancel_kb())

    elif key == "setwelcomebanner":
        _set_state(context, "setmedia", target="welcome")
        await q.edit_message_text(
            "Welcome (/start) banner ke liye Photo ya Video bhejo.\nHatane ke liye 'remove' type karo.",
            reply_markup=kb.cancel_kb(),
        )

    elif key == "setacceptbanner":
        _set_state(context, "setmedia", target="accept")
        await q.edit_message_text(
            "Accept/Invite-link message ke liye Photo ya Video bhejo.\nHatane ke liye 'remove' type karo.",
            reply_markup=kb.cancel_kb(),
        )

    # ---- Orders ----
    elif key == "pending":
        pend = db.list_pending_orders()
        if not pend:
            await q.edit_message_text("Koi pending order nahi hai.", reply_markup=kb.admin_main_kb())
            return
        await q.edit_message_text(f"🕓 {len(pend)} Pending Order(s) neeche bheje ja rahe hain:", reply_markup=kb.admin_main_kb())
        for o in pend:
            order_id = str(o["_id"])
            caption = utils.build_order_caption(o, status_label="Pending")
            if o.get("screenshot_file_id"):
                msg = await utils.safe_send_photo(context.bot, q.message.chat_id, o["screenshot_file_id"], caption, reply_markup=kb.admin_review_kb(order_id))
            else:
                msg = await utils.safe_send_message(context.bot, q.message.chat_id, caption, reply_markup=kb.admin_review_kb(order_id))
            if msg:
                db.append_admin_msg_ref(order_id, msg.chat_id, msg.message_id)


# ---------------- Order review (accept / reject / group select) ----------------

async def review_accept(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
    if not _guard(update):
        return
    q = update.callback_query
    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        await q.answer("Yeh order already process ho chuka hai.", show_alert=True)
        return
    markup = kb.groups_kb(order_id)
    if not markup:
        await q.answer("Pehle Admin Panel > Manage Groups se group add karo.", show_alert=True)
        return
    await q.answer()
    await q.edit_message_caption(caption=q.message.caption + "\n\n👉 Kaunsa group access dena hai?", parse_mode=ParseMode.HTML, reply_markup=markup)


async def review_reject(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
    if not _guard(update):
        return
    q = update.callback_query
    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        await q.answer("Yeh order already process ho chuka hai.", show_alert=True)
        return

    db.update_order_status(order_id, "rejected")
    await q.answer("Rejected")

    for chat_id, msg_id in db.get_admin_msg_refs(order_id):
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id, message_id=msg_id,
                caption=q.message.caption + "\n\nStatus: ❌ <b>Rejected</b>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    reject_msg = db.get_setting("reject_message", "Payment reject ho gaya.")
    support = db.get_setting("support_contact", "")
    if support:
        reject_msg += f"\n\nNeed help? Contact: {support}"
    await utils.safe_send_message(context.bot, order["user_id"], reject_msg)
    await log.log(context, f"❌ Rejected: order <code>{order_id}</code>")


async def review_group_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str, group_id: str):
    if not _guard(update):
        return
    q = update.callback_query
    order = db.get_order(order_id)
    group = db.get_group(group_id)
    if not order or order["status"] != "pending" or not group:
        await q.answer("Invalid / already processed.", show_alert=True)
        return

    try:
        link = await context.bot.create_chat_invite_link(
            chat_id=group["chat_id"], member_limit=1, name=f"order_{order_id}"
        )
    except Exception as e:
        await q.answer(f"Invite link fail: {e}", show_alert=True)
        return

    db.update_order_status(order_id, "accepted")
    await q.answer("Accepted ✅")

    accept_msg = db.get_setting("accept_message", "Payment Accepted!")
    support = db.get_setting("support_contact", "")
    user_text = f"{accept_msg}\n\n🔗 {link.invite_link}\n\n⚠️ Yeh link sirf ek baar use ho sakta hai."
    if support:
        user_text += f"\n\nNeed help? Contact: {support}"

    media_type = db.get_setting("accept_media_type")
    file_id = db.get_setting("accept_media_file_id")
    if media_type == "photo" and file_id:
        await utils.safe_send_photo(context.bot, order["user_id"], file_id, user_text)
    elif media_type == "video" and file_id:
        await utils.safe_send_video(context.bot, order["user_id"], file_id, user_text)
    else:
        await utils.safe_send_message(context.bot, order["user_id"], user_text)

    for chat_id, msg_id in db.get_admin_msg_refs(order_id):
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id, message_id=msg_id,
                caption=f"Status: ✅ <b>Accepted</b> → {group['name']}\nLink user ko bhej diya gaya.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    await log.log(context, f"✅ Accepted: order <code>{order_id}</code> → {group['name']}")


# ---------------- Text / Media input handler for admin state machine ----------------

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True agar message admin state-machine ne consume kar liya."""
    if not _guard(update):
        return False
    state = context.user_data.get("adm_state")
    if not state:
        return False
    data = context.user_data.get("adm_data", {})
    text = update.message.text_html if update.message.text else None

    if state == "addcourse" and text:
        db.add_course(update.message.text.strip())
        _clear_state(context)
        await update.message.reply_text("✅ Course add ho gaya.", reply_markup=kb.admin_courses_kb())
        return True

    if state == "additem" and text:
        db.add_item(data["course_id"], update.message.text.strip())
        _clear_state(context)
        await update.message.reply_text("✅ Item add ho gaya.", reply_markup=kb.admin_course_manage_kb(data["course_id"]))
        return True

    if state == "setcaption" and text:
        db.update_item_caption(data["item_id"], update.message.caption_html or text)
        _clear_state(context)
        await update.message.reply_text("✅ Caption save ho gaya.", reply_markup=kb.admin_item_manage_kb(data["item_id"], db.get_item(data["item_id"])["course_id"]))
        return True

    if state == "setprice" and update.message.text:
        try:
            price = float(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("Sirf number likho, e.g. 499")
            return True
        db.update_item_price(data["item_id"], price)
        _clear_state(context)
        await update.message.reply_text("✅ Price save ho gaya.", reply_markup=kb.admin_item_manage_kb(data["item_id"], db.get_item(data["item_id"])["course_id"]))
        return True

    if state == "addgroup":
        origin_chat = None
        if update.message.forward_origin and hasattr(update.message.forward_origin, "chat"):
            origin_chat = update.message.forward_origin.chat
        if origin_chat:
            db.add_group(origin_chat.title or str(origin_chat.id), origin_chat.id)
            _clear_state(context)
            await update.message.reply_text("✅ Group add ho gaya.", reply_markup=kb.admin_groups_kb())
            return True
        if update.message.text and "|" in update.message.text:
            name, cid = update.message.text.split("|", 1)
            try:
                db.add_group(name.strip(), int(cid.strip()))
                _clear_state(context)
                await update.message.reply_text("✅ Group add ho gaya.", reply_markup=kb.admin_groups_kb())
            except ValueError:
                await update.message.reply_text("Format galat hai. e.g. Group Name | -1001234567890")
            return True
        await update.message.reply_text("Group se message forward karo, ya 'Name | chat_id' format me bhejo.")
        return True

    if state == "setmedia" and update.message.text and update.message.text.strip().lower() == "remove":
        target = data["target"]
        db.set_setting(f"{target}_media_type", None)
        db.set_setting(f"{target}_media_file_id", None)
        _clear_state(context)
        await update.message.reply_text("✅ Banner hata diya gaya.", reply_markup=kb.admin_settings_kb())
        return True

    if state == "setting" and update.message.text:
        skey = data["setting_key"]
        if skey == "variation":
            try:
                vmin, vmax = update.message.text.split(",")
                db.set_setting("variation_min", float(vmin.strip()))
                db.set_setting("variation_max", float(vmax.strip()))
            except Exception:
                await update.message.reply_text("Format galat hai. e.g. 0.11,0.99")
                return True
        else:
            value = update.message.text_html or update.message.text
            db.set_setting(skey, value)
        _clear_state(context)
        await update.message.reply_text("✅ Setting update ho gayi.", reply_markup=kb.admin_settings_kb())
        return True

    return False


async def handle_admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True agar photo/video admin ke kisi 'set banner' state ne consume kar liya."""
    if not _guard(update):
        return False
    state = context.user_data.get("adm_state")
    data = context.user_data.get("adm_data", {})

    if state == "setmedia":
        target = data["target"]
        if update.message.photo:
            db.set_setting(f"{target}_media_type", "photo")
            db.set_setting(f"{target}_media_file_id", update.message.photo[-1].file_id)
        elif update.message.video:
            db.set_setting(f"{target}_media_type", "video")
            db.set_setting(f"{target}_media_file_id", update.message.video.file_id)
        else:
            return False
        _clear_state(context)
        await update.message.reply_text("✅ Banner save ho gaya.", reply_markup=kb.admin_settings_kb())
        return True

    if state == "setbanner":
        if update.message.photo:
            db.update_item_media(data["item_id"], "photo", update.message.photo[-1].file_id)
        elif update.message.video:
            db.update_item_media(data["item_id"], "video", update.message.video.file_id)
        else:
            return False
        _clear_state(context)
        item = db.get_item(data["item_id"])
        await update.message.reply_text("✅ Banner save ho gaya.", reply_markup=kb.admin_item_manage_kb(data["item_id"], item["course_id"]))
        return True

    return False
