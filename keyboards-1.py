"""keyboards.py -- Saare inline keyboards ek jagah."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import db


def courses_kb():
    rows = [[InlineKeyboardButton(c["name"], callback_data=f"course:{c['_id']}")] for c in db.list_courses()]
    return InlineKeyboardMarkup(rows) if rows else None


def items_kb(course_id):
    rows = [[InlineKeyboardButton(i["name"], callback_data=f"item:{i['_id']}")] for i in db.list_items(course_id)]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="back:courses")])
    return InlineKeyboardMarkup(rows)


def item_detail_kb(item_id, course_id):
    rows = [
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy:{item_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"course:{course_id}")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_review_kb(order_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ ACCEPT", callback_data=f"accept:{order_id}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject:{order_id}"),
    ]])


def groups_kb(order_id):
    rows = [[InlineKeyboardButton(g["name"], callback_data=f"grp:{order_id}:{g['_id']}")] for g in db.list_groups()]
    return InlineKeyboardMarkup(rows) if rows else None


def admin_main_kb():
    rows = [
        [InlineKeyboardButton("📚 Manage Courses", callback_data="adm:courses")],
        [InlineKeyboardButton("👥 Manage Groups", callback_data="adm:groups")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="adm:settings")],
        [InlineKeyboardButton("🕓 Pending Orders", callback_data="adm:pending")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_courses_kb():
    rows = [[InlineKeyboardButton(c["name"], callback_data=f"adm:course:{c['_id']}")] for c in db.list_courses()]
    rows.append([InlineKeyboardButton("➕ Add Course", callback_data="adm:addcourse")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm:main")])
    return InlineKeyboardMarkup(rows)


def admin_course_manage_kb(course_id):
    rows = [[InlineKeyboardButton(i["name"], callback_data=f"adm:item:{i['_id']}")] for i in db.list_items(course_id)]
    rows.append([InlineKeyboardButton("➕ Add Item/Batch", callback_data=f"adm:additem:{course_id}")])
    rows.append([InlineKeyboardButton("🗑 Delete Course", callback_data=f"adm:delcourse:{course_id}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm:courses")])
    return InlineKeyboardMarkup(rows)


def admin_item_manage_kb(item_id, course_id):
    rows = [
        [InlineKeyboardButton("🖼 Set Banner (Photo/Video)", callback_data=f"adm:setbanner:{item_id}")],
        [InlineKeyboardButton("📝 Set Caption", callback_data=f"adm:setcaption:{item_id}")],
        [InlineKeyboardButton("💰 Set Price", callback_data=f"adm:setprice:{item_id}")],
        [InlineKeyboardButton("🗑 Delete Item", callback_data=f"adm:delitem:{item_id}:{course_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"adm:course:{course_id}")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_groups_kb():
    rows = [[InlineKeyboardButton(f"🗑 {g['name']}", callback_data=f"adm:delgroup:{g['_id']}")] for g in db.list_groups()]
    rows.append([InlineKeyboardButton("➕ Add Group", callback_data="adm:addgroup")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm:main")])
    return InlineKeyboardMarkup(rows)


def admin_settings_kb():
    rows = [
        [InlineKeyboardButton("UPI ID", callback_data="adm:set:upi_id")],
        [InlineKeyboardButton("UPI Name", callback_data="adm:set:upi_name")],
        [InlineKeyboardButton("Support Contact", callback_data="adm:set:support_contact")],
        [InlineKeyboardButton("Amount Variation Range", callback_data="adm:set:variation")],
        [InlineKeyboardButton("QR Instructions Text", callback_data="adm:set:done_instructions")],
        [InlineKeyboardButton("🖼 Welcome Banner (Photo/Video)", callback_data="adm:setwelcomebanner")],
        [InlineKeyboardButton("📝 Welcome Message Text", callback_data="adm:set:welcome_caption")],
        [InlineKeyboardButton("🖼 Accept/Link Banner (Photo/Video)", callback_data="adm:setacceptbanner")],
        [InlineKeyboardButton("📝 Accept Message Text", callback_data="adm:set:accept_message")],
        [InlineKeyboardButton("Reject Message Text", callback_data="adm:set:reject_message")],
        [InlineKeyboardButton("🔙 Back", callback_data="adm:main")],
    ]
    return InlineKeyboardMarkup(rows)


def cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Cancel", callback_data="adm:cancel")]])
