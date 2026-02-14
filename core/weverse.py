# core/weverse.py
import requests
from config import USER_AGENT, PRODUCT_URL

def fetch_page() -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,es;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    r = requests.get(PRODUCT_URL, headers=headers, timeout=25)
    r.raise_for_status()
    return r.text.lower()

def is_available(html: str) -> bool:
    sold_out = ["sold out", "agotado", "esgotado", "out of stock", "inventory 0", "no stock"]
    if any(k in html for k in sold_out):
        return False

    not_ready = ["coming soon", "notify me", "notification", "wait", "preparing", "restock"]
    if any(k in html for k in not_ready):
        return False

    buy = ["add to cart", "checkout", "buy now", "comprar", "adicionar ao carrinho", "finalizar compra", "장바구니"]
    return any(k in html for k in buy)