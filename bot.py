import os
import time
import threading
import sqlite3
import hashlib
import uuid
from datetime import timedelta
from flask import Flask, request, render_template_string, session, redirect, url_for
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)
app.secret_key = "AASHIQ_HATELA_SECRET"

DB = "aashiq_bot.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    user_id TEXT UNIQUE
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (
                    user_id TEXT PRIMARY KEY,
                    chat_id TEXT,
                    target_name TEXT,
                    delay INTEGER,
                    cookies TEXT,
                    messages TEXT,
                    is_running INTEGER,
                    total_sent INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()

init_db()

def create_user(username, password):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        uid = str(uuid.uuid4())[:8]
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, user_id) VALUES (?,?,?)", (username, pwd_hash, uid))
        c.execute("INSERT INTO config (user_id, chat_id, target_name, delay, cookies, messages, is_running, total_sent) VALUES (?,?,?,?,?,?,?,?)",
                  (uid, "", "", 5, "", "Hello!\nHow are you?", 0, 0))
        conn.commit()
        return True, "Account created!"
    except:
        return False, "Username exists."
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT user_id FROM users WHERE username=? AND password=?", (username, pwd_hash))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

def get_config(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT chat_id, target_name, delay, cookies, messages, is_running, total_sent FROM config WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"chat_id": row[0], "target_name": row[1], "delay": row[2], "cookies": row[3], "messages": row[4], "is_running": row[5], "total_sent": row[6]}
    return None

def update_config(user_id, chat_id, target_name, delay, cookies, messages):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE config SET chat_id=?, target_name=?, delay=?, cookies=?, messages=? WHERE user_id=?", 
              (chat_id, target_name, delay, cookies, messages, user_id))
    conn.commit()
    conn.close()

def set_running(user_id, running):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE config SET is_running=? WHERE user_id=?", (1 if running else 0, user_id))
    conn.commit()
    conn.close()

def increment_sent_count(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE config SET total_sent = total_sent + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_sent_count(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT total_sent FROM config WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

user_logs = {}

def add_log(user_id, msg):
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    if user_id not in user_logs:
        user_logs[user_id] = []
    user_logs[user_id].append(formatted)
    if len(user_logs[user_id]) > 200:
        user_logs[user_id] = user_logs[user_id][-200:]

def get_logs(user_id):
    return user_logs.get(user_id, [])

def send_facebook_message(user_id, driver, chat_id, message, cookies_str):
    try:
        driver.get('https://www.facebook.com/')
        time.sleep(5)
        
        if cookies_str:
            for cookie in cookies_str.split(';'):
                if '=' in cookie and cookie.strip():
                    name, val = cookie.strip().split('=', 1)
                    try:
                        driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.facebook.com'})
                    except:
                        pass
            driver.refresh()
            time.sleep(5)
        
        driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
        time.sleep(8)
        
        msg_input = None
        selectors = ['div[contenteditable="true"][role="textbox"]', 'div[contenteditable="true"]', 'textarea']
        for sel in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elements:
                    if el.is_displayed():
                        msg_input = el
                        break
                if msg_input:
                    break
            except:
                continue
        
        if not msg_input:
            return False
        
        driver.execute_script("arguments[0].click();", msg_input)
        driver.execute_script("arguments[0].innerText = arguments[1];", msg_input, message)
        time.sleep(2)
        msg_input.send_keys("\n")
        return True
    except Exception as e:
        return False

running_threads = {}

def automation_worker(user_id, config):
    set_running(user_id, True)
    add_log(user_id, "🤖 REAL AUTOMATION STARTED")
    add_log(user_id, f"📱 Chat ID: {config['chat_id']}")
    
    messages = [m.strip() for m in config["messages"].split("\n") if m.strip()]
    if not messages:
        messages = ["Hello from AASHIQ HATELA!"]
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    
    driver = None
    try:
        add_log(user_id, "🚀 Starting Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        add_log(user_id, "✅ Chrome ready!")
        
        idx = 0
        while running_threads.get(user_id, False):
            msg = messages[idx % len(messages)]
            if config["target_name"]:
                full = f"🔥 {config['target_name']} 🔥 {msg}"
            else:
                full = msg
            
            add_log(user_id, f"📤 Sending: {full[:40]}...")
            success = send_facebook_message(user_id, driver, config["chat_id"], full, config["cookies"])
            
            if success:
                increment_sent_count(user_id)
                add_log(user_id, f"✅ Sent! Total: {get_sent_count(user_id)}")
            else:
                add_log(user_id, "❌ Failed")
            
            idx += 1
            time.sleep(config["delay"])
    except Exception as e:
        add_log(user_id, f"💀 Error: {str(e)[:100]}")
    finally:
        if driver:
            driver.quit()
        set_running(user_id, False)
        add_log(user_id, "🛑 Stopped")

def start_automation(user_id, config):
    if user_id in running_threads and running_threads[user_id]:
        return False
    if not config['chat_id']:
        add_log(user_id, "❌ Chat ID missing")
        return False
    running_threads[user_id] = True
    thread = threading.Thread(target=automation_worker, args=(user_id, config), daemon=True)
    thread.start()
    return True

def stop_automation(user_id):
    if user_id in running_threads:
        running_threads[user_id] = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AASHIQ HATELA - FB E2E BOT</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial; }
        body { background: linear-gradient(135deg, #0a2f1f, #145c33); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .card { background: rgba(255,255,255,0.95); border-radius: 32px; padding: 30px; max-width: 900px; width: 100%; border: 2px solid gold; }
        h1 { color: #1a472a; text-align: center; }
        .gold { color: #daa520; text-align: center; margin-bottom: 20px; }
        input, textarea { width: 100%; padding: 12px; margin: 8px 0; border-radius: 20px; border: 1px solid #2d6a4f; }
        button { background: linear-gradient(140deg,#ffd700,#daa520); color: #1a472a; font-weight: bold; padding: 12px; border: none; border-radius: 30px; width: 100%; margin-top: 10px; cursor: pointer; }
        .metric { display: inline-block; width: 30%; background: #e8f5e9; border-radius: 15px; padding: 10px; margin: 5px; text-align: center; }
        .log-box { background: #0a2f1f; border: 2px solid gold; border-radius: 20px; padding: 15px; max-height: 400px; overflow-y: auto; margin-top: 20px; }
        .log-line { color: #a5d6a7; padding: 4px 0; border-bottom: 1px solid #2d6a4f; font-size: 0.85rem; }
        .footer { text-align: center; margin-top: 30px; padding: 15px; background: rgba(0,0,0,0.3); border-radius: 20px; color: gold; }
        hr { border-color: gold; margin: 15px 0; }
    </style>
</head>
<body>
<div class="card">
    {% if not session.logged_in %}
        <h1>👑🤴 AASHIQ HATELA 🤴👑</h1>
        <div class="gold">💀 FACEBOOK E2EE OFFLINE CONVO SYSTEM 💀</div>
        <hr>
        <form method="post">
            <input type="hidden" name="form_type" value="login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">🔐 LOGIN</button>
        </form>
        <hr>
        <form method="post">
            <input type="hidden" name="form_type" value="signup">
            <input type="text" name="new_username" placeholder="New Username" required>
            <input type="password" name="new_password" placeholder="Password" required>
            <input type="password" name="confirm" placeholder="Confirm" required>
            <button type="submit">📝 SIGN UP</button>
        </form>
    {% else %}
        <h1>👑🤴 AASHIQ HATELA 🤴👑</h1>
        <div><strong>👤 {{ session.username }}</strong> | ID: {{ session.user_id }}</div>
        <div style="background:green; border-radius:15px; padding:8px; text-align:center; color:gold; margin:15px 0;">✅ PREMIUM</div>
        <form method="post"><input type="hidden" name="form_type" value="logout"><button style="background:#8B0000; color:white;">🚪 LOGOUT</button></form>
        <hr>
        <h3>⚙️ SETUP</h3>
        <form method="post">
            <input type="hidden" name="form_type" value="config">
            <input type="text" name="chat_id" placeholder="CHAT ID" value="{{ config.chat_id }}">
            <input type="text" name="target_name" placeholder="TARGET NAME" value="{{ config.target_name }}">
            <input type="number" name="delay" value="{{ config.delay }}" min="1" max="300">
            <textarea name="cookies" rows="3" placeholder="COOKIES">{{ config.cookies }}</textarea>
            <textarea name="messages" rows="4" placeholder="MESSAGES">{{ config.messages }}</textarea>
            <button type="submit">💾 SAVE</button>
        </form>
        <hr>
        <h3>🚀 AUTOMATION</h3>
        <div>
            <span class="metric">📨 SENT: {{ config.total_sent }}</span>
            <span class="metric">⚡ STATUS: {{ "RUNNING" if config.is_running else "STOPPED" }}</span>
            <span class="metric">🎯 CHAT: {{ config.chat_id[:10] + "..." if config.chat_id|length > 10 else config.chat_id or "N/A" }}</span>
        </div>
        <div style="display: flex; gap: 10px;">
            <form method="post" style="flex:1"><input type="hidden" name="form_type" value="start"><button type="submit" {% if config.is_running %}disabled{% endif %}>▶️ START</button></form>
            <form method="post" style="flex:1"><input type="hidden" name="form_type" value="stop"><button type="submit" {% if not config.is_running %}disabled{% endif %} style="background:#8B0000;">⏹️ STOP</button></form>
        </div>
        <div class="log-box">
            <div style="color:gold;">💀 LIVE OUTPUT 💀</div>
            {% for log in logs[-40:] %}<div class="log-line">{{ log }}</div>{% endfor %}
        </div>
        <form method="get"><button type="submit">🔄 REFRESH</button></form>
    {% endif %}
    <div class="footer">👑 MADE IN INDIA | AASHIQ HATELA 👑</div>
</div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'login':
            user = request.form.get('username')
            pwd = request.form.get('password')
            uid = verify_user(user, pwd)
            if uid:
                session['logged_in'] = True
                session['user_id'] = uid
                session['username'] = user
                add_log(uid, f"✅ {user} logged in")
                return redirect(url_for('index'))
            else:
                return render_template_string(HTML_TEMPLATE, session={}, error="Invalid")
        elif form_type == 'signup':
            new_user = request.form.get('new_username')
            new_pwd = request.form.get('new_password')
            confirm = request.form.get('confirm')
            if new_pwd != confirm:
                return render_template_string(HTML_TEMPLATE, session={}, error="Passwords mismatch")
            ok, msg = create_user(new_user, new_pwd)
            if ok:
                return render_template_string(HTML_TEMPLATE, session={}, success=msg)
            else:
                return render_template_string(HTML_TEMPLATE, session={}, error=msg)
        elif form_type == 'logout':
            if session.get('user_id'):
                stop_automation(session['user_id'])
            session.clear()
            return redirect(url_for('index'))
        elif form_type == 'config':
            if not session.get('logged_in'):
                return redirect(url_for('index'))
            uid = session['user_id']
            update_config(uid, 
                         request.form.get('chat_id', ''),
                         request.form.get('target_name', ''),
                         int(request.form.get('delay', 5)),
                         request.form.get('cookies', ''),
                         request.form.get('messages', 'Hello!'))
            add_log(uid, "Config saved")
            return redirect(url_for('index'))
        elif form_type == 'start':
            if not session.get('logged_in'):
                return redirect(url_for('index'))
            uid = session['user_id']
            cfg = get_config(uid)
            if cfg and cfg['chat_id']:
                start_automation(uid, cfg)
            else:
                add_log(uid, "Chat ID missing")
            return redirect(url_for('index'))
        elif form_type == 'stop':
            if not session.get('logged_in'):
                return redirect(url_for('index'))
            stop_automation(session['user_id'])
            return redirect(url_for('index'))
    if not session.get('logged_in'):
        return render_template_string(HTML_TEMPLATE, session={})
    uid = session['user_id']
    cfg = get_config(uid)
    if not cfg:
        cfg = {"chat_id": "", "target_name": "", "delay": 5, "cookies": "", "messages": "Hello!", "is_running": 0, "total_sent": 0}
    logs = get_logs(uid)
    return render_template_string(HTML_TEMPLATE, session=session, config=cfg, logs=logs)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)