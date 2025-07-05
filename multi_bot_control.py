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
tokens = os.getenv("TOKENS").split(",") if os.getenv("TOKENS") else []

# --- ID KÊNH (ĐÃ CẬP NHẬT) ---
main_channel_id = "1386973916563767396"
other_channel_id = "1387406577040101417"
ktb_channel_id = "1376777071279214662"
spam_channel_id = "1388802151723302912"
work_channel_id = "1389250541590413363"
karuta_id = "646937666251915264"
karibbit_id = "1274445226064220273"


# --- BIẾN TRẠNG THÁI ---
bots = []
main_bot = None
main_bot_2 = None
auto_grab_enabled = False
auto_grab_enabled_2 = False
heart_threshold = 50
heart_threshold_2 = 50
last_drop_msg_id = ""

# Danh sách tên các acc (ĐÃ CẬP NHẬT)
acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent", 
    "sly_dd" # Tên này tương ứng với main_bot (Acc Chính 1)
]


spam_enabled = False
spam_message = ""
spam_delay = 10

auto_work_enabled = False
work_delay_between_acc = 10
work_delay_after_all = 44100

bots_lock = threading.Lock()

# =================================================================
# === HÀM MỚI: TỰ ĐỘNG KẾT NỐI LẠI (AUTO-RECONNECT) ===
# =================================================================
def run_bot_with_reconnect(bot, bot_name):
    """Chạy bot trong một vòng lặp vô tận và tự động kết nối lại khi có lỗi."""
    while True:
        try:
            print(f"[{bot_name}] Đang kết nối gateway...")
            bot.gateway.run(auto_reconnect=True)
        except Exception as e:
            print(f"[{bot_name}] LỖI GATEWAY NGHIÊM TRỌNG: {e}. Đang thử kết nối lại sau 5 giây...")
        time.sleep(5)


# =================================================================
# === HÀM TẠO BOT (ĐÃ CẬP NHẬT ĐỂ DÙNG RECONNECT) ===
# =================================================================
def create_bot(token, bot_name, is_main=False, is_main_2=False):
    """Hàm tạo và khởi chạy một bot với cơ chế reconnect."""
    if not token or not token.strip():
        print(f"[{bot_name}] Bỏ qua vì token rỗng.")
        return None
    
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                print(f"Đã đăng nhập: {user_id} ({bot_name})")
            except Exception as e:
                print(f"[{bot_name}] Lỗi lấy user_id: {e}")

    # --- Logic on_message cho Acc Chính 1 ---
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
                        print(f"\n[{bot_name}] Phát hiện tự drop! Đọc tin nhắn Karibbit...")
                        last_drop_msg_id = msg["id"]

                        def read_karibbit():
                            time.sleep(0.5)
                            try:
                                messages = bot.getMessages(main_channel_id, num=5).json()
                                for msg_item in messages:
                                    author_id = msg_item.get("author", {}).get("id")
                                    if author_id == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                        desc = msg_item["embeds"][0].get("description", "")
                                        print(f"[{bot_name}] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[{bot_name}] ===== Kết thúc tin nhắn =====")
                                        lines = desc.split('\n')
                                        heart_numbers = []
                                        for i, line in enumerate(lines[:3]):
                                            matches = re.findall(r'`([^`]*)`', line)
                                            if len(matches) >= 2 and matches[1].isdigit():
                                                heart_numbers.append(int(matches[1]))
                                            else:
                                                heart_numbers.append(0)
                                        
                                        if sum(heart_numbers) == 0:
                                            print(f"[{bot_name}] Không có số tim nào, bỏ qua.\n")
                                        else:
                                            max_num = max(heart_numbers)
                                            if max_num < heart_threshold:
                                                print(f"[{bot_name}] Số tim lớn nhất {max_num} < {heart_threshold}, không grab!\n")
                                            else:
                                                max_index = heart_numbers.index(max_num)
                                                emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                                delay = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}[emoji]
                                                print(f"[{bot_name}] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                                def grab():
                                                    try:
                                                        bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                        bot.sendMessage(ktb_channel_id, "kt b")
                                                    except Exception as e:
                                                        print(f"[{bot_name}] Lỗi khi grab: {e}")
                                                threading.Timer(delay, grab).start()
                                        return 
                            except Exception as e:
                                print(f"[{bot_name}] Lỗi khi đọc tin nhắn Karibbit: {e}")
                        threading.Thread(target=read_karibbit).start()

    # --- Logic on_message cho Acc Chính 2 ---
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
                        print(f"\n[{bot_name}] Phát hiện tự drop! Đọc tin nhắn Karibbit...")
                        last_drop_msg_id = msg["id"]

                        def read_karibbit_2():
                            time.sleep(0.5)
                            try:
                                messages = bot.getMessages(main_channel_id, num=5).json()
                                for msg_item in messages:
                                    author_id = msg_item.get("author", {}).get("id")
                                    if author_id == karibbit_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                        desc = msg_item["embeds"][0].get("description", "")
                                        print(f"[{bot_name}] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[{bot_name}] ===== Kết thúc tin nhắn =====")
                                        lines = desc.split('\n')
                                        heart_numbers = []
                                        for i, line in enumerate(lines[:3]):
                                            matches = re.findall(r'`([^`]*)`', line)
                                            if len(matches) >= 2 and matches[1].isdigit():
                                                heart_numbers.append(int(matches[1]))
                                            else:
                                                heart_numbers.append(0)

                                        if sum(heart_numbers) == 0:
                                            print(f"[{bot_name}] Không có số tim nào, bỏ qua.\n")
                                        else:
                                            max_num = max(heart_numbers)
                                            if max_num < heart_threshold_2:
                                                print(f"[{bot_name}] Số tim lớn nhất {max_num} < {heart_threshold_2}, không grab!\n")
                                            else:
                                                max_index = heart_numbers.index(max_num)
                                                emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                                delay = {"1️⃣": 0.8, "2️⃣": 1.8, "3️⃣": 2.5}[emoji]
                                                print(f"[{bot_name}] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                                def grab_2():
                                                    try:
                                                        bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                        bot.sendMessage(ktb_channel_id, "kt b")
                                                    except Exception as e:
                                                        print(f"[{bot_name}] Lỗi khi grab: {e}")
                                                threading.Timer(delay, grab_2).start()
                                        return
                            except Exception as e:
                                print(f"[{bot_name}] Lỗi khi đọc tin nhắn Karibbit: {e}")
                        threading.Thread(target=read_karibbit_2).start()

    threading.Thread(target=run_bot_with_reconnect, args=(bot, bot_name), daemon=True).start()
    return bot

# =================================================================
# === CÁC HÀM CHỨC NĂNG (ĐÃ CẬP NHẬT) ===
# =================================================================
def reboot_bot(target_id):
    """Khởi động lại một bot dựa trên ID định danh của nó (vd: 'main_1', 'sub_2')."""
    global main_bot, main_bot_2, bots

    with bots_lock:
        print(f"[Reboot] Nhận được yêu cầu reboot cho target: {target_id}")
        if target_id == 'main_1' and main_bot:
            print("[Reboot] Đang xử lý Acc Chính 1...")
            try: main_bot.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 1: {e}")
            main_bot = create_bot(main_token, "Acc Chính 1 (Rebooted)", is_main=True)
            print("[Reboot] Acc Chính 1 đã được khởi động lại.")

        elif target_id == 'main_2' and main_bot_2:
            print("[Reboot] Đang xử lý Acc Chính 2...")
            try: main_bot_2.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 2: {e}")
            main_bot_2 = create_bot(main_token_2, "Acc Chính 2 (Rebooted)", is_main_2=True)
            print("[Reboot] Acc Chính 2 đã được khởi động lại.")

        elif target_id.startswith('sub_'):
            try:
                index = int(target_id.split('_')[1])
                if 0 <= index < len(bots):
                    print(f"[Reboot] Đang xử lý Acc Phụ {index}...")
                    try: bots[index].gateway.close()
                    except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Phụ {index}: {e}")
                    token_to_reboot = tokens[index]
                    bot_name = acc_names[index] if index < len(acc_names) else f"Acc Phụ {index}"
                    bots[index] = create_bot(token_to_reboot.strip(), f"{bot_name} (Rebooted)", is_main=False)
                    print(f"[Reboot] Acc Phụ {index} đã được khởi động lại.")
                else:
                    print(f"[Reboot] Index không hợp lệ: {index}")
            except (ValueError, IndexError) as e:
                print(f"[Reboot] Lỗi xử lý target Acc Phụ: {e}")
        else:
            print(f"[Reboot] Target không xác định: {target_id}")

def run_work_bot(token, acc_index):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = { "Authorization": token, "Content-Type": "application/json" }
    step = {"value": 0}

    def send_command(command):
        print(f"[Work Acc {acc_index}] Gửi lệnh '{command}'...")
        bot.sendMessage(work_channel_id, command)

    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            payload = {"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "a", "data": {"component_type": 2, "custom_id": custom_id}}
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
            if r.status_code != 204:
                print(f"[Work Acc {acc_index}] Click thất bại! Mã lỗi: {r.status_code}, Nội dung: {r.text}")
        except Exception as e:
            print(f"[Work Acc {acc_index}] Lỗi click tick: {str(e)}")

    @bot.gateway.command
    def on_message(resp):
        if resp.event.message:
            m = resp.parsed.auto()
            if str(m.get('channel_id')) != work_channel_id: return
            author_id = str(m.get('author', {}).get('id', ''))
            guild_id = m.get('guild_id')

            if step["value"] == 0 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', '')
                card_codes = re.findall(r'\b\w{6}\b', desc)
                if card_codes and len(card_codes) >= 10:
                    first_5, last_5 = card_codes[:5], card_codes[-5:]
                    print(f"[Work Acc {acc_index}] Mã đầu: {', '.join(first_5)}, Mã cuối: {', '.join(last_5)}")
                    for i, code in enumerate(last_5 + first_5):
                        time.sleep(1.5 + (0.5 if i == 0 else 0))
                        bot.sendMessage(work_channel_id, f"kjw {code} {chr(97 + i)}")
                    time.sleep(1); send_command("kn"); step["value"] = 1
            elif step["value"] == 1 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', '')
                lines = desc.split('\n')
                if len(lines) >= 2 and (match := re.search(r'\d+\.\s*`([^`]+)`', lines[1])):
                    resource = match.group(1)
                    print(f"[Work Acc {acc_index}] Tài nguyên chọn: {resource}")
                    time.sleep(2)
                    bot.sendMessage(work_channel_id, f"kjn `{resource}` a b c d e")
                    time.sleep(1); send_command("kw"); step["value"] = 2
            elif step["value"] == 2 and author_id == karuta_id and 'components' in m:
                message_id = m['id']
                application_id = m.get('application_id', karuta_id)
                if 'components' in m and m['components']:
                    for comp in m['components']:
                        if comp.get('components'):
                            for btn in comp['components']:
                                if btn.get('custom_id'):
                                    click_tick(work_channel_id, message_id, btn['custom_id'], application_id, guild_id)
                                    step["value"] = 3; bot.gateway.close(); return

    print(f"[Work Acc {acc_index}] Bắt đầu hoạt động...")
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    time.sleep(3); send_command("kc o:ef")
    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout: time.sleep(1)
    bot.gateway.close()
    print(f"[Work Acc {acc_index}] Đã hoàn thành hoặc hết thời gian.")

def auto_work_loop():
    global auto_work_enabled
    while True:
        if auto_work_enabled:
            print("\n[Auto Work] Bắt đầu chu trình làm việc...")
            with bots_lock: current_tokens = tokens.copy()
            for i, token in enumerate(current_tokens):
                if token.strip():
                    print(f"[Auto Work] Đang chạy acc {i+1}...")
                    run_work_bot(token.strip(), i+1)
                    if i < len(current_tokens) - 1:
                        print(f"[Auto Work] Acc {i+1} xong, chờ {work_delay_between_acc} giây...")
                        time.sleep(work_delay_between_acc)
            print(f"[Auto Work] Hoàn thành tất cả acc, chờ {work_delay_after_all / 3600:.1f} giờ để lặp lại...")
            time.sleep(work_delay_after_all)
        else:
            time.sleep(10)

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Deep</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); min-height: 100vh; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #ffffff; margin: 0; padding: 20px 0; }}
        .header-section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); }}
        .header-section h1 {{ font-size: 2.5rem; font-weight: 700; background: linear-gradient(45deg, #00d4ff, #ff9500); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.5rem; text-shadow: 0 0 20px rgba(0, 212, 255, 0.3); }}
        .header-section p {{ font-size: 1.1rem; color: #b0b0b0; margin-bottom: 0; }}
        .control-card {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); transition: all 0.3s ease; overflow: hidden; margin-bottom: 2rem; }}
        .control-card:hover {{ transform: translateY(-5px); box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4); border-color: rgba(0, 212, 255, 0.3); }}
        .control-card .card-header {{ background: linear-gradient(45deg, rgba(0, 212, 255, 0.2), rgba(255, 149, 0, 0.2)); border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding: 1.5rem; border-radius: 20px 20px 0 0; }}
        .control-card .card-header h5 {{ color: #ffffff; font-weight: 600; margin: 0; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); }}
        .control-card .card-body {{ padding: 1.5rem; }}
        .form-control, .form-select {{ background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; color: #ffffff; padding: 12px 16px; font-size: 1rem; transition: all 0.3s ease; }}
        .form-control:focus, .form-select:focus {{ background: rgba(255, 255, 255, 0.15); border-color: #00d4ff; box-shadow: 0 0 0 0.2rem rgba(0, 212, 255, 0.25); color: #ffffff; }}
        .form-control::placeholder {{ color: #b0b0b0; }}
        .form-select option {{ background: #1a1a2e; color: #ffffff; }}
        .form-label {{ color: #ffffff; font-weight: 500; margin-bottom: 0.5rem; }}
        .input-group-text {{ background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; border-radius: 12px 0 0 12px; }}
        .btn {{ border-radius: 12px; padding: 12px 24px; font-weight: 500; font-size: 1rem; transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 0.5px; border: none; position: relative; overflow: hidden; }}
        .btn::before {{ content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent); transition: left 0.5s ease; }}
        .btn:hover::before {{ left: 100%; }}
        .btn-primary {{ background: linear-gradient(45deg, #00d4ff, #0099cc); color: #ffffff; box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4); }}
        .btn-primary:hover {{ background: linear-gradient(45deg, #0099cc, #00d4ff); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 212, 255, 0.6); }}
        .btn-warning {{ background: linear-gradient(45deg, #ffc107, #ff9800); color: #1a1a2e; box-shadow: 0 4px 15px rgba(255, 193, 7, 0.4); }}
        .btn-warning:hover {{ background: linear-gradient(45deg, #ff9800, #ffc107); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255, 193, 7, 0.6); }}
        .btn-success {{ background: linear-gradient(45deg, #28a745, #20c997); color: #ffffff; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4); }}
        .btn-success:hover {{ background: linear-gradient(45deg, #20c997, #28a745); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(40, 167, 69, 0.6); }}
        .btn-danger {{ background: linear-gradient(45deg, #dc3545, #e83e8c); color: #ffffff; box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4); }}
        .btn-danger:hover {{ background: linear-gradient(45deg, #e83e8c, #dc3545); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(220, 53, 69, 0.6); }}
        .status-indicator {{ display: flex; align-items: center; margin-bottom: 1rem; }}
        .status-badge {{ display: inline-flex; align-items: center; padding: 8px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; transition: all 0.3s ease; }}
        .status-active {{ background: linear-gradient(45deg, #28a745, #20c997); color: #ffffff; box-shadow: 0 0 20px rgba(40, 167, 69, 0.3); }}
        .status-inactive {{ background: linear-gradient(45deg, #dc3545, #e83e8c); color: #ffffff; box-shadow: 0 0 20px rgba(220, 53, 69, 0.3); }}
        .alert {{ background: rgba(40, 167, 69, 0.2); border: 1px solid rgba(40, 167, 69, 0.3); border-radius: 12px; color: #ffffff; backdrop-filter: blur(10px); margin-bottom: 1rem; }}
        .alert-success {{ background: rgba(40, 167, 69, 0.2); border-color: rgba(40, 167, 69, 0.3); }}
        @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .control-card {{ animation: fadeInUp 0.6s ease-out; }}
        .quick-commands, .heart-threshold {{ margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid rgba(255, 255, 255, 0.1); }}
        .quick-commands h6, .heart-threshold h6 {{ color: #ffffff; font-weight: 600; margin-bottom: 1rem; }}
        @media (max-width: 768px) {{ .header-section {{ padding: 1.5rem; margin-bottom: 1.5rem; }} .header-section h1 {{ font-size: 2rem; }} .control-card .card-header, .control-card .card-body {{ padding: 1rem; }} .btn {{ padding: 10px 20px; font-size: 0.9rem; }} }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row"><div class="col-12"><div class="header-section"><h1 class="text-center mb-0"><i class="fas fa-robot me-3"></i> Karuta Deep</h1><p class="text-center text-muted">Quản lý bot Discord với giao diện hiện đại</p></div></div></div>
        {alert_section}
        <div class="row g-4">
            <div class="col-lg-6"><div class="control-card"><div class="card-header"><h5 class="mb-0"><i class="fas fa-paper-plane me-2"></i> Điều khiển bot nhắn tin</h5></div><div class="card-body"><form method="POST" class="mb-4"><div class="input-group"><input type="text" class="form-control" name="message" placeholder="Nhập nội dung tin nhắn..."><button class="btn btn-primary" type="submit"><i class="fas fa-send me-1"></i>Gửi thủ công</button></div></form><div class="quick-commands"><h6 class="mb-3">Menu nhanh</h6><form method="POST"><div class="input-group"><select name="quickmsg" class="form-select"><option value="kc o:w">kc o:w</option><option value="kc o:ef">kc o:ef</option><option value="kc o:p">kc o:p</option><option value="kc e:1">kc e:1</option><option value="kc e:2">kc e:2</option><option value="kc e:3">kc e:3</option><option value="kc e:4">kc e:4</option><option value="kc e:5">kc e:5</option><option value="kc e:6">kc e:6</option><option value="kc e:7">kc e:7</option></select><button type="submit" class="btn btn-success"><i class="fas fa-bolt me-1"></i>Gửi</button></div></form></div></div></div></div>
            <div class="col-lg-6"><div class="control-card"><div class="card-header"><h5 class="mb-0"><i class="fas fa-briefcase me-2"></i> Auto Work</h5></div><div class="card-body"><div class="status-indicator mb-3"><span class="status-badge {auto_work_status}"><i class="fas fa-circle me-1"></i> {auto_work_text}</span></div><form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="auto_work_toggle" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="auto_work_toggle" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></form><div class="mt-2"><small class="text-muted"><i class="fas fa-info-circle me-1"></i> Tự động làm việc cho tất cả account</small></div></div></div></div>
            <div class="col-lg-6"><div class="control-card"><div class="card-header"><h5 class="mb-0"><i class="fas fa-magic me-2"></i> Auto Grab - Acc Chính 1</h5></div><div class="card-body"><div class="status-indicator mb-3"><span class="status-badge {auto_grab_status}"><i class="fas fa-circle me-1"></i> {auto_grab_text}</span></div><form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="toggle" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="toggle" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></form><div class="heart-threshold"><h6 class="mb-3">Thiết lập mức tim tiêu chuẩn</h6><form method="POST"><div class="input-group"><span class="input-group-text"><i class="fas fa-heart text-danger"></i></span><input type="number" class="form-control" name="heart_threshold" value="{heart_threshold}" min="0" placeholder="Mức tim"><button type="submit" class="btn btn-primary"><i class="fas fa-save me-1"></i>Cập nhật</button></div></form></div></div></div></div>
            <div class="col-lg-6"><div class="control-card"><div class="card-header"><h5 class="mb-0"><i class="fas fa-magic me-2"></i> Auto Grab - Acc Chính 2</h5></div><div class="card-body"><div class="status-indicator mb-3"><span class="status-badge {auto_grab_status_2}"><i class="fas fa-circle me-1"></i> {auto_grab_text_2}</span></div><form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="toggle_2" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="toggle_2" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></form><div class="heart-threshold"><h6 class="mb-3">Thiết lập mức tim tiêu chuẩn</h6><form method="POST"><div class="input-group"><span class="input-group-text"><i class="fas fa-heart text-danger"></i></span><input type="number" class="form-control" name="heart_threshold_2" value="{heart_threshold_2}" min="0" placeholder="Mức tim"><button type="submit" class="btn btn-primary"><i class="fas fa-save me-1"></i>Cập nhật</button></div></form></div><div class="mt-2"><small class="text-muted"><i class="fas fa-info-circle me-1"></i> Delay grab chậm hơn 0.3s so với Acc chính 1</small></div></div></div></div>
            <div class="col-12"><div class="control-card"><div class="card-header"><h5 class="mb-0"><i class="fas fa-code me-2"></i> Gửi danh sách mã theo acc chọn</h5></div><div class="card-body"><form method="POST"><div class="row g-3"><div class="col-md-6"><label class="form-label">Chọn acc:</label><select name="acc_index" class="form-select">{acc_options}</select></div><div class="col-md-6"><label class="form-label">Thời gian cách nhau (giây):</label><input type="number" step="0.1" name="delay" class="form-control" value="11" placeholder="11"></div><div class="col-12"><label class="form-label">Nội dung mẫu:</label><input type="text" name="prefix" class="form-control" placeholder="vd: kt n"></div><div class="col-12"><label class="form-label">Danh sách mã:</label><textarea name="codes" class="form-control" rows="4" placeholder="Danh sách mã, cách nhau dấu phẩy hoặc xuống dòng"></textarea></div><div class="col-12"><button type="submit" name="send_codes" value="1" class="btn btn-primary btn-lg"><i class="fas fa-paper-plane me-2"></i>Gửi danh sách mã</button></div></div></form></div></div></div>
            <div class="col-12"><div class="control-card"><div class="card-header"><h5 class="mb-0"><i class="fas fa-repeat me-2"></i> Spam Control</h5></div><div class="card-body"><div class="status-indicator mb-3"><span class="status-badge {spam_status}"><i class="fas fa-circle me-1"></i> {spam_text}</span></div><form method="POST"><div class="row g-3"><div class="col-md-6"><label class="form-label">Nội dung spam:</label><input type="text" name="spammsg" class="form-control" placeholder="Nội dung spam" value="{spam_message}"></div><div class="col-md-3"><label class="form-label">Thời gian lặp (giây):</label><input type="number" name="spam_delay" class="form-control" value="{spam_delay}" min="1" placeholder="10"></div><div class="col-md-3"><label class="form-label">Điều khiển:</label><div class="btn-group w-100" role="group"><button name="spamtoggle" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="spamtoggle" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></div></div></form></div></div></div>
            <div class="col-12"><div class="control-card"><div class="card-header"><h5 class="mb-0"><i class="fas fa-sync-alt me-2"></i> Khởi động lại Bot (Reboot)</h5></div><div class="card-body"><form method="POST"><div class="input-group"><select name="reboot_target" class="form-select">{reboot_options}</select><button type="submit" class="btn btn-warning"><i class="fas fa-power-off me-1"></i>Reboot Bot</button></div></form><div class="mt-2"><small class="text-muted"><i class="fas fa-info-circle me-1"></i> Dùng khi một bot bị "đơ" hoặc không hoạt động đúng.</small></div></div></div></div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, auto_grab_enabled_2, spam_enabled, spam_message, spam_delay, heart_threshold, heart_threshold_2, auto_work_enabled
    msg_status = ""

    if request.method == "POST":
        if 'message' in request.form and request.form.get("message"):
            msg = request.form.get("message")
            with bots_lock:
                for idx, bot in enumerate(bots):
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, msg)).start()
            msg_status = "Đã gửi thủ công thành công!"
        elif 'quickmsg' in request.form:
            quickmsg = request.form.get("quickmsg")
            with bots_lock:
                for idx, bot in enumerate(bots):
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, quickmsg)).start()
            msg_status = f"Đã gửi lệnh {quickmsg} thành công!"
        elif 'toggle' in request.form:
            auto_grab_enabled = request.form['toggle'] == "on"
            msg_status = f"Tự grab Acc chính 1 {'đã bật' if auto_grab_enabled else 'đã tắt'}"
        elif 'toggle_2' in request.form:
            auto_grab_enabled_2 = request.form['toggle_2'] == "on"
            msg_status = f"Tự grab Acc chính 2 {'đã bật' if auto_grab_enabled_2 else 'đã tắt'}"
        elif 'heart_threshold' in request.form:
            try: heart_threshold = int(request.form['heart_threshold']); msg_status = f"Đã cập nhật mức tim Acc chính 1: {heart_threshold}"
            except: msg_status = "Mức tim Acc chính 1 không hợp lệ!"
        elif 'heart_threshold_2' in request.form:
            try: heart_threshold_2 = int(request.form['heart_threshold_2']); msg_status = f"Đã cập nhật mức tim Acc chính 2: {heart_threshold_2}"
            except: msg_status = "Mức tim Acc chính 2 không hợp lệ!"
        elif 'send_codes' in request.form:
            try:
                acc_index = int(request.form.get("acc_index"))
                delay = float(request.form.get("delay", 11))
                prefix = request.form.get("prefix", "").strip()
                codes_raw = request.form.get("codes", "")
                codes_list = [c.strip() for c in re.split(r'[,\n]', codes_raw) if c.strip()]
                if not codes_list:
                    msg_status = "Vui lòng nhập danh sách mã."
                elif 0 <= acc_index < len(acc_names):
                    target_bot = None
                    if acc_index == len(acc_names) - 1:
                        target_bot = main_bot
                        print(f"[Send Codes] Chọn Acc Chính 1 ({acc_names[acc_index]}) để gửi mã.")
                    elif acc_index < len(bots):
                        target_bot = bots[acc_index]
                        print(f"[Send Codes] Chọn Acc Phụ {acc_index} ({acc_names[acc_index]}) để gửi mã.")
                    if target_bot:
                        with bots_lock:
                            for i, code in enumerate(codes_list):
                                final_msg = f"{prefix} {code}" if prefix else code
                                threading.Timer(delay * i, target_bot.sendMessage, args=(other_channel_id, final_msg)).start()
                        msg_status = f"Đã bắt đầu gửi {len(codes_list)} mã từ tài khoản {acc_names[acc_index]}!"
                    else:
                        msg_status = f"Tài khoản {acc_names[acc_index]} không khả dụng."
                else:
                    msg_status = "Lựa chọn tài khoản không hợp lệ."
            except Exception as e:
                msg_status = f"Lỗi xử lý gửi mã: {e}"
        elif 'spamtoggle' in request.form:
            spam_enabled = request.form['spamtoggle'] == "on"
            spam_message = request.form.get("spammsg", "").strip()
            if spam_enabled and not spam_message:
                msg_status = "Vui lòng nhập nội dung trước khi bật spam."; spam_enabled = False
            else:
                msg_status = f"Spam {'đã bật' if spam_enabled else 'đã tắt'}"
        elif 'spam_delay' in request.form:
            try: spam_delay = int(request.form['spam_delay']); msg_status = f"Đã cập nhật thời gian spam: {spam_delay} giây"
            except: msg_status = "Thời gian spam không hợp lệ!"
        elif 'auto_work_toggle' in request.form:
            auto_work_enabled = request.form['auto_work_toggle'] == "on"
            msg_status = f"Auto Work {'đã bật' if auto_work_enabled else 'đã tắt'}"
        elif 'reboot_target' in request.form:
            reboot_bot(request.form['reboot_target'])
            msg_status = f"Đã gửi yêu cầu khởi động lại cho {request.form['reboot_target']}!"

    alert_section = f'<div class="row"><div class="col-12"><div class="alert alert-success">{msg_status}</div></div></div>' if msg_status else ""
    auto_grab_status = "status-active" if auto_grab_enabled else "status-inactive"
    auto_grab_text = "Đang bật" if auto_grab_enabled else "Đang tắt"
    auto_grab_status_2 = "status-active" if auto_grab_enabled_2 else "status-inactive"
    auto_grab_text_2 = "Đang bật" if auto_grab_enabled_2 else "Đang tắt"
    spam_status = "status-active" if spam_enabled else "status-inactive"
    spam_text = "Đang bật" if spam_enabled else "Đang tắt"
    auto_work_status = "status-active" if auto_work_enabled else "status-inactive"
    auto_work_text = "Đang bật" if auto_work_enabled else "Đang tắt"
    acc_options = "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names))
    reboot_options = ""
    if main_bot: reboot_options += '<option value="main_1">Acc Chính 1</option>'
    if main_bot_2: reboot_options += '<option value="main_2">Acc Chính 2</option>'
    # Sửa lỗi logic reboot, chỉ hiển thị các acc phụ có tồn tại
    for i in range(len(bots)):
        reboot_options += f'<option value="sub_{i}">Acc Phụ {i} ({acc_names[i]})</option>'

    # SỬA LỖI KEYERROR: Truyền biến một cách tường minh
    return render_template_string(HTML.format(
        alert_section=alert_section,
        auto_grab_status=auto_grab_status,
        auto_grab_text=auto_grab_text,
        auto_grab_status_2=auto_grab_status_2,
        auto_grab_text_2=auto_grab_text_2,
        spam_status=spam_status,
        spam_text=spam_text,
        auto_work_status=auto_work_status,
        auto_work_text=auto_work_text,
        heart_threshold=heart_threshold,
        heart_threshold_2=heart_threshold_2,
        spam_message=spam_message,
        spam_delay=spam_delay,
        acc_options=acc_options,
        reboot_options=reboot_options
    ))

def spam_loop():
    global spam_enabled, spam_message, spam_delay
    while True:
        if spam_enabled and spam_message:
            with bots_lock: bots_to_spam = bots.copy()
            for idx, bot in enumerate(bots_to_spam):
                try:
                    bot_name = acc_names[idx] if idx < len(acc_names) else f"Acc Phụ {idx}"
                    bot.sendMessage(spam_channel_id, spam_message)
                    print(f"[{bot_name}] đã gửi: {spam_message}")
                    time.sleep(2)
                except Exception as e:
                    print(f"Lỗi gửi spam từ {bot_name}: {e}")
        time.sleep(spam_delay)

def keep_alive():
    """Chạy web server."""
    port = int(os.environ.get("PORT", 8080))
    print(f"--- Khởi động Web Server tại cổng {port} ---")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# =================================================================
# === KHỐI CHẠY CHÍNH (ĐÃ CẬP NHẬT) ===
# =================================================================
if __name__ == "__main__":
    print("--- KHỞI TẠO HỆ THỐNG BOT ---")
    with bots_lock:
        if main_token:
            main_bot = create_bot(main_token, "Acc Chính 1", is_main=True)
        if main_token_2:
            main_bot_2 = create_bot(main_token_2, "Acc Chính 2", is_main_2=True)
        for i, token in enumerate(tokens):
            bot_name = acc_names[i] if i < len(acc_names) else f"Acc Phụ {i}"
            worker_bot = create_bot(token.strip(), bot_name, is_main=False)
            if worker_bot:
                bots.append(worker_bot)
    print("--- Tất cả các bot đã được khởi tạo ---")

    print("--- Đang khởi tạo các luồng nền ---")
    threading.Thread(target=spam_loop, daemon=True).start()
    print("-> Luồng Spam đã sẵn sàng.")
    threading.Thread(target=auto_work_loop, daemon=True).start()
    print("-> Luồng Auto Work đã sẵn sàng.")
    
    # Chạy web server trên luồng chính
    keep_alive()
