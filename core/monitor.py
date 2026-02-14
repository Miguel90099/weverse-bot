# core/monitor.py
import asyncio
import time
from datetime import datetime, timezone, timedelta

from config import CHAT_ID, PRODUCT_NAME, PRODUCT_URL, DOUBLE_CONFIRM_WAIT, ALERT_REPEAT
from core.weverse import fetch_page, is_available
from core.scheduler import is_peak_time
from utils.state import is_peak_enabled, is_silent_enabled, get_silent_window
from core.store import init_db, log_check, update_memory

last_status = None
last_check_mode = None  # "PEAK" o "NORMAL"

def now_sp_iso() -> str:
    sp = datetime.now(timezone.utc) + timedelta(hours=-3)
    return sp.strftime("%Y-%m-%d %H:%M:%S")

def now_sp_hhmm() -> str:
    sp = datetime.now(timezone.utc) + timedelta(hours=-3)
    return sp.strftime("%H:%M")

def _hm_to_minutes(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)

def in_silent_window() -> bool:
    if not is_silent_enabled():
        return False

    start_hm, end_hm = get_silent_window()
    start = _hm_to_minutes(start_hm)
    end = _hm_to_minutes(end_hm)

    sp = datetime.now(timezone.utc) + timedelta(hours=-3)
    now = sp.hour * 60 + sp.minute

    if start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end


async def double_confirm_available() -> bool:
    html1 = await asyncio.to_thread(fetch_page)
    if not is_available(html1):
        return False

    await asyncio.sleep(DOUBLE_CONFIRM_WAIT)

    html2 = await asyncio.to_thread(fetch_page)
    return is_available(html2)


async def send_repeated_alerts(context, mode_name: str, latency_ms: int, ts: str):
    silent_now = in_silent_window()
    hhmm = now_sp_hhmm()

    if silent_now:
        header = "💜✅ Restock detectado (modo silencioso)"
    else:
        header = "💜🚨 ARMY ALERT 🚨💜"

    msg = (
        f"{header}\n\n"
        "🟢 ¡RESTOCK CONFIRMADO! ✨\n\n"
        f"🛒 {PRODUCT_NAME}\n"
        f"🕒 {hhmm} (SP)\n"
        f"🧠 Modo: {mode_name}\n"
        f"⚡ Respuesta: {latency_ms}ms\n\n"
        "🔥 CORRE ARMY, ES AHORA 🔥\n"
        f"👉 {PRODUCT_URL}"
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=msg)

    # Si está en silencio, no repetimos spam
    if silent_now:
        return

    for i in range(2, ALERT_REPEAT + 1):
        await asyncio.sleep(10)
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=f"🚨 ({i}/{ALERT_REPEAT}) ¡Sigue intentando! 👉 {PRODUCT_URL}"
        )


async def _run_check(context, mode_name: str):
    global last_status, last_check_mode
    init_db()
    last_check_mode = mode_name

    ts = now_sp_iso()
    start = time.perf_counter()

    try:
        html = await asyncio.to_thread(fetch_page)
        current = bool(is_available(html))
        latency_ms = int((time.perf_counter() - start) * 1000)

        # log + memoria
        log_check(ts=ts, mode=mode_name, available=int(current), latency_ms=latency_ms, error=None)
        update_memory(new_status=int(current), check_ts=ts)

        if last_status is None:
            last_status = current
            return

        # 🔴 -> 🟢 : confirmar doble y avisar
        if (not last_status) and current:
            if await double_confirm_available():
                await send_repeated_alerts(context, mode_name=mode_name, latency_ms=latency_ms, ts=ts)
                last_status = True
                return

        last_status = current

    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_check(ts=ts, mode=mode_name, available=0, latency_ms=latency_ms, error=str(e))
        return


async def monitor_peak(context):
    # Solo corre si el usuario activó el modo pico
    if not is_peak_enabled():
        return
    # y solo en hora pico real
    if not is_peak_time():
        return
    await _run_check(context, "PEAK")


async def monitor_normal(context):
    # Siempre corre fuera de pico, o cuando pico está desactivado
    if is_peak_enabled() and is_peak_time():
        return
    await _run_check(context, "NORMAL")


def get_last_mode() -> str:
    return last_check_mode or "N/A"