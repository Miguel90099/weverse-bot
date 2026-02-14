# main.py
import os
import asyncio
import logging

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import Conflict, NetworkError, RetryAfter

from config import BOT_TOKEN, BASE_SECONDS, PEAK_SECONDS
from core.monitor import monitor_peak, monitor_normal
from core.store import init_db

from handlers.commands import (
    start_cmd, ping_cmd, horarios_cmd, products_cmd,
    silent_toggle_cmd, peak_toggle_cmd, info_cmd, check_cmd,
    text_router
)
from handlers.admin import (
    myid_cmd, addpremium_cmd, delpremium_cmd, premiumlist_cmd
)

# ✅ Logs: SOLO lo esencial (quita spam de apscheduler/httpx)
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    err = context.error

    if isinstance(err, RetryAfter):
        wait = getattr(err, "retry_after", 3)
        print(f"⏳ Rate limit: esperando {wait}s…")
        await asyncio.sleep(wait)
        return

    if isinstance(err, NetworkError):
        print(f"⚠️ Red Telegram: {err}  (reintentando...)")
        return

    if isinstance(err, Conflict):
        print("⛔ Conflict: otra instancia del bot está corriendo.")
        print("✅ Cierra Termux/Pydroid completamente y corre SOLO 1 vez.")
        return

    print(f"❌ Error no manejado: {err}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Falta BOT_TOKEN en config.py o en variables de entorno.")

    print("▶️ Iniciando bot…")
    init_db()
    print("✅ Bot creado")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ✅ Comandos básicos
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler("horarios", horarios_cmd))
    app.add_handler(CommandHandler("productos", products_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("info", info_cmd))

    # ✅ Toggles (premium en commands.py)
    app.add_handler(CommandHandler("pico", peak_toggle_cmd))
    app.add_handler(CommandHandler("silencio", silent_toggle_cmd))

    # ✅ Admin premium
    app.add_handler(CommandHandler("myid", myid_cmd))
    app.add_handler(CommandHandler("addpremium", addpremium_cmd))
    app.add_handler(CommandHandler("delpremium", delpremium_cmd))
    app.add_handler(CommandHandler("premiumlist", premiumlist_cmd))

    # ✅ Router de botones/texto
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    # ✅ Error handler
    app.add_error_handler(error_handler)

    # ✅ 2 JOBS (sin .interval)
    app.job_queue.run_repeating(monitor_peak, interval=PEAK_SECONDS, first=10)
    app.job_queue.run_repeating(monitor_normal, interval=BASE_SECONDS, first=10)
    print(f"⏱️ Monitores activos: PICO={PEAK_SECONDS}s | NORMAL={BASE_SECONDS}s")

    # ✅ Limpia webhook + cola
    async def post_init(application: Application):
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
            print("🧹 Webhook/cola limpiados. Listo ✅")
        except Exception as e:
            print(f"⚠️ No se pudo limpiar webhook/cola: {e}")

    app.post_init = post_init

    print("✅ Comandos + botones listos")
    print("🤖 Corriendo… en Telegram manda /start")

    app.run_polling(
        drop_pending_updates=True,
        poll_interval=1.5,
        timeout=30,
        allowed_updates=["message", "callback_query"]
    )


if __name__ == "__main__":
    main()