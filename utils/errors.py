# utils/errors.py
from telegram.error import NetworkError, TimedOut

async def error_handler(update, context):
    err = context.error
    if isinstance(err, (NetworkError, TimedOut)):
        print(f"⚠️ Red Telegram: {err} (reintentando...)")
        return
    print(f"❌ Error: {err}")