# handlers/commands.py
import asyncio
import time
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from config import PRODUCT_NAME, PRODUCT_URL, BASE_SECONDS, PEAK_SECONDS
from handlers.buttons import build_keyboard

from utils.state import (
    is_peak_enabled, toggle_peak_enabled,
    is_silent_enabled, toggle_silent_enabled,
    get_silent_window
)
from utils.premium import is_premium

from core.scheduler import is_peak_time
from core.weverse import fetch_page, is_available
from core.monitor import get_last_mode
from core.store import (
    init_db, get_memory, update_memory, log_check,
    stats_today, peak_hours_by_latency, peak_hours_by_changes
)

# ---------- Helpers ----------
def now_sp_iso() -> str:
    sp = datetime.now(timezone.utc) + timedelta(hours=-3)
    return sp.strftime("%Y-%m-%d %H:%M:%S")

def now_sp_hhmm() -> str:
    sp = datetime.now(timezone.utc) + timedelta(hours=-3)
    return sp.strftime("%H:%M")

def progress_bar(pct: int, width: int = 12) -> str:
    filled = int(width * pct / 100)
    return "▰" * filled + "▱" * (width - filled)

async def safe_edit(msg, text: str, retries: int = 3, delay: float = 0.7) -> bool:
    for i in range(retries):
        try:
            await msg.edit_text(text)
            return True
        except Exception:
            if i == retries - 1:
                return False
            await asyncio.sleep(delay)
    return False


# ---------- Premium message ----------
async def premium_locked(update: Update, feature_name: str):
    uid = update.effective_user.id
    await update.message.reply_text(
        "💎 FUNCIÓN PREMIUM 🔒\n"
        "━━━━━━━━━━━━━━\n"
        f"✨ {feature_name}\n\n"
        "Para usar esto necesitas tener Premium.\n"
        "💜 Si ya eres Premium, dime tu ID y te activo.",
        reply_markup=build_keyboard(uid)
    )


# ---------- Commands ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    uid = update.effective_user.id
    await update.message.reply_text(
        "💜🤖 Bot Restock Weverse ARMY PRO ✅\n"
        "Usa los botones de abajo 👇",
        reply_markup=build_keyboard(uid)
    )


async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        "🏓 Pong! Estoy vivo y vigilando 😎💜",
        reply_markup=build_keyboard(uid)
    )


async def horarios_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s_start, s_end = get_silent_window()
    await update.message.reply_text(
        "⏰ Horarios recomendados (São Paulo) 💜\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔥 Ventana 1: 20:30 – 02:30\n"
        "🔥 Ventana 2: 05:30 – 06:30\n\n"
        "📌 Tip ARMY: activa *Pico* solo dentro de esas ventanas.\n"
        f"🔕 Silencio (si lo activas): {s_start} – {s_end}",
        reply_markup=build_keyboard(uid)
    )


async def products_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        "📦 Productos (base) 💎\n"
        "━━━━━━━━━━━━━━\n"
        f"✅ 1) {PRODUCT_NAME}\n\n"
        "✨ Próxima mejora: lista editable (agregar/quitar productos) con ON/OFF por producto.",
        reply_markup=build_keyboard(uid)
    )


async def silent_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_premium(uid):
        await premium_locked(update, "Modo Silencio 🔕")
        return

    state = toggle_silent_enabled()
    if state:
        msg = "🔕 Silencio ACTIVADO ✅\n💤 Ideal para dormir… yo vigilo por ti, ARMY 💜"
    else:
        msg = "🔔 Silencio DESACTIVADO ✅\n📣 Avisos normales activados, ARMY 💜"
    await update.message.reply_text(msg, reply_markup=build_keyboard(uid))


async def peak_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_premium(uid):
        await premium_locked(update, "Modo Pico 🔥")
        return

    state = toggle_peak_enabled()
    if state:
        msg = f"🟢 Pico ACTIVADO 🔥 ({PEAK_SECONDS}s)\n⚡ Modo rápido dentro de horario pico."
    else:
        msg = f"⚫ Pico DESACTIVADO 🛡️ ({BASE_SECONDS}s)\n✅ Modo seguro y estable."
    await update.message.reply_text(msg, reply_markup=build_keyboard(uid))


async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    uid = update.effective_user.id

    last_status, last_change, last_check = get_memory()

    if last_status is None:
        status_txt = "— Sin datos aún"
    else:
        status_txt = "🟢 Disponible ✨" if int(last_status) == 1 else "🔴 Agotado"

    # Premium lock display
    if is_premium(uid):
        pico_txt = f"ON 🔥 ({PEAK_SECONDS}s)" if is_peak_enabled() else f"OFF 🛡️ ({BASE_SECONDS}s)"
        sil_txt = "ON 🔕" if is_silent_enabled() else "OFF 🔔"
    else:
        pico_txt = "🔒 Premium"
        sil_txt = "🔒 Premium"

    modo_hora = "PICO 🔥" if is_peak_time() else "NORMAL 💤"
    modo_actual = get_last_mode()

    total, errs, avg_ms, max_ms = stats_today()

    # Bloques “pico por TUS datos”
    top_latency = peak_hours_by_latency(3)
    top_changes = peak_hours_by_changes(3)

    if top_latency:
        latency_block = "\n".join([f"• {hour}h — n:{n} — avg:{int(avg)}ms" for hour, n, avg in top_latency])
    else:
        latency_block = "— Aún sin suficientes datos"

    if top_changes:
        changes_block = "\n".join([f"• {hour}h — hits:{hits}" for hour, hits in top_changes])
    else:
        changes_block = "— Aún sin suficientes datos"

    def hhmm(ts: str | None) -> str:
        if not ts:
            return "—"
        return ts[11:16]

    await update.message.reply_text(
        "💜 ARMY RESTOCK STATUS 💜\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🛒 Producto\n"
        f"{PRODUCT_NAME}\n"
        f"🔗 {PRODUCT_URL}\n\n"
        "📌 Estado actual\n"
        f"{status_txt}\n\n"
        "🕒 Último cambio de estado\n"
        f"• {hhmm(last_change)}\n\n"
        "🕒 Última verificación\n"
        f"• {hhmm(last_check)}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🛡️ CONFIGURACIÓN DEL BOT\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ Modo Pico: {pico_txt}\n"
        f"🔕 Modo Silencio: {sil_txt}\n"
        f"🕒 Estado actual: {modo_hora}\n"
        f"🧠 Último modo usado: {modo_actual}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 ACTIVIDAD (24 HORAS)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔁 Chequeos realizados: {total or 0}\n"
        f"🌐 Errores de red: {errs or 0}\n"
        f"⚡ Latencia promedio: {int(avg_ms) if avg_ms else 0}ms\n"
        f"🚀 Latencia máxima: {int(max_ms) if max_ms else 0}ms\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📈 ANÁLISIS ARMY (tus datos)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔥 Horas con más carga:\n"
        f"{latency_block}\n\n"
        "💡 Horas con más cambios:\n"
        f"{changes_block}\n\n"
        "💜 Seguimos vigilando por ti, ARMY\n"
        "✨ Trust the bot",
        reply_markup=build_keyboard(uid)
    )


async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    steps = [10, 20, 35, 70, 90, 100]
    mode = "MANUAL"

    # teclado siempre visible
    await update.message.reply_text("🔎 Preparando revisión… 💜", reply_markup=build_keyboard(uid))

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    msg = await update.message.reply_text(f"⏳ Revisando stock…\n{progress_bar(10)} 10%")

    start = time.perf_counter()
    ts = now_sp_iso()
    hhmm = now_sp_hhmm()

    try:
        # animación
        for pct in steps[1:-1]:
            await asyncio.sleep(0.25)
            ok = await safe_edit(msg, f"⏳ Revisando stock…\n{progress_bar(pct)} {pct}%")
            if not ok:
                msg = await update.message.reply_text(f"⏳ Revisando stock…\n{progress_bar(pct)} {pct}%")

        # request real (en hilo)
        html = await asyncio.to_thread(fetch_page)
        available = bool(is_available(html))
        latency_ms = int((time.perf_counter() - start) * 1000)

        # guardar stats y memoria
        log_check(ts=ts, mode=mode, available=int(available), latency_ms=latency_ms, error=None)
        update_memory(new_status=int(available), check_ts=ts)

        await asyncio.sleep(0.15)
        await safe_edit(msg, f"✅ Listo.\n{progress_bar(100)} 100%") or await update.message.reply_text(
            f"✅ Listo.\n{progress_bar(100)} 100%"
        )
        await asyncio.sleep(0.15)

        if available:
            text = (
                "💜🚨 ARMY ALERT 🚨💜\n\n"
                "🟢 ¡Parece DISPONIBLE ahora!\n\n"
                f"🛒 {PRODUCT_NAME}\n"
                f"🕒 Revisión: {hhmm}\n"
                f"⚡ Respuesta del sitio: {latency_ms/1000:.1f}s\n\n"
                "🔥 Corre ARMY, es ahora 🔥\n"
                f"👉 {PRODUCT_URL}"
            )
            await safe_edit(msg, text) or await update.message.reply_text(text, reply_markup=build_keyboard(uid))
        else:
            text = (
                "💜 ARMY UPDATE 💜\n\n"
                "❌ Aún no hay stock disponible\n"
                f"🛒 {PRODUCT_NAME}\n\n"
                f"🕒 Última revisión: {hhmm}\n"
                f"⚡ Respuesta del sitio: {latency_ms/1000:.1f}s\n\n"
                "⏳ El bot sigue vigilando sin descanso…\n"
                "✨ Mantente lista, ARMY"
            )
            fallback = (
                "❌ Sin stock por ahora, ARMY 💜\n"
                f"🛒 {PRODUCT_NAME}\n"
                f"🕒 {hhmm}\n\n"
                "⏳ Seguimos atentos…"
            )
            await safe_edit(msg, text) or await update.message.reply_text(fallback, reply_markup=build_keyboard(uid))

    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_check(ts=ts, mode=mode, available=0, latency_ms=latency_ms, error=str(e))

        err_text = (
            "🌐⚠️ ARMY UPDATE ⚠️🌐\n\n"
            "Hubo un fallo de red al revisar (normal a veces).\n"
            "✨ Reintentaremos en el próximo ciclo.\n\n"
            f"🕒 {hhmm}\n"
            f"⚡ {latency_ms/1000:.1f}s"
        )
        await safe_edit(msg, err_text) or await update.message.reply_text(err_text, reply_markup=build_keyboard(uid))


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip().lower()
    uid = update.effective_user.id

    # Botones bloqueados (premium)
    if "pico premium" in txt:
        await premium_locked(update, "Modo Pico 🔥")
        return
    if "silencio premium" in txt:
        await premium_locked(update, "Modo Silencio 🔕")
        return

    # Toggles premium
    if "pico" in txt and ("on" in txt or "off" in txt):
        await peak_toggle_cmd(update, context)
        return
    if "silencio" in txt:
        await silent_toggle_cmd(update, context)
        return

    if "check" in txt or "revis" in txt:
        await check_cmd(update, context)
    elif "info" in txt:
        await info_cmd(update, context)
    elif "ping" in txt:
        await ping_cmd(update, context)
    elif "horarios" in txt:
        await horarios_cmd(update, context)
    elif "productos" in txt:
        await products_cmd(update, context)
    else:
        await update.message.reply_text("Usa los botones 👇💜", reply_markup=build_keyboard(uid))