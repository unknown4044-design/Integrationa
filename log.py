"""
log.py -- Optional activity log channel.

ENV: LOG_CHANNEL_ID (channel ki chat id, e.g. -1001234567890)
Agar set nahi hai to kuch nahi hota, koi error nahi aayega.

Design choice: poora user<->bot chat mirror NAHI karte (jaisa maanga tha,
channel me data zyada na bhare) -- sirf important activity milestones log
hoti hain (start, buy shuru, screenshot mila, admin ne accept/reject kiya).
Isse channel readable rehta hai aur monitoring ka kaam bhi ho jaata hai.
"""

import os
from telegram.constants import ParseMode

LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", "")


async def log(context, text: str):
    if not LOG_CHANNEL_ID:
        return
    try:
        await context.bot.send_message(LOG_CHANNEL_ID, text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
