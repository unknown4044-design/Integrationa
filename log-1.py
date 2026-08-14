"""
log.py -- Optional log channel.

ENV: LOG_CHANNEL_ID (channel ki chat id, e.g. -1001234567890)
Agar set nahi hai to kuch nahi hota, koi error nahi aayega.

Design: sirf 2 cheezein log hoti hain -- (1) jab buyer payment screenshot bheje,
uski asli photo + user details wahan post hoti hai, (2) jab admin Accept/Reject
kare, wahi photo ka caption update hoke final status dikhata hai. Isse channel
saaf rehta hai (koi start/buy jaisi chhoti activity spam nahi hoti) aur har
transaction ka pura record (kisne, kya, kitna, accept/reject) ek hi jagah milta hai.
"""

import os
from telegram.constants import ParseMode

LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", "")


async def log_photo(context, photo, caption: str):
    """Screenshot ke saath naya log entry post karta hai. Sent message return karta hai
    (taaki uska chat_id/message_id save karke baad me caption update kiya ja sake), ya None."""
    if not LOG_CHANNEL_ID:
        return None
    try:
        return await context.bot.send_photo(LOG_CHANNEL_ID, photo, caption=caption, parse_mode=ParseMode.HTML)
    except Exception:
        return None


async def edit_log_caption(context, chat_id, message_id, caption: str):
    """Accept/Reject hone par log channel wali entry ka caption update kar deta hai."""
    if not LOG_CHANNEL_ID or not chat_id or not message_id:
        return
    try:
        await context.bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=caption, parse_mode=ParseMode.HTML)
    except Exception:
        pass
