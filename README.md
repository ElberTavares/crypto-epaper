<div align="center">

```
 ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗
██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗
██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║
██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║
╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝
 ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝
 ███████╗      ██████╗  █████╗ ██████╗ ███████╗██████╗
 ██╔════╝     ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
 █████╗ █████╗██████╔╝███████║██████╔╝█████╗  ██████╔╝
 ██╔══╝ ╚════╝██╔═══╝ ██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
 ███████╗     ██║     ██║  ██║██║     ███████╗██║  ██║
 ╚══════╝     ╚═╝     ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
```

**Real-time cryptocurrency price display for Raspberry Pi Zero W + Waveshare 2.12" e-Paper**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Zero%20W-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white)](https://raspberrypi.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![API](https://img.shields.io/badge/API-CoinGecko-8DC647?style=flat-square)](https://coingecko.com)

</div>

---

## 📸 Display Preview

**Online — normal operation:**

<img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/d83b8c6e-ff93-4a57-8bf5-1c76b655ec40" />

**Offline — no internet connection:**

<img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/1e5453f0-100e-4eb3-a2c0-c45c07376af0" />

**Wallet monitor:**

<img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/a69cae56-f937-448d-9a39-d6995ef0c0bd" />


> The `!` indicator appears when price alerts are active.
> When offline, the display shows the last known price until internet is restored.

---

## ✨ Features

- 📈 **Live prices** — fetches Bitcoin, Ethereum, Solana and more from CoinGecko
- 💼 **Wallet monitor** — track a BTC, ETH or SOL wallet balance and its fiat value in real time
- 🌍 **Multi-currency** — USD, BRL, EUR, GBP, JPY
- ⏱️ **Configurable interval** — update every 1 minute up to 1 hour
- 🎨 **Display themes** — switch between normal (black bg) and inverted (white bg)
- 📡 **Offline mode** — shows last known price with offline indicator when disconnected
- 📶 **No Wi-Fi screen** — displays hotspot instructions so you can connect and configure the device
- 🔄 **Wi-Fi watchdog** — auto-reconnects every 2 minutes; falls back to a phone hotspot if saved network is unavailable
- 🌐 **Wi-Fi setup page** — scan networks and connect to a new Wi-Fi directly from the dashboard
- 🔔 **Price alerts** — buzzer sounds when price crosses a high or low threshold
- 🔊 **Custom alert sounds** — separate configurable sound for price-up and price-down alerts
- 🎵 **Morse code & beep sequences** — type any text or numbers to play on the buzzer
- 👁️ **Live preview** — visual dot/dash preview before playing Morse in the browser
- 🔁 **Auto-start on boot** — systemd services keep everything running 24/7
- 💾 **Low power** — optimized for continuous operation on Pi Zero W

---

## 🔩 Required Hardware

| Component | Details |
|---|---|
| **Raspberry Pi Zero W** | Must have Wi-Fi. Pi Zero 2 W also works. |
| **Waveshare e-Paper HAT 2.12"** | Version V2 or V3 (250×122 px, SPI) |
| **MicroSD card** | Minimum 8 GB, Class 10 or better |
| **Power supply** | 5V / 1A via Micro USB — stable regulated supply recommended |
| **Buzzer** *(optional)* | Active buzzer 3.3V — or passive buzzer for volume control |

### Where to buy

- Waveshare 2.12" e-Paper HAT — [waveshare.com](https://www.waveshare.com/2.13inch-e-paper-hat.htm) or AliExpress
- Raspberry Pi Zero W — [raspberrypi.com](https://www.raspberrypi.com/products/raspberry-pi-zero-w/) or local electronics stores
- Active buzzer 3.3V — any electronics or hobby store (~$0.50)

### Active vs Passive Buzzer

| Type | Volume Control | Notes |
|---|---|---|
| **Active** | ❌ Fixed | Simplest — just needs on/off signal |
| **Passive** | ✅ Via PWM | Enable PWM mode in dashboard settings |

### Display Wiring

The HAT plugs directly onto the 40-pin GPIO header — **no wiring needed**.
If connecting with jumper wires:

| HAT Pin | GPIO Pin | Function |
|---------|----------|----------|
| VCC     | Pin 17   | 3.3V     |
| GND     | Pin 20   | GND      |
| DIN     | Pin 19   | SPI MOSI |
| CLK     | Pin 23   | SPI CLK  |
| CS      | Pin 24   | SPI CE0  |
| DC      | Pin 22   | GPIO 25  |
| RST     | Pin 11   | GPIO 17  |
| BUSY    | Pin 18   | GPIO 24  |

### Buzzer Wiring

```
Buzzer (+) long leg  ──── GPIO 18 (Pin 12)
Buzzer (-) short leg ──── GND     (Pin 14)
```

### Power Supply Notes

The Pi Zero W is sensitive to voltage drops, especially during boot. For stable operation:

- Use a **regulated 5V / 1A** power supply (phone charger works well)
- If powering via the GPIO pads (PP1/PP6), use **thick wire (24 AWG or lower gauge number)**
- A **1000µF electrolytic capacitor** in parallel with the power rails helps absorb voltage dips:
  ```
  Capacitor (+) ──── 5V (PP1 or Pin 2)
  Capacitor (-) ──── GND (PP6 or Pin 6)
  ```
- 2 slow blinks on the green LED = under-voltage warning — check your power supply

---

## 💿 OS Setup

### 1. Flash the OS

Use **[Raspberry Pi Imager](https://rpi.imager.io)**:

1. Select **Raspberry Pi OS Lite (32-bit)** — Bookworm (Debian 12) recommended
2. Click ⚙️ and configure:
   - Hostname: `crypto-epaper`
   - Enable SSH
   - Wi-Fi SSID and password
   - Username and password
3. Flash to SD card

### 2. First boot & SSH

```bash
ssh pi@crypto-epaper.local
passwd   # change default password immediately
```

### 3. Enable SPI

```bash
sudo raspi-config nonint do_spi 0 && sudo reboot
```

---

## ⚙️ Installation

```bash
git clone https://github.com/ElberTavares/crypto-epaper.git ~/crypto-epaper/files
cd ~/crypto-epaper/files
bash setup.sh
sudo reboot
```

The setup script handles everything: system packages, Waveshare driver, fonts, Python virtualenv, dependencies, and systemd services.

### Set up Wi-Fi watchdog (recommended)

```bash
sudo cp wifi-watchdog.sh /usr/local/bin/wifi-watchdog.sh
sudo chmod +x /usr/local/bin/wifi-watchdog.sh
(sudo crontab -l 2>/dev/null; echo '*/2 * * * * /usr/local/bin/wifi-watchdog.sh') | sudo crontab -
```

### Verify services

```bash
sudo systemctl status crypto-epaper
sudo systemctl status crypto-epaper-web
```

---

## 🌐 Web Dashboard

```
http://crypto-epaper.local:8080
```

### Web Dashboard Features

<img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/904c80ae-057a-4a6f-a1ed-6ea266a31eeb" />
<img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/58fcc4a8-a446-41a5-b4e6-506e88d95085" />
<img width="500" height="154" alt="image" src="https://github.com/user-attachments/assets/97c7d500-1782-4de8-b061-1681a8f9370a" />
<img width="500" height="600" alt="image" src="https://github.com/user-attachments/assets/cb12cd11-9e2d-423d-9105-ec1723c949ff" />

---

### 📊 Current Price

Live price from CoinGecko, auto-refreshing every 60 seconds.
Shows 24h percentage change with color indicator.
In hotspot/offline mode this section shows "No internet" until Wi-Fi is configured.

---

### ⚙️ Settings

| Field | Options |
|---|---|
| **Cryptocurrency** | Bitcoin, Ethereum, Solana, Cardano, Dogecoin, XRP, Polkadot, Litecoin |
| **Fiat Currency** | USD, BRL, EUR, GBP, JPY |
| **Update Interval** | 1 / 2 / 5 / 10 / 15 / 30 min or 1 hour |

---

### 🎨 Display Appearance

| Mode | Description |
|---|---|
| ☀️ **Normal** | Black background, white text |
| 🌙 **Inverted** | White background, black text |

---

### 💼 Display Mode & Wallet Monitor

The display can show either the **live market price** or a **specific wallet balance**.

Toggle **"Show wallet instead of price"** in the dashboard to switch modes.

**Wallet mode settings:**

| Field | Description |
|---|---|
| **Network** | Bitcoin (BTC), Ethereum (ETH) or Solana (SOL) |
| **Wallet Address** | Your public address — no private key needed, read-only |
| **🔍 Preview Balance** | Fetches balance instantly to verify before saving |

**What the display shows in wallet mode:**
```
┌──────────────────────────────────────────────┐
│ BTC WALLET                          23:00   │
│ bc1q...a3f2                                  │
├──────────────────────────────────────────────┤
│          0.0341 BTC                          │
│            $2,193.40                         │
└──────────────────────────────────────────────┘
```

- Network label and time in the header
- Wallet address shown as first 6 + last 6 characters (`bc1q...a3f2`)
- Balance in native units (BTC / ETH / SOL)
- Fiat equivalent value below

The display updates at the same interval as price mode. If no address is configured, it falls back to price mode automatically.

---

### 📡 Wi-Fi & Offline Behavior

**No Wi-Fi screen**

If the Pi boots with no Wi-Fi available, the display shows instructions:
```
** NO WI-FI **
Create a phone hotspot:
SSID: crypto-epaper
Pass: bitcoin123
Then access the dashboard
http://cripto.local:8080
```

**Hotspot fallback**

The Pi Zero W cannot act as a Wi-Fi access point and client simultaneously due to hardware limitations. Instead, the watchdog connects to a **phone hotspot** as fallback.

How it works:

1. Pi loses Wi-Fi → tries to reconnect to the saved network
2. If reconnect fails → scans for the fallback hotspot and connects automatically
3. Once connected to the hotspot, access the dashboard at `http://crypto-epaper.local:8080`
4. From the dashboard, connect to a new permanent Wi-Fi network

Default hotspot credentials (configurable in the dashboard under **📡 Wi-Fi**):

| Setting | Default |
|---|---|
| **Hotspot SSID** | `crypto-epaper` |
| **Hotspot Password** | `bitcoin123` |

Create a hotspot on your phone with these credentials and the Pi will connect automatically within 2 minutes.

**Offline display behavior**

When connected to Wi-Fi but without internet access, the display shows:
- `** OFFLINE **` banner at the top
- Last known price for reference
- Current time
- Returns to normal automatically when internet is restored

---

### 🔔 Price Alerts

| Field | Description |
|---|---|
| **Buzzer enabled** | Master on/off toggle |
| **GPIO pin** | GPIO pin number (default: 18) |
| **Alert if price ABOVE** | Fires custom sound when price rises above this value |
| **Alert if price BELOW** | Fires custom sound when price falls below this value |
| **📈 Sound when ABOVE** | Pattern to play on high alert (e.g. `3`, `SOS`, `1,2`) |
| **📉 Sound when BELOW** | Pattern to play on low alert (e.g. `5`, `SOS`, `3,1`) |
| **Reset fired alert** | Re-arms the alert after it fires |

Both thresholds work simultaneously. Set to `0` to disable either one.
When alerts are active, a `!` appears next to the coin name on the display.

**Example — monitor a range:**
```
Alert above: 90000  →  custom sound if BTC breaks $90k upward
Alert below: 60000  →  custom sound if BTC drops under $60k
```

---

### 🎵 Buzzer — Custom Patterns

| Input | Result |
|---|---|
| `SOS` | `... --- ...` in Morse |
| `BITCOIN` | Full Morse for each letter |
| `3` | 3 beeps |
| `1,2,3` | 1 beep · pause · 2 beeps · pause · 3 beeps |

**Live preview** shows dots `●` and dashes `━` as you type.

| Control | Description |
|---|---|
| **▶ Play** | Plays immediately on hardware |
| **Volume** (1–95%) | PWM duty cycle — capped at 95% to keep buzzer vibrating |
| **WPM** (5–30) | Morse speed in words per minute |
| **💾 Save** | Saves pattern and settings to config |

> Volume is capped at 95% — at 100% the PWM signal becomes DC and the buzzer stops vibrating.

---

### 🔧 Service Control

| Button | Description |
|---|---|
| 🔄 **Restart Display** | Restarts display controller |
| ⏹ **Stop Display** | Stops updates (screen keeps last image) |
| ▶ **Start Display** | Starts display if stopped |

---

## 📁 Project Structure

```
crypto-epaper/
├── display_controller.py     # Main loop: price/wallet fetch + display render + offline/no-wifi detection
├── web_server.py             # Flask web dashboard + Wi-Fi setup page — port 8080
├── buzzer_controller.py      # Morse code, beep sequences, PWM volume
├── config.json               # Runtime config (re-read every cycle)
├── setup.sh                  # Automated installer
├── sd_health.sh              # SD card maintenance (cron)
├── wifi-watchdog.sh          # Wi-Fi watchdog + phone hotspot fallback
├── crypto-epaper.service     # systemd display service
├── crypto-epaper-web.service # systemd Flask service
├── .gitignore
└── README.md

# Auto-generated by setup.sh — not tracked by git:
├── venv/
├── waveshare_epd/
├── fonts/
└── logs/
```

---

## ⚙️ config.json Reference

```json
{
  "crypto":           "bitcoin",
  "fiat":             "usd",
  "interval_sec":     300,
  "cores_invertidas": false,
  "buzzer_ativo":     false,
  "buzzer_gpio":      18,
  "buzzer_volume":    80,
  "buzzer_wpm":       15,
  "buzzer_pattern":   "",
  "sound_high":       "3",
  "sound_low":        "5",
  "alerta_acima":     0,
  "alerta_abaixo":    0,
  "alerta_disparado": false,
  "display_mode":     "price",
  "wallet_address":   "",
  "wallet_network":   "bitcoin",
  "ap_ssid":          "crypto-epaper",
  "ap_pass":          "bitcoin123"
}
```

---

## 🔋 24/7 Optimization

### Reduce SD card writes

Add to `/etc/fstab`:
```
tmpfs  /tmp     tmpfs  defaults,noatime,size=30m  0 0
tmpfs  /var/log tmpfs  defaults,noatime,size=30m  0 0
```

### Disable unused hardware (`/boot/config.txt`)
```ini
hdmi_blanking=2
dtparam=act_led_trigger=none
dtparam=act_led_activelow=on
gpu_mem=16
dtoverlay=disable-bt
```

### SD card maintenance cron
```bash
crontab -e
# Add:
0 3 * * * /home/pi/crypto-epaper/files/sd_health.sh
```

---

## 🛠️ Useful Commands

```bash
tail -f ~/crypto-epaper/files/logs/display.log   # live display log
tail -f ~/crypto-epaper/files/logs/wifi.log       # live wifi watchdog log
sudo systemctl restart crypto-epaper              # restart display
sudo systemctl restart crypto-epaper-web          # restart web dashboard
journalctl -u crypto-epaper -n 50 --no-pager      # systemd logs
```

---


## 📦 Python Dependencies

```
requests>=2.28
flask>=2.3
pillow==10.4.0
RPi.GPIO>=0.7
spidev>=3.5
gpiozero>=2.0
lgpio>=0.2
```

---


## 📄 License

MIT — use it, modify it, share it freely.

**This project was developed with the assistance of Claude, Anthropic's AI agent.**

---

<div align="center">

Built with ☕ and many `sudo reboot`s on a Pi Zero W

**If this project helped you, consider giving it a ⭐ on GitHub!**

</div>
