import sys
import warnings
warnings.filterwarnings('ignore')
import streamlit as st
import time
import threading
import uuid
import hashlib
import sqlite3
import os
import json
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import requests
import shutil
import random

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🤴 AASHIQ HATELA - FB E2E ULTIMATE BOT 🤴",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS (Dark/Light Theme Support) ====================
def get_css(theme):
    if theme == "dark":
        return """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');
        * { font-family: 'Outfit', sans-serif !important; }
        .stApp { background: linear-gradient(135deg, #0a0a0a, #1a1a2e); background-attachment: fixed; }
        .main .block-container { background: rgba(0,0,0,0.85); border-radius: 28px; padding: 40px; border: 1px solid gold; }
        .main-header { background: linear-gradient(135deg, #16213e, #0f3460); border-radius: 25px; padding: 50px 25px; text-align: center; border: 2px solid gold; }
        .main-header h1 { color: gold; font-size: 3rem; font-weight: 900; }
        .main-header p { color: #ffd700; }
        .stButton>button { background: linear-gradient(140deg, #ffd700, #daa520); color: #1a472a; font-weight: 800; }
        .console-output { background: #0a0a0a; border: 2px solid gold; border-radius: 15px; padding: 20px; max-height: 400px; color: #ffd700; overflow-y: auto; }
        .console-line { background: #1a1a1a; padding: 10px; border-left: 4px solid gold; border-radius: 6px; margin-bottom: 8px; }
        .footer { text-align: center; color: gold; margin-top: 2rem; padding: 1.5rem; background: rgba(0,0,0,0.5); border-radius: 20px; }
        .metric-card { background: #16213e; border-radius: 15px; padding: 15px; text-align: center; border: 1px solid gold; }
        </style>
        """
    else:
        return """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');
        * { font-family: 'Outfit', sans-serif !important; }
        .stApp { background: linear-gradient(136deg, #f6f9ff 0%, #e9f3ff 40%, #e1f0ff 100%); background-attachment: fixed; }
        .main .block-container { background: rgba(255,255,255,0.92); border-radius: 28px; padding: 40px; border: 1px solid rgba(255,215,0,0.3); }
        .main-header { background: linear-gradient(135deg, #1a472a, #2d6a4f, #1b4332); border-radius: 25px; padding: 50px 25px; text-align: center; border: 2px solid gold; }
        .main-header h1 { color: gold; font-size: 3rem; font-weight: 900; }
        .main-header p { color: #ffd700; }
        .stButton>button { background: linear-gradient(140deg, #ffd700, #daa520); color: #1a472a; font-weight: 800; }
        .console-output { background: #0a2f1f; border: 2px solid gold; border-radius: 15px; padding: 20px; max-height: 400px; color: #ffd700; overflow-y: auto; }
        .console-line { background: #0e3d25; padding: 10px; border-left: 4px solid gold; border-radius: 6px; margin-bottom: 8px; }
        .footer { text-align: center; color: gold; margin-top: 2rem; padding: 1.5rem; background: rgba(0,0,0,0.3); border-radius: 20px; }
        .metric-card { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); border-radius: 15px; padding: 15px; text-align: center; border: 1px solid gold; }
        </style>
        """

# Theme toggle in session state
if 'theme' not in st.session_state:
    st.session_state.theme = "light"

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# ==================== DATABASE SETUP ====================
DB_PATH = "aashiq_bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  user_id TEXT UNIQUE,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # User config table
    c.execute('''CREATE TABLE IF NOT EXISTS user_config
                 (user_id TEXT PRIMARY KEY,
                  chat_id TEXT,
                  name_prefix TEXT,
                  delay INTEGER DEFAULT 5,
                  cookies TEXT,
                  messages TEXT,
                  automation_running INTEGER DEFAULT 0,
                  total_sent INTEGER DEFAULT 0,
                  total_failed INTEGER DEFAULT 0)''')
    # Templates table
    c.execute('''CREATE TABLE IF NOT EXISTS templates
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  name TEXT,
                  content TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    # Scheduled messages table
    c.execute('''CREATE TABLE IF NOT EXISTS scheduled_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  chat_id TEXT,
                  message TEXT,
                  schedule_time TEXT,
                  status TEXT DEFAULT 'pending',
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    # Contacts table
    c.execute('''CREATE TABLE IF NOT EXISTS contacts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  name TEXT,
                  chat_id TEXT,
                  phone TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    # Analytics table
    c.execute('''CREATE TABLE IF NOT EXISTS analytics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  date TEXT,
                  messages_sent INTEGER DEFAULT 0,
                  messages_failed INTEGER DEFAULT 0,
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    # Auto reply rules table
    c.execute('''CREATE TABLE IF NOT EXISTS auto_reply
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  keyword TEXT,
                  reply TEXT,
                  is_active INTEGER DEFAULT 1,
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    # Multi account table
    c.execute('''CREATE TABLE IF NOT EXISTS accounts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  account_name TEXT,
                  chat_id TEXT,
                  cookies TEXT,
                  is_active INTEGER DEFAULT 1,
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    conn.commit()
    conn.close()

init_db()

# ==================== USER FUNCTIONS ====================
def create_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        user_id = str(uuid.uuid4())[:8]
        hashed = hashlib.sha256(password.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, user_id) VALUES (?, ?, ?)",
                  (username, hashed, user_id))
        c.execute("INSERT INTO user_config (user_id, chat_id, name_prefix, delay, cookies, messages) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, "", "", 5, "", "Hello!\nHow are you?"))
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists!"
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT user_id FROM users WHERE username = ? AND password = ?", (username, hashed))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_config(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id, name_prefix, delay, cookies, messages, automation_running, total_sent, total_failed FROM user_config WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {
            'chat_id': result[0] or '',
            'name_prefix': result[1] or '',
            'delay': result[2] or 5,
            'cookies': result[3] or '',
            'messages': result[4] or 'Hello!\nHow are you?',
            'automation_running': result[5] == 1,
            'total_sent': result[6] or 0,
            'total_failed': result[7] or 0
        }
    return None

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE user_config SET chat_id=?, name_prefix=?, delay=?, cookies=?, messages=? WHERE user_id=?",
              (chat_id, name_prefix, delay, cookies, messages, user_id))
    conn.commit()
    conn.close()

def set_automation_running(user_id, running):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE user_config SET automation_running = ? WHERE user_id = ?", (1 if running else 0, user_id))
    conn.commit()
    conn.close()

def update_stats(user_id, sent=0, failed=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE user_config SET total_sent = total_sent + ?, total_failed = total_failed + ? WHERE user_id = ?",
              (sent, failed, user_id))
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO analytics (user_id, date, messages_sent, messages_failed) VALUES (?, ?, ?, ?) ON CONFLICT DO UPDATE SET messages_sent = messages_sent + ?, messages_failed = messages_failed + ?",
              (user_id, today, sent, failed, sent, failed))
    conn.commit()
    conn.close()

# ==================== TEMPLATE FUNCTIONS ====================
def add_template(user_id, name, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO templates (user_id, name, content) VALUES (?, ?, ?)", (user_id, name, content))
    conn.commit()
    conn.close()

def get_templates(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, content FROM templates WHERE user_id = ?", (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def delete_template(template_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()

# ==================== CONTACT FUNCTIONS ====================
def add_contact(user_id, name, chat_id, phone=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO contacts (user_id, name, chat_id, phone) VALUES (?, ?, ?, ?)", (user_id, name, chat_id, phone))
    conn.commit()
    conn.close()

def get_contacts(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, chat_id, phone FROM contacts WHERE user_id = ?", (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def delete_contact(contact_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()

# ==================== SCHEDULER FUNCTIONS ====================
def add_scheduled_message(user_id, chat_id, message, schedule_time):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO scheduled_messages (user_id, chat_id, message, schedule_time) VALUES (?, ?, ?, ?)",
              (user_id, chat_id, message, schedule_time))
    conn.commit()
    conn.close()

def get_scheduled_messages(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, chat_id, message, schedule_time, status FROM scheduled_messages WHERE user_id = ? AND status = 'pending'", (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def mark_scheduled_complete(msg_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE scheduled_messages SET status = 'sent' WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

# ==================== AUTO REPLY FUNCTIONS ====================
def add_auto_reply(user_id, keyword, reply):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO auto_reply (user_id, keyword, reply) VALUES (?, ?, ?)", (user_id, keyword.lower(), reply))
    conn.commit()
    conn.close()

def get_auto_replies(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, keyword, reply, is_active FROM auto_reply WHERE user_id = ?", (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def toggle_auto_reply(reply_id, is_active):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE auto_reply SET is_active = ? WHERE id = ?", (1 if is_active else 0, reply_id))
    conn.commit()
    conn.close()

# ==================== MULTI ACCOUNT FUNCTIONS ====================
def add_account(user_id, account_name, chat_id, cookies):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO accounts (user_id, account_name, chat_id, cookies) VALUES (?, ?, ?, ?)",
              (user_id, account_name, chat_id, cookies))
    conn.commit()
    conn.close()

def get_accounts(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, account_name, chat_id, cookies, is_active FROM accounts WHERE user_id = ?", (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def delete_account(account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()

# ==================== BACKUP FUNCTION ====================
def backup_database(user_id):
    backup_dir = f"backups/{user_id}"
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/backup_{timestamp}.db"
    shutil.copy2(DB_PATH, backup_file)
    return backup_file

# ==================== SESSION STATE INIT ====================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'automation_state' not in st.session_state:
    class AutoState:
        def __init__(self):
            self.running = False
            self.message_count = 0
            self.logs = []
    st.session_state.automation_state = AutoState()

# ==================== LOGGING ====================
def log_message(msg, state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    if state:
        state.logs.append(formatted)
    else:
        st.session_state.automation_state.logs.append(formatted)

# ==================== WEBHOOK FUNCTION ====================
def send_webhook(user_id, message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT webhook_url FROM webhooks WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result and result[0]:
        try:
            requests.post(result[0], json={"message": message, "user": st.session_state.username}, timeout=5)
        except:
            pass

# ==================== SELENIUM SETUP ====================
def setup_browser(proxy=None):
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    
    if proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def send_message_with_retry(driver, chat_id, message, cookies_str, max_retries=3):
    for attempt in range(max_retries):
        try:
            driver.get('https://www.facebook.com/')
            time.sleep(5)
            
            if cookies_str:
                for cookie in cookies_str.split(';'):
                    if '=' in cookie:
                        name, val = cookie.strip().split('=', 1)
                        try:
                            driver.add_cookie({'name': name, 'value': val, 'domain': '.facebook.com'})
                        except:
                            pass
                driver.refresh()
                time.sleep(5)
            
            driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
            time.sleep(10)
            
            input_box = None
            selectors = ['div[contenteditable="true"][role="textbox"]', 'div[contenteditable="true"]', 'textarea']
            for sel in selectors:
                try:
                    input_box = driver.find_element(By.CSS_SELECTOR, sel)
                    if input_box:
                        break
                except:
                    continue
            
            if not input_box:
                return False
            
            driver.execute_script("arguments[0].click();", input_box)
            driver.execute_script("arguments[0].innerText = arguments[1];", input_box, message)
            time.sleep(2)
            
            try:
                send_btn = driver.find_element(By.CSS_SELECTOR, 'div[aria-label*="Send" i], [data-testid="send-button"]')
                send_btn.click()
            except:
                input_box.send_keys("\n")
            
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                return False
            time.sleep(5)
    return False

# ==================== GROUP MESSAGING ====================
def send_to_group(driver, group_id, message, cookies_str):
    return send_message_with_retry(driver, group_id, message, cookies_str)

# ==================== BULK MESSAGING ====================
def send_bulk_messages(user_id, driver, chat_ids, message, cookies_str, delay):
    success_count = 0
    for chat_id in chat_ids:
        if send_message_with_retry(driver, chat_id, message, cookies_str):
            success_count += 1
            update_stats(user_id, sent=1)
        else:
            update_stats(user_id, failed=1)
        time.sleep(delay)
    return success_count

# ==================== MEDIA SHARING ====================
def send_media(driver, chat_id, media_path, caption, cookies_str):
    try:
        driver.get('https://www.facebook.com/')
        time.sleep(5)
        
        if cookies_str:
            for cookie in cookies_str.split(';'):
                if '=' in cookie:
                    name, val = cookie.strip().split('=', 1)
                    try:
                        driver.add_cookie({'name': name, 'value': val, 'domain': '.facebook.com'})
                    except:
                        pass
            driver.refresh()
            time.sleep(5)
        
        driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
        time.sleep(10)
        
        # Find attachment button and click
        attach_btn = None
        attach_selectors = ['div[aria-label*="attachment"]', 'div[aria-label*="photo"]', 'div[aria-label*="file"]']
        for sel in attach_selectors:
            try:
                attach_btn = driver.find_element(By.CSS_SELECTOR, sel)
                if attach_btn:
                    attach_btn.click()
                    break
            except:
                continue
        
        time.sleep(2)
        
        # Find file input and send file
        file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
        file_input.send_keys(os.path.abspath(media_path))
        time.sleep(5)
        
        # Add caption if provided
        if caption:
            input_box = driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
            input_box.send_keys(caption)
            time.sleep(2)
        
        # Send button
        send_btn = driver.find_element(By.CSS_SELECTOR, 'div[aria-label*="Send" i]')
        send_btn.click()
        
        return True
    except Exception as e:
        return False

# ==================== AUTO REPLY CHECKER (Background Thread) ====================
def auto_reply_checker():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT user_id, keyword, reply FROM auto_reply WHERE is_active = 1")
            rules = c.fetchall()
            conn.close()
            
            for user_id, keyword, reply in rules:
                # This would check incoming messages (requires Facebook API/WebSocket)
                # For now, it's a placeholder
                pass
        except:
            pass
        time.sleep(30)

# ==================== SCHEDULER THREAD ====================
def scheduler_thread():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("SELECT id, user_id, chat_id, message FROM scheduled_messages WHERE schedule_time <= ? AND status = 'pending'", (now,))
            pending = c.fetchall()
            conn.close()
            
            for msg_id, user_id, chat_id, message in pending:
                user_config = get_user_config(user_id)
                if user_config:
                    driver = setup_browser()
                    success = send_message_with_retry(driver, chat_id, message, user_config['cookies'], 3)
                    driver.quit()
                    if success:
                        mark_scheduled_complete(msg_id)
                        update_stats(user_id, sent=1)
                        send_webhook(user_id, f"Scheduled message sent to {chat_id}")
        except:
            pass
        time.sleep(60)

# Start background threads
if not hasattr(st, 'scheduler_started'):
    st.scheduler_started = True
    threading.Thread(target=scheduler_thread, daemon=True).start()
    threading.Thread(target=auto_reply_checker, daemon=True).start()

# ==================== AUTOMATION WORKER ====================
def automation_worker(user_id, config, bulk_chats=None):
    set_automation_running(user_id, True)
    log_message("🤖 AUTOMATION STARTED with all features!", st.session_state.automation_state)
    
    messages = [m.strip() for m in config['messages'].split('\n') if m.strip()]
    if not messages:
        messages = ["Hello from AASHIQ HATELA Bot!"]
    
    driver = None
    try:
        driver = setup_browser()
        log_message("✅ Chrome browser ready!", st.session_state.automation_state)
        
        idx = 0
        while st.session_state.automation_state.running:
            msg = messages[idx % len(messages)]
            if config['name_prefix']:
                final_msg = f"🔥 {config['name_prefix']} 🔥 {msg}"
            else:
                final_msg = msg
            
            if bulk_chats:
                # Bulk messaging mode
                success_count = send_bulk_messages(user_id, driver, bulk_chats, final_msg, config['cookies'], config['delay'])
                log_message(f"📤 Bulk send: {success_count}/{len(bulk_chats)} messages sent!", st.session_state.automation_state)
                update_stats(user_id, sent=success_count, failed=len(bulk_chats)-success_count)
            else:
                # Single chat mode
                log_message(f"📤 Sending: {final_msg[:50]}...", st.session_state.automation_state)
                success = send_message_with_retry(driver, config['chat_id'], final_msg, config['cookies'], 3)
                if success:
                    st.session_state.automation_state.message_count += 1
                    update_stats(user_id, sent=1)
                    log_message(f"✅ Sent! Total: {st.session_state.automation_state.message_count}", st.session_state.automation_state)
                else:
                    update_stats(user_id, failed=1)
                    log_message(f"❌ Failed to send!", st.session_state.automation_state)
            
            idx += 1
            
            # Random delay for spam protection (adds randomness)
            delay = config['delay']
            if config.get('random_delay', False):
                delay = random.randint(int(delay*0.8), int(delay*1.2))
            
            for _ in range(delay):
                if not st.session_state.automation_state.running:
                    break
                time.sleep(1)
                
    except Exception as e:
        log_message(f"💀 Error: {str(e)}", st.session_state.automation_state)
    finally:
        if driver:
            driver.quit()
        set_automation_running(user_id, False)
        log_message("🛑 Automation stopped", st.session_state.automation_state)
        send_webhook(user_id, "Automation stopped")

def start_automation(config, user_id, bulk_chats=None):
    if st.session_state.automation_state.running:
        return
    st.session_state.automation_state.running = True
    st.session_state.automation_state.message_count = 0
    st.session_state.automation_state.logs = []
    thread = threading.Thread(target=automation_worker, args=(user_id, config, bulk_chats), daemon=True)
    thread.start()

def stop_automation():
    st.session_state.automation_state.running = False

# ==================== ANALYTICS DASHBOARD ====================
def show_analytics(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_sent, total_failed FROM user_config WHERE user_id = ?", (user_id,))
    total = c.fetchone()
    
    c.execute("SELECT date, messages_sent FROM analytics WHERE user_id = ? ORDER BY date DESC LIMIT 7", (user_id,))
    last_7_days = c.fetchall()
    conn.close()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📨 Total Sent", total[0] if total else 0)
    with col2:
        st.metric("❌ Total Failed", total[1] if total else 0)
    
    if last_7_days:
        st.subheader("📊 Last 7 Days Activity")
        chart_data = {day[0]: day[1] for day in last_7_days}
        st.bar_chart(chart_data)

# ==================== LOGIN PAGE ====================
def login_page():
    st.markdown("""
    <div class="main-header">
        <h1>👑🤴 AASHIQ HATELA 🤴👑</h1>
        <p>💀 FACEBOOK E2EE ULTIMATE BOT 💀</p>
        <p>🔥 15+ FEATURES | ALL-IN-ONE 🔥</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["🔐 LOGIN", "📝 SIGN UP"])
        with tab1:
            username = st.text_input("USERNAME")
            password = st.text_input("PASSWORD", type="password")
            if st.button("LOGIN", use_container_width=True):
                user_id = verify_user(username, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.success(f"✅ Welcome {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")
        with tab2:
            new_user = st.text_input("USERNAME")
            new_pass = st.text_input("PASSWORD", type="password")
            confirm = st.text_input("CONFIRM PASSWORD", type="password")
            if st.button("CREATE ACCOUNT", use_container_width=True):
                if new_pass == confirm:
                    success, msg = create_user(new_user, new_pass)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("Passwords don't match!")

# ==================== MAIN APP ====================
def main_app():
    # Theme toggle in sidebar
    with st.sidebar:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌞 Light Mode", use_container_width=True):
                st.session_state.theme = "light"
                st.rerun()
        with col2:
            if st.button("🌙 Dark Mode", use_container_width=True):
                st.session_state.theme = "dark"
                st.rerun()
    
    st.markdown("""
    <div class="main-header">
        <h1>👑🤴 AASHIQ HATELA 🤴👑</h1>
        <p>💀 FACEBOOK E2EE ULTIMATE BOT WITH 15+ FEATURES 💀</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown(f"**👤 USER:** {st.session_state.username}")
    st.sidebar.markdown(f"**🆔 ID:** {st.session_state.user_id}")
    
    if st.sidebar.button("🚪 LOGOUT", use_container_width=True):
        if st.session_state.automation_state.running:
            stop_automation()
        st.session_state.logged_in = False
        st.rerun()
    
    user_config = get_user_config(st.session_state.user_id)
    
    if not user_config:
        st.warning("⚠️ Loading configuration...")
        st.rerun()
        return
    
    tabs = st.tabs([
        "⚙️ MAIN SETUP", 
        "🚀 AUTOMATION", 
        "📝 TEMPLATES",
        "👥 CONTACTS",
        "⏰ SCHEDULER",
        "🤖 AUTO REPLY",
        "👤 MULTI ACCOUNT",
        "📊 ANALYTICS",
        "💾 BACKUP",
        "🔗 WEBHOOK"
    ])
    
    # Tab 1: Main Setup
    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            chat_id = st.text_input("📱 CHAT ID / GROUP ID", value=user_config['chat_id'], 
                                   placeholder="Facebook chat ID or group ID")
            name_prefix = st.text_input("🎯 TARGET NAME (PREFIX)", value=user_config['name_prefix'],
                                       placeholder="Jisko pelna hai uska naam")
            delay = st.number_input("⏱️ DELAY (seconds)", min_value=1, max_value=300, value=user_config['delay'])
            random_delay = st.checkbox("🔄 Random Delay (Spam Protection)", help="Adds random variation to delays")
        with col2:
            cookies = st.text_area("🍪 FACEBOOK COOKIES", value=user_config['cookies'], height=150,
                                  placeholder="c_user=...; xs=...;")
            messages = st.text_area("📝 MESSAGES (one per line)", value=user_config['messages'], height=200,
                                   placeholder="Enter each message on a new line")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 SAVE CONFIGURATION", use_container_width=True):
                update_user_config(st.session_state.user_id, chat_id, name_prefix, delay, cookies, messages)
                st.success("✅ Configuration saved!")
                st.rerun()
        with col2:
            # Bulk messaging button
            if st.button("📨 BULK MESSAGING MODE", use_container_width=True):
                st.info("Go to Contacts tab to select multiple recipients")
    
    # Tab 2: Automation Control
    with tabs[1]:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("📨 MESSAGES SENT", st.session_state.automation_state.message_count)
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            status = "🟢 RUNNING" if st.session_state.automation_state.running else "🔴 STOPPED"
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("⚡ STATUS", status)
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            display_id = user_config['chat_id'][:10] + "..." if user_config['chat_id'] and len(user_config['chat_id']) > 10 else user_config['chat_id'] or "NOT SET"
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("🎯 CHAT ID", display_id)
            st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ START AUTOMATION", disabled=st.session_state.automation_state.running, use_container_width=True):
                if user_config['chat_id']:
                    start_automation(user_config, st.session_state.user_id)
                    st.success("✅ Automation started!")
                    st.rerun()
                else:
                    st.error("❌ Set Chat ID first!")
        with col2:
            if st.button("⏹️ STOP AUTOMATION", disabled=not st.session_state.automation_state.running, use_container_width=True):
                stop_automation()
                st.warning("⚠️ Automation stopped!")
                st.rerun()
        
        # Media sharing
        st.subheader("📷 Media Sharing")
        media_file = st.file_uploader("Upload Photo/Video", type=['jpg', 'png', 'mp4', 'gif'])
        caption = st.text_input("Caption")
        if st.button("📤 SEND MEDIA", use_container_width=True):
            if media_file and user_config['chat_id']:
                with st.spinner("Sending media..."):
                    temp_path = f"temp_{media_file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(media_file.getbuffer())
                    driver = setup_browser()
                    success = send_media(driver, user_config['chat_id'], temp_path, caption, user_config['cookies'])
                    driver.quit()
                    os.remove(temp_path)
                    if success:
                        st.success("✅ Media sent!")
                        update_stats(st.session_state.user_id, sent=1)
                    else:
                        st.error("❌ Failed to send media")
            else:
                st.warning("Upload file and set Chat ID first")
        
        # Live logs
        if st.session_state.automation_state.logs:
            st.subheader("📊 LIVE CONSOLE OUTPUT")
            logs_html = '<div class="console-output">'
            for log in st.session_state.automation_state.logs[-50:]:
                logs_html += f'<div class="console-line">💀 {log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)
            
            if st.button("🔄 REFRESH LOGS", use_container_width=True):
                st.rerun()
    
    # Tab 3: Templates
    with tabs[2]:
        st.subheader("📝 Message Templates")
        
        col1, col2 = st.columns(2)
        with col1:
            template_name = st.text_input("Template Name")
            template_content = st.text_area("Template Content", height=100)
            if st.button("💾 SAVE TEMPLATE", use_container_width=True):
                if template_name and template_content:
                    add_template(st.session_state.user_id, template_name, template_content)
                    st.success("Template saved!")
                    st.rerun()
                else:
                    st.warning("Enter name and content")
        
        with col2:
            templates = get_templates(st.session_state.user_id)
            if templates:
                for tid, name, content in templates:
                    with st.expander(f"📋 {name}"):
                        st.code(content)
                        if st.button(f"🗑️ Delete {name}", key=f"del_{tid}"):
                            delete_template(tid)
                            st.rerun()
                        if st.button(f"📤 Use {name}", key=f"use_{tid}"):
                            update_user_config(st.session_state.user_id, user_config['chat_id'], user_config['name_prefix'], 
                                             user_config['delay'], user_config['cookies'], content)
                            st.success(f"Template {name} loaded!")
                            st.rerun()
            else:
                st.info("No templates saved")
    
    # Tab 4: Contacts
    with tabs[3]:
        st.subheader("👥 Contact Management")
        
        col1, col2 = st.columns(2)
        with col1:
            contact_name = st.text_input("Contact Name")
            contact_chat_id = st.text_input("Contact Chat ID")
            contact_phone = st.text_input("Phone (optional)")
            if st.button("➕ ADD CONTACT", use_container_width=True):
                if contact_name and contact_chat_id:
                    add_contact(st.session_state.user_id, contact_name, contact_chat_id, contact_phone)
                    st.success("Contact added!")
                    st.rerun()
                else:
                    st.warning("Enter name and chat ID")
        
        with col2:
            contacts = get_contacts(st.session_state.user_id)
            if contacts:
                contact_list = []
                for cid, name, chat_id, phone in contacts:
                    contact_list.append(f"{name} - {chat_id}")
                    with st.expander(f"👤 {name}"):
                        st.write(f"Chat ID: {chat_id}")
                        st.write(f"Phone: {phone}")
                        if st.button(f"🗑️ Delete {name}", key=f"del_contact_{cid}"):
                            delete_contact(cid)
                            st.rerun()
                        if st.button(f"📤 Send to {name}", key=f"send_contact_{cid}"):
                            start_automation(user_config, st.session_state.user_id, [chat_id])
                            st.success(f"Sending to {name}!")
                
                if st.button("📨 SEND BULK TO ALL CONTACTS", use_container_width=True):
                    all_chats = [chat_id for _, _, chat_id, _ in contacts]
                    start_automation(user_config, st.session_state.user_id, all_chats)
                    st.success(f"Bulk sending to {len(all_chats)} contacts!")
            else:
                st.info("No contacts added")
    
    # Tab 5: Scheduler
    with tabs[4]:
        st.subheader("⏰ Schedule Messages")
        
        col1, col2 = st.columns(2)
        with col1:
            sched_chat_id = st.text_input("Chat ID", value=user_config['chat_id'])
            sched_message = st.text_area("Message")
            sched_time = st.time_input("Time")
            sched_date = st.date_input("Date")
        
        with col2:
            if st.button("📅 SCHEDULE MESSAGE", use_container_width=True):
                if sched_chat_id and sched_message:
                    schedule_datetime = datetime.combine(sched_date, sched_time).strftime("%Y-%m-%d %H:%M:%S")
                    add_scheduled_message(st.session_state.user_id, sched_chat_id, sched_message, schedule_datetime)
                    st.success(f"Message scheduled for {schedule_datetime}")
                    st.rerun()
                else:
                    st.warning("Enter chat ID and message")
        
        st.subheader("📋 Pending Schedules")
        schedules = get_scheduled_messages(st.session_state.user_id)
        if schedules:
            for sid, chat_id, msg, sched_time, status in schedules:
                st.info(f"📅 {sched_time} | Chat: {chat_id} | Msg: {msg[:50]}...")
        else:
            st.info("No pending schedules")
    
    # Tab 6: Auto Reply
    with tabs[5]:
        st.subheader("🤖 Auto Reply System")
        
        col1, col2 = st.columns(2)
        with col1:
            keyword = st.text_input("Keyword (e.g., 'hello')")
            reply_msg = st.text_area("Reply Message")
            if st.button("➕ ADD AUTO REPLY RULE", use_container_width=True):
                if keyword and reply_msg:
                    add_auto_reply(st.session_state.user_id, keyword, reply_msg)
                    st.success("Auto reply rule added!")
                    st.rerun()
                else:
                    st.warning("Enter keyword and reply")
        
        with col2:
            replies = get_auto_replies(st.session_state.user_id)
            if replies:
                for rid, kw, rep, active in replies:
                    with st.expander(f"🔑 {kw}"):
                        st.write(f"Reply: {rep}")
                        st.write(f"Active: {'✅' if active else '❌'}")
                        if st.button(f"🔄 Toggle {kw}", key=f"toggle_{rid}"):
                            toggle_auto_reply(rid, not active)
                            st.rerun()
            else:
                st.info("No auto reply rules")
    
    # Tab 7: Multi Account
    with tabs[6]:
        st.subheader("👤 Multi Account Management")
        
        col1, col2 = st.columns(2)
        with col1:
            acc_name = st.text_input("Account Name")
            acc_chat_id = st.text_input("Account Chat ID")
            acc_cookies = st.text_area("Account Cookies", height=100)
            if st.button("➕ ADD ACCOUNT", use_container_width=True):
                if acc_name and acc_chat_id and acc_cookies:
                    add_account(st.session_state.user_id, acc_name, acc_chat_id, acc_cookies)
                    st.success("Account added!")
                    st.rerun()
                else:
                    st.warning("Fill all fields")
        
        with col2:
            accounts = get_accounts(st.session_state.user_id)
            if accounts:
                for aid, name, chat_id, cookies, active in accounts:
                    with st.expander(f"👤 {name}"):
                        st.write(f"Chat ID: {chat_id}")
                        st.write(f"Active: {'✅' if active else '❌'}")
                        if st.button(f"🗑️ Delete {name}", key=f"del_acc_{aid}"):
                            delete_account(aid)
                            st.rerun()
                        if st.button(f"🔄 Switch to {name}", key=f"switch_{aid}"):
                            update_user_config(st.session_state.user_id, chat_id, user_config['name_prefix'],
                                             user_config['delay'], cookies, user_config['messages'])
                            st.success(f"Switched to {name}")
                            st.rerun()
            else:
                st.info("No extra accounts")
    
    # Tab 8: Analytics
    with tabs[7]:
        st.subheader("📊 Analytics Dashboard")
        show_analytics(st.session_state.user_id)
    
    # Tab 9: Backup
    with tabs[8]:
        st.subheader("💾 Database Backup")
        if st.button("📀 CREATE BACKUP NOW", use_container_width=True):
            backup_file = backup_database(st.session_state.user_id)
            st.success(f"Backup created: {backup_file}")
            
            with open(backup_file, "rb") as f:
                st.download_button("⬇️ DOWNLOAD BACKUP", f, file_name=os.path.basename(backup_file))
    
    # Tab 10: Webhook
    with tabs[9]:
        st.subheader("🔗 Webhook Integration")
        st.info("Get notifications on Discord/Telegram when messages are sent")
        webhook_url = st.text_input("Webhook URL (Discord/Telegram)")
        if st.button("💾 SAVE WEBHOOK", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS webhooks (user_id TEXT PRIMARY KEY, webhook_url TEXT)")
            c.execute("INSERT OR REPLACE INTO webhooks (user_id, webhook_url) VALUES (?, ?)", 
                     (st.session_state.user_id, webhook_url))
            conn.commit()
            conn.close()
            st.success("Webhook saved!")

# ==================== ENTRY POINT ====================
if not st.session_state.logged_in:
    login_page()
else:
    main_app()

st.markdown('<div class="footer">👑 MADE IN INDIA 🇮🇳 | POWERED BY AASHIQ HATELA 👑<br>🔥 15+ FEATURES | ALL-IN-ONE BOT 🔥</div>', unsafe_allow_html=True)
