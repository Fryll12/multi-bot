# multi_bot_control_final_fixed_full.py
import discum
import threading
import time
import os
import random
import re
import requests
from flask import Flask, request, render_template_string, jsonify
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
main_token = os.getenv("MAIN_TOKEN")
main_token_2 = os.getenv("MAIN_TOKEN_2")
main_token_3 = os.getenv("MAIN_TOKEN_3")
tokens = os.getenv("TOKENS").split(",") if os.getenv("TOKENS") else []
main_channel_id = "1386973916563767396"
other_channel_id = "1387406577040101417"
ktb_channel_id = "1376777071279214662"
spam_channel_id = "1388802151723302912"
work_channel_id = "1389250541590413363"
karuta_id = "646937666251915264"
karibbit_id = "1274445226064220273"

# --- BIẾN TRẠNG THÁI ---
bots, acc_names = [], [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent",
]
main_bot, main_bot_2, main_bot_3 = None, None, None
auto_grab_enabled, auto_grab_enabled_2, auto_grab_enabled_3 = False, False, False
heart_threshold, heart_threshold_2, heart_threshold_3 = 50, 50, 50
spam_enabled, auto_work_enabled, auto_reboot_enabled = False, False, False
spam_message, spam_delay, work_delay_between_acc, work_delay_after_all, auto_reboot_delay = "", 10, 10, 44100, 3600
last_work_cycle_time, last_reboot_cycle_time, last_spam_time = 0, 0, 0
spam_thread, auto_reboot_thread, auto_reboot_stop_event = None, None, None
bots_lock = threading.Lock()

# --- CÁC HÀM LOGIC BOT ---

def reboot_bot(target_id):
    global main_bot, main_bot_2, main_bot_3, bots
    with bots_lock:
        print(f"[Reboot] Nhận được yêu cầu reboot cho target: {target_id}")
        if target_id == 'main_1' and main_bot:
            try: main_bot.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 1: {e}")
            main_bot = create_bot(main_token, is_main=True)
            print("[Reboot] Acc Chính 1 đã được khởi động lại.")
        elif target_id == 'main_2' and main_bot_2:
            try: main_bot_2.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 2: {e}")
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
            print("[Reboot] Acc Chính 2 đã được khởi động lại.")
        elif target_id == 'main_3' and main_bot_3:
            try: main_bot_3.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 3: {e}")
            main_bot_3 = create_bot(main_token_3, is_main_3=True)
            print("[Reboot] Acc Chính 3 đã được khởi động lại.")
        elif target_id.startswith('sub_'):
            try:
                index = int(target_id.split('_')[1])
                if 0 <= index < len(bots):
                    try: bots[index].gateway.close()
                    except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Phụ {index}: {e}")
                    token_to_reboot = tokens[index]
                    bots[index] = create_bot(token_to_reboot.strip(), is_main=False)
                    print(f"[Reboot] Acc Phụ {index} đã được khởi động lại.")
            except (ValueError, IndexError) as e: print(f"[Reboot] Lỗi xử lý target Acc Phụ: {e}")

def create_bot(token, is_main=False, is_main_2=False, is_main_3=False):
    bot = discum.Client(token=token, log=False)
    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            user_id = resp.raw["user"]["id"]
            bot_type = "(Acc chính)" if is_main else "(Acc chính 2)" if is_main_2 else "(Acc chính 3)" if is_main_3 else ""
            print(f"Đã đăng nhập: {user_id} {bot_type}")

    if is_main:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled, heart_threshold, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto()
                if msg.get("author", {}).get("id") == karuta_id and msg.get("channel_id") == main_channel_id and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled:
                    last_drop_msg_id = msg["id"]
                    def read_karibbit():
                        time.sleep(0.5)
                        messages = bot.getMessages(main_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                if sum(heart_numbers) > 0 and (max_num := max(heart_numbers)) >= heart_threshold:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 0.5), ("2️⃣", 1.5), ("3️⃣", 2.2)][max_index]
                                    print(f"[Bot 1] Chọn dòng {max_index+1} với {max_num} tim -> Emoji {emoji} sau {delay}s")
                                    def grab():
                                        bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                        bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab).start()
                                break
                    threading.Thread(target=read_karibbit).start()
    if is_main_2:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_2, heart_threshold_2, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto()
                if msg.get("author", {}).get("id") == karuta_id and msg.get("channel_id") == main_channel_id and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_2:
                    last_drop_msg_id = msg["id"]
                    def read_karibbit_2():
                        time.sleep(0.5)
                        messages = bot.getMessages(main_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                if sum(heart_numbers) > 0 and (max_num := max(heart_numbers)) >= heart_threshold_2:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 0.8), ("2️⃣", 1.8), ("3️⃣", 2.5)][max_index]
                                    print(f"[Bot 2] Chọn dòng {max_index+1} với {max_num} tim -> Emoji {emoji} sau {delay}s")
                                    def grab_2():
                                        bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                        bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab_2).start()
                                break
                    threading.Thread(target=read_karibbit_2).start()
    if is_main_3:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_3, heart_threshold_3, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto()
                if msg.get("author", {}).get("id") == karuta_id and msg.get("channel_id") == main_channel_id and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_3:
                    last_drop_msg_id = msg["id"]
                    def read_karibbit_3():
                        time.sleep(0.5)
                        messages = bot.getMessages(main_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                if sum(heart_numbers) > 0 and (max_num := max(heart_numbers)) >= heart_threshold_3:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 1.1), ("2️⃣", 2.1), ("3️⃣", 2.8)][max_index]
                                    print(f"[Bot 3] Chọn dòng {max_index+1} với {max_num} tim -> Emoji {emoji} sau {delay}s")
                                    def grab_3():
                                        bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                        bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab_3).start()
                                break
                    threading.Thread(target=read_karibbit_3).start()

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

def run_work_bot(token, acc_index):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = {"Authorization": token, "Content-Type": "application/json"}
    step = {"value": 0}
    def send_karuta_command(): bot.sendMessage(work_channel_id, "kc o:ef")
    def send_kn_command(): bot.sendMessage(work_channel_id, "kn")
    def send_kw_command(): bot.sendMessage(work_channel_id, "kw"); step["value"] = 2
    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json={"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "a", "data": {"component_type": 2, "custom_id": custom_id}})
            print(f"[Work Acc {acc_index}] Click tick: Status {r.status_code}")
        except Exception as e: print(f"[Work Acc {acc_index}] Lỗi click tick: {e}")
    @bot.gateway.command
    def on_message(resp):
        if resp.event.message:
            m = resp.parsed.auto()
            if str(m.get('channel_id')) != work_channel_id: return
            author_id = str(m.get('author', {}).get('id', ''))
            guild_id = m.get('guild_id')
            if step["value"] == 0 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                card_codes = re.findall(r'\b\w{4,}\b', m['embeds'][0].get('description', ''))
                if len(card_codes) >= 10:
                    first_5, last_5 = card_codes[:5], card_codes[-5:]
                    for i, code in enumerate(last_5): bot.sendMessage(work_channel_id, f"kjw {code} {chr(97 + i)}"); time.sleep(1.5)
                    for i, code in enumerate(first_5): bot.sendMessage(work_channel_id, f"kjw {code} {chr(97 + i)}"); time.sleep(1.5)
                    send_kn_command(); step["value"] = 1
            elif step["value"] == 1 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                match = re.search(r'\d+\.\s*`([^`]+)`', m['embeds'][0].get('description', '').split('\n')[1])
                if match: bot.sendMessage(work_channel_id, f"kjn `{match.group(1)}` a b c d e"); time.sleep(1); send_kw_command()
            elif step["value"] == 2 and author_id == karuta_id and 'components' in m:
                for comp in m['components']:
                    if comp['type'] == 1 and (btn := next((b for b in comp['components'] if b['type'] == 2), None)):
                        click_tick(work_channel_id, m['id'], btn['custom_id'], m.get('application_id', karuta_id), guild_id)
                        step["value"] = 3; bot.gateway.close(); break
    print(f"[Work Acc {acc_index}] Bắt đầu hoạt động...")
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    time.sleep(3); send_karuta_command()
    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout: time.sleep(1)
    bot.gateway.close()
    print(f"[Work Acc {acc_index}] Đã hoàn thành.")

def auto_work_loop():
    global auto_work_enabled, last_work_cycle_time
    while True:
        if auto_work_enabled:
            with bots_lock: current_tokens = tokens.copy()
            for i, token in enumerate(current_tokens):
                if not auto_work_enabled: break
                if token.strip():
                    print(f"[Work] Đang chạy acc {i+1}...")
                    run_work_bot(token.strip(), i+1)
                    print(f"[Work] Acc {i+1} xong, chờ {work_delay_between_acc} giây...")
                    time.sleep(work_delay_between_acc)
            if auto_work_enabled:
                print(f"[Work] Hoàn thành chu kỳ, chờ {work_delay_after_all} giây...")
                last_work_cycle_time = time.time()
                start_wait = time.time()
                while time.time() - start_wait < work_delay_after_all:
                    if not auto_work_enabled: break
                    time.sleep(1)
        else:
            time.sleep(1)

def auto_reboot_loop():
    global auto_reboot_stop_event, last_reboot_cycle_time
    print("[Reboot] Luồng tự động reboot đã bắt đầu.")
    while not auto_reboot_stop_event.is_set():
        last_reboot_cycle_time = time.time()
        interrupted = auto_reboot_stop_event.wait(timeout=auto_reboot_delay)
        if interrupted: break
        print("[Reboot] Hết thời gian chờ, tiến hành reboot 3 tài khoản chính.")
        if main_bot: reboot_bot('main_1'); time.sleep(5)
        if main_bot_2: reboot_bot('main_2'); time.sleep(5)
        if main_bot_3: reboot_bot('main_3')
    print("[Reboot] Luồng tự động reboot đã dừng.")

def spam_loop():
    global spam_enabled, spam_message, spam_delay, last_spam_time
    while True:
        if spam_enabled and spam_message:
            last_spam_time = time.time()
            with bots_lock: bots_to_spam = bots.copy()
            for idx, bot in enumerate(bots_to_spam):
                if not spam_enabled: break
                try:
                    bot.sendMessage(spam_channel_id, spam_message)
                    print(f"[{acc_names[idx]}] đã gửi: {spam_message}")
                    time.sleep(2)
                except Exception as e: print(f"Lỗi gửi spam: {e}")
            
            print(f"[Spam] Chờ {spam_delay} giây cho lượt tiếp theo...")
            start_wait = time.time()
            while time.time() - start_wait < spam_delay:
                if not spam_enabled: break
                time.sleep(1)
        else:
            time.sleep(1)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOT CONTROL MATRIX</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon-green: #00ff41; --neon-cyan: #00ffff; --neon-red: #ff0040; --neon-yellow: #fff000; --primary-bg: #0a0a0a; --secondary-bg: #111111; --accent-bg: #1a1a1a; --border-color: #333333; --text-primary: #ffffff; --text-muted: #cccccc; --shadow-glow: 0 0 15px; --font-primary: 'Orbitron', monospace; --font-mono: 'Courier Prime', monospace; }
        body { font-family: var(--font-primary); background-color: var(--primary-bg); color: var(--text-primary); margin:0; padding:0; }
        .container { max-width: 1600px; margin: 0 auto; padding: 15px; }
        .header { text-align: center; margin-bottom: 20px; padding: 15px; border: 2px solid var(--neon-green); border-radius: 8px; box-shadow: var(--shadow-glow) var(--neon-green); }
        .title { font-size: 2.2em; font-weight: 900; color: var(--neon-green); text-shadow: var(--shadow-glow) var(--neon-green); }
        .control-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 15px; }
        .control-panel { background: var(--secondary-bg); border: 1px solid var(--border-color); border-radius: 8px; display: flex; flex-direction: column; }
        .panel-header { padding: 10px 15px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 10px; font-weight: 700; color: var(--neon-cyan); }
        .panel-content { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; gap: 15px; }
        .status-badge { padding: 3px 8px; border-radius: 12px; font-size: 0.75em; font-weight: 700; border: 1px solid; }
        .status-badge.active { border-color: var(--neon-green); background: rgba(0, 255, 65, 0.2); color: var(--neon-green); }
        .status-badge.inactive { border-color: var(--neon-red); background: rgba(255, 0, 64, 0.2); color: var(--neon-red); }
        .status-row { display: flex; justify-content: space-between; align-items: center; padding: 10px; background-color: var(--accent-bg); border-radius: 4px;}
        .status-name { font-weight: 700; display: flex; align-items: center; gap: 8px; }
        .timer-display { font-family: var(--font-mono); font-size: 1.1em; color: var(--neon-yellow); font-weight: 700; }
        .status-timer { display: flex; align-items: center; gap: 10px; }
        .input-group { display: flex; flex-direction: column; gap: 5px; }
        .input-label { font-size: 0.8em; color: var(--text-muted); font-weight: 700; }
        .input-cyber, textarea.input-cyber, select.input-cyber { padding: 8px; background: var(--primary-bg); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-family: var(--font-mono); width: 100%; box-sizing: border-box; resize: vertical; }
        .btn-cyber { padding: 10px 15px; border: 1px solid; border-radius: 4px; background: transparent; color: var(--text-primary); font-family: var(--font-primary); font-weight: 700; cursor: pointer; transition: all 0.2s ease; width: 100%; }
        .btn-primary { border-color: var(--neon-green); color: var(--neon-green); } .btn-primary:hover { background: var(--neon-green); color: var(--primary-bg); box-shadow: var(--shadow-glow) var(--neon-green); }
        .btn-danger { border-color: var(--neon-red); color: var(--neon-red); } .btn-danger:hover { background: var(--neon-red); color: var(--primary-bg); box-shadow: var(--shadow-glow) var(--neon-red); }
        .control-row { display: flex; gap: 10px; align-items: flex-end; }
        .sub-accounts-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; }
        .msg-status { text-align: center; color: var(--neon-yellow); font-family: var(--font-mono); padding: 10px; border: 1px dashed var(--border-color); border-radius: 4px; margin-top: 15px; margin-bottom: 15px;}
        .account-section { margin-bottom: 10px; padding: 10px; background: var(--accent-bg); border-radius: 4px; border: 1px solid var(--border-color); }
        .account-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .account-name { font-size: 1em; font-weight: 700; color: var(--neon-cyan); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><div class="title">BOT CONTROL MATRIX</div></div>
        
        {% if msg_status %}
        <div class="msg-status">{{ msg_status }}</div>
        {% endif %}

        <div class="control-grid">
            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-clock"></i><span>REAL-TIME STATUS</span></div>
                <div class="panel-content">
                    <div class="status-row">
                        <div class="status-name"><i class="fas fa-cogs"></i><span>AUTO WORK</span></div>
                        <div class="status-timer">
                            <span id="work-timer" class="timer-display">--:--:--</span>
                            <span id="work-status-badge" class="status-badge inactive">OFF</span>
                        </div>
                    </div>
                    <div class="status-row">
                        <div class="status-name"><i class="fas fa-redo"></i><span>AUTO REBOOT</span></div>
                        <div class="status-timer">
                            <span id="reboot-timer" class="timer-display">--:--:--</span>
                            <span id="reboot-status-badge" class="status-badge inactive">OFF</span>
                        </div>
                    </div>
                    <div class="status-row">
                        <div class="status-name"><i class="fas fa-comments"></i><span>SPAM</span></div>
                        <div class="status-timer">
                            <span id="spam-timer" class="timer-display">--:--:--</span>
                            <span id="spam-status-badge" class="status-badge inactive">OFF</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-crosshairs"></i><span>AUTO GRAB PROTOCOL</span></div>
                <div class="panel-content">
                    <form method="post" class="account-section">
                        <div class="account-header">
                            <span class="account-name">ALPHA NODE</span>
                            <div class="status-badge {{ grab_status }}">{{ grab_text }}</div>
                        </div>
                        <div class="control-row">
                             <div class="input-group" style="flex: 1;"><label class="input-label">THRESHOLD</label><input type="number" name="heart_threshold" value="{{ heart_threshold }}" class="input-cyber"></div>
                             <button type="submit" name="toggle" value="1" class="{{ grab_button_class }}">{{ grab_action }}</button>
                        </div>
                    </form>
                    <form method="post" class="account-section">
                         <div class="account-header">
                             <span class="account-name">BETA NODE</span>
                             <div class="status-badge {{ grab_status_2 }}">{{ grab_text_2 }}</div>
                         </div>
                         <div class="control-row">
                              <div class="input-group" style="flex: 1;"><label class="input-label">THRESHOLD</label><input type="number" name="heart_threshold_2" value="{{ heart_threshold_2 }}" class="input-cyber"></div>
                              <button type="submit" name="toggle_2" value="1" class="{{ grab_button_class_2 }}">{{ grab_action_2 }}</button>
                         </div>
                    </form>
                    <form method="post" class="account-section">
                         <div class="account-header">
                             <span class="account-name">GAMMA NODE</span>
                             <div class="status-badge {{ grab_status_3 }}">{{ grab_text_3 }}</div>
                         </div>
                         <div class="control-row">
                              <div class="input-group" style="flex: 1;"><label class="input-label">THRESHOLD</label><input type="number" name="heart_threshold_3" value="{{ heart_threshold_3 }}" class="input-cyber"></div>
                              <button type="submit" name="toggle_3" value="1" class="{{ grab_button_class_3 }}">{{ grab_action_3 }}</button>
                         </div>
                    </form>
                </div>
            </div>

            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-keyboard"></i><span>MANUAL OPERATIONS</span></div>
                <div class="panel-content">
                    <form method="post" style="display: flex; flex-direction: column; gap: 15px;">
                        <div class="control-row">
                            <input type="text" name="message" class="input-cyber" placeholder="Enter manual message..." style="flex-grow: 1;">
                            <button type="submit" class="btn-cyber btn-primary" style="width: auto; padding: 10px;"><i class="fas fa-paper-plane"></i> SEND</button>
                        </div>
                        <div class="control-row">
                            <button type="submit" name="quickmsg" value="kc o:w" class="btn-cyber">KC O:W</button>
                            <button type="submit" name="quickmsg" value="kc o:ef" class="btn-cyber">KC O:EF</button>
                            <button type="submit" name="quickmsg" value="kc o:p" class="btn-cyber">KC O:P</button>
                        </div>
                    </form>
                </div>
            </div>

            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-satellite-dish"></i><span>SPAM INJECTION</span></div>
                <div class="panel-content">
                    <form method="post">
                        <div class="input-group">
                            <label class="input-label">MESSAGE</label>
                            <textarea name="spammsg" class="input-cyber" rows="2">{{ spam_message }}</textarea>
                        </div>
                        <div class="control-row" style="margin-top:15px;">
                            <div class="input-group" style="flex-grow: 1;">
                                <label class="input-label">DELAY (s)</label>
                                <input type="number" name="spam_delay" value="{{ spam_delay }}" class="input-cyber">
                            </div>
                            <button type="submit" name="spamtoggle" class="{{ spam_button_class }}">{{ spam_action }}</button>
                        </div>
                    </form>
                </div>
            </div>

            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-robot"></i><span>WORK AUTOMATION</span></div>
                <div class="panel-content">
                     <form method="post">
                        <div class="control-row">
                            <div class="input-group" style="flex: 1;">
                                <label class="input-label">ACC DELAY (s)</label>
                                <input type="number" name="work_delay_between_acc" value="{{ work_delay_between_acc }}" class="input-cyber">
                            </div>
                             <div class="input-group" style="flex: 1;">
                                <label class="input-label">CYCLE DELAY (s)</label>
                                <input type="number" name="work_delay_after_all" value="{{ work_delay_after_all }}" class="input-cyber">
                            </div>
                        </div>
                        <button type="submit" name="auto_work_toggle" class="{{ work_button_class }}" style="margin-top: 15px;">{{ work_action }}</button>
                    </form>
                </div>
            </div>
            
            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-code"></i><span>CODE INJECTION</span></div>
                <div class="panel-content">
                     <form method="post" style="display: flex; flex-direction: column; gap: 15px;">
                        <div class="control-row">
                            <div class="input-group" style="flex: 1;"><label class="input-label">TARGET ACC</label><select name="acc_index" class="input-cyber">{{ acc_options|safe }}</select></div>
                            <div class="input-group" style="width: 80px;"><label class="input-label">DELAY</label><input type="number" name="delay" value="1.0" step="0.1" class="input-cyber"></div>
                        </div>
                         <div class="input-group"><label class="input-label">PREFIX</label><input type="text" name="prefix" placeholder="kt n" class="input-cyber"></div>
                         <div class="input-group"><label class="input-label">CODE LIST</label><textarea name="codes" placeholder="dán mã vào đây, cách nhau bằng dấu phẩy" rows="3" class="input-cyber"></textarea></div>
                        <button type="submit" name="send_codes" value="1" class="btn-cyber btn-primary">INJECT CODES</button>
                    </form>
                </div>
            </div>

            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-history"></i><span>AUTO REBOOT CYCLE</span></div>
                <div class="panel-content">
                    <form method="post">
                        <div class="control-row">
                            <div class="input-group" style="flex: 1;">
                                <label class="input-label">INTERVAL (s)</label>
                                <input type="number" name="auto_reboot_delay" value="{{ auto_reboot_delay }}" class="input-cyber">
                            </div>
                            <button type="submit" name="auto_reboot_toggle" class="{{ reboot_button_class }}" style="width: 120px;">{{ reboot_action }}</button>
                        </div>
                    </form>
                </div>
            </div>

            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-power-off"></i><span>MANUAL OVERRIDE</span></div>
                <div class="panel-content">
                    <form method="post">
                        <button type="submit" name="reboot_target" value="all" class="btn-cyber btn-danger" style="margin-bottom: 15px;">REBOOT ALL SYSTEMS</button>
                        <h4>MAIN NODES</h4>
                        <div class="sub-accounts-grid">
                            <button type="submit" name="reboot_target" value="main_1" class="btn-cyber">ALPHA</button>
                            <button type="submit" name="reboot_target" value="main_2" class="btn-cyber">BETA</button>
                            <button type="submit" name="reboot_target" value="main_3" class="btn-cyber">GAMMA</button>
                        </div>
                        <h4 style="margin-top: 15px;">SLAVE NODES ({{ num_bots }})</h4>
                        <div class="sub-accounts-grid">
                            {{ sub_account_buttons|safe }}
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function () {
            function formatTime(seconds) {
                if (isNaN(seconds) || seconds < 0) return "--:--:--";
                seconds = Math.floor(seconds);
                const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
                const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
                const s = (seconds % 60).toString().padStart(2, '0');
                return `${h}:${m}:${s}`;
            }
            function updateStatusBadge(elementId, isActive) {
                const badge = document.getElementById(elementId);
                badge.textContent = isActive ? 'ON' : 'OFF';
                badge.className = `status-badge ${isActive ? 'active' : 'inactive'}`;
            }
            async function fetchStatus() {
                try {
                    const response = await fetch('/status');
                    const data = await response.json();
                    document.getElementById('work-timer').textContent = formatTime(data.work_countdown);
                    updateStatusBadge('work-status-badge', data.work_enabled);
                    document.getElementById('reboot-timer').textContent = formatTime(data.reboot_countdown);
                    updateStatusBadge('reboot-status-badge', data.reboot_enabled);
                    document.getElementById('spam-timer').textContent = formatTime(data.spam_countdown);
                    updateStatusBadge('spam-status-badge', data.spam_enabled);
                } catch (error) { console.error('Error fetching status:', error); }
            }
            setInterval(fetchStatus, 1000);
        });
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, auto_grab_enabled_2, auto_grab_enabled_3
    global spam_enabled, spam_message, spam_delay, spam_thread, last_spam_time
    global heart_threshold, heart_threshold_2, heart_threshold_3
    global auto_work_enabled, work_delay_between_acc, work_delay_after_all, last_work_cycle_time
    global auto_reboot_enabled, auto_reboot_delay, auto_reboot_thread, auto_reboot_stop_event, last_reboot_cycle_time
    
    msg_status = ""
    if request.method == "POST":
        # Manual message
        if 'message' in request.form and request.form['message']:
            msg = request.form['message']; msg_status = f"Sent: {msg}"
            with bots_lock:
                for idx, bot in enumerate(bots): threading.Timer(0.5 * idx, bot.sendMessage, args=(other_channel_id, msg)).start()
        elif 'quickmsg' in request.form:
            msg = request.form['quickmsg']; msg_status = f"Sent: {msg}"
            with bots_lock:
                for idx, bot in enumerate(bots): threading.Timer(0.5 * idx, bot.sendMessage, args=(other_channel_id, msg)).start()
        
        # Auto Grab
        elif 'toggle' in request.form:
            auto_grab_enabled = not auto_grab_enabled
            heart_threshold = int(request.form.get('heart_threshold', 50))
            msg_status = f"Auto Grab 1 {'enabled' if auto_grab_enabled else 'disabled'}"
        elif 'toggle_2' in request.form:
            auto_grab_enabled_2 = not auto_grab_enabled_2
            heart_threshold_2 = int(request.form.get('heart_threshold_2', 50))
            msg_status = f"Auto Grab 2 {'enabled' if auto_grab_enabled_2 else 'disabled'}"
        elif 'toggle_3' in request.form:
            auto_grab_enabled_3 = not auto_grab_enabled_3
            heart_threshold_3 = int(request.form.get('heart_threshold_3', 50))
            msg_status = f"Auto Grab 3 {'enabled' if auto_grab_enabled_3 else 'disabled'}"
        
        # Spam toggle
        elif 'spamtoggle' in request.form:
            spam_message = request.form.get("spammsg", "").strip()
            spam_delay = int(request.form.get("spam_delay", 10))
            if not spam_enabled and spam_message:
                spam_enabled = True; last_spam_time = time.time(); msg_status = "Spam enabled."
                if spam_thread is None or not spam_thread.is_alive():
                    spam_thread = threading.Thread(target=spam_loop, daemon=True); spam_thread.start()
            else:
                spam_enabled = False; msg_status = "Spam disabled."

        # Auto Work toggle
        elif 'auto_work_toggle' in request.form:
            auto_work_enabled = not auto_work_enabled
            if auto_work_enabled: last_work_cycle_time = time.time()
            work_delay_between_acc = int(request.form.get('work_delay_between_acc', 10))
            work_delay_after_all = int(request.form.get('work_delay_after_all', 44100))
            msg_status = f"Auto Work {'enabled' if auto_work_enabled else 'disabled'}."

        # Code Injection
        elif 'send_codes' in request.form:
            try:
                acc_idx = int(request.form.get("acc_index"))
                delay_val = float(request.form.get("delay", 1.0))
                prefix = request.form.get("prefix", "")
                codes_list = request.form.get("codes", "").split(',')
                if acc_idx < len(bots):
                    with bots_lock:
                        for i, code in enumerate(codes_list):
                            if code.strip():
                                final_msg = f"{prefix} {code.strip()}" if prefix else code.strip()
                                threading.Timer(delay_val * i, bots[acc_idx].sendMessage, args=(other_channel_id, final_msg)).start()
                    msg_status = f"Injecting {len(codes_list)} codes to {acc_names[acc_idx]}..."
                else: msg_status = "Error: Invalid account index."
            except Exception as e: msg_status = f"Code Injection Error: {e}"

        # Auto Reboot toggle
        elif 'auto_reboot_toggle' in request.form:
            auto_reboot_enabled = not auto_reboot_enabled
            auto_reboot_delay = int(request.form.get("auto_reboot_delay", 3600))
            if auto_reboot_enabled and (auto_reboot_thread is None or not auto_reboot_thread.is_alive()):
                auto_reboot_stop_event = threading.Event()
                auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True); auto_reboot_thread.start()
                msg_status = "Auto Reboot enabled."
            elif not auto_reboot_enabled and auto_reboot_stop_event:
                auto_reboot_stop_event.set(); auto_reboot_thread = None; msg_status = "Auto Reboot disabled."

        # Manual Reboot
        elif 'reboot_target' in request.form:
            target = request.form.get('reboot_target')
            msg_status = f"Rebooting {target}..."
            if target == "all":
                if main_bot: reboot_bot('main_1'); time.sleep(1)
                if main_bot_2: reboot_bot('main_2'); time.sleep(1)
                if main_bot_3: reboot_bot('main_3'); time.sleep(1)
                with bots_lock:
                    for i in range(len(bots)): reboot_bot(f'sub_{i}'); time.sleep(1)
            else:
                reboot_bot(target)
    
    grab_status, grab_text, grab_action, grab_button_class = ("active", "ON", "DISABLE", "btn-cyber btn-danger") if auto_grab_enabled else ("inactive", "OFF", "ENABLE", "btn-cyber btn-primary")
    grab_status_2, grab_text_2, grab_action_2, grab_button_class_2 = ("active", "ON", "DISABLE", "btn-cyber btn-danger") if auto_grab_enabled_2 else ("inactive", "OFF", "ENABLE", "btn-cyber btn-primary")
    grab_status_3, grab_text_3, grab_action_3, grab_button_class_3 = ("active", "ON", "DISABLE", "btn-cyber btn-danger") if auto_grab_enabled_3 else ("inactive", "OFF", "ENABLE", "btn-cyber btn-primary")
    spam_action = "DISABLE" if spam_enabled else "ENABLE"
    spam_button_class = "btn-cyber btn-danger" if spam_enabled else "btn-cyber btn-primary"
    work_action = "DISABLE" if auto_work_enabled else "ENABLE"
    work_button_class = "btn-cyber btn-danger" if auto_work_enabled else "btn-cyber btn-primary"
    reboot_action = "DISABLE" if auto_reboot_enabled else "ENABLE"
    reboot_button_class = "btn-cyber btn-danger" if auto_reboot_enabled else "btn-cyber btn-primary"
    
    acc_options = "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names[:len(bots)]))
    sub_account_buttons = "".join(f'<button type="submit" name="reboot_target" value="sub_{i}" class="btn-cyber">{name}</button>' for i, name in enumerate(acc_names[:len(bots)]))

    return render_template_string(HTML_TEMPLATE, 
        msg_status=msg_status,
        grab_status=grab_status, grab_text=grab_text, grab_action=grab_action, grab_button_class=grab_button_class, heart_threshold=heart_threshold,
        grab_status_2=grab_status_2, grab_text_2=grab_text_2, grab_action_2=grab_action_2, grab_button_class_2=grab_button_class_2, heart_threshold_2=heart_threshold_2,
        grab_status_3=grab_status_3, grab_text_3=grab_text_3, grab_action_3=grab_action_3, grab_button_class_3=grab_button_class_3, heart_threshold_3=heart_threshold_3,
        spam_message=spam_message, spam_delay=spam_delay, spam_action=spam_action, spam_button_class=spam_button_class,
        work_delay_between_acc=work_delay_between_acc, work_delay_after_all=work_delay_after_all, work_action=work_action, work_button_class=work_button_class,
        auto_reboot_delay=auto_reboot_delay, reboot_action=reboot_action, reboot_button_class=reboot_button_class,
        acc_options=acc_options, num_bots=len(bots), sub_account_buttons=sub_account_buttons
    )

@app.route("/status")
def status():
    now = time.time()
    work_countdown = (last_work_cycle_time + work_delay_after_all - now) if auto_work_enabled else 0
    reboot_countdown = (last_reboot_cycle_time + auto_reboot_delay - now) if auto_reboot_enabled else 0
    spam_countdown = (last_spam_time + spam_delay - now) if spam_enabled else 0
    return jsonify({
        'work_enabled': auto_work_enabled, 'work_countdown': work_countdown,
        'reboot_enabled': auto_reboot_enabled, 'reboot_countdown': reboot_countdown,
        'spam_enabled': spam_enabled, 'spam_countdown': spam_countdown,
    })

if __name__ == "__main__":
    print("Đang khởi tạo các bot...")
    with bots_lock:
        if main_token: main_bot = create_bot(main_token, is_main=True)
        if main_token_2: main_bot_2 = create_bot(main_token_2, is_main_2=True)
        if main_token_3: main_bot_3 = create_bot(main_token_3, is_main_3=True)
        for token in tokens:
            if token.strip(): bots.append(create_bot(token.strip()))
    
    print("Đang khởi tạo các luồng nền...")
    threading.Thread(target=spam_loop, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 8080))
    print(f"Khởi động Web Server tại http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)