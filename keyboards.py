"""keyboards.py -- Saare inline keyboards ek jagah. Grid-style layout (2 buttons per row)
jahan attractive lagta hai, single/full-width row jahan zaroori hai (Back/Cancel/Buy Now)."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import db


def _grid(buttons, cols=2):
    """List of InlineKeyboardButton ko N-N karke rows me arrange karta hai."""
    return [buttons[i:i + cols] for i in range(0, len(buttons), cols)]


def courses_kb():
    buttons = [InlineKeyboardButton(c["name"], callback_data=f"course:{c['_id']}") for c in db.list_courses() if c.get("active", True)]
    return InlineKeyboardMarkup(_grid(buttons)) if buttons else None


def items_kb(course_id):
    buttons = [InlineKeyboardButton(i["name"], callback_data=f"item:{i['_id']}") for i in db.list_items(course_id) if i.get("active", True)]
    rows = _grid(buttons)
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="back:courses")])
    return InlineKeyboardMarkup(rows)


def item_detail_kb(item_id, course_id):
    rows = [
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy:{item_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"course:{course_id}"), InlineKeyboardButton("🏠 Home", callback_data="back:courses")],
    ]
    return InlineKeyboardMarkup(rows)


def home_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="back:courses")]])


def admin_review_kb(order_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ ACCEPT", callback_data=f"accept:{order_id}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject:{order_id}"),
    ]])


def groups_kb(order_id):
    buttons = [InlineKeyboardButton(g["name"], callback_data=f"grp:{order_id}:{g['_id']}") for g in db.list_groups()]
    if not buttons:
        return None
    rows = _grid(buttons)
    rows.append([InlineKeyboardButton("🔙 Back", callback_data=f"backreview:{order_id}")])
    return InlineKeyboardMarkup(rows)


def admin_main_kb():
    buttons = [
        InlineKeyboardButton("📚 Manage Courses", callback_data="adm:courses"),
        InlineKeyboardButton("👥 Manage Groups", callback_data="adm:groups"),
        InlineKeyboardButton("⚙️ Settings", callback_data="adm:settings"),
        InlineKeyboardButton("🕓 Pending Orders", callback_data="adm:pending"),
        InlineKeyboardButton("📢 Broadcast", callback_data="adm:broadcast"),
    ]
    return InlineKeyboardMarkup(_grid(buttons))


def clones_kb():
    rows = [[InlineKeyboardButton(f"🗑 @{c['label']}", callback_data=f"adm:delclone:{c['_id']}")] for c in db.list_clones()]
    rows.append([InlineKeyboardButton("➕ Add Buyers Bot", callback_data="adm:addclone")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm:settings")])
    return InlineKeyboardMarkup(rows)


def admin_courses_kb():
    buttons = [
        InlineKeyboardButton(('✅ ' if c.get('active', True) else '⛔ ') + c["name"], callback_data=f"adm:course:{c['_id']}")
        for c in db.list_courses()
    ]
    rows = _grid(buttons)
    rows.append([InlineKeyboardButton("➕ Add Course", callback_data="adm:addcourse")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm:main")])
    return InlineKeyboardMarkup(rows)


def admin_course_manage_kb(course_id):
    course = db.get_course(course_id)
    active = course.get("active", True) if course else True
    buttons = [
        InlineKeyboardButton(('✅ ' if i.get('active', True) else '⛔ ') + i["name"], callback_data=f"adm:item:{i['_id']}")
        for i in db.list_items(course_id)
    ]
    rows = _grid(buttons)
    rows.append([InlineKeyboardButton("➕ Add Item/Batch", callback_data=f"adm:additem:{course_id}")])
    rows.append([InlineKeyboardButton("✏️ Rename Course", callback_data=f"adm:renamecourse:{course_id}")])
    rows.append([InlineKeyboardButton("🖼 Set Course Banner", callback_data=f"adm:setcoursebanner:{course_id}")])
    rows.append([InlineKeyboardButton("📝 Set Course Caption", callback_data=f"adm:setcoursecaption:{course_id}")])
    toggle_label = "⛔ Disable Course" if active else "✅ Enable Course"
    rows.append([InlineKeyboardButton(toggle_label, callback_data=f"adm:togglecourse:{course_id}")])
    rows.append([InlineKeyboardButton("🗑 Delete Course", callback_data=f"adm:delcourse:{course_id}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm:courses")])
    return InlineKeyboardMarkup(rows)


def admin_item_manage_kb(item_id, course_id):
    item = db.get_item(item_id)
    active = item.get("active", True) if item else True
    grid_buttons = [
        InlineKeyboardButton("🖼 Set Banner", callback_data=f"adm:setbanner:{item_id}"),
        InlineKeyboardButton("📝 Set Caption", callback_data=f"adm:setcaption:{item_id}"),
        InlineKeyboardButton("💰 Set Price", callback_data=f"adm:setprice:{item_id}"),
        InlineKeyboardButton("🗑 Delete Item", callback_data=f"adm:delitem:{item_id}:{course_id}"),
    ]
    rows = _grid(grid_buttons)
    rows.append([InlineKeyboardButton("✏️ Rename Item", callback_data=f"adm:renameitem:{item_id}:{course_id}")])
    toggle_label = "⛔ Disable Item" if active else "✅ Enable Item"
    rows.append([InlineKeyboardButton(toggle_label, callback_data=f"adm:toggleitem:{item_id}:{course_id}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data=f"adm:course:{course_id}")])
    return InlineKeyboardMarkup(rows)


def admin_groups_kb():
    buttons = [InlineKeyboardButton(f"🗑 {g['name']}", callback_data=f"adm:delgroup:{g['_id']}") for g in db.list_groups()]
    rows = _grid(buttons)
    rows.append([InlineKeyboardButton("➕ Add Group", callback_data="adm:addgroup")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm:main")])
    return InlineKeyboardMarkup(rows)


def admin_settings_kb():
    grid_buttons = [
        InlineKeyboardButton("UPI ID", callback_data="adm:set:upi_id"),
        InlineKeyboardButton("UPI Name", callback_data="adm:set:upi_name"),
        InlineKeyboardButton("Support Contact", callback_data="adm:set:support_contact"),
        InlineKeyboardButton("Variation Range", callback_data="adm:set:variation"),
        InlineKeyboardButton("QR Instructions", callback_data="adm:set:done_instructions"),
        InlineKeyboardButton("📸 Screenshot-Received Text", callback_data="adm:set:pending_message"),
        InlineKeyboardButton("⏰ Payment Time-Out Text", callback_data="adm:set:expiry_message"),
        InlineKeyboardButton("🖼 Welcome Banner", callback_data="adm:setwelcomebanner"),
        InlineKeyboardButton("📝 Welcome Text", callback_data="adm:set:welcome_caption"),
        InlineKeyboardButton("🖼 Accept Banner", callback_data="adm:setacceptbanner"),
        InlineKeyboardButton("📝 Accept Text", callback_data="adm:set:accept_message"),
        InlineKeyboardButton("Reject Text", callback_data="adm:set:reject_message"),
    ]
    rows = _grid(grid_buttons)
    rows.append([InlineKeyboardButton("🤖 Buyers Bot", callback_data="adm:clones")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm:main")])
    return InlineKeyboardMarkup(rows)


def cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Cancel", callback_data="adm:cancel")]])


def broadcast_button_choice_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Button Add Karo", callback_data="adm:bcbtn:yes")],
        [InlineKeyboardButton("⏭ Skip (bina button)", callback_data="adm:bcbtn:no")],
        [InlineKeyboardButton("✖️ Cancel", callback_data="adm:cancel")],
    ])


def broadcast_protect_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Forward/Copy BAND karo", callback_data="adm:bcprotect:yes")],
        [InlineKeyboardButton("🔓 Allow karo", callback_data="adm:bcprotect:no")],
        [InlineKeyboardButton("✖️ Cancel", callback_data="adm:cancel")],
    ])
