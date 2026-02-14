# core/scheduler.py
from datetime import datetime, time
from config import BASE_SECONDS, PEAK_SECONDS

# Picos (Brasil São Paulo):
# 20:30–02:30 y 05:30–06:30
PEAK_WINDOWS = [
    (time(20, 30), time(2, 30)),  # cruza medianoche
    (time(5, 30), time(6, 30)),
]

def _in_window(now_t: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= now_t <= end
    return now_t >= start or now_t <= end  # cruza medianoche

def is_peak_time() -> bool:
    now_t = datetime.now().time()  # usa hora del cel (São Paulo)
    return any(_in_window(now_t, s, e) for s, e in PEAK_WINDOWS)

def current_interval_seconds() -> int:
    return PEAK_SECONDS if is_peak_time() else BASE_SECONDS