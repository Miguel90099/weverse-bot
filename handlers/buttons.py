# handlers/buttons.py
from telegram import ReplyKeyboardMarkup
from config import BASE_SECONDS, PEAK_SECONDS
from utils.state import is_peak_enabled, is_silent_enabled
from utils.premium import is_premium

def build_keyboard(user_id: int):
    premium = is_premium(user_id)

    # Botón Pico (premium)
    if premium:
        pico_btn = f"🟢 Pico ON ({PEAK_SECONDS}s)" if is_peak_enabled() else f"⚫ Pico OFF ({BASE_SECONDS}s)"
    else:
        pico_btn = "🔒 Pico Premium"

    # Botón Silencio (premium)
    if premium:
        silent_btn = "🔕 Silencio: ON" if is_silent_enabled() else "🔔 Silencio: OFF"
    else:
        silent_btn = "🔒 Silencio Premium"

    return ReplyKeyboardMarkup(
        [
            ["🔎 Check", "📋 Info"],
            ["⏰ Horarios", pico_btn],
            ["📦 Productos", silent_btn],
            ["🏓 Ping"],
        ],
        resize_keyboard=True
    )