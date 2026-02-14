# handlers/admin.py
from telegram import Update
from telegram.ext import ContextTypes

from utils.premium import add_premium, remove_premium, list_premium
from handlers.buttons import build_keyboard

# 👉 CAMBIA ESTO por TU user_id (admin principal)
ADMIN_IDS = {8297783963}  # <-- pon tu ID aquí

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def myid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        f"🆔 Tu ID es:\n\n`{uid}`",
        parse_mode="Markdown",
        reply_markup=build_keyboard(uid)
    )

async def addpremium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Solo el admin puede usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("Uso: /addpremium <user_id>")
        return

    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")
        return

    added = add_premium(target)
    if added:
        msg = f"💎 Usuario `{target}` ahora es PREMIUM ✅"
    else:
        msg = f"ℹ️ El usuario `{target}` ya era PREMIUM"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def delpremium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Solo el admin puede usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("Uso: /delpremium <user_id>")
        return

    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")
        return

    removed = remove_premium(target)
    if removed:
        msg = f"🗑️ Usuario `{target}` removido de PREMIUM"
    else:
        msg = f"ℹ️ El usuario `{target}` no estaba en PREMIUM"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def premiumlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Solo el admin puede usar este comando.")
        return

    ids = list_premium()
    if not ids:
        await update.message.reply_text("📭 No hay usuarios Premium aún.")
        return

    text = "💎 Usuarios PREMIUM\n━━━━━━━━━━━━━━\n"
    text += "\n".join([f"• `{i}`" for i in ids])
    await update.message.reply_text(text, parse_mode="Markdown")