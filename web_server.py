#!/usr/bin/env python3
"""
web_server.py - Flask web dashboard
Local configuration panel served on port 8080.
"""

import json, logging, subprocess, threading
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
        }


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crypto E-Paper</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--border:#2d3147;--accent:#6c63ff;
      --text:#e2e8f0;--muted:#8892a4;--green:#34d399;--red:#f87171;--yellow:#fbbf24;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',sans-serif;
     min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:24px 16px;}
h1{font-size:1.5rem;margin-bottom:4px;}
.subtitle{color:var(--muted);font-size:.85rem;margin-bottom:28px;}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;
      padding:24px;width:100%;max-width:480px;margin-bottom:16px;}
.card h2{font-size:1rem;color:var(--accent);margin-bottom:16px;}
label{display:block;color:var(--muted);font-size:.8rem;margin-bottom:4px;
      margin-top:14px;text-transform:uppercase;letter-spacing:.05em;}
select,input[type=number],input[type=text]{width:100%;background:var(--bg);
  border:1px solid var(--border);color:var(--text);padding:10px 12px;
  border-radius:8px;font-size:.95rem;}
input[type=range]{width:100%;accent-color:var(--accent);margin-top:4px;}
.toggle-row{display:flex;justify-content:space-between;align-items:center;
            padding:10px 0;border-bottom:1px solid var(--border);}
.toggle-row:last-child{border-bottom:none;}
.toggle{position:relative;width:42px;height:24px;}
.toggle input{opacity:0;width:0;height:0;}
.slider{position:absolute;inset:0;background:var(--border);border-radius:24px;cursor:pointer;transition:.3s;}
.slider:before{content:'';position:absolute;height:18px;width:18px;left:3px;bottom:3px;
               background:white;border-radius:50%;transition:.3s;}
input:checked+.slider{background:var(--accent);}
input:checked+.slider:before{transform:translateX(18px);}
.btn{display:block;width:100%;padding:12px;border:none;border-radius:8px;
     font-size:1rem;font-weight:600;cursor:pointer;margin-top:8px;transition:opacity .2s;}
.btn:hover{opacity:.85;}
.btn-primary{background:var(--accent);color:white;}
.btn-warn{background:#78350f;color:var(--yellow);}
.btn-danger{background:#374151;color:var(--red);}
.btn-green{background:#064e3b;color:var(--green);}
.btn-sm{padding:8px 14px;font-size:.85rem;width:auto;display:inline-block;}
.status{font-size:.82rem;text-align:center;margin-top:8px;}
.status.ok{color:var(--green);} .status.err{color:var(--red);}
.price-box{background:var(--bg);border-radius:8px;padding:16px;text-align:center;margin-bottom:16px;}
.price-val{font-size:2rem;font-weight:700;}
.price-change{font-size:.9rem;margin-top:4px;}
.up{color:var(--green);} .dn{color:var(--red);}
.badge{display:inline-block;background:#78350f;color:var(--yellow);
       border-radius:6px;padding:2px 8px;font-size:.75rem;margin-left:8px;}
.preview-row{display:flex;gap:12px;margin-top:12px;}
.preview-box{flex:1;border-radius:8px;padding:12px;text-align:center;cursor:pointer;
             border:2px solid transparent;transition:.2s;font-size:.85rem;font-weight:600;}
.preview-box.selected{border-color:var(--accent);}
.preview-normal{background:#fff;color:#000;}
.preview-inverted{background:#000;color:#fff;border:1px solid #444;}
.morse-preview{background:var(--bg);border:1px solid var(--border);border-radius:8px;
               padding:10px 12px;margin-top:8px;font-family:monospace;font-size:.82rem;
               color:var(--green);min-height:40px;word-break:break-all;line-height:1.8;}
.morse-preview .dot{display:inline-block;width:7px;height:7px;background:var(--green);
                    border-radius:50%;margin:0 2px;vertical-align:middle;}
.morse-preview .dash{display:inline-block;width:20px;height:7px;background:var(--green);
                     border-radius:4px;margin:0 2px;vertical-align:middle;}
.morse-preview .gap{display:inline-block;width:12px;vertical-align:middle;}
.morse-type{font-size:.72rem;color:var(--muted);margin-top:4px;}
.sound-row{display:flex;gap:8px;align-items:flex-end;margin-top:8px;}
.sound-row .sound-input{flex:1;}
.sound-label{font-size:.75rem;color:var(--muted);margin-bottom:4px;}
.input-action-row{display:flex;gap:8px;margin-top:8px;}
.input-action-row input{flex:1;}
.hint{font-size:.75rem;color:var(--muted);margin-top:6px;line-height:1.5;}
.divider{border:none;border-top:1px solid var(--border);margin:16px 0;}
footer{color:var(--muted);font-size:.75rem;margin-top:24px;}
</style></head><body>
<h1>🖥️ Crypto E-Paper</h1>
<p class="subtitle">Configuration panel — Raspberry Pi</p>
{% if msg %}<div class="status {{ 'ok' if ok else 'err' }}">{{ msg }}</div>{% endif %}

<!-- Current Price -->
<div class="card"><h2>📊 Current Price</h2>
  <div class="price-box">
    <div class="price-val" id="pv">Loading…</div>
    <div class="price-change" id="pc"></div>
    <div style="color:var(--muted);font-size:.75rem;margin-top:6px" id="pt"></div>
  </div>
</div>

<!-- Settings -->
<form method="POST" action="/save">
<div class="card"><h2>⚙️ Settings</h2>
  <label>Cryptocurrency</label>
  <select name="crypto">{% for id,name in cryptos %}
    <option value="{{ id }}" {{ 'selected' if cfg.crypto==id }}>{{ name }}</option>
  {% endfor %}</select>
  <label>Fiat Currency</label>
  <select name="fiat">{% for id,name in fiats %}
    <option value="{{ id }}" {{ 'selected' if cfg.fiat==id }}>{{ name }}</option>
  {% endfor %}</select>
  <label>Update Interval</label>
  <select name="interval_sec">{% for sec,lbl in intervals %}
    <option value="{{ sec }}" {{ 'selected' if cfg.interval_sec==sec }}>{{ lbl }}</option>
  {% endfor %}</select>
  <button type="submit" class="btn btn-primary" style="margin-top:20px">💾 Save Settings</button>
</div></form>

<!-- Appearance -->
<form method="POST" action="/save_display">
<div class="card"><h2>🎨 Display Appearance</h2>
  <label>Color Scheme</label>
  <div class="preview-row">
    <div class="preview-box preview-normal {{ 'selected' if not cfg.cores_invertidas }}"
         onclick="selectTheme('normal')">
      ☀️ Normal<br><small style="font-weight:400">Black bg · White text</small>
    </div>
    <div class="preview-box preview-inverted {{ 'selected' if cfg.cores_invertidas }}"
         onclick="selectTheme('inverted')">
      🌙 Inverted<br><small style="font-weight:400">White bg · Black text</small>
    </div>
  </div>
  <input type="hidden" name="cores_invertidas" id="theme_input"
         value="{{ 'true' if cfg.cores_invertidas else 'false' }}">
  <button type="submit" class="btn btn-primary" style="margin-top:16px">🎨 Apply Theme</button>
</div></form>

<!-- Price Alerts -->
<form method="POST" action="/save_alertas">
<div class="card"><h2>🔔 Price Alerts
  {% if cfg.buzzer_ativo %}<span class="badge">ACTIVE</span>{% endif %}
</h2>
  <div class="toggle-row"><span>Buzzer enabled</span>
    <label class="toggle">
      <input type="checkbox" name="buzzer_ativo" {{ 'checked' if cfg.buzzer_ativo }}>
      <span class="slider"></span>
    </label>
  </div>

  <label>GPIO Pin</label>
  <input type="number" name="buzzer_gpio" value="{{ cfg.buzzer_gpio }}" min="1" max="40">

  <label>Alert if price ABOVE (0 = disabled)</label>
  <input type="number" name="alerta_acima" value="{{ cfg.alerta_acima }}" min="0" step="100">

  <label>Alert if price BELOW (0 = disabled)</label>
  <input type="number" name="alerta_abaixo" value="{{ cfg.alerta_abaixo }}" min="0" step="100">

  <hr class="divider">

  <!-- Custom alert sounds -->
  <div style="color:var(--text);font-size:.9rem;font-weight:600;margin-bottom:4px">🔊 Alert Sounds</div>
  <div class="hint">Use letters for Morse code or numbers for beep sequences (e.g. SOS, 3, 1,2,3)</div>

  <label>📈 Sound when price goes ABOVE threshold</label>
  <div class="sound-row">
    <div class="sound-input">
      <input type="text" name="sound_high" id="sound_high_input"
             value="{{ cfg.get('sound_high', '3') }}"
             placeholder="e.g. 3  or  SOS  or  1,2"
             oninput="updateSoundPreview('sound_high_input','sound_high_preview','sound_high_type')">
    </div>
    <button type="button" class="btn btn-green btn-sm"
            onclick="testSound('sound_high_input')">▶ Test</button>
  </div>
  <div class="morse-preview" id="sound_high_preview">—</div>
  <div class="morse-type" id="sound_high_type"></div>

  <label>📉 Sound when price goes BELOW threshold</label>
  <div class="sound-row">
    <div class="sound-input">
      <input type="text" name="sound_low" id="sound_low_input"
             value="{{ cfg.get('sound_low', '5') }}"
             placeholder="e.g. 5  or  SOS  or  3,1"
             oninput="updateSoundPreview('sound_low_input','sound_low_preview','sound_low_type')">
    </div>
    <button type="button" class="btn btn-danger btn-sm"
            onclick="testSound('sound_low_input')">▶ Test</button>
  </div>
  <div class="morse-preview" id="sound_low_preview">—</div>
  <div class="morse-type" id="sound_low_type"></div>

  {% if cfg.alerta_disparado %}
  <div style="color:var(--yellow);font-size:.85rem;margin-top:12px">⚠️ Alert already fired this cycle.</div>
  {% endif %}

  <button type="submit" class="btn btn-warn" style="margin-top:16px">🔔 Save Alerts</button>
  <a href="/resetar_alerta"><button type="button" class="btn btn-danger">↺ Reset fired alert</button></a>
</div></form>

<!-- Custom Buzzer Pattern -->
<div class="card"><h2>🎵 Buzzer — Custom Pattern</h2>
  <label>Pattern</label>
  <div class="input-action-row">
    <input type="text" id="buzzer_pattern_input"
           placeholder="e.g. SOS  |  BITCOIN  |  3  |  1,2,3"
           value="{{ cfg.get('buzzer_pattern','') }}"
           oninput="updatePreview(this.value)">
    <button type="button" class="btn btn-green btn-sm" onclick="playNow()">▶ Play</button>
  </div>
  <div class="hint">
    💡 <strong>Letters</strong> → Morse code &nbsp;|&nbsp;
    <strong>Numbers</strong> → N beeps &nbsp;|&nbsp;
    <strong>1,3,2</strong> → 1 beep, pause, 3 beeps, pause, 2 beeps
  </div>
  <div class="morse-preview" id="morse_preview">Type something above to see the preview…</div>
  <div class="morse-type" id="morse_type"></div>

  <label style="margin-top:16px">Volume <span id="vol_label">{{ cfg.get('buzzer_volume', 80) }}%</span></label>
  <input type="range" id="vol_range" min="1" max="95" step="5"
         value="{{ cfg.get('buzzer_volume', 80) }}"
         oninput="document.getElementById('vol_label').textContent=this.value+'%'">
  <div class="hint">⚠️ Max capped at 95% — at 100% PWM becomes DC and buzzer stops vibrating</div>

  <label>Morse Speed (WPM) <span id="wpm_label">{{ cfg.get('buzzer_wpm', 15) }}</span></label>
  <input type="range" id="wpm_range" min="5" max="30" step="1"
         value="{{ cfg.get('buzzer_wpm', 15) }}"
         oninput="document.getElementById('wpm_label').textContent=this.value">

  <button type="button" class="btn btn-primary" style="margin-top:16px" onclick="saveBuzzer()">💾 Save Buzzer Settings</button>
</div>

<!-- Service Control -->
<div class="card"><h2>🔧 Service Control</h2>
  <form method="POST" action="/service/restart">
    <button type="submit" class="btn btn-primary">🔄 Restart Display</button></form>
  <form method="POST" action="/service/stop">
    <button type="submit" class="btn btn-danger">⏹ Stop Display</button></form>
  <form method="POST" action="/service/start">
    <button type="submit" class="btn btn-green">▶ Start Display</button></form>
</div>

<footer>Crypto E-Paper · {{ now }}</footer>

<script>
const MORSE_TABLE = {
  'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....','I':'..','J':'.---',
  'K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.','Q':'--.-','R':'.-.','S':'...','T':'-',
  'U':'..-','V':'...-','W':'.--','X':'-..-','Y':'-.--','Z':'--..',
  '0':'-----','1':'.----','2':'..---','3':'...--','4':'....-','5':'.....','6':'-....','7':'--...','8':'---..','9':'----.',
  '.':'.-.-.-',',':'--..--','?':'..--..','!':'-.-.--'
};

function isNumericSeq(txt){ return /^[\d,\s]+$/.test(txt.trim()); }

function renderMorseHTML(text){
  let html='';
  for(const ch of text.toUpperCase()){
    if(ch===' '){ html+='<span style="display:inline-block;width:24px"></span>'; continue; }
    const code=MORSE_TABLE[ch];
    if(!code){ html+=`<span style="color:var(--red)">${ch}?</span> `; continue; }
    html+=`<span style="color:var(--muted);font-size:.68rem;margin-right:1px">${ch}</span>`;
    for(const s of code){
      if(s==='.') html+='<span class="dot"></span>';
      else        html+='<span class="dash"></span>';
    }
    html+='<span class="gap"></span>';
  }
  return html;
}

function renderSeqHTML(nums){
  return nums.map(n=>'🔔'.repeat(Math.min(n,15))+` <small style="color:var(--muted)">(${n}x)</small>`).join(' <span style="color:var(--muted)">→</span> ');
}

function buildPreview(val){
  if(!val || !val.trim()) return {html:'—', desc:''};
  if(isNumericSeq(val)){
    const nums=val.trim().split(/[,\s]+/).filter(Boolean).map(Number).filter(n=>!isNaN(n)&&n>0);
    if(nums.length) return {html:renderSeqHTML(nums), desc:`Beep sequence: ${nums.join(' → ')}`};
  }
  const morseText=[...val.toUpperCase()].map(c=>MORSE_TABLE[c]||'?').join(' ');
  return {html:renderMorseHTML(val), desc:`Morse: ${morseText}`};
}

function updatePreview(val){
  const p=buildPreview(val);
  document.getElementById('morse_preview').innerHTML=p.html || 'Type something above to see the preview…';
  document.getElementById('morse_type').textContent=p.desc;
}

function updateSoundPreview(inputId, previewId, typeId){
  const val=document.getElementById(inputId).value;
  const p=buildPreview(val);
  document.getElementById(previewId).innerHTML=p.html || '—';
  document.getElementById(typeId).textContent=p.desc;
}

// Initialize previews on load
updatePreview(document.getElementById('buzzer_pattern_input').value);
updateSoundPreview('sound_high_input','sound_high_preview','sound_high_type');
updateSoundPreview('sound_low_input','sound_low_preview','sound_low_type');

async function testSound(inputId){
  const pattern=document.getElementById(inputId).value.trim();
  const volume=document.getElementById('vol_range').value;
  const wpm=document.getElementById('wpm_range').value;
  if(!pattern){ alert('Enter a pattern first!'); return; }
  const btn=event.currentTarget;
  btn.textContent='⏳'; btn.disabled=true;
  try{
    const r=await fetch('/buzzer/play',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({pattern,volume:parseInt(volume),wpm:parseInt(wpm)})});
    const d=await r.json();
    btn.textContent=d.ok?'✅':'❌';
  }catch(e){ btn.textContent='❌'; }
  setTimeout(()=>{ btn.textContent='▶ Test'; btn.disabled=false; },2000);
}

async function playNow(){
  const pattern=document.getElementById('buzzer_pattern_input').value.trim();
  const volume=document.getElementById('vol_range').value;
  const wpm=document.getElementById('wpm_range').value;
  if(!pattern){ alert('Enter a pattern first!'); return; }
  const btn=event.currentTarget;
  btn.textContent='⏳'; btn.disabled=true;
  try{
    const r=await fetch('/buzzer/play',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({pattern,volume:parseInt(volume),wpm:parseInt(wpm)})});
    const d=await r.json();
    btn.textContent=d.ok?'✅':'❌';
  }catch(e){ btn.textContent='❌'; }
  setTimeout(()=>{ btn.textContent='▶ Play'; btn.disabled=false; },2000);
}

async function saveBuzzer(){
  const pattern=document.getElementById('buzzer_pattern_input').value.trim();
  const volume=document.getElementById('vol_range').value;
  const wpm=document.getElementById('wpm_range').value;
  const r=await fetch('/buzzer/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({pattern,volume:parseInt(volume),wpm:parseInt(wpm)})});
  const d=await r.json();
  showMsg(d.ok?'✅ Buzzer settings saved!':'❌ Save failed');
}

function showMsg(text){
  let el=document.querySelector('.flash-msg');
  if(!el){ el=document.createElement('div'); el.className='status ok flash-msg'; document.querySelector('h1').after(el); }
  el.textContent=text;
  setTimeout(()=>el.remove(),3000);
}

function selectTheme(mode){
  document.getElementById('theme_input').value=mode==='inverted'?'true':'false';
  document.querySelectorAll('.preview-box').forEach(e=>e.classList.remove('selected'));
  event.currentTarget.classList.add('selected');
}

async function refreshPrice(){
  try{
    const r=await fetch('/api/price'); const d=await r.json();
    if(d.error){ document.getElementById('pv').textContent='API error'; return; }
    const p=d.price;
    document.getElementById('pv').textContent=d.fiat_symbol+(p>=1000?
      p.toLocaleString('en-US',{maximumFractionDigits:0}):
      p.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}));
    const chg=d.change_24h; const el=document.getElementById('pc');
    el.textContent=(chg>=0?'▲':'▼')+' '+Math.abs(chg).toFixed(2)+'%';
    el.className='price-change '+(chg>=0?'up':'dn');
    document.getElementById('pt').textContent='Updated: '+new Date().toLocaleTimeString();
  }catch(e){ document.getElementById('pv').textContent='No connection'; }
}
refreshPrice(); setInterval(refreshPrice,60000);
</script></body></html>
"""


@app.route("/")
def index():
    cfg = load_config()
    cfg.setdefault("cores_invertidas", False)
    cfg.setdefault("buzzer_volume",    80)
    cfg.setdefault("buzzer_wpm",       15)
    cfg.setdefault("buzzer_pattern",   "")
    cfg.setdefault("sound_high",       "3")
    cfg.setdefault("sound_low",        "5")
    return render_template_string(HTML, cfg=cfg, cryptos=CRYPTOS, fiats=FIATS, intervals=INTERVALS,
        msg=request.args.get("msg", ""), ok=request.args.get("ok", "1") == "1",
        now=datetime.now().strftime("%Y-%m-%d %H:%M"))


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
    return redirect(url_for("index", msg="✅ Theme applied — takes effect on next update.", ok=1))


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
            import sys
            sys.path.insert(0, str(BASE_DIR))
            from buzzer_controller import tocar_buzzer_custom
            tocar_buzzer_custom(gpio=gpio, texto=pattern, volume=volume, wpm=wpm)
        except Exception as e:
            log.error(f"Buzzer play error: {e}")

    threading.Thread(target=_play, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/resetar_alerta")
def resetar_alerta():
    cfg = load_config()
    cfg["alerta_disparado"] = False
    save_config(cfg)
    return redirect(url_for("index", msg="✅ Alert reset.", ok=1))


@app.route("/api/price")
def api_price():
    import requests as req
    cfg = load_config()
    sym = {"usd": "$", "brl": "R$", "eur": "€", "gbp": "£", "jpy": "¥"}.get(cfg["fiat"], cfg["fiat"].upper())
    try:
        r = req.get("https://api.coingecko.com/api/v3/simple/price",
            params={"ids": cfg["crypto"], "vs_currencies": cfg["fiat"], "include_24hr_change": "true"},
            timeout=8)
        d = r.json().get(cfg["crypto"], {})
        return jsonify({
            "price":      d.get(cfg["fiat"], 0),
            "change_24h": d.get(f"{cfg['fiat']}_24h_change", 0),
            "fiat_symbol": sym,
            "crypto":     cfg["crypto"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/service/<action>", methods=["POST"])
def service(action):
    cmds = {
        "restart": ["sudo", "systemctl", "restart", "crypto-epaper"],
        "stop":    ["sudo", "systemctl", "stop",    "crypto-epaper"],
        "start":   ["sudo", "systemctl", "start",   "crypto-epaper"],
    }
    if action not in cmds:
        return redirect(url_for("index", msg="Invalid action.", ok=0))
    try:
        subprocess.run(cmds[action], timeout=10, check=True)
        labels = {"restart": "restarted", "stop": "stopped", "start": "started"}
        return redirect(url_for("index", msg=f"✅ Service {labels[action]}.", ok=1))
    except Exception as e:
        return redirect(url_for("index", msg=f"Error: {e}", ok=0))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
