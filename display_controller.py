#!/usr/bin/env python3
"""
display_controller.py - Main display loop
Modes:
  - price  : shows live crypto price + 24h change
  - wallet : shows wallet balance in crypto + fiat value
Handles offline (no internet) and no-wifi states with instructions on display.
"""

import sys, json, time, logging, socket, signal, subprocess, threading
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

# Wallet API endpoints
WALLET_APIS = {
    "bitcoin":  "https://blockchain.info/q/addressbalance/{address}?confirmations=1",
    "ethereum": "https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest",
    "solana":   "https://api.mainnet-beta.solana.com",
}


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        cfg.setdefault("crypto",           "bitcoin")
        cfg.setdefault("fiat",             "usd")
        cfg.setdefault("interval_sec",     300)
        cfg.setdefault("display_model",    "epd2in13_V2")
        cfg.setdefault("buzzer_ativo",     False)
        cfg.setdefault("buzzer_gpio",      18)
        cfg.setdefault("buzzer_volume",    80)
        cfg.setdefault("buzzer_wpm",       15)
        cfg.setdefault("buzzer_pattern",   "")
        cfg.setdefault("sound_high",       "3")
        cfg.setdefault("sound_low",        "5")
        cfg.setdefault("alerta_acima",     0)
        cfg.setdefault("alerta_abaixo",    0)
        cfg.setdefault("alerta_disparado", False)
        cfg.setdefault("cores_invertidas", False)
        cfg.setdefault("display_mode",     "price")   # "price" or "wallet"
        cfg.setdefault("wallet_address",   "")
        cfg.setdefault("wallet_network",   "bitcoin") # bitcoin / ethereum / solana
        cfg.setdefault("ap_ssid",          "crypto-epaper")
        cfg.setdefault("ap_pass",          "bitcoin123")
        cfg["fiat_symbol"] = FIAT_SYMBOLS.get(cfg["fiat"], cfg["fiat"].upper())
        return cfg
    except Exception as e:
        log.warning(f"Config load error: {e}")
        return {
            "crypto": "bitcoin", "fiat": "usd", "fiat_symbol": "$",
            "interval_sec": 300, "display_model": "epd2in13_V2",
            "buzzer_ativo": False, "buzzer_gpio": 18,
            "buzzer_volume": 80, "buzzer_wpm": 15, "buzzer_pattern": "",
            "sound_high": "3", "sound_low": "5",
            "alerta_acima": 0, "alerta_abaixo": 0,
            "alerta_disparado": False, "cores_invertidas": False,
            "display_mode": "price", "wallet_address": "", "wallet_network": "bitcoin",
            "ap_ssid": "crypto-epaper", "ap_pass": "bitcoin123",
        }


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log.error(f"Config save error: {e}")


def is_wifi_connected() -> bool:
    """Check if wlan0 is associated to any AP."""
    try:
        result = subprocess.run(
            ["iwgetid", "-r"], capture_output=True, text=True, timeout=3
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def is_online() -> bool:
    """Check internet connectivity via TCP probe."""
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
        log.error(f"Price fetch error: {e}")
        return None


def fetch_wallet_balance(network: str, address: str) -> float | None:
    """Fetch wallet balance in native units (BTC, ETH, SOL)."""
    try:
        if network == "bitcoin":
            r = requests.get(
                f"https://blockchain.info/q/addressbalance/{address}?confirmations=1",
                timeout=10
            )
            satoshis = int(r.text.strip())
            return satoshis / 1e8  # satoshis to BTC

        elif network == "ethereum":
            r = requests.get(
                "https://api.etherscan.io/api",
                params={"module": "account", "action": "balance",
                        "address": address, "tag": "latest"},
                timeout=10
            )
            d = r.json()
            if d.get("status") == "1":
                return int(d["result"]) / 1e18  # wei to ETH
            return None

        elif network == "solana":
            r = requests.post(
                "https://api.mainnet-beta.solana.com",
                json={"jsonrpc": "2.0", "id": 1, "method": "getBalance",
                      "params": [address]},
                timeout=10
            )
            lamports = r.json()["result"]["value"]
            return lamports / 1e9  # lamports to SOL

    except Exception as e:
        log.error(f"Wallet fetch error ({network}): {e}")
        return None


def format_price(symbol: str, price: float) -> str:
    if price >= 1000:   return f"{symbol}{price:,.0f}"
    elif price >= 1:    return f"{symbol}{price:,.2f}"
    else:               return f"{symbol}{price:.4f}"


def format_balance(balance: float, network: str) -> str:
    symbols = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}
    sym = symbols.get(network, "")
    if balance >= 1:    return f"{balance:.4f} {sym}"
    elif balance > 0:   return f"{balance:.6f} {sym}"
    else:               return f"0.000000 {sym}"


def short_address(address: str) -> str:
    """Returns first 6 + ... + last 6 chars of address."""
    if len(address) <= 14:
        return address
    return f"{address[:6]}...{address[-6:]}"


def play_alert(cfg, pattern):
    try:
        sys.path.insert(0, str(BASE_DIR))
        from buzzer_controller import tocar_alerta
        tocar_alerta(gpio=cfg["buzzer_gpio"], pattern=pattern,
                     volume=cfg.get("buzzer_volume", 80), wpm=cfg.get("buzzer_wpm", 15))
    except Exception as e:
        log.warning(f"Buzzer alert failed: {e}")


def check_alerts(cfg, price):
    if not cfg.get("buzzer_ativo") or cfg.get("alerta_disparado"):
        return
    acima  = float(cfg.get("alerta_acima",  0))
    abaixo = float(cfg.get("alerta_abaixo", 0))
    if acima > 0 and price >= acima:
        log.info(f"ALERT HIGH: {price} >= {acima}")
        play_alert(cfg, cfg.get("sound_high", "3"))
        cfg["alerta_disparado"] = True
        save_config(cfg)
    elif abaixo > 0 and price <= abaixo:
        log.info(f"ALERT LOW: {price} <= {abaixo}")
        play_alert(cfg, cfg.get("sound_low", "5"))
        cfg["alerta_disparado"] = True
        save_config(cfg)


# ── Rendering ──────────────────────────────────────────────────────────────────

def _base_image(cfg, W, H):
    inv  = cfg.get("cores_invertidas", False)
    bg   = 255 if inv else 0
    fg   = 0   if inv else 1
    img  = Image.new("1", (W, H), bg)
    draw = ImageDraw.Draw(img)
    return img, draw, fg, bg


def render_price(cfg, data, W, H) -> Image.Image:
    img, draw, fg, bg = _base_image(cfg, W, H)
    font_big = ImageFont.load_default(size=58)
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
    y_price = min(122 - ph - 4, 50)
    draw.text(((W - pw) // 2, y_price), price_str, font=font_big, fill=fg)
    return img


def render_wallet(cfg, balance, price_data, W, H) -> Image.Image:
    """Render wallet screen: network, short address, balance, fiat value.
    wallet_primary: 'crypto' = big crypto / small fiat (default)
                    'fiat'   = big fiat   / small crypto
    """
    img, draw, fg, bg = _base_image(cfg, W, H)
    font_big = ImageFont.load_default(size=36)
    font_med = ImageFont.load_default(size=16)
    font_sml = ImageFont.load_default(size=10)

    draw.rectangle([0, 0, W-1, H-1], outline=fg, width=2)
    draw.line([0, 22, W, 22], fill=fg, width=1)

    network  = cfg.get("wallet_network", "bitcoin")
    address  = cfg.get("wallet_address", "")
    time_str = datetime.now().strftime("%H:%M")
    primary  = cfg.get("wallet_primary", "crypto")  # "crypto" or "fiat"
    net_labels = {"bitcoin": "BTC WALLET", "ethereum": "ETH WALLET", "solana": "SOL WALLET"}

    # Header
    draw.text((8, 6),   net_labels.get(network, "WALLET"), font=font_sml, fill=fg)
    draw.text((185, 6), time_str,                           font=font_sml, fill=fg)

    # Short address
    draw.text((8, 26), short_address(address), font=font_sml, fill=fg)

    draw.line([0, 40, W, 40], fill=fg, width=1)

    bal_str  = format_balance(balance, network)
    fiat_str = ""
    if price_data and balance is not None:
        fiat_val = balance * price_data["price"]
        fiat_str = format_price(cfg["fiat_symbol"], fiat_val)

    if primary == "fiat":
        big_str   = fiat_str if fiat_str else "---"
        small_str = bal_str
    else:
        big_str   = bal_str
        small_str = fiat_str if fiat_str else ""

    # Big value
    bbox = draw.textbbox((0, 0), big_str, font=font_big)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - bw) // 2, 44), big_str, font=font_big, fill=fg)

    # Small value below
    if small_str:
        bbox2 = draw.textbbox((0, 0), small_str, font=font_med)
        sw = bbox2[2] - bbox2[0]
        draw.text(((W - sw) // 2, 44 + bh + 6), small_str, font=font_med, fill=fg)

    return img


def render_offline(cfg, last_data, W, H) -> Image.Image:
    """Render offline screen — internet connected but API unavailable."""
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
    draw.text((8, 25),   cfg["crypto"].upper(), font=font_sml, fill=fg)
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


def render_no_wifi(cfg, W, H) -> Image.Image:
    """Render no-wifi screen with hotspot instructions."""
    img, draw, fg, bg = _base_image(cfg, W, H)
    font_med = ImageFont.load_default(size=13)
    font_sml = ImageFont.load_default(size=10)
    font_xs  = ImageFont.load_default(size=9)

    draw.rectangle([0, 0, W-1, H-1], outline=fg, width=2)

    # Header banner
    draw.rectangle([0, 0, W, 20], fill=fg)
    title = "** NO WI-FI **"
    bbox = draw.textbbox((0, 0), title, font=font_med)
    bw = bbox[2] - bbox[0]
    draw.text(((W - bw) // 2, 3), title, font=font_med, fill=bg)

    draw.line([0, 40, W, 40], fill=fg, width=1)

    ap_ssid = cfg.get("ap_ssid", "crypto-epaper")
    ap_pass = cfg.get("ap_pass", "bitcoin123")

    # Instructions
    lines = [
        "Create a phone hotspot:",
        f"SSID: {ap_ssid}",
        f"Pass: {ap_pass}",
        "Then access the dashboard",
    ]
    y = 24
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_xs)
        lw = bbox[2] - bbox[0]
        draw.text(((W - lw) // 2, y), line, font=font_xs, fill=fg)
        y += 12

    draw.line([0, 80, W, 80], fill=fg, width=1)

    time_str = datetime.now().strftime("%H:%M")
    draw.text((8, 84),   "http://cripto.local:8080", font=font_xs, fill=fg)
    draw.text((205, 84), time_str,                   font=font_xs, fill=fg)

    return img


def render_qr(cfg, W, H) -> Image.Image:
    """Render QR code of wallet address."""
    img, draw, fg, bg = _base_image(cfg, W, H)
    font_sml = ImageFont.load_default(size=10)
    font_xs  = ImageFont.load_default(size=9)

    address = cfg.get("wallet_address", "").strip()
    network = cfg.get("wallet_network", "bitcoin")
    net_labels = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}
    label = net_labels.get(network, "WALLET")

    draw.rectangle([0, 0, W-1, H-1], outline=fg, width=2)

    if not address:
        draw.text((8, 50), "No wallet address set", font=font_sml, fill=fg)
        return img

    try:
        import qrcode
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                           box_size=2, border=1)
        qr.add_data(address)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black" if fg == 0 else "white",
                               back_color="white" if bg == 255 else "black")
        qr_img = qr_img.convert("L")
        qr_size = min(H - 8, 112)
        qr_img  = qr_img.resize((qr_size, qr_size), Image.NEAREST)
        img.paste(qr_img, (4, (H - qr_size) // 2))

        # Address and label on the right
        x_text = qr_size + 10
        draw.text((x_text, 8),  label,                       font=font_sml, fill=fg)
        draw.text((x_text, 22), "Wallet",                    font=font_xs,  fill=fg)
        draw.line([x_text, 34, W - 4, 34], fill=fg, width=1)
        # Short address split into chunks
        short = address[:6] + ".." + address[-6:]
        draw.text((x_text, 38), short, font=font_xs, fill=fg)

    except ImportError:
        # qrcode not installed — show address as text
        draw.text((8, 6), f"{label} ADDRESS", font=font_sml, fill=fg)
        draw.line([0, 20, W, 20], fill=fg, width=1)
        # Split address into lines of ~20 chars
        y = 26
        chunk = 22
        for i in range(0, min(len(address), chunk * 4), chunk):
            draw.text((4, y), address[i:i+chunk], font=font_xs, fill=fg)
            y += 12
        draw.text((4, H - 14), "pip install qrcode[pil]", font=font_xs, fill=fg)

    return img


# ── Main loop ──────────────────────────────────────────────────────────────────

class CryptoDisplay:
    BUTTON_GPIO = 26
    MODES       = ["price", "wallet", "qr"]

    def __init__(self):
        self.running      = True
        self.epd          = None
        self.W            = 0
        self.H            = 0
        self.last_data    = None
        self.last_balance = None
        self.was_offline  = False
        self.was_no_wifi  = False
        self._button_pressed = False
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT,  self._shutdown)

    def _shutdown(self, *_):
        log.info("Shutdown signal received.")
        self.running = False
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except Exception:
            pass
        if self.epd:
            try: self.epd.sleep()
            except Exception: pass
        sys.exit(0)

    def _setup_button(self):
        """Setup GPIO button with interrupt — press cycles through modes."""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            # Clean up this pin only in case of leftover state from previous run
            try:
                GPIO.remove_event_detect(self.BUTTON_GPIO)
            except Exception:
                pass
            try:
                GPIO.cleanup(self.BUTTON_GPIO)
            except Exception:
                pass
            GPIO.setup(self.BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self.BUTTON_GPIO, GPIO.FALLING,
                                  callback=self._on_button, bouncetime=400)
            log.info(f"Button ready on GPIO {self.BUTTON_GPIO}")
        except Exception as e:
            log.warning(f"Button setup failed: {e}")

    def _on_button(self, channel):
        """Cycle to next display mode on button press."""
        cfg  = load_config()
        cur  = cfg.get("display_mode", "price")
        # Only cycle between price/wallet if no wallet address set
        address = cfg.get("wallet_address", "").strip()
        modes = self.MODES if address else ["price", "wallet"]
        try:
            idx = modes.index(cur)
        except ValueError:
            idx = 0
        next_mode = modes[(idx + 1) % len(modes)]
        cfg["display_mode"] = next_mode
        save_config(cfg)
        self._button_pressed = True
        log.info(f"Button pressed — switching to mode: {next_mode}")

    def run(self):
        log.info("=== Crypto E-Paper starting ===")
        from epd2in13_V2 import EPD
        self.epd = EPD()
        self.epd.init(self.epd.FULL_UPDATE)
        self.epd.Clear(0xFF)
        self.W, self.H = 250, 122
        log.info(f"Display ready {self.W}x{self.H}")
        self._setup_button()

        while self.running:
            self._button_pressed = False  # reset flag at start of each cycle
            cfg  = load_config()
            mode = cfg.get("display_mode", "price")

            wifi   = is_wifi_connected()
            online = is_online() if wifi else False

            # ── No Wi-Fi ──────────────────────────────────────────────────────
            if not wifi:
                if not self.was_no_wifi:
                    log.warning("No Wi-Fi — showing hotspot instructions")
                    self.was_no_wifi = True
                img = render_no_wifi(cfg, self.W, self.H)

            # ── Wi-Fi but no internet ─────────────────────────────────────────
            elif not online:
                if not self.was_offline:
                    log.warning("Wi-Fi connected but no internet")
                    self.was_offline  = True
                    self.was_no_wifi  = False
                img = render_offline(cfg, self.last_data, self.W, self.H)

            # ── Online ────────────────────────────────────────────────────────
            else:
                self.was_offline = False
                self.was_no_wifi = False

                if mode == "qr":
                    img = render_qr(cfg, self.W, self.H)
                    log.info("[QR] Showing wallet QR code")

                elif mode == "wallet":
                    network = cfg.get("wallet_network", "bitcoin")
                    address = cfg.get("wallet_address", "").strip()

                    if not address:
                        log.warning("Wallet mode selected but no address configured")
                        data = fetch_price(cfg["crypto"], cfg["fiat"])
                        if data:
                            self.last_data = data
                            check_alerts(cfg, data["price"])
                            img = render_price(cfg, data, self.W, self.H)
                        else:
                            img = render_offline(cfg, self.last_data, self.W, self.H)
                    else:
                        # Map wallet network to CoinGecko id
                        cg_id = {"bitcoin": "bitcoin", "ethereum": "ethereum", "solana": "solana"}.get(network, network)
                        price_data = fetch_price(cg_id, cfg["fiat"])
                        balance    = fetch_wallet_balance(network, address)

                        if balance is not None:
                            self.last_balance = balance
                            if price_data:
                                self.last_data = price_data
                            img = render_wallet(cfg, balance, price_data or self.last_data, self.W, self.H)
                            log.info(f"[WALLET] {format_balance(balance, network)} = "
                                     f"{cfg['fiat_symbol']}{(balance * (price_data or self.last_data or {}).get('price', 0)):,.2f}")
                        else:
                            img = render_offline(cfg, self.last_data, self.W, self.H)

                else:  # mode == "price"
                    data = fetch_price(cfg["crypto"], cfg["fiat"])
                    if data:
                        self.last_data = data
                        check_alerts(cfg, data["price"])
                        img = render_price(cfg, data, self.W, self.H)
                        log.info(f"[{cfg['crypto'].upper()}] {cfg['fiat_symbol']}{data['price']:,.2f} ({data['change_24h']:+.2f}%)")
                    else:
                        img = render_offline(cfg, self.last_data, self.W, self.H)
                        log.warning("API returned no data")

            self.epd.init(self.epd.FULL_UPDATE)
            self.epd.display(self.epd.getbuffer(img))
            self.epd.sleep()

            interval = max(60, int(cfg.get("interval_sec", 300)))
            log.info(f"wifi={wifi} online={online} mode={mode} | next in {interval}s")

            # Wait for interval but wake immediately on button press
            elapsed = 0
            while self.running and elapsed < interval:
                time.sleep(0.2)
                elapsed += 0.2
                if self._button_pressed:
                    log.info("Button press detected — refreshing now")
                    break


if __name__ == "__main__":
    CryptoDisplay().run()
