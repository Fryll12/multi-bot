# multi_bot_control_full_plus_acc3_and_auto_reboot.py (LOGIC CỦA BẠN - GIAO DIỆN MỚI)
import discum
import threading
import time
import os
import random
import re
import requests
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH (GIỮ NGUYÊN CỦA BẠN) ---
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

# --- BIẾN TRẠNG THÁI (GIỮ NGUYÊN CỦA BẠN) ---
bots = []
main_bot = None
main_bot_2 = None
main_bot_3 = None
auto_grab_enabled = False
auto_grab_enabled_2 = False
auto_grab_enabled_3 = False
heart_threshold = 50
heart_threshold_2 = 50
heart_threshold_3 = 50
last_drop_msg_id = ""
acc_names = [
     "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent",
]

spam_enabled = False
spam_message = ""
spam_delay = 10
spam_thread = None # Thêm biến này để quản lý luồng tốt hơn

auto_work_enabled = False
work_delay_between_acc = 10
work_delay_after_all = 44100

auto_reboot_enabled = False
auto_reboot_delay = 3600
auto_reboot_thread = None
auto_reboot_stop_event = None

bots_lock = threading.Lock()

# --- LOGIC CỦA BẠN (GIỮ NGUYÊN 100%) ---

def reboot_bot(target_id):
    global main_bot, main_bot_2, main_bot_3, bots

    with bots_lock:
        print(f"[Reboot] Nhận được yêu cầu reboot cho target: {target_id}")
        if target_id == 'main_1' and main_bot:
            print("[Reboot] Đang xử lý Acc Chính 1...")
            try:
                main_bot.gateway.close()
            except Exception as e:
                print(f"[Reboot] Lỗi khi đóng Acc Chính 1: {e}")
            main_bot = create_bot(main_token, is_main=True)
            print("[Reboot] Acc Chính 1 đã được khởi động lại.")

        elif target_id == 'main_2' and main_bot_2:
            print("[Reboot] Đang xử lý Acc Chính 2...")
            try:
                main_bot_2.gateway.close()
            except Exception as e:
                print(f"[Reboot] Lỗi khi đóng Acc Chính 2: {e}")
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
            print("[Reboot] Acc Chính 2 đã được khởi động lại.")

        elif target_id == 'main_3' and main_bot_3:
            print("[Reboot] Đang xử lý Acc Chính 3...")
            try:
                main_bot_3.gateway.close()
            except Exception as e:
                print(f"[Reboot] Lỗi khi đóng Acc Chính 3: {e}")
            main_bot_3 = create_bot(main_token_3, is_main_3=True)
            print("[Reboot] Acc Chính 3 đã được khởi động lại.")

        elif target_id.startswith('sub_'):
            try:
                index = int(target_id.split('_')[1])
                if 0 <= index < len(bots):
                    print(f"[Reboot] Đang xử lý Acc Phụ {index}...")
                    try:
                        bots[index].gateway.close()
                    except Exception as e:
                        print(f"[Reboot] Lỗi khi đóng Acc Phụ {index}: {e}")
                    
                    token_to_reboot = tokens[index]
                    bots[index] = create_bot(token_to_reboot.strip(), is_main=False)
                    print(f"[Reboot] Acc Phụ {index} đã được khởi động lại.")
                else:
                    print(f"[Reboot] Index không hợp lệ: {index}")
            except (ValueError, IndexError) as e:
                print(f"[Reboot] Lỗi xử lý target Acc Phụ: {e}")
        else:
            print(f"[Reboot] Target không xác định: {target_id}")

def create_bot(token, is_main=False, is_main_2=False, is_main_3=False):
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                bot_type = "(Acc chính)" if is_main else "(Acc chính 2)" if is_main_2 else "(Acc chính 3)" if is_main_3 else ""
                print(f"Đã đăng nhập: {user_id} {bot_type}")
            except Exception as e:
                print(f"Lỗi lấy user_id: {e}")

    if is_main:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled, heart_threshold, last_drop_msg_id

            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])

                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled:
                        print("\n[Bot 1] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                        last_drop_msg_id = msg["id"]

                        def read_karibbit():
                            time.sleep(0.5)
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_item in messages:
                                author_id = msg_item.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                    desc = msg_item["embeds"][0].get("description", "")
                                    print(f"\n[Bot 1] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 1] ===== Kết thúc tin nhắn =====\n")

                                    lines = desc.split('\n')
                                    heart_numbers = []

                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            num = int(matches[1])
                                            heart_numbers.append(num)
                                        else:
                                            heart_numbers.append(0)

                                    if sum(heart_numbers) == 0:
                                        print("[Bot 1] Không có số tim nào, bỏ qua.\n")
                                    else:
                                        max_num = max(heart_numbers)
                                        if max_num < heart_threshold:
                                            print(f"[Bot 1] Số tim lớn nhất {max_num} < {heart_threshold}, không grab!\n")
                                        else:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}[emoji]
                                            print(f"[Bot 1] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")

                                            def grab():
                                                try:
                                                    bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                    print("[Bot 1] Đã thả emoji grab!")
                                                    bot.sendMessage(ktb_channel_id, "kt b")
                                                    print("[Bot 1] Đã nhắn 'kt b'!")
                                                except Exception as e:
                                                    print(f"[Bot 1] Lỗi khi grab hoặc nhắn kt b: {e}")

                                            threading.Timer(delay, grab).start()
                                    break
                        threading.Thread(target=read_karibbit).start()
    if is_main_2:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_2, heart_threshold_2, last_drop_msg_id

            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])

                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled_2:
                        print("\n[Bot 2] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                        last_drop_msg_id = msg["id"]

                        def read_karibbit_2():
                            time.sleep(0.5)
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_item in messages:
                                author_id = msg_item.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                    desc = msg_item["embeds"][0].get("description", "")
                                    print(f"\n[Bot 2] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 2] ===== Kết thúc tin nhắn =====\n")

                                    lines = desc.split('\n')
                                    heart_numbers = []

                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            num = int(matches[1])
                                            heart_numbers.append(num)
                                        else:
                                            heart_numbers.append(0)

                                    if sum(heart_numbers) == 0:
                                        print("[Bot 2] Không có số tim nào, bỏ qua.\n")
                                    else:
                                        max_num = max(heart_numbers)
                                        if max_num < heart_threshold_2:
                                            print(f"[Bot 2] Số tim lớn nhất {max_num} < {heart_threshold_2}, không grab!\n")
                                        else:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 0.8, "2️⃣": 1.8, "3️⃣": 2.5}[emoji]
                                            print(f"[Bot 2] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")

                                            def grab_2():
                                                try:
                                                    bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                    print("[Bot 2] Đã thả emoji grab!")
                                                    bot.sendMessage(ktb_channel_id, "kt b")
                                                    print("[Bot 2] Đã nhắn 'kt b'!")
                                                except Exception as e:
                                                    print(f"[Bot 2] Lỗi khi grab hoặc nhắn kt b: {e}")

                                            threading.Timer(delay, grab_2).start()
                                    break
                        threading.Thread(target=read_karibbit_2).start()

    if is_main_3:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_3, heart_threshold_3, last_drop_msg_id

            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])

                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled_3:
                        print("\n[Bot 3] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                        last_drop_msg_id = msg["id"]

                        def read_karibbit_3():
                            time.sleep(0.5)
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_item in messages:
                                author_id = msg_item.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                    desc = msg_item["embeds"][0].get("description", "")
                                    print(f"\n[Bot 3] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 3] ===== Kết thúc tin nhắn =====\n")

                                    lines = desc.split('\n')
                                    heart_numbers = []

                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            num = int(matches[1])
                                            heart_numbers.append(num)
                                        else:
                                            heart_numbers.append(0)

                                    if sum(heart_numbers) == 0:
                                        print("[Bot 3] Không có số tim nào, bỏ qua.\n")
                                    else:
                                        max_num = max(heart_numbers)
                                        if max_num < heart_threshold_3:
                                            print(f"[Bot 3] Số tim lớn nhất {max_num} < {heart_threshold_3}, không grab!\n")
                                        else:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 1.1, "2️⃣": 2.1, "3️⃣": 2.8}[emoji]
                                            print(f"[Bot 3] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")

                                            def grab_3():
                                                try:
                                                    bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                    print("[Bot 3] Đã thả emoji grab!")
                                                    bot.sendMessage(ktb_channel_id, "kt b")
                                                    print("[Bot 3] Đã nhắn 'kt b'!")
                                                except Exception as e:
                                                    print(f"[Bot 3] Lỗi khi grab hoặc nhắn kt b: {e}")

                                            threading.Timer(delay, grab_3).start()
                                    break
                        threading.Thread(target=read_karibbit_3).start()
    
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

def run_work_bot(token, acc_index):
    bot = discum.Client(token=token, log={"console": False, "file": False})

    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }

    step = {"value": 0}

    def send_karuta_command():
        print(f"[Work Acc {acc_index}] Gửi lệnh 'kc o:ef'...")
        bot.sendMessage(work_channel_id, "kc o:ef")

    def send_kn_command():
        print(f"[Work Acc {acc_index}] Gửi lệnh 'kn'...")
        bot.sendMessage(work_channel_id, "kn")

    def send_kw_command():
        print(f"[Work Acc {acc_index}] Gửi lệnh 'kw'...")
        bot.sendMessage(work_channel_id, "kw")
        step["value"] = 2

    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            payload = {
                "type": 3,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "message_id": message_id,
                "application_id": application_id,
                "session_id": "a",
                "data": {
                    "component_type": 2,
                    "custom_id": custom_id
                }
            }
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
            if r.status_code == 204:
                print(f"[Work Acc {acc_index}] Click tick thành công!")
            else:
                print(f"[Work Acc {acc_index}] Click thất bại! Mã lỗi: {r.status_code}, Nội dung: {r.text}")
        except Exception as e:
            print(f"[Work Acc {acc_index}] Lỗi click tick: {str(e)}")

    @bot.gateway.command
    def on_message(resp):
        if resp.event.message:
            m = resp.parsed.auto()
            if str(m.get('channel_id')) != work_channel_id:
                return

            author_id = str(m.get('author', {}).get('id', ''))
            guild_id = m.get('guild_id')

            if step["value"] == 0 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', '')
                card_codes = re.findall(r'\bv[a-zA-Z0-9]{6}\b', desc)
                if card_codes and len(card_codes) >= 10:
                    first_5 = card_codes[:5]
                    last_5 = card_codes[-5:]

                    print(f"[Work Acc {acc_index}] Mã đầu: {', '.join(first_5)}")
                    print(f"[Work Acc {acc_index}] Mã cuối: {', '.join(last_5)}")

                    for i, code in enumerate(last_5):
                        suffix = chr(97 + i)
                        if i == 0:
                            time.sleep(2)
                        else:
                            time.sleep(1.5)
                        bot.sendMessage(work_channel_id, f"kjw {code} {suffix}")

                    for i, code in enumerate(first_5):
                        suffix = chr(97 + i)
                        time.sleep(1.5)
                        bot.sendMessage(work_channel_id, f"kjw {code} {suffix}")

                    time.sleep(1)
                    send_kn_command()
                    step["value"] = 1

            elif step["value"] == 1 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', '')
                lines = desc.split('\n')
                if len(lines) >= 2:
                    match = re.search(r'\d+\.\s*`([^`]+)`', lines[1])
                    if match:
                        resource = match.group(1)
                        print(f"[Work Acc {acc_index}] Tài nguyên chọn: {resource}")
                        time.sleep(2)
                        bot.sendMessage(work_channel_id, f"kjn `{resource}` a b c d e")
                        time.sleep(1)
                        send_kw_command()

            elif step["value"] == 2 and author_id == karuta_id and 'components' in m:
                message_id = m['id']
                application_id = m.get('application_id', karuta_id)
                last_custom_id = None
                for comp in m['components']:
                    if comp['type'] == 1:
                        for btn in comp['components']:
                            if btn['type'] == 2:
                                last_custom_id = btn['custom_id']
                                print(f"[Work Acc {acc_index}] Phát hiện button, custom_id: {last_custom_id}")

                if last_custom_id:
                    click_tick(work_channel_id, message_id, last_custom_id, application_id, guild_id)
                    step["value"] = 3
                    bot.gateway.close()

    print(f"[Work Acc {acc_index}] Bắt đầu hoạt động...")
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    time.sleep(3)
    send_karuta_command()

    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout:
        time.sleep(1)

    bot.gateway.close()
    print(f"[Work Acc {acc_index}] Đã hoàn thành, chuẩn bị tới acc tiếp theo.")

def auto_work_loop():
    global auto_work_enabled
    while True:
        if auto_work_enabled:
            with bots_lock:
                current_tokens = tokens.copy()
            for i, token in enumerate(current_tokens):
                if token.strip():
                    print(f"[Auto Work] Đang chạy acc {i+1}...")
                    run_work_bot(token.strip(), i+1)
                    print(f"[Auto Work] Acc {i+1} xong, chờ {work_delay_between_acc} giây...")
                    time.sleep(work_delay_between_acc)
            
            print(f"[Auto Work] Hoàn thành tất cả acc, chờ {work_delay_after_all} giây để lặp lại...")
            time.sleep(work_delay_after_all)
        else:
            time.sleep(10)

def auto_reboot_loop():
    """Vòng lặp chạy nền để tự động reboot các bot chính theo chu kỳ."""
    global auto_reboot_stop_event
    print("[Auto Reboot] Luồng tự động reboot đã bắt đầu.")
    
    while not auto_reboot_stop_event.is_set():
        print(f"[Auto Reboot] Bắt đầu chu kỳ reboot. Chờ {auto_reboot_delay} giây cho chu kỳ tiếp theo...")
        
        interrupted = auto_reboot_stop_event.wait(timeout=auto_reboot_delay)
        
        if interrupted:
            break
            
        print("[Auto Reboot] Hết thời gian chờ, tiến hành reboot 3 tài khoản chính.")
        
        if main_bot:
            reboot_bot('main_1')
            time.sleep(5)
        
        if main_bot_2:
            reboot_bot('main_2')
            time.sleep(5)

        if main_bot_3:
            reboot_bot('main_3')
            
    print("[Auto Reboot] Luồng tự động reboot đã dừng.")

def spam_loop():
    global spam_enabled, spam_message, spam_delay
    while True:
        if spam_enabled and spam_message:
            with bots_lock:
                bots_to_spam = bots.copy()
            for idx, bot in enumerate(bots_to_spam):
                try:
                    bot.sendMessage(spam_channel_id, spam_message)
                    print(f"[{acc_names[idx]}] đã gửi: {spam_message}")
                    time.sleep(2)
                except Exception as e:
                    print(f"Lỗi gửi spam: {e}")
        time.sleep(spam_delay)

def keep_alive():
    while True:
        try:
            if main_bot:
                pass
            time.sleep(random.randint(60, 120))
        except:
            pass

app = Flask(__name__)

# --- GIAO DIỆN HTML MỚI (ĐÃ SỬA LỖI KEYERROR) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KARUTA DEEP - Bot Control Matrix</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --neon-green: #00ff41; --neon-cyan: #00ffff; --neon-red: #ff0040; --neon-purple: #8000ff;
            --primary-bg: #0a0a0a; --secondary-bg: #111111; --accent-bg: #1a1a1a;
            --border-color: #333333; --text-primary: #ffffff; --text-muted: #cccccc;
            --shadow-glow: 0 0 15px; --font-primary: 'Orbitron', monospace; --font-mono: 'Courier Prime', monospace;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: var(--font-primary); background: linear-gradient(135deg, var(--primary-bg), var(--secondary-bg)); color: var(--text-primary); min-height: 100vh; overflow-x: hidden; position: relative; }}
        body::before {{ content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: radial-gradient(circle at 20% 80%, rgba(0, 255, 65, 0.1) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(0, 255, 255, 0.1) 0%, transparent 50%), radial-gradient(circle at 40% 40%, rgba(255, 0, 64, 0.1) 0%, transparent 50%); pointer-events: none; z-index: -1; }}
        .matrix-bg {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: -1; opacity: 0.1; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 15px; }}
        .header {{ text-align: center; margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, var(--accent-bg), var(--secondary-bg)); border: 2px solid var(--neon-green); border-radius: 8px; box-shadow: var(--shadow-glow) var(--neon-green); }}
        .logo {{ display: flex; align-items: center; justify-content: center; gap: 15px; }}
        .logo i {{ font-size: 2.2em; color: var(--neon-red); text-shadow: var(--shadow-glow) var(--neon-red); animation: pulse-glow 2s ease-in-out infinite alternate; }}
        @keyframes pulse-glow {{ 0% {{ text-shadow: var(--shadow-glow) var(--neon-red); }} 100% {{ text-shadow: 0 0 25px var(--neon-red), 0 0 35px var(--neon-red); }} }}
        .title {{ font-size: 2.2em; font-weight: 900; color: var(--neon-green); text-shadow: var(--shadow-glow) var(--neon-green); letter-spacing: 2px; }}
        .subtitle {{ font-size: 0.8em; color: var(--text-muted); font-family: var(--font-mono); letter-spacing: 1px; }}
        .flash-messages {{ margin-bottom: 20px; }}
        .flash-message {{ padding: 12px 20px; border-radius: 8px; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; border: 2px solid; animation: flash-appear 0.3s ease-out; }}
        @keyframes flash-appear {{ 0% {{ opacity: 0; transform: translateY(-20px); }} 100% {{ opacity: 1; transform: translateY(0); }} }}
        .flash-message.success {{ border-color: var(--neon-green); background: rgba(0, 255, 65, 0.1); color: var(--neon-green); }}
        .flash-message.error {{ border-color: var(--neon-red); background: rgba(255, 0, 64, 0.1); color: var(--neon-red); }}
        .control-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 15px; }}
        .control-panel {{ background: linear-gradient(135deg, var(--accent-bg), var(--secondary-bg)); border: 1px solid var(--border-color); border-radius: 8px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5); transition: all 0.3s ease; }}
        .control-panel:hover {{ border-color: var(--neon-cyan); box-shadow: var(--shadow-glow) var(--neon-cyan); }}
        .panel-header {{ padding: 10px 15px; background: linear-gradient(135deg, var(--secondary-bg), var(--primary-bg)); border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 10px; font-weight: 700; color: var(--neon-cyan); text-shadow: var(--shadow-glow) var(--neon-cyan); letter-spacing: 1px; }}
        .panel-content {{ padding: 8px; }}
        .account-section {{ margin-bottom: 6px; padding: 6px; background: var(--accent-bg); border-radius: 4px; border: 1px solid var(--border-color); }}
        .account-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }}
        .account-name {{ font-size: 1em; font-weight: 700; color: var(--neon-cyan); text-shadow: var(--shadow-glow) var(--neon-cyan); }}
        .status-badge {{ padding: 3px 8px; border-radius: 12px; font-size: 0.75em; font-weight: 700; text-align: center; border: 1px solid; letter-spacing: 0.5px; }}
        .status-badge.active {{ border-color: var(--neon-green); background: rgba(0, 255, 65, 0.2); color: var(--neon-green); }}
        .status-badge.inactive {{ border-color: var(--neon-red); background: rgba(255, 0, 64, 0.2); color: var(--neon-red); }}
        .control-row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .inline-form {{ display: flex; gap: 6px; align-items: center; flex: 1; }}
        .input-group {{ display: flex; flex-direction: column; gap: 3px; min-width: 100px; }}
        .input-label {{ font-size: 0.75em; color: var(--text-muted); font-weight: 700; letter-spacing: 0.5px; }}
        .input-cyber {{ padding: 6px 8px; background: var(--primary-bg); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-family: var(--font-mono); font-size: 0.85em; transition: all 0.3s ease; }}
        .input-cyber:focus {{ outline: none; border-color: var(--neon-green); box-shadow: var(--shadow-glow) var(--neon-green); background: rgba(0, 255, 65, 0.05); }}
        .btn-cyber {{ padding: 6px 12px; border: 1px solid; border-radius: 4px; background: transparent; color: var(--text-primary); font-family: var(--font-primary); font-weight: 700; font-size: 0.8em; cursor: pointer; transition: all 0.3s ease; display: inline-flex; align-items: center; gap: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .btn-cyber:hover {{ transform: translateY(-1px); box-shadow: var(--shadow-glow) currentColor; }}
        .input-cyber option {{ background: var(--primary-bg); color: var(--text-primary); }}
        .btn-primary {{ border-color: var(--neon-green); color: var(--neon-green); }}
        .btn-primary:hover {{ background: var(--neon-green); color: var(--primary-bg); }}
        .btn-danger {{ border-color: var(--neon-red); color: var(--neon-red); }}
        .btn-danger:hover {{ background: var(--neon-red); color: var(--primary-bg); }}
        .btn-warning {{ border-color: var(--neon-purple); color: var(--neon-purple); }}
        .btn-warning:hover {{ background: var(--neon-purple); color: var(--primary-bg); }}
        .btn-quick {{ padding: 4px 8px; margin: 2px; min-width: 60px; font-size: 0.75em; background: transparent; border-color: var(--neon-cyan); color: var(--neon-cyan); opacity: 0.8; }}
        .btn-quick:hover {{ background: var(--neon-cyan); color: var(--primary-bg); opacity: 1; transform: translateY(-1px); }}
        .quick-commands {{ margin-top: 8px; }}
        .quick-commands .control-row {{ justify-content: center; gap: 6px; margin-bottom: 6px; }}
        .status-section {{ display: flex; justify-content: center; margin-bottom: 6px; }}
        .spam-form, .work-form, .reboot-form {{ display: flex; flex-direction: column; gap: 6px; }}
        .reboot-grid {{ display: grid; gap: 10px; }}
        .reboot-section h4 {{ color: var(--neon-cyan); margin-bottom: 8px; font-size: 1em; text-shadow: var(--shadow-glow) var(--neon-cyan); }}
        .sub-accounts-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 6px; }}
        @media (max-width: 768px) {{ .control-grid {{ grid-template-columns: 1fr; }} .title {{ font-size: 1.8em; }} .container {{ padding: 10px; }} }}
    </style>
</head>
<body>
    <canvas class="matrix-bg" id="matrixCanvas"></canvas>
    <div class="container">
        <div class="header">
            <div class="logo"><i class="fas fa-skull"></i><div><div class="title">KARUTA DEEP</div><div class="subtitle">BOT CONTROL MATRIX</div></div></div>
        </div>
        {{% if msg_status %}}
        <div class="flash-messages"><div class="flash-message success"><i class="fas fa-check-circle"></i> {{ msg_status }}</div></div>
        {{% endif %}}
        <div class="control-grid">
            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-terminal"></i><span>MANUAL OPERATIONS</span></div>
                <div class="panel-content">
                    <form method="POST" class="spam-form">
                        <div class="control-row">
                            <div class="input-group" style="flex: 1;"><span class="input-label">MESSAGE</span><input type="text" name="message" placeholder="Enter manual message..." class="input-cyber"></div>
                            <button type="submit" class="btn-cyber btn-primary" style="align-self: flex-end;"><i class="fas fa-paper-plane"></i> SEND</button>
                        </div>
                    </form>
                    <div class="quick-commands">
                        <div class="control-row">
                            <form method="POST" style="display: inline;"><input type="hidden" name="quickmsg" value="kc o:w"><button type="submit" class="btn-cyber btn-quick">kc o:w</button></form>
                            <form method="POST" style="display: inline;"><input type="hidden" name="quickmsg" value="kc o:ef"><button type="submit" class="btn-cyber btn-quick">kc o:ef</button></form>
                            <form method="POST" style="display: inline;"><input type="hidden" name="quickmsg" value="kc o:p"><button type="submit" class="btn-cyber btn-quick">kc o:p</button></form>
                        </div>
                    </div>
                </div>
            </div>
            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-crosshairs"></i><span>AUTO GRAB PROTOCOL</span></div>
                <div class="panel-content">
                    <div class="account-section">
                        <div class="account-header"><span class="account-name">ALPHA NODE (Acc 1)</span><div class="status-badge {grab_status}">{grab_text}</div></div>
                        <form method="POST" class="inline-form">
                            <div class="input-group"><span class="input-label">THRESHOLD</span><input type="number" name="heart_threshold" value="{heart_threshold}" min="1" max="999" class="input-cyber"></div>
                            <button type="submit" name="toggle" value="on" class="btn-cyber {grab_btn_class}"><i class="fas fa-{grab_icon}"></i> {grab_action}</button>
                        </form>
                    </div>
                    <div class="account-section">
                        <div class="account-header"><span class="account-name">BETA NODE (Acc 2)</span><div class="status-badge {grab_status_2}">{grab_text_2}</div></div>
                        <form method="POST" class="inline-form">
                            <div class="input-group"><span class="input-label">THRESHOLD</span><input type="number" name="heart_threshold_2" value="{heart_threshold_2}" min="1" max="999" class="input-cyber"></div>
                            <button type="submit" name="toggle_2" value="on" class="btn-cyber {grab_btn_class_2}"><i class="fas fa-{grab_icon_2}"></i> {grab_action_2}</button>
                        </form>
                    </div>
                    <div class="account-section">
                        <div class="account-header"><span class="account-name">GAMMA NODE (Acc 3)</span><div class="status-badge {grab_status_3}">{grab_text_3}</div></div>
                        <form method="POST" class="inline-form">
                            <div class="input-group"><span class="input-label">THRESHOLD</span><input type="number" name="heart_threshold_3" value="{heart_threshold_3}" min="1" max="999" class="input-cyber"></div>
                            <button type="submit" name="toggle_3" value="on" class="btn-cyber {grab_btn_class_3}"><i class="fas fa-{grab_icon_3}"></i> {grab_action_3}</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-comments"></i><span>SPAM INJECTION</span></div>
                <div class="panel-content">
                    <div class="status-section"><div class="status-badge {spam_status}">{spam_text}</div></div>
                    <form method="POST" class="spam-form">
                        <div class="control-row">
                            <div class="input-group" style="flex: 1;"><span class="input-label">MESSAGE</span><input type="text" name="spammsg" value="{spam_message}" placeholder="Tin nhắn spam..." class="input-cyber"></div>
                            <div class="input-group"><span class="input-label">DELAY (s)</span><input type="number" name="spam_delay" value="{spam_delay}" min="1" max="3600" class="input-cyber"></div>
                        </div>
                        <button type="submit" name="spamtoggle" value="on" class="btn-cyber {spam_btn_class}"><i class="fas fa-{spam_icon}"></i> {spam_action}</button>
                    </form>
                </div>
            </div>
            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-cogs"></i><span>WORK AUTOMATION</span></div>
                <div class="panel-content">
                    <div class="status-section"><div class="status-badge {work_status}">{work_text}</div></div>
                    <form method="POST" class="work-form">
                        <div class="control-row">
                            <div class="input-group" style="flex: 1;"><span class="input-label">ACC DELAY (s)</span><input type="number" name="work_delay_between_acc" value="{work_delay_between_acc}" min="1" max="3600" class="input-cyber"></div>
                            <div class="input-group" style="flex: 1;"><span class="input-label">CYCLE DELAY (s)</span><input type="number" name="work_delay_after_all" value="{work_delay_after_all}" min="1" max="86400" class="input-cyber"></div>
                        </div>
                        <button type="submit" name="auto_work_toggle" value="on" class="btn-cyber {work_btn_class}"><i class="fas fa-{work_icon}"></i> {work_action}</button>
                    </form>
                </div>
            </div>
            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-code"></i><span>CODE INJECTION</span></div>
                <div class="panel-content">
                    <form method="POST" class="spam-form">
                        <div class="control-row">
                            <div class="input-group" style="flex: 1;"><span class="input-label">TARGET ACC</span><select name="acc_index" class="input-cyber">{acc_options}</select></div>
                            <div class="input-group"><span class="input-label">DELAY (s)</span><input type="number" name="delay" value="11" step="0.1" class="input-cyber"></div>
                            <div class="input-group"><span class="input-label">PREFIX</span><input type="text" name="prefix" placeholder="kt n" class="input-cyber"></div>
                        </div>
                        <div class="input-group" style="width: 100%;"><span class="input-label">CODE LIST</span><textarea name="codes" placeholder="Danh sách mã, cách nhau dấu phẩy" rows="2" class="input-cyber"></textarea></div>
                        <button type="submit" name="send_codes" value="1" class="btn-cyber btn-primary"><i class="fas fa-paper-plane"></i> INJECT CODES</button>
                    </form>
                </div>
            </div>
            <div class="control-panel">
                <div class="panel-header"><i class="fas fa-redo"></i><span>AUTO REBOOT CYCLE</span></div>
                <div class="panel-content">
                    <div class="status-section"><div class="status-badge {auto_reboot_status}">{auto_reboot_text}</div></div>
                    <form method="POST" class="reboot-form">
                        <div class="input-group" style="width: 100%;"><span class="input-label">INTERVAL (s)</span><input type="number" name="auto_reboot_delay" value="{auto_reboot_delay}" min="60" max="86400" class="input-cyber"></div>
                        <button type="submit" name="auto_reboot_toggle" value="on" class="btn-cyber {auto_reboot_btn_class}"><i class="fas fa-{auto_reboot_icon}"></i> {auto_reboot_action}</button>
                    </form>
                </div>
            </div>
             <div class="control-panel">
                <div class="panel-header"><i class="fas fa-power-off"></i><span>MANUAL OVERRIDE</span></div>
                <div class="panel-content">
                    <div class="reboot-grid">
                        <div class="reboot-section"><h4>EMERGENCY CONTROLS</h4>
                            <form method="POST" style="display: inline-block;"><button type="submit" name="reboot_target" value="all" class="btn-cyber btn-danger"><i class="fas fa-bomb"></i> REBOOT ALL SYSTEMS</button></form>
                        </div>
                        <div class="reboot-section"><h4>MAIN NODES</h4>
                            <form method="POST" style="display: inline-block; margin-right: 5px;"><button type="submit" name="reboot_target" value="main_1" class="btn-cyber btn-warning"><i class="fas fa-sync"></i> ALPHA</button></form>
                            <form method="POST" style="display: inline-block; margin-right: 5px;"><button type="submit" name="reboot_target" value="main_2" class="btn-cyber btn-warning"><i class="fas fa-sync"></i> BETA</button></form>
                            <form method="POST" style="display: inline-block;"><button type="submit" name="reboot_target" value="main_3" class="btn-cyber btn-warning"><i class="fas fa-sync"></i> GAMMA</button></form>
                        </div>
                        <div class="reboot-section"><h4>SLAVE NODES ({num_bots})</h4><div class="sub-accounts-grid">{sub_account_buttons}</div></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        function createMatrixRain() {{
            const canvas = document.getElementById('matrixCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            const matrix = "アカサタナハマヤラワ0123456789ABCDEF";
            const matrixArray = matrix.split("");
            const fontSize = 10;
            const columns = canvas.width / fontSize;
            const drops = Array.from({{ length: Math.ceil(columns) }}).fill(1);
            function draw() {{
                ctx.fillStyle = 'rgba(0, 0, 0, 0.04)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#0F3';
                ctx.font = fontSize + 'px monospace';
                for (let i = 0; i < drops.length; i++) {{
                    const text = matrixArray[Math.floor(Math.random() * matrixArray.length)];
                    ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                    if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {{
                        drops[i] = 0;
                    }}
                    drops[i]++;
                }}
            }}
            setInterval(draw, 50);
            window.addEventListener('resize', () => {{
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                drops.length = Math.ceil(window.innerWidth / fontSize);
            }});
        }}
        document.addEventListener('DOMContentLoaded', createMatrixRain);
    </script>
</body>
</html>
"""

# --- HÀM XỬ LÝ WEB (ĐÃ CẬP NHẬT CHO GIAO DIỆN MỚI) ---
@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, auto_grab_enabled_2, auto_grab_enabled_3
    global spam_enabled, spam_message, spam_delay, spam_thread
    global heart_threshold, heart_threshold_2, heart_threshold_3
    global auto_work_enabled, work_delay_between_acc, work_delay_after_all
    global auto_reboot_enabled, auto_reboot_delay, auto_reboot_thread, auto_reboot_stop_event
    
    msg_status = ""

    if request.method == "POST":
        # Điều khiển thủ công
        if 'message' in request.form and request.form['message']:
            msg = request.form['message']
            with bots_lock:
                for idx, bot in enumerate(bots):
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, msg)).start()
            msg_status = f"Đã gửi tin nhắn: {msg}"
        elif 'quickmsg' in request.form:
            quickmsg = request.form['quickmsg']
            with bots_lock:
                 for idx, bot in enumerate(bots):
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, quickmsg)).start()
            msg_status = f"Đã gửi lệnh nhanh: {quickmsg}"

        # Điều khiển Auto Grab
        elif 'toggle' in request.form:
            auto_grab_enabled = not auto_grab_enabled
            if 'heart_threshold' in request.form:
                 heart_threshold = int(request.form.get('heart_threshold', 50))
            msg_status = f"Auto Grab Acc 1: {'BẬT' if auto_grab_enabled else 'TẮT'} (Tim: {heart_threshold})"
        elif 'toggle_2' in request.form:
            auto_grab_enabled_2 = not auto_grab_enabled_2
            if 'heart_threshold_2' in request.form:
                 heart_threshold_2 = int(request.form.get('heart_threshold_2', 50))
            msg_status = f"Auto Grab Acc 2: {'BẬT' if auto_grab_enabled_2 else 'TẮT'} (Tim: {heart_threshold_2})"
        elif 'toggle_3' in request.form:
            auto_grab_enabled_3 = not auto_grab_enabled_3
            if 'heart_threshold_3' in request.form:
                 heart_threshold_3 = int(request.form.get('heart_threshold_3', 50))
            msg_status = f"Auto Grab Acc 3: {'BẬT' if auto_grab_enabled_3 else 'TẮT'} (Tim: {heart_threshold_3})"

        # Điều khiển Spam
        elif 'spamtoggle' in request.form:
            spammsg = request.form.get("spammsg", "").strip()
            if not spam_enabled and spammsg:
                spam_enabled = True
                spam_message = spammsg
                spam_delay = int(request.form.get("spam_delay", 10))
                if spam_thread is None or not spam_thread.is_alive():
                    spam_thread = threading.Thread(target=spam_loop, daemon=True)
                    spam_thread.start()
                msg_status = f"Spam BẬT: '{spam_message}' mỗi {spam_delay}s"
            elif spam_enabled:
                spam_enabled = False
                msg_status = "Spam đã TẮT"
            else:
                 msg_status = "Vui lòng nhập tin nhắn để bật Spam!"
        elif "spam_delay" in request.form and 'spamtoggle' not in request.form:
            spam_delay = int(request.form.get("spam_delay", 10))
            spam_message = request.form.get("spammsg", spam_message).strip() # Giữ lại tin nhắn cũ nếu có
            msg_status = f"Đã cập nhật cài đặt spam."

        # Điều khiển Auto Work
        elif 'auto_work_toggle' in request.form:
            auto_work_enabled = not auto_work_enabled
            if auto_work_enabled:
                work_delay_between_acc = int(request.form.get('work_delay_between_acc', 10))
                work_delay_after_all = int(request.form.get('work_delay_after_all', 44100))
            msg_status = f"Auto Work {'BẬT' if auto_work_enabled else 'TẮT'}"
        elif ('work_delay_between_acc' in request.form or 'work_delay_after_all' in request.form) and 'auto_work_toggle' not in request.form:
             work_delay_between_acc = int(request.form.get('work_delay_between_acc', 10))
             work_delay_after_all = int(request.form.get('work_delay_after_all', 44100))
             msg_status = f"Cập nhật delay Auto Work."

        # Điều khiển Auto Reboot
        elif 'auto_reboot_toggle' in request.form:
            auto_reboot_enabled = not auto_reboot_enabled
            if auto_reboot_enabled:
                auto_reboot_delay = int(request.form.get("auto_reboot_delay", 3600))
                if auto_reboot_thread is None or not auto_reboot_thread.is_alive():
                    auto_reboot_stop_event = threading.Event()
                    auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
                    auto_reboot_thread.start()
                msg_status = "Đã BẬT chế độ tự động reboot."
            else:
                if auto_reboot_stop_event: auto_reboot_stop_event.set()
                auto_reboot_thread = None
                msg_status = "Đã TẮT chế độ tự động reboot."
        elif 'auto_reboot_delay' in request.form and 'auto_reboot_toggle' not in request.form:
             auto_reboot_delay = int(request.form.get("auto_reboot_delay"))
             msg_status = f"Cập nhật delay Auto Reboot: {auto_reboot_delay} giây."

        # Điều khiển Manual Reboot
        elif 'reboot_target' in request.form:
            target = request.form['reboot_target']
            if target == "all":
                if main_bot: reboot_bot('main_1')
                time.sleep(1)
                if main_bot_2: reboot_bot('main_2')
                time.sleep(1)
                if main_bot_3: reboot_bot('main_3')
                time.sleep(1)
                for i in range(len(bots)): 
                    reboot_bot(f'sub_{i}')
                    time.sleep(1)
                msg_status = "Đã gửi yêu cầu reboot tất cả bot!"
            else:
                reboot_bot(target)
                msg_status = f"Đã gửi yêu cầu reboot cho {target}!"

        # Điều khiển Gửi mã
        elif 'send_codes' in request.form:
            try:
                acc_idx = int(request.form.get("acc_index"))
                delay_val = float(request.form.get("delay"))
                prefix = request.form.get("prefix")
                codes_list = request.form.get("codes").split(',')
                if acc_idx < len(bots):
                    with bots_lock:
                        for i, code in enumerate(codes_list):
                            final_msg = f"{prefix} {code.strip()}" if prefix else code.strip()
                            threading.Timer(delay_val * i, bots[acc_idx].sendMessage, args=(other_channel_id, final_msg)).start()
                    msg_status = f"Đang gửi {len(codes_list)} mã tới acc {acc_names[acc_idx]}..."
                else:
                    msg_status = "Lỗi: Index của Acc không hợp lệ."
            except Exception as e:
                msg_status = f"Lỗi khi gửi mã: {e}"
    
    # Chuẩn bị biến cho giao diện
    grab_status, grab_text, grab_action, grab_icon, grab_btn_class = ("active", "ONLINE", "DISABLE", "stop", "btn-danger") if auto_grab_enabled else ("inactive", "OFFLINE", "ENABLE", "play", "btn-primary")
    grab_status_2, grab_text_2, grab_action_2, grab_icon_2, grab_btn_class_2 = ("active", "ONLINE", "DISABLE", "stop", "btn-danger") if auto_grab_enabled_2 else ("inactive", "OFFLINE", "ENABLE", "play", "btn-primary")
    grab_status_3, grab_text_3, grab_action_3, grab_icon_3, grab_btn_class_3 = ("active", "ONLINE", "DISABLE", "stop", "btn-danger") if auto_grab_enabled_3 else ("inactive", "OFFLINE", "ENABLE", "play", "btn-primary")
    spam_status, spam_text, spam_action, spam_icon, spam_btn_class = ("active", "ONLINE", "TERMINATE", "stop", "btn-danger") if spam_enabled else ("inactive", "OFFLINE", "ACTIVATE", "play", "btn-primary")
    work_status, work_text, work_action, work_icon, work_btn_class = ("active", "ONLINE", "TERMINATE", "stop", "btn-danger") if auto_work_enabled else ("inactive", "OFFLINE", "INITIATE", "play", "btn-primary")
    auto_reboot_status, auto_reboot_text, auto_reboot_action, auto_reboot_icon, auto_reboot_btn_class = ("active", "ONLINE", "DISABLE", "stop", "btn-danger") if auto_reboot_enabled else ("inactive", "OFFLINE", "ENABLE", "play", "btn-primary")

    acc_options = "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names) if i < len(bots))
    sub_account_buttons = "".join(f'<form method="POST" style="display: inline-block; margin: 2px;"><button type="submit" name="reboot_target" value="sub_{i}" class="btn-cyber btn-warning" style="font-size: 0.7rem; padding: 4px 8px;"><i class="fas fa-sync"></i> {acc_names[i] if i < len(acc_names) else f"NODE {i+1}"}</button></form>' for i in range(len(bots)))

    return render_template_string(HTML_TEMPLATE.format(
        msg_status=msg_status,
        grab_status=grab_status, grab_text=grab_text, grab_action=grab_action, grab_icon=grab_icon, grab_btn_class=grab_btn_class, heart_threshold=heart_threshold,
        grab_status_2=grab_status_2, grab_text_2=grab_text_2, grab_action_2=grab_action_2, grab_icon_2=grab_icon_2, grab_btn_class_2=grab_btn_class_2, heart_threshold_2=heart_threshold_2,
        grab_status_3=grab_status_3, grab_text_3=grab_text_3, grab_action_3=grab_action_3, grab_icon_3=grab_icon_3, grab_btn_class_3=grab_btn_class_3, heart_threshold_3=heart_threshold_3,
        spam_status=spam_status, spam_text=spam_text, spam_action=spam_action, spam_icon=spam_icon, spam_btn_class=spam_btn_class, spam_message=spam_message, spam_delay=spam_delay,
        work_status=work_status, work_text=work_text, work_action=work_action, work_icon=work_icon, work_btn_class=work_btn_class, work_delay_between_acc=work_delay_between_acc, work_delay_after_all=work_delay_after_all,
        auto_reboot_status=auto_reboot_status, auto_reboot_text=auto_reboot_text, auto_reboot_action=auto_reboot_action, auto_reboot_icon=auto_reboot_icon, auto_reboot_btn_class=auto_reboot_btn_class, auto_reboot_delay=auto_reboot_delay,
        acc_options=acc_options, num_bots=len(bots), sub_account_buttons=sub_account_buttons
    ))

# --- KHỞI CHẠY CHƯƠNG TRÌNH (GIỮ NGUYÊN CỦA BẠN) ---
if __name__ == "__main__":
    print("Đang khởi tạo các bot...")
    with bots_lock:
        if main_token:
            main_bot = create_bot(main_token, is_main=True)
        if main_token_2:
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
        if main_token_3:
            main_bot_3 = create_bot(main_token_3, is_main_3=True)

        for token in tokens:
            if token.strip():
                bots.append(create_bot(token.strip(), is_main=False))
    print("Tất cả các bot đã được khởi tạo.")

    print("Đang khởi tạo các luồng nền...")
    threading.Thread(target=spam_loop, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    # Khởi tạo luồng auto_reboot nếu cần
    if auto_reboot_enabled:
        auto_reboot_stop_event = threading.Event()
        auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
        auto_reboot_thread.start()
    print("Các luồng nền đã sẵn sàng.")

    port = int(os.environ.get("PORT", 8080))
    print(f"Khởi động Web Server tại cổng {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)