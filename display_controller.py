#!/usr/bin/env python3
"""
display_controller.py - Main display loop
Fetches crypto price from CoinGecko and renders it on the Waveshare e-Paper display.
Handles offline mode, price alerts with custom sounds, and buzzer integration.
"""

import sys, json, time, logging, socket, signal
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests

BASE_DIR    = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE    = BASE_DIR / "logs" / "display.log"

LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

sys.path.insert(0, str(BASE_DIR / "waveshare_epd"))

FIAT_SYMBOLS = {"usd": "$", "eur": "€", "brl": "R$", "gbp": "£", "jpy": "¥"}


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        cfg.setdefault("crypto",            "bitcoin")
        cfg.setdefault("fiat",              "usd")
        cfg.setdefault("interval_sec",      300)
        cfg.setdefault("display_model",     "epd2in13_V2")
        cfg.setdefault("buzzer_ativo",      False)
        cfg.setdefault("buzzer_gpio",       18)
        cfg.setdefault("buzzer_volume",     80)
        cfg.setdefault("buzzer_wpm",        15)
        cfg.setdefault("buzzer_pattern",    "")
        cfg.setdefault("alerta_acima",      0)
        cfg.setdefault("alerta_abaixo",     0)
        cfg.setdefault("alerta_disparado",  False)
        cfg.setdefault("cores_invertidas",  False)
        cfg.setdefault("sound_high",        "3")    # sound when price goes above threshold
        cfg.setdefault("sound_low",         "5")    # sound when price goes below threshold
        cfg["fiat_symbol"] = FIAT_SYMBOLS.get(cfg["fiat"], cfg["fiat"].upper())
        return cfg
    except Exception as e:
        log.warning(f"Config load error: {e}")
        return {
            "crypto": "bitcoin", "fiat": "usd", "fiat_symbol": "$",
            "interval_sec": 300, "display_model": "epd2in13_V2",
            "buzzer_ativo": False, "buzzer_gpio": 18,
            "buzzer_volume": 80, "buzzer_wpm": 15, "buzzer_pattern": "",
            "alerta_acima": 0, "alerta_abaixo": 0,
            "alerta_disparado": False, "cores_invertidas": False,
            "sound_high": "3", "sound_low": "5",
        }


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log.error(f"Config save error: {e}")


def is_online() -> bool:
    """Check internet connectivity via TCP probe to Google DNS."""
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False


def fetch_price(crypto: str, fiat: str):
    """Fetch current price and 24h change from CoinGecko."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": crypto, "vs_currencies": fiat, "include_24hr_change": "true"},
            timeout=10,
        )
        d = r.json().get(crypto, {})
        price = d.get(fiat, 0)
        if price == 0:
            return None
        return {"price": price, "change_24h": d.get(f"{fiat}_24h_change", 0)}
    except Exception as e:
        log.error(f"API fetch error: {e}")
        return None


def format_price(symbol: str, price: float) -> str:
    if price >= 1000:   return f"{symbol}{price:,.0f}"
    elif price >= 1:    return f"{symbol}{price:,.2f}"
    else:               return f"{symbol}{price:.4f}"


def play_alert(cfg: dict, pattern: str):
    """Play a buzzer alert with the given pattern."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from buzzer_controller import tocar_alerta
        tocar_alerta(
            gpio    = cfg["buzzer_gpio"],
            pattern = pattern,
            volume  = cfg.get("buzzer_volume", 80),
            wpm     = cfg.get("buzzer_wpm", 15),
        )
    except Exception as e:
        log.warning(f"Buzzer alert failed: {e}")


def check_alerts(cfg: dict, price: float):
    """Fire buzzer alerts if price crosses defined thresholds."""
    if not cfg.get("buzzer_ativo") or cfg.get("alerta_disparado"):
        return

    acima  = float(cfg.get("alerta_acima",  0))
    abaixo = float(cfg.get("alerta_abaixo", 0))

    if acima > 0 and price >= acima:
        log.info(f"ALERT HIGH: {price} >= {acima} — playing: {cfg.get('sound_high', '3')}")
        play_alert(cfg, cfg.get("sound_high", "3"))
        cfg["alerta_disparado"] = True
        save_config(cfg)

    elif abaixo > 0 and price <= abaixo:
        log.info(f"ALERT LOW: {price} <= {abaixo} — playing: {cfg.get('sound_low', '5')}")
        play_alert(cfg, cfg.get("sound_low", "5"))
        cfg["alerta_disparado"] = True
        save_config(cfg)


# ── Rendering ──────────────────────────────────────────────────────────────────

def _base_image(cfg: dict, W: int, H: int):
    inv  = cfg.get("cores_invertidas", False)
    bg   = 255 if inv else 0
    fg   = 0   if inv else 1
    img  = Image.new("1", (W, H), bg)
    draw = ImageDraw.Draw(img)
    return img, draw, fg, bg


def render_price(cfg: dict, data: dict, W: int, H: int) -> Image.Image:
    """Render normal price screen."""
    img, draw, fg, bg = _base_image(cfg, W, H)

    font_big = ImageFont.load_default(size=62)
    font_med = ImageFont.load_default(size=14)
    font_sml = ImageFont.load_default(size=11)

    draw.rectangle([0, 0, W-1, H-1], outline=fg, width=2)
    draw.line([0, 38, W, 38], fill=fg, width=2)

    change   = data["change_24h"]
    arrow    = "^" if change >= 0 else "v"
    time_str = datetime.now().strftime("%H:%M")
    alert    = " !" if cfg.get("buzzer_ativo") else ""

    draw.text((8,   6),  cfg["crypto"].upper() + alert, font=font_med, fill=fg)
    draw.text((8,  22),  f"{arrow} {abs(change):.2f}%", font=font_sml, fill=fg)
    draw.text((175, 6),  cfg["fiat"].upper(),            font=font_sml, fill=fg)
    draw.text((165, 22), time_str,                       font=font_sml, fill=fg)

    price_str = format_price(cfg["fiat_symbol"], data["price"])
    bbox = draw.textbbox((0, 0), price_str, font=font_big)
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - pw) // 2, 38 + (84 - ph) // 2), price_str, font=font_big, fill=fg)

    return img


def render_offline(cfg: dict, last_data, W: int, H: int) -> Image.Image:
    """Render offline screen showing last known price."""
    img, draw, fg, bg = _base_image(cfg, W, H)

    font_big = ImageFont.load_default(size=48)
    font_med = ImageFont.load_default(size=14)
    font_sml = ImageFont.load_default(size=11)

    draw.rectangle([0, 0, W-1, H-1], outline=fg, width=2)

    draw.rectangle([0, 0, W, 22], fill=fg)
    banner = "** OFFLINE **"
    bbox = draw.textbbox((0, 0), banner, font=font_med)
    bw = bbox[2] - bbox[0]
    draw.text(((W - bw) // 2, 4), banner, font=font_med, fill=bg)

    draw.line([0, 38, W, 38], fill=fg, width=1)

    time_str = datetime.now().strftime("%H:%M")
    draw.text((8,   25), cfg["crypto"].upper(), font=font_sml, fill=fg)
    draw.text((175, 25), time_str,              font=font_sml, fill=fg)

    if last_data and last_data.get("price", 0) > 0:
        price_str = format_price(cfg["fiat_symbol"], last_data["price"])
        bbox = draw.textbbox((0, 0), price_str, font=font_big)
        pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((W - pw) // 2, 40 + (80 - ph) // 2), price_str, font=font_big, fill=fg)
        note = "last known price"
        bbox2 = draw.textbbox((0, 0), note, font=font_sml)
        nw = bbox2[2] - bbox2[0]
        draw.text(((W - nw) // 2, H - 14), note, font=font_sml, fill=fg)
    else:
        no_data = "no data"
        bbox = draw.textbbox((0, 0), no_data, font=font_med)
        nw = bbox[2] - bbox[0]
        draw.text(((W - nw) // 2, 60), no_data, font=font_med, fill=fg)

    return img


# ── Main loop ──────────────────────────────────────────────────────────────────

class CryptoDisplay:
    def __init__(self):
        self.running     = True
        self.epd         = None
        self.W           = 0
        self.H           = 0
        self.last_data   = None
        self.was_offline = False
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT,  self._shutdown)

    def _shutdown(self, *_):
        log.info("Shutdown signal received.")
        self.running = False
        if self.epd:
            try: self.epd.sleep()
            except Exception: pass
        sys.exit(0)

    def run(self):
        log.info("=== Crypto E-Paper starting ===")
        from epd2in13_V2 import EPD
        self.epd = EPD()
        self.epd.init(self.epd.FULL_UPDATE)
        self.epd.Clear(0xFF)
        self.W, self.H = 250, 122
        log.info(f"Display ready {self.W}x{self.H}")

        while self.running:
            cfg    = load_config()
            online = is_online()

            if online:
                data = fetch_price(cfg["crypto"], cfg["fiat"])
                if data:
                    self.last_data   = data
                    self.was_offline = False
                    check_alerts(cfg, data["price"])
                    img = render_price(cfg, data, self.W, self.H)
                    log.info(f"[{cfg['crypto'].upper()}] {cfg['fiat_symbol']}{data['price']:,.2f} ({data['change_24h']:+.2f}%)")
                else:
                    img = render_offline(cfg, self.last_data, self.W, self.H)
                    log.warning("Online but API returned no data — showing last known price")
            else:
                if not self.was_offline:
                    log.warning("No internet — switching to offline screen")
                    self.was_offline = True
                img = render_offline(cfg, self.last_data, self.W, self.H)

            self.epd.init(self.epd.FULL_UPDATE)
            self.epd.display(self.epd.getbuffer(img))
            self.epd.sleep()

            interval = max(60, int(cfg.get("interval_sec", 300)))
            log.info(f"online={online} | next update in {interval}s")
            time.sleep(interval)


if __name__ == "__main__":
    CryptoDisplay().run()
