# PHIÊN BẢN CUỐI CÙNG - GIAO DIỆN "KARUTA DEEP" VÀ ĐẦY ĐỦ TÍNH NĂNG
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
        if target_id == 'main_1' and main_token:
            try: 
                if main_bot: main_bot.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 1: {e}")
            main_bot = create_bot(main_token, is_main=True)
            print("[Reboot] Acc Chính 1 đã được khởi động lại.")
        elif target_id == 'main_2' and main_token_2:
            try: 
                if main_bot_2: main_bot_2.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 2: {e}")
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
            print("[Reboot] Acc Chính 2 đã được khởi động lại.")
        elif target_id == 'main_3' and main_token_3:
            try: 
                if main_bot_3: main_bot_3.gateway.close()
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
            if is_main: bot_type = "(ALPHA)"
            elif is_main_2: bot_type = "(BETA)"
            elif is_main_3: bot_type = "(GAMMA)"
            else: bot_type = ""
            print(f"Đã đăng nhập: {user_id} {bot_type}")

    if is_main:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled, heart_threshold
            if resp.event.message:
                msg = resp.parsed.auto()
                if msg.get("author", {}).get("id") == karuta_id and msg.get("channel_id") == main_channel_id and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled:
                    last_drop_msg_id = msg["id"]
                    def read_karibbit():
                        time.sleep(0.5)
                        try:
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_item in messages:
                                if msg_item.get("author", {}).get("id") == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                    desc = msg_item["embeds"][0].get("description", "")
                                    lines = desc.split('\n')
                                    heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                    max_num = max(heart_numbers)
                                    if sum(heart_numbers) > 0 and max_num >= heart_threshold:
                                        max_index = heart_numbers.index(max_num)
                                        emoji, delay = [("1️⃣", 0.5), ("2️⃣", 1.5), ("3️⃣", 2.2)][max_index]
                                        print(f"[Bot 1] Chọn dòng {max_index+1} với {max_num} tim -> Emoji {emoji} sau {delay}s")
                                        def grab():
                                            bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                            bot.sendMessage(ktb_channel_id, "kt b")
                                        threading.Timer(delay, grab).start()
                                    break
                        except Exception as e:
                            print(f"Lỗi khi đọc tin nhắn Karibbit (Bot 1): {e}")
                    threading.Thread(target=read_karibbit).start()
    if is_main_2:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_2, heart_threshold_2
            if resp.event.message:
                msg = resp.parsed.auto()
                if msg.get("author", {}).get("id") == karuta_id and msg.get("channel_id") == main_channel_id and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_2:
                    last_drop_msg_id = msg["id"]
                    def read_karibbit_2():
                        time.sleep(0.5)
                        try:
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_item in messages:
                                if msg_item.get("author", {}).get("id") == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                    desc = msg_item["embeds"][0].get("description", "")
                                    lines = desc.split('\n')
                                    heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                    max_num = max(heart_numbers)
                                    if sum(heart_numbers) > 0 and max_num >= heart_threshold_2:
                                        max_index = heart_numbers.index(max_num)
                                        emoji, delay = [("1️⃣", 0.8), ("2️⃣", 1.8), ("3️⃣", 2.5)][max_index]
                                        print(f"[Bot 2] Chọn dòng {max_index+1} với {max_num} tim -> Emoji {emoji} sau {delay}s")
                                        def grab_2():
                                            bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                            bot.sendMessage(ktb_channel_id, "kt b")
                                        threading.Timer(delay, grab_2).start()
                                    break
                        except Exception as e:
                            print(f"Lỗi khi đọc tin nhắn Karibbit (Bot 2): {e}")
                    threading.Thread(target=read_karibbit_2).start()
    if is_main_3:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_3, heart_threshold_3
            if resp.event.message:
                msg = resp.parsed.auto()
                if msg.get("author", {}).get("id") == karuta_id and msg.get("channel_id") == main_channel_id and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_3:
                    last_drop_msg_id = msg["id"]
                    def read_karibbit_3():
                        time.sleep(0.5)
                        try:
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_item in messages:
                                if msg_item.get("author", {}).get("id") == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                    desc = msg_item["embeds"][0].get("description", "")
                                    lines = desc.split('\n')
                                    heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                    max_num = max(heart_numbers)
                                    if sum(heart_numbers) > 0 and max_num >= heart_threshold_3:
                                        max_index = heart_numbers.index(max_num)
                                        emoji, delay = [("1️⃣", 1.1), ("2️⃣", 2.1), ("3️⃣", 2.8)][max_index]
                                        print(f"[Bot 3] Chọn dòng {max_index+1} với {max_num} tim -> Emoji {emoji} sau {delay}s")
                                        def grab_3():
                                            bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                            bot.sendMessage(ktb_channel_id, "kt b")
                                        threading.Timer(delay, grab_3).start()
                                    break
                        except Exception as e:
                            print(f"Lỗi khi đọc tin nhắn Karibbit (Bot 3): {e}")
                    threading.Thread(target=read_karibbit_3).start()
    
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

def run_work_bot(token, acc_name):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = {"Authorization": token, "Content-Type": "application/json"}
    step = {"value": 0}
    def send_karuta_command(): bot.sendMessage(work_channel_id, "kc o:ef")
    def send_kn_command(): bot.sendMessage(work_channel_id, "kn")
    def send_kw_command(): bot.sendMessage(work_channel_id, "kw"); step["value"] = 2
    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json={"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "a", "data": {"component_type": 2, "custom_id": custom_id}})
            print(f"[Work][{acc_name}] Click tick: Status {r.status_code}")
        except Exception as e: print(f"[Work][{acc_name}] Lỗi click tick: {e}")
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
                    btn = next((b for b in comp['components'] if b['type'] == 2), None)
                    if comp['type'] == 1 and btn:
                        click_tick(work_channel_id, m['id'], btn['custom_id'], m.get('application_id', karuta_id), guild_id)
                        step["value"] = 3; bot.gateway.close(); break
    print(f"[Work][{acc_name}] Bắt đầu hoạt động...")
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    time.sleep(3); send_karuta_command()
    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout: time.sleep(1)
    bot.gateway.close()
    print(f"[Work][{acc_name}] Đã hoàn thành.")

def auto_work_loop():
    global auto_work_enabled, last_work_cycle_time
    while True:
        if auto_work_enabled:
            # B1: Tạo một danh sách làm việc tạm thời
            work_items = []
            
            # B2: Thêm acc chính 2 và 3 vào danh sách nếu có token
            if main_token_2: 
                work_items.append({"name": "BETA NODE", "token": main_token_2})
            if main_token_3: 
                work_items.append({"name": "GAMMA NODE", "token": main_token_3})
            
            # B3: Thêm tất cả các acc phụ vào danh sách
            with bots_lock:
                sub_account_items = [{"name": acc_names[i] if i < len(acc_names) else f"Sub {i+1}", "token": token} for i, token in enumerate(tokens) if token.strip()]
                work_items.extend(sub_account_items)

            # B4: Lặp qua danh sách tổng hợp để làm việc
            for item in work_items:
                if not auto_work_enabled: break
                print(f"[Work] Đang chạy acc '{item['name']}'...")
                run_work_bot(item['token'].strip(), item['name'])
                print(f"[Work] Acc '{item['name']}' xong, chờ {work_delay_between_acc} giây...")
                time.sleep(work_delay_between_acc)

            if auto_work_enabled:
                print(f"[Work] Hoàn thành chu kỳ, chờ {work_delay_after_all / 3600:.2f} giờ...")
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
            with bots_lock:
                bots_to_spam = bots.copy()
            for idx, bot in enumerate(bots_to_spam):
                if not spam_enabled: break
                try:
                    acc_name = acc_names[idx] if idx < len(acc_names) else f"Sub {idx+1}"
                    bot.sendMessage(spam_channel_id, spam_message)
                    print(f"[{acc_name}] đã gửi: {spam_message}")
                    time.sleep(2)
                except Exception as e: print(f"Lỗi gửi spam từ [{acc_name}]: {e}")
            
            print(f"[Spam] Chờ {spam_delay} giây cho lượt tiếp theo...")
            start_wait = time.time()
            while time.time() - start_wait < spam_delay:
                if not spam_enabled: break
                time.sleep(1)
        else:
            time.sleep(1)

app = Flask(__name__)

# --- GIAO DIỆN WEB ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Deep - Shadow Network Control</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Creepster&family=Orbitron:wght@400;700;900&family=Courier+Prime:wght@400;700&family=Nosifer&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-bg: #0a0a0a; --secondary-bg: #1a1a1a; --panel-bg: #111111; --border-color: #333333;
            --shadow-color: #660000; --blood-red: #8b0000; --dark-red: #550000; --bone-white: #f8f8ff;
            --ghost-gray: #666666; --void-black: #000000; --deep-purple: #2d1b69; --necro-green: #228b22;
            --shadow-cyan: #008b8b; --text-primary: #f0f0f0; --text-secondary: #cccccc; --text-muted: #888888;
            --neon-yellow: #fff000;
            --shadow-red: 0 0 20px rgba(139, 0, 0, 0.5); --shadow-purple: 0 0 20px rgba(45, 27, 105, 0.5);
            --shadow-green: 0 0 20px rgba(34, 139, 34, 0.5); --shadow-cyan: 0 0 20px rgba(0, 139, 139, 0.5);
        }
        body { font-family: 'Courier Prime', monospace; background: var(--primary-bg); color: var(--text-primary); margin: 0; padding: 0;}
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; padding: 30px; background: linear-gradient(135deg, var(--void-black), rgba(139, 0, 0, 0.3)); border: 2px solid var(--blood-red); border-radius: 15px; box-shadow: var(--shadow-red), inset 0 0 20px rgba(139, 0, 0, 0.1); }
        .skull-icon { font-size: 4rem; color: var(--blood-red); margin-bottom: 15px; }
        .title { font-family: 'Creepster', cursive; font-size: 3.5rem; letter-spacing: 4px; }
        .title-main { color: var(--blood-red); text-shadow: 0 0 30px var(--blood-red); }
        .title-sub { color: var(--deep-purple); text-shadow: 0 0 30px var(--deep-purple); }
        .subtitle { font-size: 1.3rem; color: var(--text-secondary); letter-spacing: 2px; margin-bottom: 15px; font-family: 'Orbitron', monospace; }
        .main-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .panel { background: linear-gradient(135deg, var(--panel-bg), rgba(26, 26, 26, 0.9)); border: 1px solid var(--border-color); border-radius: 10px; padding: 25px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); }
        .panel h2 { font-family: 'Nosifer', cursive; font-size: 1.4rem; margin-bottom: 20px; text-transform: uppercase; border-bottom: 2px solid; padding-bottom: 10px; }
        .panel h2 i { margin-right: 10px; }
        .blood-panel { border-color: var(--blood-red); box-shadow: var(--shadow-red); }
        .blood-panel h2 { color: var(--blood-red); border-color: var(--blood-red); }
        .dark-panel { border-color: var(--deep-purple); box-shadow: var(--shadow-purple); }
        .dark-panel h2 { color: var(--deep-purple); border-color: var(--deep-purple); }
        .void-panel { border-color: var(--ghost-gray); box-shadow: 0 0 20px rgba(102, 102, 102, 0.3); }
        .void-panel h2 { color: var(--ghost-gray); border-color: var(--ghost-gray); }
        .necro-panel { border-color: var(--necro-green); box-shadow: var(--shadow-green); }
        .necro-panel h2 { color: var(--necro-green); border-color: var(--necro-green); }
        .status-panel { 
            border-color: var(--bone-white); 
            box-shadow: 0 0 20px rgba(248, 248, 255, 0.2);
            grid-column: 1 / -1;
        }
        .status-panel h2 { color: var(--bone-white); border-color: var(--bone-white); }
        .code-panel { border-color: var(--shadow-cyan); box-shadow: var(--shadow-cyan); }
        .code-panel h2 { color: var(--shadow-cyan); border-color: var(--shadow-cyan); }
        .ops-panel { border-color: var(--neon-yellow, #fff000); box-shadow: 0 0 20px rgba(255, 240, 0, 0.4); }
        .ops-panel h2 { color: var(--neon-yellow, #fff000); border-color: var(--neon-yellow, #fff000); }
        .btn { background: linear-gradient(135deg, var(--secondary-bg), #333); border: 1px solid var(--border-color); color: var(--text-primary); padding: 10px 15px; border-radius: 4px; cursor: pointer; font-family: 'Orbitron', monospace; font-weight: 700; text-transform: uppercase; }
        .btn-blood { border-color: var(--blood-red); color: var(--blood-red); } .btn-blood:hover { background: var(--blood-red); color: var(--primary-bg); box-shadow: var(--shadow-red); }
        .btn-necro { border-color: var(--necro-green); color: var(--necro-green); } .btn-necro:hover { background: var(--necro-green); color: var(--primary-bg); box-shadow: var(--shadow-green); }
        .btn-primary { border-color: var(--shadow-cyan); color: var(--shadow-cyan); } .btn-primary:hover { background: var(--shadow-cyan); color: var(--primary-bg); box-shadow: var(--shadow-cyan); }
        .btn-sm { padding: 8px 12px; font-size: 0.8rem; }
        .input-group { display: flex; align-items: stretch; gap: 10px; margin-bottom: 15px; }
        .input-group label { color: var(--text-secondary); font-weight: 600; font-family: 'Orbitron', monospace; padding: 10px; background: rgba(0,0,0,0.4); border: 1px solid var(--border-color); border-right: none; border-radius: 5px 0 0 5px;}
        .input-group input, .input-group textarea, .input-group select { flex-grow: 1; background: rgba(0, 0, 0, 0.8); border: 1px solid var(--border-color); color: var(--text-primary); padding: 10px 15px; border-radius: 0 5px 5px 0; font-family: 'Courier Prime', monospace; }
        .grab-section { margin-bottom: 15px; padding: 15px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px;}
        .grab-section h3 { color: var(--text-secondary); margin-top:0; margin-bottom: 15px; font-family: 'Orbitron', monospace; text-shadow: 0 0 10px var(--text-secondary); display: flex; justify-content: space-between; align-items: center;}
        .reboot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; }
        .msg-status { text-align: center; color: var(--shadow-cyan); font-family: 'Courier Prime', monospace; padding: 12px; border: 1px dashed var(--border-color); border-radius: 4px; margin-bottom: 20px; background: rgba(0, 139, 139, 0.1); }
        .status-grid { display: flex; flex-direction: column; gap: 15px; }
        .status-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(0,0,0,0.6); border: 1px solid var(--border-color); border-radius: 8px; }
        .status-label { font-weight: 600; font-family: 'Orbitron'; }
        .timer-display { font-family: 'Courier Prime', monospace; font-size: 1.2em; font-weight: 700; }
        .status-badge { padding: 4px 10px; border-radius: 15px; text-transform: uppercase; font-size: 0.8em; }
        .status-badge.active { background: var(--necro-green); color: var(--primary-bg); box-shadow: var(--shadow-green); }
        .status-badge.inactive { background: var(--dark-red); color: var(--text-secondary); }
        .quick-cmd-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 10px; }
        .bot-status-container {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 20px;
            margin-top: 15px;
            border-top: 1px solid var(--border-color);
            padding-top: 15px;
        }
        .bot-status-grid {
            display: grid; 
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }
        .bot-status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 5px 8px;
            background: rgba(0,0,0,0.3);
            border-radius: 4px;
            font-family: 'Courier Prime', monospace;
            border: 1px solid var(--blood-red);
        }
        .status-indicator {
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.9em;
        }
        .status-indicator.online { color: var(--necro-green); }
        .status-indicator.offline { color: var(--blood-red); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="skull-icon">💀</div>
            <h1 class="title"><span class="title-main">KARUTA</span> <span class="title-sub">DEEP</span></h1>
            <p class="subtitle">Shadow Network Control Interface</p>
        </div>
        
        {% if msg_status %}
        <div class="msg-status"><i class="fas fa-info-circle"></i> {{ msg_status }}</div>
        {% endif %}

        <div class="main-grid">
            <div class="panel status-panel">
                <h2><i class="fas fa-heartbeat"></i> System Status</h2>
                <div class="bot-status-container">
                    <div class="status-grid">
                        <div class="status-row"><span class="status-label"><i class="fas fa-cogs"></i> Auto Work</span><div><span id="work-timer" class="timer-display">--:--:--</span> <span id="work-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-redo"></i> Auto Reboot</span><div><span id="reboot-timer" class="timer-display">--:--:--</span> <span id="reboot-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-broadcast-tower"></i> Auto Spam</span><div><span id="spam-timer" class="timer-display">--:--:--</span><span id="spam-status-badge" class="status-badge inactive">OFF</span></div></div>
                    </div>
                    <div id="bot-status-list" class="bot-status-grid">
                        </div>
                </div>
            </div>

            <div class="panel blood-panel">
                <h2><i class="fas fa-crosshairs"></i> Soul Harvest</h2>
                <form method="post">
                    <div class="grab-section"><h3>ALPHA NODE <span class="status-badge {{ grab_status }}">{{ grab_text }}</span></h3><div class="input-group"><input type="number" name="heart_threshold" value="{{ heart_threshold }}" min="1" max="100"><button type="submit" name="toggle" value="1" class="btn {{ grab_button_class }}">{{ grab_action }}</button></div></div>
                    <div class="grab-section"><h3>BETA NODE <span class="status-badge {{ grab_status_2 }}">{{ grab_text_2 }}</span></h3><div class="input-group"><input type="number" name="heart_threshold_2" value="{{ heart_threshold_2 }}" min="1" max="100"><button type="submit" name="toggle_2" value="1" class="btn {{ grab_button_class_2 }}">{{ grab_action_2 }}</button></div></div>
                    <div class="grab-section"><h3>GAMMA NODE <span class="status-badge {{ grab_status_3 }}">{{ grab_text_3 }}</span></h3><div class="input-group"><input type="number" name="heart_threshold_3" value="{{ heart_threshold_3 }}" min="1" max="100"><button type="submit" name="toggle_3" value="1" class="btn {{ grab_button_class_3 }}">{{ grab_action_3 }}</button></div></div>
                </form>
            </div>

            <div class="panel ops-panel">
                <h2><i class="fas fa-keyboard"></i> Manual Operations</h2>
                <form method="post" style="display: flex; flex-direction: column; gap: 15px;">
                    <div class="input-group">
                        <input type="text" name="message" placeholder="Enter manual message for slaves..." style="border-radius: 5px;">
                        <button type="submit" class="btn" style="flex-shrink: 0; border-color: var(--neon-yellow, #fff000); color: var(--neon-yellow, #fff000);">SEND</button>
                    </div>
                    <div class="quick-cmd-grid">
                        <button type="submit" name="quickmsg" value="kc o:w" class="btn">KC O:W</button>
                        <button type="submit" name="quickmsg" value="kc o:ef" class="btn">KC O:EF</button>
                        <button type="submit" name="quickmsg" value="kc o:p" class="btn">KC O:P</button>

                        <button type="submit" name="quickmsg" value="kc e:1" class="btn">KC E:1</button>
                        <button type="submit" name="quickmsg" value="kc e:2" class="btn">KC E:2</button>
                        <button type="submit" name="quickmsg" value="kc e:3" class="btn">KC E:3</button>
                        <button type="submit" name="quickmsg" value="kc e:4" class="btn">KC E:4</button>
                        <button type="submit" name="quickmsg" value="kc e:5" class="btn">KC E:5</button>
                        <button type="submit" name="quickmsg" value="kc e:6" class="btn">KC E:6</button>
                        <button type="submit" name="quickmsg" value="kc e:7" class="btn">KC E:7</button>
                    </div>
                </form>
            </div>
            
            <div class="panel dark-panel">
                <h2><i class="fas fa-broadcast-tower"></i> Shadow Broadcast</h2>
                <form method="post">
                    <div class="input-group"><label>Message</label><textarea name="spammsg" rows="2">{{ spam_message }}</textarea></div>
                    <div class="input-group"><label>Delay (s)</label><input type="number" name="spam_delay" value="{{ spam_delay }}"></div>
                    <button type="submit" name="spamtoggle" class="btn {{ spam_button_class }}" style="width:100%; margin-top: 10px;">{{ spam_action }} SPAM</button>
                </form>
            </div>

            <div class="panel void-panel">
                <h2><i class="fas fa-cogs"></i> Shadow Labor</h2>
                <form method="post">
                    <div class="input-group"><label>Node Delay</label><input type="number" name="work_delay_between_acc" value="{{ work_delay_between_acc }}"></div>
                    <div class="input-group"><label>Cycle Delay</label><input type="number" name="work_delay_after_all" value="{{ work_delay_after_all }}"></div>
                    <button type="submit" name="auto_work_toggle" class="btn {{ work_button_class }}" style="width:100%; margin-top: 10px;">{{ work_action }} WORK</button>
                </form>
            </div>

            <div class="panel necro-panel">
                 <h2><i class="fas fa-skull"></i> Shadow Resurrection</h2>
                 <form method="post">
                    <div class="input-group"><label>Interval (s)</label><input type="number" name="auto_reboot_delay" value="{{ auto_reboot_delay }}"></div>
                    <button type="submit" name="auto_reboot_toggle" class="btn {{ reboot_button_class }}" style="width:100%;">{{ reboot_action }} AUTO REBOOT</button>
                    <hr style="border-color: var(--border-color); margin: 20px 0;">
                    <h3 style="text-align:center; font-family: 'Orbitron';">MANUAL OVERRIDE</h3>
                    <div class="reboot-grid" style="margin-top: 15px;">
                        <button type="submit" name="reboot_target" value="main_1" class="btn btn-necro btn-sm">NODE 1</button>
                        <button type="submit" name="reboot_target" value="main_2" class="btn btn-necro btn-sm">NODE 2</button>
                        <button type="submit" name="reboot_target" value="main_3" class="btn btn-necro btn-sm">NODE 3</button>
                        {{ sub_account_buttons|safe }}
                    </div>
                     <button type="submit" name="reboot_target" value="all" class="btn btn-blood" style="width:100%; margin-top: 15px;">REBOOT ALL SYSTEMS</button>
                 </form>
            </div>
            
            <div class="panel code-panel">
                <h2><i class="fas fa-code"></i> Code Injection</h2>
                <form method="post">
                    <div class="input-group"><label>Target</label><select name="acc_index">{{ acc_options|safe }}</select></div>
                    <div class="input-group"><label>Prefix</label><input type="text" name="prefix" placeholder="e.g. kt n"></div>
                    <div class="input-group"><label>Delay</label><input type="number" name="delay" value="1.0" step="0.1"></div>
                    <div class="input-group" style="flex-direction: column; align-items: stretch;">
                        <label style="border-radius: 5px 5px 0 0; border-bottom: none;">Code List (comma-separated)</label>
                        <textarea name="codes" placeholder="paste codes here, separated by commas" rows="3" style="border-radius: 0 0 5px 5px;"></textarea>
                    </div>
                    <button type="submit" name="send_codes" value="1" class="btn btn-primary" style="width: 100%; margin-top:10px;">Inject Codes</button>
                </form>
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
            if (!badge) return;
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

                const listContainer = document.getElementById('bot-status-list');
                listContainer.innerHTML = ''; 

                const allBots = [...data.bot_statuses.main_bots, ...data.bot_statuses.sub_accounts];

                allBots.forEach(bot => {
                    const statusClass = bot.status ? 'online' : 'offline';
                    const statusText = bot.status ? 'ONLINE' : 'OFFLINE';
                    const item = document.createElement('div');
                    item.className = 'bot-status-item';
                    item.innerHTML = `<span>${bot.name}</span><span class="status-indicator ${statusClass}">${statusText}</span>`;
                    listContainer.appendChild(item);
                });

            } catch (error) { console.error('Error fetching status:', error); }
        }
        setInterval(fetchStatus, 1000);
    });
</script>
</body>
</html>
"""

# --- FLASK ROUTES ---

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, auto_grab_enabled_2, auto_grab_enabled_3
    global spam_enabled, spam_message, spam_delay, spam_thread, last_spam_time
    global heart_threshold, heart_threshold_2, heart_threshold_3
    global auto_work_enabled, work_delay_between_acc, work_delay_after_all, last_work_cycle_time
    global auto_reboot_enabled, auto_reboot_delay, auto_reboot_thread, auto_reboot_stop_event, last_reboot_cycle_time
    
    msg_status = ""
    if request.method == "POST":
        if 'message' in request.form and request.form['message']:
            msg = request.form['message']
            msg_status = f"Sent to slaves: {msg}"
            with bots_lock:
                for idx, bot in enumerate(bots): 
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, msg)).start()
        elif 'quickmsg' in request.form:
            msg = request.form['quickmsg']
            msg_status = f"Sent to slaves: {msg}"
            with bots_lock:
                for idx, bot in enumerate(bots): 
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, msg)).start()

        elif 'toggle' in request.form:
            auto_grab_enabled = not auto_grab_enabled
            heart_threshold = int(request.form.get('heart_threshold', 50))
            msg_status = f"Auto Grab 1 was {'ENABLED' if auto_grab_enabled else 'DISABLED'}"
        elif 'toggle_2' in request.form:
            auto_grab_enabled_2 = not auto_grab_enabled_2
            heart_threshold_2 = int(request.form.get('heart_threshold_2', 50))
            msg_status = f"Auto Grab 2 was {'ENABLED' if auto_grab_enabled_2 else 'DISABLED'}"
        elif 'toggle_3' in request.form:
            auto_grab_enabled_3 = not auto_grab_enabled_3
            heart_threshold_3 = int(request.form.get('heart_threshold_3', 50))
            msg_status = f"Auto Grab 3 was {'ENABLED' if auto_grab_enabled_3 else 'DISABLED'}"
        
        elif 'spamtoggle' in request.form:
            spam_message = request.form.get("spammsg", "").strip()
            spam_delay = int(request.form.get("spam_delay", 10))
            if not spam_enabled and spam_message:
                spam_enabled = True
                last_spam_time = time.time()
                msg_status = "Spam ENABLED."
                if spam_thread is None or not spam_thread.is_alive():
                    spam_thread = threading.Thread(target=spam_loop, daemon=True)
                    spam_thread.start()
            else:
                spam_enabled = False
                msg_status = "Spam DISABLED."

        elif 'auto_work_toggle' in request.form:
            auto_work_enabled = not auto_work_enabled
            if auto_work_enabled: last_work_cycle_time = time.time()
            work_delay_between_acc = int(request.form.get('work_delay_between_acc', 10))
            work_delay_after_all = int(request.form.get('work_delay_after_all', 44100))
            msg_status = f"Auto Work {'ENABLED' if auto_work_enabled else 'DISABLED'}."

        elif 'send_codes' in request.form:
            try:
                target_id_str = request.form.get("acc_index")
                delay_val = float(request.form.get("delay", 1.0))
                prefix = request.form.get("prefix", "")
                codes_list = [c.strip() for c in request.form.get("codes", "").split(',') if c.strip()]
                
                target_bot = None
                target_name = ""

                if target_id_str == 'main_1':
                    target_bot = main_bot
                    target_name = "ALPHA NODE (Main)"
                elif target_id_str == 'main_2':
                    target_bot = main_bot_2
                    target_name = "BETA NODE (Main)"
                elif target_id_str == 'main_3':
                    target_bot = main_bot_3
                    target_name = "GAMMA NODE (Main)"
                else:
                    acc_idx = int(target_id_str)
                    if acc_idx < len(bots):
                        target_bot = bots[acc_idx]
                        target_name = acc_names[acc_idx]

                if target_bot:
                    with bots_lock:
                        for i, code in enumerate(codes_list):
                            final_msg = f"{prefix} {code}" if prefix else code
                            threading.Timer(delay_val * i, target_bot.sendMessage, args=(other_channel_id, final_msg)).start()
                    msg_status = f"Injecting {len(codes_list)} codes to '{target_name}'."
                else:
                    msg_status = "Error: Invalid account selected for injection."
            except Exception as e:
                msg_status = f"Code Injection Error: {e}"

        elif 'auto_reboot_toggle' in request.form:
            auto_reboot_enabled = not auto_reboot_enabled
            auto_reboot_delay = int(request.form.get("auto_reboot_delay", 3600))
            if auto_reboot_enabled and (auto_reboot_thread is None or not auto_reboot_thread.is_alive()):
                auto_reboot_stop_event = threading.Event()
                auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
                auto_reboot_thread.start()
                msg_status = "Auto Reboot ENABLED."
            elif not auto_reboot_enabled and auto_reboot_stop_event:
                auto_reboot_stop_event.set()
                auto_reboot_thread = None
                msg_status = "Auto Reboot DISABLED."

        elif 'reboot_target' in request.form:
            target = request.form.get('reboot_target')
            msg_status = f"Rebooting target: {target.upper()}"
            if target == "all":
                if main_bot: reboot_bot('main_1'); time.sleep(1)
                if main_bot_2: reboot_bot('main_2'); time.sleep(1)
                if main_bot_3: reboot_bot('main_3'); time.sleep(1)
                with bots_lock:
                    for i in range(len(bots)): reboot_bot(f'sub_{i}'); time.sleep(1)
            else:
                reboot_bot(target)
    
    grab_status, grab_text, grab_action, grab_button_class = ("active", "ON", "DISABLE", "btn btn-blood") if auto_grab_enabled else ("inactive", "OFF", "ENABLE", "btn btn-necro")
    grab_status_2, grab_text_2, grab_action_2, grab_button_class_2 = ("active", "ON", "DISABLE", "btn btn-blood") if auto_grab_enabled_2 else ("inactive", "OFF", "ENABLE", "btn btn-necro")
    grab_status_3, grab_text_3, grab_action_3, grab_button_class_3 = ("active", "ON", "DISABLE", "btn btn-blood") if auto_grab_enabled_3 else ("inactive", "OFF", "ENABLE", "btn btn-necro")
    spam_action, spam_button_class = ("DISABLE", "btn-blood") if spam_enabled else ("ENABLE", "btn-necro")
    work_action, work_button_class = ("DISABLE", "btn-blood") if auto_work_enabled else ("ENABLE", "btn-necro")
    reboot_action, reboot_button_class = ("DISABLE", "btn-blood") if auto_reboot_enabled else ("ENABLE", "btn-necro")
    
    acc_options = "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names[:len(bots)]))
    if main_bot:
        acc_options += '<option value="main_1">ALPHA NODE (Main)</option>'
    if main_bot_2:
        acc_options += '<option value="main_2">BETA NODE (Main)</option>'
    if main_bot_3:
        acc_options += '<option value="main_3">GAMMA NODE (Main)</option>'

    sub_account_buttons = "".join(f'<button type="submit" name="reboot_target" value="sub_{i}" class="btn btn-necro btn-sm">{name}</button>' for i, name in enumerate(acc_names[:len(bots)]))

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

    bot_statuses = {
        "main_bots": [
            {"name": "ALPHA NODE", "status": main_bot is not None},
            {"name": "BETA NODE", "status": main_bot_2 is not None},
            {"name": "GAMMA NODE", "status": main_bot_3 is not None}
        ],
        "sub_accounts": []
    }
    with bots_lock:
        bot_statuses["sub_accounts"] = [{"name": acc_names[i] if i < len(acc_names) else f"Sub {i+1}", "status": bot is not None} for i, bot in enumerate(bots)]

    return jsonify({
        'work_enabled': auto_work_enabled, 'work_countdown': work_countdown,
        'reboot_enabled': auto_reboot_enabled, 'reboot_countdown': reboot_countdown,
        'spam_enabled': spam_enabled, 'spam_countdown': spam_countdown,
        'bot_statuses': bot_statuses
    })

# --- MAIN EXECUTION ---
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
    print(f"Khởi động Web Server tại http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)