#!/usr/bin/env python3
"""
web_server.py - Flask web dashboard
Local configuration panel served on port 8080.
"""

import json, logging, subprocess, threading, time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, jsonify

BASE_DIR    = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE    = BASE_DIR / "logs" / "web.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)
app = Flask(__name__)

CRYPTOS = [
    ("bitcoin",  "Bitcoin (BTC)"),  ("ethereum", "Ethereum (ETH)"),
    ("solana",   "Solana (SOL)"),   ("cardano",  "Cardano (ADA)"),
    ("dogecoin", "Dogecoin (DOGE)"),("ripple",   "XRP"),
    ("polkadot", "Polkadot (DOT)"), ("litecoin", "Litecoin (LTC)"),
]
FIATS = [
    ("usd", "Dollar (USD)"), ("brl", "Real (BRL)"),
    ("eur", "Euro (EUR)"),   ("gbp", "Pound (GBP)"), ("jpy", "Yen (JPY)"),
]
INTERVALS = [
    (60, "1 minute"), (120, "2 minutes"), (300, "5 minutes"),
    (600, "10 minutes"), (900, "15 minutes"), (1800, "30 minutes"), (3600, "1 hour"),
]


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {
            "crypto": "bitcoin", "fiat": "usd", "interval_sec": 300,
            "buzzer_ativo": False, "buzzer_gpio": 18, "buzzer_volume": 80,
            "buzzer_wpm": 15, "buzzer_pattern": "",
            "sound_high": "3", "sound_low": "5",
            "alerta_acima": 0, "alerta_abaixo": 0,
            "alerta_disparado": False, "cores_invertidas": False,
            "display_mode": "price", "wallet_address": "", "wallet_network": "bitcoin",
            "ap_ssid": "crypto-epaper", "ap_pass": "bitcoin123",
        }


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def ap_is_active() -> bool:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE", "con", "show", "--active"],
            capture_output=True, text=True, timeout=5
        )
        return "crypto-epaper" in result.stdout
    except Exception:
        return False


def scan_wifi_networks() -> list:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
            capture_output=True, text=True, timeout=15
        )
        networks = []
        seen = set()
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                ssid     = parts[0].strip()
                signal   = parts[1].strip() if len(parts) > 1 else "?"
                security = parts[2].strip() if len(parts) > 2 else ""
                if ssid and ssid not in seen and ssid != "crypto-epaper":
                    seen.add(ssid)
                    networks.append({
                        "ssid":    ssid,
                        "signal":  int(signal) if signal.isdigit() else 0,
                        "secured": bool(security and security != "--"),
                    })
        networks.sort(key=lambda x: x["signal"], reverse=True)
        return networks[:20]
    except Exception as e:
        log.error(f"Wi-Fi scan error: {e}")
        return []


def connect_wifi(ssid: str, password: str) -> bool:
    try:
        subprocess.run(["nmcli", "connection", "delete", ssid],
                       capture_output=True, timeout=5)
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["nmcli", "device", "wifi", "connect", ssid, "password", password],
            capture_output=True, text=True, timeout=30
        )
        success = result.returncode == 0
        log.info(f"Wi-Fi connect '{ssid}': {'ok' if success else result.stderr.strip()}")
        return success
    except Exception as e:
        log.error(f"Wi-Fi connect error: {e}")
        return False


# ── Wi-Fi Page ─────────────────────────────────────────────────────────────────
WIFI_PAGE = """<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wi-Fi Setup</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--border:#2d3147;--accent:#6c63ff;
      --text:#e2e8f0;--muted:#8892a4;--green:#34d399;--red:#f87171;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',sans-serif;
     min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:24px 16px;}
h1{font-size:1.4rem;margin-bottom:4px;}
.sub{color:var(--muted);font-size:.85rem;margin-bottom:24px;}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;
      padding:20px;width:100%;max-width:420px;margin-bottom:14px;}
.card h2{font-size:.95rem;color:var(--accent);margin-bottom:14px;}
label{display:block;color:var(--muted);font-size:.78rem;text-transform:uppercase;
      letter-spacing:.05em;margin-bottom:4px;margin-top:12px;}
label:first-of-type{margin-top:0;}
input{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);
      padding:10px 12px;border-radius:8px;font-size:.95rem;}
.btn{display:block;width:100%;padding:11px;border:none;border-radius:8px;font-size:.95rem;
     font-weight:600;cursor:pointer;margin-top:10px;transition:opacity .2s;}
.btn:hover{opacity:.85;}
.btn-primary{background:var(--accent);color:#fff;}
.btn-scan{background:#1f2937;color:var(--text);}
.net{display:flex;justify-content:space-between;align-items:center;
     padding:10px 12px;border:1px solid var(--border);border-radius:8px;
     margin-bottom:6px;cursor:pointer;transition:border-color .2s;}
.net:hover,.net.sel{border-color:var(--accent);}
.net-name{font-size:.9rem;font-weight:500;}
.net-meta{font-size:.75rem;color:var(--muted);}
.st{font-size:.85rem;text-align:center;padding:10px;border-radius:8px;margin-top:8px;}
.st.ok{background:#064e3b;color:var(--green);}
.st.err{background:#450a0a;color:var(--red);}
.st.loading{background:#1f2937;color:var(--muted);}
.spin{display:inline-block;width:12px;height:12px;border:2px solid var(--muted);
      border-top-color:var(--accent);border-radius:50%;animation:sp .8s linear infinite;margin-right:6px;vertical-align:middle;}
@keyframes sp{to{transform:rotate(360deg)}}
a.back{color:var(--muted);font-size:.85rem;text-decoration:none;margin-top:16px;display:block;text-align:center;}
a.back:hover{color:var(--text);}
</style></head><body>
<h1>📡 Wi-Fi Setup</h1>
<p class="sub">Scan and connect to a new network.</p>
<div class="card"><h2>🔍 Available Networks</h2>
  <button type="button" class="btn btn-scan" onclick="scan()">🔄 Scan for networks</button>
  <div id="list"><div style="color:var(--muted);font-size:.85rem;margin-top:8px">Click scan to search…</div></div>
</div>
<div class="card"><h2>🔑 Connect</h2>
  <label>Network (SSID)</label>
  <input type="text" id="ssid" placeholder="Network name">
  <label>Password</label>
  <input type="password" id="pass" placeholder="Wi-Fi password">
  <button type="button" class="btn btn-primary" onclick="connect()">🔗 Connect & Save</button>
  <div id="st"></div>
</div>
<a class="back" href="/">← Back to dashboard</a>
<script>
async function scan(){
  const l=document.getElementById('list');
  l.innerHTML='<div style="color:var(--muted);font-size:.85rem;margin-top:8px"><span class="spin"></span>Scanning…</div>';
  try{
    const d=await(await fetch('/wifi/scan')).json();
    if(!d.networks?.length){l.innerHTML='<div style="color:var(--muted);font-size:.85rem;margin-top:8px">No networks found.</div>';return;}
    l.innerHTML='';
    for(const n of d.networks){
      const e=document.createElement('div');e.className='net';
      e.innerHTML=`<div><div class="net-name">${n.ssid}</div><div class="net-meta">${n.secured?'🔒':'🔓'} ${n.secured?'Secured':'Open'}</div></div><div class="net-meta">${n.signal}%</div>`;
      e.onclick=()=>{document.querySelectorAll('.net').forEach(x=>x.classList.remove('sel'));e.classList.add('sel');document.getElementById('ssid').value=n.ssid;document.getElementById('pass').focus();};
      l.appendChild(e);
    }
  }catch{l.innerHTML='<div style="color:var(--red);font-size:.85rem;margin-top:8px">Scan failed.</div>';}
}
async function connect(){
  const ssid=document.getElementById('ssid').value.trim(),pass=document.getElementById('pass').value,s=document.getElementById('st');
  if(!ssid){s.className='st err';s.textContent='Enter a network name.';return;}
  s.className='st loading';s.innerHTML='<span class="spin"></span>Connecting…';
  try{
    const d=await(await fetch('/wifi/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid,password:pass})})).json();
    if(d.ok){s.className='st ok';s.innerHTML='✅ Connecting… Reconnect your device to home Wi-Fi then open <strong>http://crypto-epaper.local:8080</strong>';}
    else{s.className='st err';s.textContent='❌ Failed — check the password.';}
  }catch{s.className='st ok';s.innerHTML='✅ Sent — reconnect to your Wi-Fi and open <strong>http://crypto-epaper.local:8080</strong>';}
}
</script></body></html>"""


# ── Main Page ──────────────────────────────────────────────────────────────────
MAIN_HTML = """<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crypto E-Paper</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--border:#2d3147;--accent:#6c63ff;
      --text:#e2e8f0;--muted:#8892a4;--green:#34d399;--red:#f87171;--yellow:#fbbf24;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',sans-serif;
     min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:20px 16px 40px;}

/* header */
h1{font-size:1.45rem;margin-bottom:2px;letter-spacing:-.01em;}
.sub{color:var(--muted);font-size:.82rem;margin-bottom:18px;}

/* price box */
.price-box{background:var(--card);border:1px solid var(--border);border-radius:14px;
           padding:22px 24px 18px;width:100%;max-width:480px;text-align:center;margin-bottom:14px;}
.price-val{font-size:2.4rem;font-weight:700;line-height:1.1;}
.price-change{font-size:.9rem;margin-top:6px;}
.price-time{color:var(--muted);font-size:.72rem;margin-top:6px;}
.up{color:var(--green);} .dn{color:var(--red);}

/* banners */
.ap-banner{background:#78350f;border:1px solid #d97706;border-radius:10px;
           padding:11px 16px;margin-bottom:12px;width:100%;max-width:480px;font-size:.84rem;line-height:1.6;}
.ap-banner a{color:#fbbf24;font-weight:600;}
.flash{font-size:.82rem;text-align:center;padding:9px 14px;border-radius:8px;
       margin-bottom:12px;width:100%;max-width:480px;}
.flash.ok{background:#064e3b;color:var(--green);}
.flash.err{background:#450a0a;color:var(--red);}

/* accordion */
.acc{width:100%;max-width:480px;border:1px solid var(--border);border-radius:12px;
     overflow:hidden;margin-bottom:8px;}
.acc-head{display:flex;justify-content:space-between;align-items:center;
          padding:15px 18px;cursor:pointer;background:var(--card);user-select:none;
          transition:background .15s;}
.acc-head:hover{background:#1e2235;}
.acc-head h2{font-size:.92rem;font-weight:600;display:flex;align-items:center;gap:8px;}
.arr{color:var(--muted);font-size:.75rem;transition:transform .22s;}
.open .arr{transform:rotate(180deg);}
.acc-body{background:var(--card);border-top:1px solid var(--border);
          max-height:0;overflow:hidden;transition:max-height .3s ease,padding .3s ease;padding:0 18px;}
.acc-body.show{max-height:1400px;padding:18px;}

/* form */
label{display:block;color:var(--muted);font-size:.76rem;text-transform:uppercase;
      letter-spacing:.06em;margin-bottom:4px;margin-top:13px;}
label:first-child{margin-top:0;}
select,input[type=number],input[type=text]{width:100%;background:var(--bg);
  border:1px solid var(--border);color:var(--text);padding:10px 12px;border-radius:8px;font-size:.93rem;}
input[type=range]{width:100%;accent-color:var(--accent);margin-top:4px;}
.row{display:flex;gap:8px;align-items:center;}
.row select,.row input{flex:1;margin-top:0;}
.hr{border:none;border-top:1px solid var(--border);margin:14px 0;}
.hint{font-size:.74rem;color:var(--muted);margin-top:5px;line-height:1.5;}

/* toggle */
.tog-row{display:flex;justify-content:space-between;align-items:center;
         padding:10px 0;border-bottom:1px solid var(--border);}
.tog-row:last-of-type{border-bottom:none;}
.tog-row span{font-size:.9rem;}
.tog{position:relative;width:42px;height:24px;flex-shrink:0;}
.tog input{opacity:0;width:0;height:0;}
.sl{position:absolute;inset:0;background:var(--border);border-radius:24px;cursor:pointer;transition:.25s;}
.sl:before{content:'';position:absolute;height:18px;width:18px;left:3px;bottom:3px;
           background:#fff;border-radius:50%;transition:.25s;}
input:checked+.sl{background:var(--accent);}
input:checked+.sl:before{transform:translateX(18px);}

/* buttons */
.btn{display:block;width:100%;padding:11px;border:none;border-radius:8px;
     font-size:.92rem;font-weight:600;cursor:pointer;margin-top:10px;transition:opacity .2s;}
.btn:hover{opacity:.85;}
.btn-p{background:var(--accent);color:#fff;}
.btn-g{background:#064e3b;color:var(--green);}
.btn-r{background:#3b1515;color:var(--red);}
.btn-y{background:#78350f;color:var(--yellow);}
.btn-sm{padding:9px 14px;font-size:.82rem;width:auto;display:inline-block;margin-top:0;white-space:nowrap;}

/* theme preview */
.themes{display:flex;gap:10px;margin-top:10px;}
.theme{flex:1;border-radius:8px;padding:12px;text-align:center;cursor:pointer;
       border:2px solid transparent;transition:.2s;font-size:.85rem;font-weight:600;}
.theme.sel{border-color:var(--accent);}
.t-normal{background:#fff;color:#000;}
.t-inv{background:#111;color:#fff;border:1px solid #444;}

/* morse */
.morse-box{background:var(--bg);border:1px solid var(--border);border-radius:8px;
           padding:10px 12px;margin-top:8px;font-size:.8rem;min-height:34px;
           word-break:break-all;line-height:1.9;}
.morse-desc{font-size:.72rem;color:var(--muted);margin-top:4px;}
.dot{display:inline-block;width:7px;height:7px;background:var(--green);
     border-radius:50%;margin:0 2px;vertical-align:middle;}
.dsh{display:inline-block;width:20px;height:7px;background:var(--green);
     border-radius:4px;margin:0 2px;vertical-align:middle;}
.gap{display:inline-block;width:12px;vertical-align:middle;}

/* wallet preview result */
.wal-res{background:var(--bg);border:1px solid var(--border);border-radius:8px;
         padding:12px 14px;margin-top:10px;font-size:.88rem;line-height:1.8;display:none;}
.wal-res.show{display:block;}

/* badge */
.badge{display:inline-block;border-radius:5px;padding:1px 7px;font-size:.7rem;
       font-weight:600;margin-left:6px;vertical-align:middle;}
.badge-blue{background:#1e3a5f;color:#60a5fa;}
.badge-on{background:#064e3b;color:var(--green);}
.badge-warn{background:#78350f;color:var(--yellow);}

footer{color:var(--muted);font-size:.73rem;margin-top:28px;}
</style></head><body>

<h1>🖥️ Crypto E-Paper</h1>
<p class="sub">Configuration Panel</p>

{% if ap_mode %}
<div class="ap-banner">
  📡 <strong>No internet</strong> — connected via hotspot.<br>
  <a href="/wifi">→ Configure Wi-Fi network</a>
</div>
{% endif %}

{% if msg %}
<div class="flash {{ 'ok' if ok else 'err' }}">{{ msg }}</div>
{% endif %}

<!-- Live Price -->
<div class="price-box">
  <div class="price-val" id="pv">{% if ap_mode %}No internet{% else %}Loading…{% endif %}</div>
  <div class="price-change" id="pc"></div>
  <div class="price-time" id="pt"></div>
</div>

<!-- ① Display Mode + Wallet ──────────────────────────────────────────────── -->
<div class="acc">
  <div class="acc-head" onclick="tog(this)">
    <h2>📺 Display Mode
      <span class="badge badge-blue">{{ 'Wallet' if cfg.get('display_mode')=='wallet' else 'Price' }}</span>
    </h2>
    <span class="arr">▼</span>
  </div>
  <div class="acc-body {% if cfg.get('display_mode')=='wallet' %}show{% endif %}">
    <form method="POST" action="/save_mode">
      <div class="tog-row">
        <span>Show wallet instead of price</span>
        <label class="tog">
          <input type="checkbox" name="wallet_mode" id="wm_tog"
            {{ 'checked' if cfg.get('display_mode')=='wallet' }}
            onchange="document.getElementById('wal_sec').style.display=this.checked?'block':'none'">
          <span class="sl"></span>
        </label>
      </div>

      <div id="wal_sec" style="display:{{ 'block' if cfg.get('display_mode')=='wallet' else 'none' }}">
        <label style="margin-top:14px">Network</label>
        <select name="wallet_network" id="wnet">
          <option value="bitcoin"  {{ 'selected' if cfg.get('wallet_network')=='bitcoin'  }}>Bitcoin (BTC)</option>
          <option value="ethereum" {{ 'selected' if cfg.get('wallet_network')=='ethereum' }}>Ethereum (ETH)</option>
          <option value="solana"   {{ 'selected' if cfg.get('wallet_network')=='solana'   }}>Solana (SOL)</option>
        </select>

        <label>Wallet Address</label>
        <input type="text" name="wallet_address" id="waddr"
               value="{{ cfg.get('wallet_address','') }}"
               placeholder="Paste your public address here">
        <div class="hint">Read-only — public address only, no private key needed.</div>

        <div class="row" style="margin-top:10px">
          <button type="button" class="btn btn-g btn-sm" onclick="previewWallet()">🔍 Preview Balance</button>
        </div>
        <div class="wal-res" id="wal_res"></div>

        <hr style="border:none;border-top:1px solid var(--border);margin:14px 0">
        <div style="font-size:.85rem;font-weight:600;margin-bottom:8px">📊 Display Priority</div>
        <div class="themes">
          <div class="theme {{ 'sel' if cfg.get('wallet_primary','crypto')=='crypto' else '' }}"
               style="{{ 'background:#1a1d27;color:#e2e8f0;' if cfg.get('wallet_primary','crypto')=='crypto' else 'background:#111;color:#888;' }}border:2px solid {{ 'var(--accent)' if cfg.get('wallet_primary','crypto')=='crypto' else 'var(--border)' }}"
               onclick="setWalletPrimary('crypto',this)">
            🪙 Crypto big<br><small style="font-weight:400">USD small</small>
          </div>
          <div class="theme {{ 'sel' if cfg.get('wallet_primary','crypto')=='fiat' else '' }}"
               style="{{ 'background:#1a1d27;color:#e2e8f0;' if cfg.get('wallet_primary','crypto')=='fiat' else 'background:#111;color:#888;' }}border:2px solid {{ 'var(--accent)' if cfg.get('wallet_primary','crypto')=='fiat' else 'var(--border)' }}"
               onclick="setWalletPrimary('fiat',this)">
            💵 USD big<br><small style="font-weight:400">Crypto small</small>
          </div>
        </div>
        <input type="hidden" name="wallet_primary" id="wallet_primary_val"
               value="{{ cfg.get('wallet_primary','crypto') }}">
      </div>

      <button type="submit" class="btn btn-p" style="margin-top:14px">💾 Save Display Mode</button>
      <hr style="border:none;border-top:1px solid var(--border);margin:12px 0">
      <a href="/set_mode/qr" style="text-decoration:none">
        <button type="button" class="btn btn-g">📷 Show QR Code now</button>
      </a>
    </form>
  </div>
</div>

<!-- ② Settings ───────────────────────────────────────────────────────────── -->
<div class="acc">
  <div class="acc-head" onclick="tog(this)">
    <h2>⚙️ Settings</h2>
    <span class="arr">▼</span>
  </div>
  <div class="acc-body">
    <form method="POST" action="/save">
      <label>Cryptocurrency</label>
      <select name="crypto">
        {% for id,name in cryptos %}
        <option value="{{ id }}" {{ 'selected' if cfg.crypto==id }}>{{ name }}</option>
        {% endfor %}
      </select>
      <label>Fiat Currency</label>
      <select name="fiat">
        {% for id,name in fiats %}
        <option value="{{ id }}" {{ 'selected' if cfg.fiat==id }}>{{ name }}</option>
        {% endfor %}
      </select>
      <label>Update Interval</label>
      <select name="interval_sec">
        {% for sec,lbl in intervals %}
        <option value="{{ sec }}" {{ 'selected' if cfg.interval_sec==sec }}>{{ lbl }}</option>
        {% endfor %}
      </select>
      <button type="submit" class="btn btn-p">💾 Save Settings</button>
    </form>
  </div>
</div>

<!-- ③ Appearance ─────────────────────────────────────────────────────────── -->
<div class="acc">
  <div class="acc-head" onclick="tog(this)">
    <h2>🎨 Appearance</h2>
    <span class="arr">▼</span>
  </div>
  <div class="acc-body">
    <form method="POST" action="/save_display">
      <label>Color Scheme</label>
      <div class="themes">
        <div class="theme t-normal {{ 'sel' if not cfg.cores_invertidas }}" onclick="setTheme('false',this)">
          ☀️ Normal<br><small style="font-weight:400">Black bg</small></div>
        <div class="theme t-inv {{ 'sel' if cfg.cores_invertidas }}" onclick="setTheme('true',this)">
          🌙 Inverted<br><small style="font-weight:400">White bg</small></div>
      </div>
      <input type="hidden" name="cores_invertidas" id="theme_val"
             value="{{ 'true' if cfg.cores_invertidas else 'false' }}">
      <button type="submit" class="btn btn-p">🎨 Apply Theme</button>
    </form>
  </div>
</div>

<!-- ④ Price Alerts ───────────────────────────────────────────────────────── -->
<div class="acc">
  <div class="acc-head" onclick="tog(this)">
    <h2>🔔 Price Alerts
      {% if cfg.buzzer_ativo %}<span class="badge badge-on">ON</span>{% endif %}
      {% if cfg.alerta_disparado %}<span class="badge badge-warn">FIRED</span>{% endif %}
    </h2>
    <span class="arr">▼</span>
  </div>
  <div class="acc-body {% if cfg.alerta_disparado %}show{% endif %}">
    <form method="POST" action="/save_alertas">
      <div class="tog-row">
        <span>Buzzer enabled</span>
        <label class="tog">
          <input type="checkbox" name="buzzer_ativo" {{ 'checked' if cfg.buzzer_ativo }}>
          <span class="sl"></span>
        </label>
      </div>
      <label>GPIO Pin</label>
      <input type="number" name="buzzer_gpio" value="{{ cfg.buzzer_gpio }}" min="1" max="40">
      <label>Alert if price ABOVE (0 = off)</label>
      <input type="number" name="alerta_acima" value="{{ cfg.alerta_acima }}" min="0" step="100">
      <label>Alert if price BELOW (0 = off)</label>
      <input type="number" name="alerta_abaixo" value="{{ cfg.alerta_abaixo }}" min="0" step="100">
      <hr class="hr">
      <div style="font-size:.85rem;font-weight:600;margin-bottom:6px">🔊 Alert Sounds</div>
      <div class="hint" style="margin-bottom:8px">Letters = Morse · Numbers = beeps · e.g. SOS · 3 · 1,2</div>

      <label>📈 Sound when price goes ABOVE</label>
      <div class="row">
        <input type="text" name="sound_high" id="sh_in"
               value="{{ cfg.get('sound_high','3') }}"
               oninput="updSnd('sh_in','sh_pre','sh_dsc')">
        <button type="button" class="btn btn-g btn-sm" onclick="testSnd('sh_in')">▶</button>
      </div>
      <div class="morse-box" id="sh_pre"></div>
      <div class="morse-desc" id="sh_dsc"></div>

      <label>📉 Sound when price goes BELOW</label>
      <div class="row">
        <input type="text" name="sound_low" id="sl_in"
               value="{{ cfg.get('sound_low','5') }}"
               oninput="updSnd('sl_in','sl_pre','sl_dsc')">
        <button type="button" class="btn btn-r btn-sm" onclick="testSnd('sl_in')">▶</button>
      </div>
      <div class="morse-box" id="sl_pre"></div>
      <div class="morse-desc" id="sl_dsc"></div>

      <button type="submit" class="btn btn-y" style="margin-top:14px">🔔 Save Alerts</button>
      <a href="/resetar_alerta" style="text-decoration:none">
        <button type="button" class="btn btn-r">↺ Reset fired alert</button>
      </a>
    </form>
  </div>
</div>

<!-- ⑤ Buzzer ─────────────────────────────────────────────────────────────── -->
<div class="acc">
  <div class="acc-head" onclick="tog(this)">
    <h2>🎵 Buzzer — Custom Pattern</h2>
    <span class="arr">▼</span>
  </div>
  <div class="acc-body">
    <label>Pattern</label>
    <div class="row">
      <input type="text" id="bz_in" placeholder="SOS · BITCOIN · 3 · 1,2,3"
             value="{{ cfg.get('buzzer_pattern','') }}"
             oninput="updPrev(this.value)">
      <button type="button" class="btn btn-g btn-sm" onclick="playNow()">▶ Play</button>
    </div>
    <div class="hint">Letters → Morse &nbsp;|&nbsp; Numbers → beeps &nbsp;|&nbsp; 1,3,2 → groups</div>
    <div class="morse-box" id="bz_pre" style="color:var(--green)">Type a pattern…</div>
    <div class="morse-desc" id="bz_dsc"></div>

    <label>Volume — <span id="vol_lbl">{{ cfg.get('buzzer_volume',80) }}%</span></label>
    <input type="range" id="vol_r" min="1" max="95" step="5"
           value="{{ cfg.get('buzzer_volume',80) }}"
           oninput="document.getElementById('vol_lbl').textContent=this.value+'%'">
    <div class="hint">⚠️ Max 95% — at 100% PWM becomes DC and buzzer stops</div>

    <label>Morse Speed — <span id="wpm_lbl">{{ cfg.get('buzzer_wpm',15) }}</span> WPM</label>
    <input type="range" id="wpm_r" min="5" max="30" step="1"
           value="{{ cfg.get('buzzer_wpm',15) }}"
           oninput="document.getElementById('wpm_lbl').textContent=this.value">

    <button type="button" class="btn btn-p" onclick="saveBuzzer()">💾 Save Buzzer</button>
  </div>
</div>

<!-- ⑥ Wi-Fi ──────────────────────────────────────────────────────────────── -->
<div class="acc">
  <div class="acc-head" onclick="tog(this)">
    <h2>📡 Wi-Fi</h2>
    <span class="arr">▼</span>
  </div>
  <div class="acc-body">
    <p class="hint" style="font-size:.84rem;line-height:1.7;margin-bottom:12px">
      If the Pi loses Wi-Fi, it will try connecting to the fallback hotspot below.<br>
      Create a hotspot on your phone with these credentials.
    </p>
    <label>Fallback Hotspot SSID</label>
    <input type="text" id="ap_ssid" value="{{ cfg.get('ap_ssid','crypto-epaper') }}">
    <label>Fallback Hotspot Password</label>
    <input type="text" id="ap_pass" value="{{ cfg.get('ap_pass','bitcoin123') }}">
    <button type="button" class="btn btn-y" onclick="saveHotspot()">💾 Save Hotspot Credentials</button>
    <hr class="hr">
    <a href="/wifi" style="text-decoration:none">
      <button type="button" class="btn btn-p">🔗 Connect to a new Wi-Fi network</button>
    </a>
  </div>
</div>

<!-- ⑦ Service Control ────────────────────────────────────────────────────── -->
<div class="acc">
  <div class="acc-head" onclick="tog(this)">
    <h2>🔧 Service Control</h2>
    <span class="arr">▼</span>
  </div>
  <div class="acc-body">
    <form method="POST" action="/service/restart" style="margin-bottom:0">
      <button type="submit" class="btn btn-p">🔄 Restart Display</button></form>
    <form method="POST" action="/service/stop" style="margin-bottom:0">
      <button type="submit" class="btn btn-r">⏹ Stop Display</button></form>
    <form method="POST" action="/service/start" style="margin-bottom:0">
      <button type="submit" class="btn btn-g">▶ Start Display</button></form>
  </div>
</div>

<footer>Crypto E-Paper · {{ now }}</footer>

<script>
// ── Accordion ──────────────────────────────────────────────────────────────
function tog(head){
  const body=head.nextElementSibling;
  const open=body.classList.toggle('show');
  head.classList.toggle('open',open);
}

// ── Morse engine ───────────────────────────────────────────────────────────
const MC={A:'.-',B:'-...',C:'-.-.',D:'-..',E:'.',F:'..-.',G:'--.',H:'....',I:'..',J:'.---',
  K:'-.-',L:'.-..',M:'--',N:'-.',O:'---',P:'.--.',Q:'--.-',R:'.-.',S:'...',T:'-',
  U:'..-',V:'...-',W:'.--',X:'-..-',Y:'-.--',Z:'--..',
  '0':'-----','1':'.----','2':'..---','3':'...--','4':'....-','5':'.....',
  '6':'-....','7':'--...','8':'---..','9':'----.','.':'.-.-.-',',':'--..--','?':'..--..'};
function isSeq(v){return /^[\d,\s]+$/.test(v.trim());}
function morseHTML(txt){
  let h='';
  for(const c of txt.toUpperCase()){
    if(c===' '){h+='<span style="display:inline-block;width:22px"></span>';continue;}
    const m=MC[c];
    if(!m){h+=`<span style="color:var(--red)">${c}?</span> `;continue;}
    h+=`<span style="color:var(--muted);font-size:.65rem;margin-right:1px">${c}</span>`;
    for(const s of m)h+=s==='.'?'<span class="dot"></span>':'<span class="dsh"></span>';
    h+='<span class="gap"></span>';
  }
  return h;
}
function seqHTML(nums){
  return nums.map(n=>'🔔'.repeat(Math.min(n,10))+`<small style="color:var(--muted);margin-left:3px">${n}x</small>`).join(' <span style="color:var(--border)">│</span> ');
}
function buildPrev(v){
  if(!v?.trim())return{html:'',desc:''};
  if(isSeq(v)){
    const ns=v.trim().split(/[,\s]+/).filter(Boolean).map(Number).filter(n=>!isNaN(n)&&n>0);
    if(ns.length)return{html:seqHTML(ns),desc:`Beep sequence: ${ns.join(' → ')}`};
  }
  return{html:morseHTML(v),desc:`Morse: ${[...v.toUpperCase()].map(c=>MC[c]||'?').join(' ')}`};
}
function updPrev(v){
  const p=buildPrev(v);
  document.getElementById('bz_pre').innerHTML=p.html||'<span style="color:var(--muted)">Type a pattern…</span>';
  document.getElementById('bz_dsc').textContent=p.desc;
}
function updSnd(iid,pid,did){
  const p=buildPrev(document.getElementById(iid).value);
  document.getElementById(pid).innerHTML=p.html||'<span style="color:var(--muted)">—</span>';
  document.getElementById(did).textContent=p.desc;
}
// init previews
updPrev(document.getElementById('bz_in').value);
updSnd('sh_in','sh_pre','sh_dsc');
updSnd('sl_in','sl_pre','sl_dsc');

// ── Buzzer ─────────────────────────────────────────────────────────────────
function getVW(){return{volume:parseInt(document.getElementById('vol_r').value),wpm:parseInt(document.getElementById('wpm_r').value)};}
async function testSnd(iid){
  const pat=document.getElementById(iid).value.trim();
  if(!pat){flash('Enter a pattern first',false);return;}
  const btn=event.currentTarget;btn.textContent='⏳';btn.disabled=true;
  const {volume,wpm}=getVW();
  try{const d=await(await fetch('/buzzer/play',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pattern:pat,volume,wpm})})).json();btn.textContent=d.ok?'✅':'❌';}
  catch{btn.textContent='❌';}
  setTimeout(()=>{btn.textContent='▶';btn.disabled=false;},2000);
}
async function playNow(){
  const pat=document.getElementById('bz_in').value.trim();
  if(!pat){flash('Enter a pattern first',false);return;}
  const btn=event.currentTarget;btn.textContent='⏳';btn.disabled=true;
  const {volume,wpm}=getVW();
  try{const d=await(await fetch('/buzzer/play',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pattern:pat,volume,wpm})})).json();btn.textContent=d.ok?'✅':'❌';}
  catch{btn.textContent='❌';}
  setTimeout(()=>{btn.textContent='▶ Play';btn.disabled=false;},2500);
}
async function saveBuzzer(){
  const {volume,wpm}=getVW();
  const d=await(await fetch('/buzzer/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({pattern:document.getElementById('bz_in').value.trim(),volume,wpm})})).json();
  flash(d.ok?'✅ Buzzer saved!':'❌ Save failed',d.ok);
}

// ── Hotspot ────────────────────────────────────────────────────────────────
async function saveHotspot(){
  const ssid=document.getElementById('ap_ssid').value.trim(),pass=document.getElementById('ap_pass').value.trim();
  if(!ssid||!pass){flash('SSID and password required',false);return;}
  const d=await(await fetch('/hotspot/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ap_ssid:ssid,ap_pass:pass})})).json();
  flash(d.ok?'✅ Hotspot credentials saved!':'❌ Save failed',d.ok);
}

// ── Wallet preview ─────────────────────────────────────────────────────────
async function previewWallet(){
  const addr=document.getElementById('waddr').value.trim();
  const net=document.getElementById('wnet').value;
  const el=document.getElementById('wal_res');
  if(!addr){el.className='wal-res show';el.style.color='var(--red)';el.textContent='Enter a wallet address first.';return;}
  el.className='wal-res show';el.style.color='var(--muted)';el.textContent='Fetching balance…';
  try{
    const d=await(await fetch('/wallet/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({address:addr,network:net})})).json();
    if(d.ok){el.style.color='var(--green)';el.innerHTML=`Balance: <strong>${d.balance}</strong><br>Value: <strong>${d.fiat_value}</strong>`;}
    else{el.style.color='var(--red)';el.textContent='Error: '+d.error;}
  }catch(e){el.style.color='var(--red)';el.textContent='Request failed: '+e.message;}
}

// ── Theme ──────────────────────────────────────────────────────────────────
function setTheme(val,el){
  document.getElementById('theme_val').value=val;
  document.querySelectorAll('.theme').forEach(e=>e.classList.remove('sel'));
  el.classList.add('sel');
}
function setWalletPrimary(val,el){
  document.getElementById('wallet_primary_val').value=val;
  el.closest('.themes').querySelectorAll('.theme').forEach(e=>{
    e.style.borderColor='var(--border)';e.style.color='#888';
  });
  el.style.borderColor='var(--accent)';el.style.color='var(--text)';
}

// ── Flash ──────────────────────────────────────────────────────────────────
function flash(msg,ok=true){
  let el=document.getElementById('_flash');
  if(!el){el=document.createElement('div');el.id='_flash';el.style.cssText='position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:999;min-width:240px;text-align:center;';document.body.appendChild(el);}
  el.className='flash '+(ok?'ok':'err');el.textContent=msg;el.style.display='block';
  clearTimeout(el._t);el._t=setTimeout(()=>el.style.display='none',3000);
}

// ── Live price ─────────────────────────────────────────────────────────────
{% if not ap_mode %}
async function refreshPrice(){
  try{
    const d=await(await fetch('/api/price')).json();
    if(d.error){document.getElementById('pv').textContent='API error';return;}
    const p=d.price;
    document.getElementById('pv').textContent=d.fiat_symbol+(p>=1000?
      p.toLocaleString('en-US',{maximumFractionDigits:0}):
      p.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:4}));
    const c=d.change_24h,el=document.getElementById('pc');
    el.textContent=(c>=0?'▲':'▼')+' '+Math.abs(c).toFixed(2)+'% (24h)';
    el.className='price-change '+(c>=0?'up':'dn');
    document.getElementById('pt').textContent='Updated: '+new Date().toLocaleTimeString();
  }catch{document.getElementById('pv').textContent='Offline';}
}
refreshPrice();setInterval(refreshPrice,60000);
{% endif %}
</script></body></html>"""


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    cfg = load_config()
    cfg.setdefault("cores_invertidas", False)
    cfg.setdefault("buzzer_volume",    80)
    cfg.setdefault("buzzer_wpm",       15)
    cfg.setdefault("buzzer_pattern",   "")
    cfg.setdefault("sound_high",       "3")
    cfg.setdefault("sound_low",        "5")
    cfg.setdefault("display_mode",     "price")
    cfg.setdefault("wallet_address",   "")
    cfg.setdefault("wallet_network",   "bitcoin")
    cfg.setdefault("ap_ssid",          "crypto-epaper")
    cfg.setdefault("ap_pass",          "bitcoin123")
    return render_template_string(MAIN_HTML, cfg=cfg, cryptos=CRYPTOS, fiats=FIATS,
        intervals=INTERVALS, ap_mode=ap_is_active(),
        msg=request.args.get("msg", ""), ok=request.args.get("ok", "1") == "1",
        now=datetime.now().strftime("%Y-%m-%d %H:%M"))


@app.route("/wifi")
def wifi_page():
    return render_template_string(WIFI_PAGE)


@app.route("/wifi/scan")
def wifi_scan():
    return jsonify({"networks": scan_wifi_networks()})


@app.route("/wifi/connect", methods=["POST"])
def wifi_connect():
    data     = request.get_json()
    ssid     = data.get("ssid", "").strip()
    password = data.get("password", "")
    if not ssid:
        return jsonify({"ok": False, "error": "SSID required"})
    def _connect():
        time.sleep(1)
        connect_wifi(ssid, password)
    threading.Thread(target=_connect, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/save", methods=["POST"])
def save():
    cfg = load_config()
    cfg["crypto"]       = request.form.get("crypto", cfg["crypto"])
    cfg["fiat"]         = request.form.get("fiat",   cfg["fiat"])
    cfg["interval_sec"] = int(request.form.get("interval_sec", 300))
    save_config(cfg)
    return redirect(url_for("index", msg="✅ Settings saved!", ok=1))


@app.route("/save_display", methods=["POST"])
def save_display():
    cfg = load_config()
    cfg["cores_invertidas"] = request.form.get("cores_invertidas", "false") == "true"
    save_config(cfg)
    return redirect(url_for("index", msg="✅ Theme applied.", ok=1))


@app.route("/set_mode/<mode>")
def set_mode(mode):
    if mode not in ("price", "wallet", "qr"):
        return redirect(url_for("index", msg="Invalid mode.", ok=0))
    cfg = load_config()
    cfg["display_mode"] = mode
    save_config(cfg)
    # Restart display service so change takes effect immediately
    try:
        subprocess.run(["sudo", "systemctl", "restart", "crypto-epaper"], timeout=10)
    except Exception as e:
        log.warning(f"Could not restart display service: {e}")
    labels = {"price": "Price", "wallet": "Wallet", "qr": "QR Code"}
    return redirect(url_for("index", msg=f"✅ Switched to {labels[mode]} mode.", ok=1))


@app.route("/save_mode", methods=["POST"])
def save_mode():
    cfg = load_config()
    cfg["display_mode"]   = "wallet" if "wallet_mode" in request.form else "price"
    cfg["wallet_network"] = request.form.get("wallet_network", "bitcoin")
    cfg["wallet_address"] = request.form.get("wallet_address", "").strip()
    cfg["wallet_primary"] = request.form.get("wallet_primary", "crypto")
    save_config(cfg)
    try:
        subprocess.run(["sudo", "systemctl", "restart", "crypto-epaper"], timeout=10)
    except Exception as e:
        log.warning(f"Could not restart display service: {e}")
    return redirect(url_for("index", msg="✅ Display mode saved!", ok=1))


@app.route("/save_alertas", methods=["POST"])
def save_alertas():
    cfg = load_config()
    cfg["buzzer_ativo"]  = "buzzer_ativo" in request.form
    cfg["buzzer_gpio"]   = int(request.form.get("buzzer_gpio",   18))
    cfg["alerta_acima"]  = float(request.form.get("alerta_acima",  0))
    cfg["alerta_abaixo"] = float(request.form.get("alerta_abaixo", 0))
    cfg["sound_high"]    = request.form.get("sound_high", "3").strip() or "3"
    cfg["sound_low"]     = request.form.get("sound_low",  "5").strip() or "5"
    save_config(cfg)
    return redirect(url_for("index", msg="✅ Alerts saved!", ok=1))


@app.route("/buzzer/save", methods=["POST"])
def buzzer_save():
    cfg  = load_config()
    data = request.get_json()
    cfg["buzzer_pattern"] = data.get("pattern", "")
    cfg["buzzer_volume"]  = int(data.get("volume", 80))
    cfg["buzzer_wpm"]     = int(data.get("wpm",    15))
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/buzzer/play", methods=["POST"])
def buzzer_play():
    cfg     = load_config()
    data    = request.get_json()
    pattern = data.get("pattern", "").strip()
    volume  = int(data.get("volume", cfg.get("buzzer_volume", 80)))
    wpm     = int(data.get("wpm",    cfg.get("buzzer_wpm",    15)))
    gpio    = cfg.get("buzzer_gpio", 18)
    if not pattern:
        return jsonify({"ok": False, "error": "Empty pattern"})
    def _play():
        try:
            import sys; sys.path.insert(0, str(BASE_DIR))
            from buzzer_controller import tocar_buzzer_custom
            tocar_buzzer_custom(gpio=gpio, texto=pattern, volume=volume, wpm=wpm)
        except Exception as e:
            log.error(f"Buzzer play error: {e}")
    threading.Thread(target=_play, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/hotspot/save", methods=["POST"])
def hotspot_save():
    cfg  = load_config()
    data = request.get_json()
    cfg["ap_ssid"] = data.get("ap_ssid", "crypto-epaper").strip()
    cfg["ap_pass"] = data.get("ap_pass", "bitcoin123").strip()
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/resetar_alerta")
def resetar_alerta():
    cfg = load_config()
    cfg["alerta_disparado"] = False
    save_config(cfg)
    return redirect(url_for("index", msg="✅ Alert reset.", ok=1))


@app.route("/wallet/preview", methods=["POST"])
def wallet_preview():
    import requests as req
    data    = request.get_json()
    address = data.get("address", "").strip()
    network = data.get("network", "bitcoin")
    cfg     = load_config()
    sym     = {"usd":"$","brl":"R$","eur":"€","gbp":"£","jpy":"¥"}.get(cfg["fiat"], cfg["fiat"].upper())
    try:
        if network == "bitcoin":
            r       = req.get(f"https://blockchain.info/q/addressbalance/{address}?confirmations=1", timeout=10)
            balance = int(r.text.strip()) / 1e8
            unit    = "BTC"
        elif network == "ethereum":
            r = req.get("https://api.etherscan.io/api",
                params={"module":"account","action":"balance","address":address,"tag":"latest"}, timeout=10)
            d = r.json()
            if d.get("status") != "1":
                return jsonify({"ok": False, "error": d.get("message", "API error")})
            balance = int(d["result"]) / 1e18
            unit    = "ETH"
        elif network == "solana":
            r       = req.post("https://api.mainnet-beta.solana.com",
                json={"jsonrpc":"2.0","id":1,"method":"getBalance","params":[address]}, timeout=10)
            balance = r.json()["result"]["value"] / 1e9
            unit    = "SOL"
        else:
            return jsonify({"ok": False, "error": "Unknown network"})
        pr       = req.get("https://api.coingecko.com/api/v3/simple/price",
            params={"ids": network, "vs_currencies": cfg["fiat"]}, timeout=10)
        price    = pr.json().get(network, {}).get(cfg["fiat"], 0)
        fiat_val = balance * price
        bal_str  = f"{balance:.6f} {unit}" if balance < 1 else f"{balance:.4f} {unit}"
        fiat_str = f"{sym}{fiat_val:,.2f}"
        return jsonify({"ok": True, "balance": bal_str, "fiat_value": fiat_str})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/price")
def api_price():
    import requests as req
    cfg = load_config()
    sym = {"usd":"$","brl":"R$","eur":"€","gbp":"£","jpy":"¥"}.get(cfg["fiat"], cfg["fiat"].upper())
    try:
        r = req.get("https://api.coingecko.com/api/v3/simple/price",
            params={"ids":cfg["crypto"],"vs_currencies":cfg["fiat"],"include_24hr_change":"true"},
            timeout=8)
        d = r.json().get(cfg["crypto"], {})
        return jsonify({"price":d.get(cfg["fiat"],0),
            "change_24h":d.get(f"{cfg['fiat']}_24h_change",0),
            "fiat_symbol":sym,"crypto":cfg["crypto"]})
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/service/<action>", methods=["POST"])
def service(action):
    cmds = {
        "restart":["sudo","systemctl","restart","crypto-epaper"],
        "stop":   ["sudo","systemctl","stop",   "crypto-epaper"],
        "start":  ["sudo","systemctl","start",  "crypto-epaper"],
    }
    if action not in cmds:
        return redirect(url_for("index", msg="Invalid action.", ok=0))
    try:
        subprocess.run(cmds[action], timeout=10, check=True)
        labels = {"restart":"restarted","stop":"stopped","start":"started"}
        return redirect(url_for("index", msg=f"✅ Service {labels[action]}.", ok=1))
    except Exception as e:
        return redirect(url_for("index", msg=f"Error: {e}", ok=0))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
