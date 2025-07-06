# multi_bot_control_final_fix.py
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
bots = []
main_bot, main_bot_2, main_bot_3 = None, None, None
auto_grab_enabled, auto_grab_enabled_2, auto_grab_enabled_3 = False, False, False
heart_threshold, heart_threshold_2, heart_threshold_3 = 50, 50, 50
last_drop_msg_id = ""
acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Silent",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", 
    "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "HellNBack"]
spam_enabled, spam_message, spam_delay = False, "", 10
auto_work_enabled, work_delay_between_acc, work_delay_after_all = False, 10, 44100

auto_reboot_enabled = False
auto_reboot_delay = 3600
auto_reboot_thread = None
auto_reboot_stop_event = None

bots_lock = threading.Lock()

def reboot_bot(target_id):
    """Khởi động lại một bot dựa trên ID định danh của nó."""
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
                    bots[index] = create_bot(token_to_reboot.strip())
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
                user = resp.raw["user"]
                bot_type = "(Acc chính 1)" if is_main else "(Acc chính 2)" if is_main_2 else "(Acc chính 3)" if is_main_3 else "(Acc phụ)"
                print(f"Đã đăng nhập: {user['username']}#{user['discriminator']} {bot_type}")
            except Exception as e:
                # Nếu token sai, lỗi sẽ xảy ra ở đây.
                print(f"!!! LỖI NGHIÊM TRỌNG KHI KHỞI TẠO BOT. TOKEN CÓ THỂ SAI HOẶC BỊ VÔ HIỆU HÓA. Lỗi: {e}")


    # ... (Toàn bộ phần code on_message của bạn được giữ nguyên) ...
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
                            for msg_inner in messages:
                                author_id = msg_inner.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                    desc = msg_inner["embeds"][0].get("description", "")
                                    print(f"\n[Bot 1] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 1] ===== Kết thúc tin nhắn =====\n")
                                    lines = desc.split('\n')
                                    heart_numbers = []
                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            heart_numbers.append(int(matches[1]))
                                            print(f"[Bot 1] Dòng {i+1} số tim: {int(matches[1])}")
                                        else:
                                            heart_numbers.append(0)
                                            print(f"[Bot 1] Dòng {i+1} không tìm thấy số tim, mặc định 0")
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
        def on_message_2(resp):
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
                            for msg_inner in messages:
                                author_id = msg_inner.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                    desc = msg_inner["embeds"][0].get("description", "")
                                    print(f"\n[Bot 2] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 2] ===== Kết thúc tin nhắn =====\n")
                                    lines = desc.split('\n')
                                    heart_numbers = []
                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            heart_numbers.append(int(matches[1]))
                                            print(f"[Bot 2] Dòng {i+1} số tim: {int(matches[1])}")
                                        else:
                                            heart_numbers.append(0)
                                            print(f"[Bot 2] Dòng {i+1} không tìm thấy số tim, mặc định 0")
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
        def on_message_3(resp):
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
                            for msg_inner in messages:
                                author_id = msg_inner.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                    desc = msg_inner["embeds"][0].get("description", "")
                                    print(f"\n[Bot 3] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 3] ===== Kết thúc tin nhắn =====\n")
                                    lines = desc.split('\n')
                                    heart_numbers = []
                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            heart_numbers.append(int(matches[1]))
                                            print(f"[Bot 3] Dòng {i+1} số tim: {int(matches[1])}")
                                        else:
                                            heart_numbers.append(0)
                                            print(f"[Bot 3] Dòng {i+1} không tìm thấy số tim, mặc định 0")
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
    headers = {"Authorization": token, "Content-Type": "application/json"}
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
            payload = {"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "a", "data": {"component_type": 2, "custom_id": custom_id}}
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
            if r.status_code == 204: print(f"[Work Acc {acc_index}] Click tick thành công!")
            else: print(f"[Work Acc {acc_index}] Click thất bại! Mã lỗi: {r.status_code}, Nội dung: {r.text}")
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
                    first_5, last_5 = card_codes[:5], card_codes[-5:]
                    print(f"[Work Acc {acc_index}] Mã đầu: {', '.join(first_5)}")
                    print(f"[Work Acc {acc_index}] Mã cuối: {', '.join(last_5)}")
                    for i, code in enumerate(last_5):
                        suffix = chr(97 + i)
                        time.sleep(2 if i == 0 else 1.5)
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
                    bot_name = acc_names[idx] if idx < len(acc_names) else f"Acc Phụ {idx + 1}"
                    bot.sendMessage(spam_channel_id, spam_message)
                    print(f"[{bot_name}] đã gửi spam: {spam_message}")
                    time.sleep(2)
                except Exception as e:
                    bot_name_for_error = acc_names[idx] if idx < len(acc_names) else f"Acc Phụ {idx + 1}"
                    print(f"!!! LỖI SPAM từ {bot_name_for_error}: {e}")
        time.sleep(spam_delay)


def keep_alive():
    while True:
        try:
            time.sleep(random.randint(60, 120))
        except:
            pass

app = Flask(__name__)
HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Karuta Deep</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; }} body {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); min-height: 100vh; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #ffffff; margin: 0; padding: 20px 0; }}
        .header-section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); }}
        .header-section h1 {{ font-size: 2.5rem; font-weight: 700; background: linear-gradient(45deg, #00d4ff, #ff9500); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.5rem; text-shadow: 0 0 20px rgba(0, 212, 255, 0.3); }}
        .header-section p {{ font-size: 1.1rem; color: #b0b0b0; margin-bottom: 0; }} .control-card {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); transition: all 0.3s ease; overflow: hidden; margin-bottom: 2rem; }}
        .control-card:hover {{ transform: translateY(-5px); box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4); border-color: rgba(0, 212, 255, 0.3); }} .control-card .card-header {{ background: linear-gradient(45deg, rgba(0, 212, 255, 0.2), rgba(255, 149, 0, 0.2)); border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding: 1.5rem; border-radius: 20px 20px 0 0; }}
        .control-card .card-header h5 {{ color: #ffffff; font-weight: 600; margin: 0; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); }} .control-card .card-body {{ padding: 1.5rem; }}
        .form-control {{ background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; color: #ffffff; padding: 12px 16px; font-size: 1rem; transition: all 0.3s ease; }}
        .form-control:focus {{ background: rgba(255, 255, 255, 0.15); border-color: #00d4ff; box-shadow: 0 0 0 0.2rem rgba(0, 212, 255, 0.25); color: #ffffff; }}
        .form-control::placeholder {{ color: #b0b0b0; }} .form-select {{ background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; color: #ffffff; padding: 12px 16px; font-size: 1rem; transition: all 0.3s ease; }}
        .form-select:focus {{ background: rgba(255, 255, 255, 0.15); border-color: #00d4ff; box-shadow: 0 0 0 0.2rem rgba(0, 212, 255, 0.25); color: #ffffff; }}
        .form-select option {{ background: #1a1a2e; color: #ffffff; }} .form-label {{ color: #ffffff; font-weight: 500; margin-bottom: 0.5rem; }}
        .input-group-text {{ background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; border-radius: 12px 0 0 12px; }}
        .btn {{ border-radius: 12px; padding: 12px 24px; font-weight: 500; font-size: 1rem; transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 0.5px; border: none; position: relative; overflow: hidden; }}
        .btn::before {{ content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent); transition: left 0.5s ease; }}
        .btn:hover::before {{ left: 100%; }} .btn-primary {{ background: linear-gradient(45deg, #00d4ff, #0099cc); color: #ffffff; box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4); }}
        .btn-primary:hover {{ background: linear-gradient(45deg, #0099cc, #00d4ff); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 212, 255, 0.6); }} .btn-warning {{ background: linear-gradient(45deg, #ffc107, #ff9800); color: #1a1a2e; box-shadow: 0 4px 15px rgba(255, 193, 7, 0.4); }}
        .btn-warning:hover {{ background: linear-gradient(45deg, #ff9800, #ffc107); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255, 193, 7, 0.6); }} .btn-success {{ background: linear-gradient(45deg, #28a745, #20c997); color: #ffffff; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4); }}
        .btn-success:hover {{ background: linear-gradient(45deg, #20c997, #28a745); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(40, 167, 69, 0.6); }} .btn-danger {{ background: linear-gradient(45deg, #dc3545, #e83e8c); color: #ffffff; box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4); }}
        .btn-danger:hover {{ background: linear-gradient(45deg, #e83e8c, #dc3545); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(220, 53, 69, 0.6); }} .status-indicator {{ display: flex; align-items: center; margin-bottom: 1rem; }}
        .status-badge {{ display: inline-flex; align-items: center; padding: 8px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; transition: all 0.3s ease; }}
        .status-active {{ background: linear-gradient(45deg, #28a745, #20c997); color: #ffffff; box-shadow: 0 0 20px rgba(40, 167, 69, 0.3); }}
        .status-inactive {{ background: linear-gradient(45deg, #dc3545, #e83e8c); color: #ffffff; box-shadow: 0 0 20px rgba(220, 53, 69, 0.3); }}
        .alert {{ background: rgba(40, 167, 69, 0.2); border: 1px solid rgba(40, 167, 69, 0.3); border-radius: 12px; color: #ffffff; backdrop-filter: blur(10px); margin-bottom: 1rem; }}
        .alert-success {{ background: rgba(40, 167, 69, 0.2); border-color: rgba(40, 167, 69, 0.3); }}
        @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .control-card {{ animation: fadeInUp 0.6s ease-out; }} .quick-commands {{ margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid rgba(255, 255, 255, 0.1); }}
        .quick-commands h6 {{ color: #ffffff; font-weight: 600; margin-bottom: 1rem; }} .heart-threshold {{ margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid rgba(255, 255, 255, 0.1); }}
        .heart-threshold h6 {{ color: #ffffff; font-weight: 600; margin-bottom: 1rem; }}
        @media (max-width: 768px) {{ .header-section {{ padding: 1.5rem; margin-bottom: 1.5rem; }} .header-section h1 {{ font-size: 2rem; }} .control-card .card-header, .control-card .card-body {{ padding: 1rem; }} .btn {{ padding: 10px 20px; font-size: 0.9rem; }} }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row"><div class="col-12"><div class="header-section">
            <h1 class="text-center mb-0"><i class="fas fa-robot me-3"></i> Karuta Deep</h1>
            <p class="text-center text-muted">Quản lý bot Discord với giao diện hiện đại</p>
        </div></div></div>
        {alert_section}
        <div class="row g-4">
            <div class="col-12"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-check-circle me-2"></i>Chẩn đoán & Kiểm tra</h5></div>
                <div class="card-body text-center">
                    <p class="text-muted">Nếu bot không hoạt động, hãy nhấn nút này để kiểm tra tất cả các tài khoản. Xem kết quả trong cửa sổ console.</p>
                    <form method="POST">
                        <button name="check_all_bots" value="1" type="submit" class="btn btn-warning">
                            <i class="fas fa-stethoscope me-2"></i>Kiểm tra Toàn bộ Bot
                        </button>
                    </form>
                </div>
            </div></div>

            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-paper-plane me-2"></i>Điều khiển bot nhắn tin (Acc phụ)</h5></div>
                <div class="card-body">
                    <form method="POST" class="mb-4"><div class="input-group">
                        <input type="text" class="form-control" name="message" placeholder="Nhập nội dung tin nhắn...">
                        <button class="btn btn-primary" type="submit"><i class="fas fa-send me-1"></i>Gửi thủ công</button>
                    </div></form>
                    <div class="quick-commands"><h6 class="mb-3">Menu nhanh</h6><form method="POST"><div class="input-group">
                        <select name="quickmsg" class="form-select">
                            <option value="kc o:w">kc o:w</option><option value="kc o:ef">kc o:ef</option><option value="kc o:p">kc o:p</option>
                            <option value="kc e:1">kc e:1</option><option value="kc e:2">kc e:2</option><option value="kc e:3">kc e:3</option>
                            <option value="kc e:4">kc e:4</option><option value="kc e:5">kc e:5</option><option value="kc e:6">kc e:6</option><option value="kc e:7">kc e:7</option>
                        </select>
                        <button type="submit" class="btn btn-success"><i class="fas fa-bolt me-1"></i>Gửi</button>
                    </div></form></div>
                </div>
            </div>