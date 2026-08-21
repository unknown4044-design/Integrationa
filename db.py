"""
db.py -- MongoDB (free Atlas cluster) par sab data.
Collections: courses, items, groups, orders, settings (single config doc)

Sirf ek ENV chahiye: MONGO_URI
"""

import os
import time
from pymongo import MongoClient
from bson import ObjectId

_client = MongoClient(os.environ["MONGO_URI"])
_db = _client[os.environ.get("MONGO_DB_NAME", "course_bot")]

courses = _db.courses
items = _db.items
groups = _db.groups
orders = _db.orders
settings = _db.settings
users = _db.users
clones = _db.clones
media_cache = _db.media_cache

_DEFAULT_SETTINGS = {
    "_id": "config",
    "upi_id": "",
    "upi_name": "",
    "support_contact": "",
    "variation_min": 0.11,
    "variation_max": 0.99,
    # Yeh saare messages admin panel -> Settings se change ho sakte hain
    "done_instructions": (
        "QR scan karke payment karo. ⏰ Aapke paas <b>5 minute</b> hain.\n"
        "Payment ho jaane ke baad iska <b>screenshot yahin bhej do</b> — koi button dabane ki zarurat nahi."
    ),
    "pending_message": "Aapka payment verification ke liye bhej diya gaya hai. Thodi der me confirm ho jayega ✅",
    "expiry_message": (
        "⏰ <b>Time khatam!</b> Yeh transaction 5 minute me confirm nahi hua isliye close ho gaya.\n"
        "Agar payment kar chuke ho to turant support se contact karo, warna naya order banao."
    ),
    "accept_message": "🎉 Payment Accepted! Neeche aapka private access link hai:",
    "reject_message": "❌ Aapka payment verify nahi ho paya. Dobara try karo ya support se contact karo.",
    # Welcome (/start) aur Accept/Invite-link message ke liye optional banner
    "welcome_caption": "",
    "welcome_media_type": None,
    "welcome_media_file_id": None,
    "accept_media_type": None,
    "accept_media_file_id": None,
    # Forward/Copy/Save protection -- "1" = ON (buyer kuch bhi forward/copy nahi kar sakta,
    # sirf QR wali photo exclude hai taaki payment ke liye screenshot le sake), "0" = OFF
    "protect_content": "1",
}


def init_db():
    if settings.find_one({"_id": "config"}) is None:
        settings.insert_one(_DEFAULT_SETTINGS)
    else:
        existing = settings.find_one({"_id": "config"})
        missing = {k: v for k, v in _DEFAULT_SETTINGS.items() if k not in existing}
        if missing:
            settings.update_one({"_id": "config"}, {"$set": missing})
    courses.create_index("position")
    items.create_index("course_id")
    orders.create_index("user_id")
    orders.create_index("status")


# ---------------- Settings ----------------

def get_settings():
    return settings.find_one({"_id": "config"})


def get_setting(key, default=""):
    doc = get_settings()
    return doc.get(key, default) if doc else default


def set_setting(key, value):
    settings.update_one({"_id": "config"}, {"$set": {key: value}})


# ---------------- Courses ----------------

def add_course(name):
    return str(courses.insert_one({"name": name, "position": int(time.time()), "active": True}).inserted_id)


def set_course_active(course_id, active: bool):
    courses.update_one({"_id": ObjectId(course_id)}, {"$set": {"active": active}})


def list_courses():
    return list(courses.find().sort("position", 1))


def get_course(course_id):
    return courses.find_one({"_id": ObjectId(course_id)})


def update_course_name(course_id, name):
    courses.update_one({"_id": ObjectId(course_id)}, {"$set": {"name": name}})


def update_course_caption(course_id, caption):
    courses.update_one({"_id": ObjectId(course_id)}, {"$set": {"caption": caption}})


def update_course_media(course_id, media_type, file_id):
    courses.update_one({"_id": ObjectId(course_id)}, {"$set": {"media_type": media_type, "media_file_id": file_id}})


def delete_course(course_id):
    items.delete_many({"course_id": course_id})
    courses.delete_one({"_id": ObjectId(course_id)})


# ---------------- Items (sub-buttons / batches) ----------------

def add_item(course_id, name):
    doc = {
        "course_id": course_id,
        "name": name,
        "media_type": None,
        "media_file_id": None,
        "caption": "",
        "price": 0,
        "position": int(time.time()),
        "active": True,
    }
    return str(items.insert_one(doc).inserted_id)


def set_item_active(item_id, active: bool):
    items.update_one({"_id": ObjectId(item_id)}, {"$set": {"active": active}})


def update_item_media(item_id, media_type, file_id):
    items.update_one({"_id": ObjectId(item_id)}, {"$set": {"media_type": media_type, "media_file_id": file_id}})


def update_item_caption(item_id, caption_html):
    items.update_one({"_id": ObjectId(item_id)}, {"$set": {"caption": caption_html}})


def update_item_price(item_id, price):
    items.update_one({"_id": ObjectId(item_id)}, {"$set": {"price": price}})


def update_item_name(item_id, name):
    items.update_one({"_id": ObjectId(item_id)}, {"$set": {"name": name}})


def list_items(course_id):
    return list(items.find({"course_id": course_id}).sort("position", 1))


def get_item(item_id):
    return items.find_one({"_id": ObjectId(item_id)})


def delete_item(item_id):
    items.delete_one({"_id": ObjectId(item_id)})


# ---------------- Groups ----------------

def add_group(name, chat_id):
    return str(groups.insert_one({"name": name, "chat_id": chat_id}).inserted_id)


def get_group_by_chat_id(chat_id):
    return groups.find_one({"chat_id": chat_id})


def list_groups():
    return list(groups.find())


def get_group(group_id):
    return groups.find_one({"_id": ObjectId(group_id)})


def delete_group(group_id):
    groups.delete_one({"_id": ObjectId(group_id)})


# ---------------- Orders ----------------

def create_order(user_id, username, full_name, item_id, item_name, base_amount, final_amount, bot_key=None):
    now = int(time.time())
    doc = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "item_id": item_id,
        "item_name": item_name,
        "base_amount": base_amount,
        "final_amount": final_amount,
        "status": "awaiting_payment",
        "screenshot_file_id": None,
        "admin_msg_refs": [],
        "bot_key": bot_key,
        "created_at": now,
        "updated_at": now,
    }
    return str(orders.insert_one(doc).inserted_id)


def get_order(order_id):
    return orders.find_one({"_id": ObjectId(order_id)})


def update_order_status(order_id, status):
    orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": status, "updated_at": int(time.time())}})


def set_order_screenshot(order_id, file_id):
    orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"screenshot_file_id": file_id, "status": "pending", "updated_at": int(time.time())}},
    )


def append_admin_msg_ref(order_id, chat_id, msg_id):
    orders.update_one({"_id": ObjectId(order_id)}, {"$push": {"admin_msg_refs": [chat_id, msg_id]}})


def set_order_log_msg(order_id, chat_id, msg_id):
    orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"log_msg": [chat_id, msg_id]}})


def get_admin_msg_refs(order_id):
    order = get_order(order_id)
    return order.get("admin_msg_refs", []) if order else []


def find_active_order_for_user(user_id):
    return orders.find_one(
        {"user_id": user_id, "status": {"$in": ["awaiting_payment", "pending"]}},
        sort=[("created_at", -1)],
    )


def find_awaiting_payment_order(user_id):
    """Woh order jiska QR abhi dikhaya gaya hai aur screenshot ka wait ho raha hai (5-min window)."""
    return orders.find_one({"user_id": user_id, "status": "awaiting_payment"}, sort=[("created_at", -1)])


def list_pending_orders():
    return list(orders.find({"status": "pending"}).sort("created_at", 1))


def clear_pending_orders_for_bot(bot_key):
    """Bot delete hone par uske saare abhi-tak-pending orders ko 'abandoned' kar deta hai,
    taaki woh Master ke Pending Orders count/list se hamesha ke liye hat jayein
    (kyunki delete hue bot se ab kabhi link nahi bheja ja sakta)."""
    orders.update_many(
        {"bot_key": bot_key, "status": {"$in": ["pending", "awaiting_payment"]}},
        {"$set": {"status": "abandoned", "updated_at": int(time.time())}},
    )


# ---------------- Users (broadcast ke liye) ----------------

def upsert_user(user_id, username, full_name, bot_key=None):
    users.update_one(
        {"_id": user_id},
        {"$set": {"username": username, "full_name": full_name, "bot_key": bot_key},
         "$setOnInsert": {"first_seen": int(time.time())}},
        upsert=True,
    )


def list_user_ids():
    return [u["_id"] for u in users.find({}, {"_id": 1})]


def list_users():
    return list(users.find({}))


def count_users():
    return users.count_documents({})


# ---------------- Clone Bots (Master bot se manage hote hain) ----------------

def add_clone(token, label):
    return str(clones.insert_one({"token": token, "label": label, "added_at": int(time.time())}).inserted_id)


def list_clones():
    return list(clones.find())


def get_clone(clone_id):
    return clones.find_one({"_id": ObjectId(clone_id)})


def delete_clone(clone_id):
    clones.delete_one({"_id": ObjectId(clone_id)})


# ---------------- Media cache (cross-bot file_id resolve, speed ke liye) ----------------
# Master bot ka file_id Buyer bot me seedha kaam nahi karta -- pehli baar download+upload
# karna padta hai, uske baad naya file_id yahan cache ho jaata hai taaki dubara download
# na karna pade (turant, fast response).

def get_cached_file_id(bot_key, source_file_id):
    doc = media_cache.find_one({"_id": f"{bot_key}:{source_file_id}"})
    return doc["file_id"] if doc else None


def set_cached_file_id(bot_key, source_file_id, resolved_file_id):
    media_cache.update_one(
        {"_id": f"{bot_key}:{source_file_id}"},
        {"$set": {"file_id": resolved_file_id}},
        upsert=True,
    )
