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

main_token = os.getenv("MAIN_TOKEN")
main_token_2 = os.getenv("MAIN_TOKEN_2")
tokens = os.getenv("TOKENS").split(",") if os.getenv("TOKENS") else []

main_channel_id = "1386973916563767396"
other_channel_id = "1387406577040101417"
ktb_channel_id = "1376777071279214662"
karuta_id = "646937666251915264"
karibbit_id = "1274445226064220273"

bots = []
main_bot = None
main_bot_2 = None
auto_grab_enabled = False
auto_grab_enabled_2 = False
heart_threshold = 50
heart_threshold_2 = 50
last_drop_msg_id = ""
acc_names = [
    "sly_dd", "HellNBack", Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent",
]

spam_enabled = False
spam_message = ""
spam_delay = 10  # thời gian vòng lặp spam (giây)
spam_channel_id = "1388802151723302912"

# Auto Work variables
auto_work_enabled = False
work_channel_id = "1389250541590413363"
work_delay_between_acc = 10
work_delay_after_all = 44100

def create_bot(token, is_main=False, is_main_2=False):
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                bot_type = "(Acc chính)" if is_main else "(Acc chính 2)" if is_main_2 else ""
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
                            for msg_kb in messages:
                                author_id = msg_kb.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_kb and len(msg_kb["embeds"]) > 0:
                                    desc = msg_kb["embeds"][0].get("description", "")
                                    print(f"\n[Bot 1] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 1] ===== Kết thúc tin nhắn =====\n")

                                    lines = desc.split('\n')
                                    heart_numbers = []

                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            num = int(matches[1])
                                            heart_numbers.append(num)
                                            print(f"[Bot 1] Dòng {i+1} số tim: {num}")
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
                            for msg_kb in messages:
                                author_id = msg_kb.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_kb and len(msg_kb["embeds"]) > 0:
                                    desc = msg_kb["embeds"][0].get("description", "")
                                    print(f"\n[Bot 2] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 2] ===== Kết thúc tin nhắn =====\n")

                                    lines = desc.split('\n')
                                    heart_numbers = []

                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            num = int(matches[1])
                                            heart_numbers.append(num)
                                            print(f"[Bot 2] Dòng {i+1} số tim: {num}")
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
                                            # Thêm 0.3 giây delay cho acc chính 2
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

    # Define a helper function for bot connection lifecycle
    def run_bot_connection_lifecycle(bot_instance, bot_name_for_log):
        while True:
            try:
                bot_instance.gateway.run(auto_reconnect=True)
            except Exception as e:
                print(f"[{bot_name_for_log}] Bot bị ngắt kết nối hoặc gặp lỗi nghiêm trọng, đang thử kết nối lại sau 5 giây: {e}")
            time.sleep(5)

    # Start the connection lifecycle in a separate daemon thread
    bot_log_name = "Bot chính 1" if is_main else ("Bot chính 2" if is_main_2 else "Bot phụ")
    threading.Thread(target=run_bot_connection_lifecycle, args=(bot, bot_log_name), daemon=True).start()
    return bot # This return statement was originally incorrectly indented

# --- Bot Initialization ---
main_bot = create_bot(main_token, is_main=True)
if main_token_2:
    main_bot_2 = create_bot(main_token_2, is_main_2=True)

for token in tokens:
    if token.strip():
        bots.append(create_bot(token.strip(), is_main=False))

# Auto Work Functions
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
            if str(m.get('channel_id')) != work_channel_id or m.get('author', {}).get('id') == bot.gateway.session.user['id']:
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
    # This bot will use run_bot_connection_lifecycle if it's one of the persistent bots
    # created by create_bot. If it's a new, temporary bot created just for work,
    # its gateway needs to be explicitly run and managed here.
    # To avoid creating multiple discum clients for the same token and to ensure the work bot
    # also attempts to reconnect, we should reuse the persistent bot instance from `create_bot`.
    # However, to maintain existing structure of `run_work_bot`, I will keep this logic as-is,
    # and acknowledge it means a separate, temporary discum instance is created here.
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
            for i, token in enumerate(tokens):
                if token.strip():
                    # The acc_names indexing for work bots should match the dropdown in Flask
                    # For `tokens` list (additional bots), it corresponds to acc_names from index 2 onwards.
                    acc_name = acc_names[i + 2] if (i + 2) < len(acc_names) else f"Acc phụ {i+1}"
                    print(f"[Auto Work] Đang chạy acc {acc_name}...")
                    run_work_bot(token.strip(), acc_name) # Pass acc_name for logging
                    print(f"[Auto Work] Acc {acc_name} xong, chờ {work_delay_between_acc} giây...")
                    time.sleep(work_delay_between_acc)
            
            print(f"[Auto Work] Hoàn thành tất cả acc, chờ {work_delay_after_all} giây để lặp lại...")
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
        /* Global Styles */
        * {{
            box-sizing: border-box;
        }}

        body {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #ffffff;
            margin: 0;
            padding: 20px 0;
        }}

        /* Header Styles */
        .header-section {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}

        .header-section h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(45deg, #00d4ff, #ff9500);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
        }}

        .header-section p {{
            font-size: 1.1rem;
            color: #b0b0b0;
            margin-bottom: 0;
        }}

        /* Control Card Styles */
        .control-card {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
            overflow: hidden;
            margin-bottom: 2rem;
        }}

        .control-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
            border-color: rgba(0, 212, 255, 0.3);
        }}

        .control-card .card-header {{
            background: linear-gradient(45deg, rgba(0, 212, 255, 0.2), rgba(255, 149, 0, 0.2));
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            border-radius: 20px 20px 0 0;
        }}

        .control-card .card-header h5 {{
            color: #ffffff;
            font-weight: 600;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }}

        .control-card .card-body {{
            padding: 1.5rem;
        }}

        /* Form Styles */
        .form-control {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            color: #ffffff;
            padding: 12px 16px;
            font-size: 1rem;
            transition: all 0.3s ease;
        }}

        .form-control:focus {{
            background: rgba(255, 255, 255, 0.15);
            border-color: #00d4ff;
            box-shadow: 0 0 0 0.2rem rgba(0, 212, 255, 0.25);
            color: #ffffff;
        }}

        .form-control::placeholder {{
            color: #b0b0b0;
        }}

        .form-select {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            color: #ffffff;
            padding: 12px 16px;
            font-size: 1rem;
            transition: all 0.3s ease;
        }}

        .form-select:focus {{
            background: rgba(255, 255, 255, 0.15);
            border-color: #00d4ff;
            box-shadow: 0 0 0 0.2rem rgba(0, 212, 255, 0.25);
            color: #ffffff;
        }}

        .form-select option {{
            background: #1a1a2e;
            color: #ffffff;
        }}

        .form-label {{
            color: #ffffff;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}

        .input-group-text {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #ffffff;
            border-radius: 12px 0 0 12px;
        }}

        /* Button Styles */
        .btn {{
            border-radius: 12px;
            padding: 12px 24px;
            font-weight: 500;
            font-size: 1rem;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: none;
            position: relative;
            overflow: hidden;
        }}

        .btn::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s ease;
        }}

        .btn:hover::before {{
            left: 100%;
        }}

        .btn-primary {{
            background: linear-gradient(45deg, #00d4ff, #0099cc);
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
        }}

        .btn-primary:hover {{
            background: linear-gradient(45deg, #0099cc, #00d4ff);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 212, 255, 0.6);
        }}

        .btn-success {{
            background: linear-gradient(45deg, #28a745, #20c997);
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4);
        }}

        .btn-success:hover {{
            background: linear-gradient(45deg, #20c997, #28a745);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.6);
        }}

        .btn-danger {{
            background: linear-gradient(45deg, #dc3545, #e83e8c);
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
        }}

        .btn-danger:hover {{
            background: linear-gradient(45deg, #e83e8c, #dc3545);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(220, 53, 69, 0.6);
        }}

        /* Status Indicators */
        .status-indicator {{
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }}

        .status-badge {{
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            transition: all 0.3s ease;
        }}

        .status-active {{
            background: linear-gradient(45deg, #28a745, #20c997);
            color: #ffffff;
            box-shadow: 0 0 20px rgba(40, 167, 69, 0.3);
        }}

        .status-inactive {{
            background: linear-gradient(45deg, #dc3545, #e83e8c);
            color: #ffffff;
            box-shadow: 0 0 20px rgba(220, 53, 69, 0.3);
        }}

        /* Alert Styles */
        .alert {{
            background: rgba(40, 167, 69, 0.2);
            border: 1px solid rgba(40, 167, 69, 0.3);
            border-radius: 12px;
            color: #ffffff;
            backdrop-filter: blur(10px);
            margin-bottom: 1rem;
        }}

        .alert-success {{
            background: rgba(40, 167, 69, 0.2);
            border-color: rgba(40, 167, 69, 0.3);
        }}

        /* Animation */
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .control-card {{
            animation: fadeInUp 0.6s ease-out;
        }}

        .quick-commands {{
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .quick-commands h6 {{
            color: #ffffff;
            font-weight: 600;
            margin-bottom: 1rem;
        }}

        .heart-threshold {{
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .heart-threshold h6 {{
            color: #ffffff;
            font-weight: 600;
            margin-bottom: 1rem;
        }}

        /* Responsive Design */
        @media (max-width: 768px) {{
            .header-section {{
                padding: 1.5rem;
                margin-bottom: 1.5rem;
            }}
            
            .header-section h1 {{
                font-size: 2rem;
            }}
            
            .control-card .card-header,
            .control-card .card-body {{
                padding: 1rem;
            }}
            
            .btn {{
                padding: 10px 20px;
                font-size: 0.9rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <div class="header-section">
                    <h1 class="text-center mb-0">
                        <i class="fas fa-robot me-3"></i>
                        Karuta Deep
                    </h1>
                    <p class="text-center text-muted">Quản lý bot Discord với giao diện hiện đại</p>
                </div>
            </div>
        </div>

        {alert_section}

        <div class="row g-4">
            <div class="col-lg-6">
                <div class="control-card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-paper-plane me-2"></i>
                            Điều khiển bot nhắn tin
                        </h5>
                    </div>
                    <div class="card-body">
                        <form method="POST" class="mb-4">
                            <div class="input-group">
                                <input type="text" 
                                       class="form-control" 
                                       name="message" 
                                       placeholder="Nhập nội dung tin nhắn...">
                                <button class="btn btn-primary" type="submit">
                                    <i class="fas fa-send me-1"></i>Gửi thủ công
                                </button>
                            </div>
                        </form>

                        <div class="quick-commands">
                            <h6 class="mb-3">Menu nhanh</h6>
                            <form method="POST">
                                <div class="input-group">
                                    <select name="quickmsg" class="form-select">
                                        <option value="kc o:w">kc o:w</option>
                                        <option value="kc o:ef">kc o:ef</option>
                                        <option value="kc o:p">kc o:p</option>
                                        <option value="kc e:1">kc e:1</option>
                                        <option value="kc e:2">kc e:2</option>
                                        <option value="kc e:3">kc e:3</option>
                                        <option value="kc e:4">kc e:4</option>
                                        <option value="kc e:5">kc e:5</option>
                                        <option value="kc e:6">kc e:6</option>
                                        <option value="kc e:7">kc e:7</option>
                                    </select>
                                    <button type="submit" class="btn btn-success">
                                        <i class="fas fa-bolt me-1"></i>Gửi
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="control-card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-briefcase me-2"></i>
                            Auto Work
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="status-indicator mb-3">
                            <span class="status-badge {auto_work_status}">
                                <i class="fas fa-circle me-1"></i>
                                {auto_work_text}
                            </span>
                        </div>

                        <form method="POST" class="mb-4">
                            <div class="btn-group w-100" role="group">
                                <button name="auto_work_toggle" value="on" type="submit" class="btn btn-success">
                                    <i class="fas fa-play me-1"></i>Bật
                                </button>
                                <button name="auto_work_toggle" value="off" type="submit" class="btn btn-danger">
                                    <i class="fas fa-stop me-1"></i>Tắt
                                </button>
                            </div>
                        </form>

                        <div class="mt-2">
                            <small class="text-muted">
                                <i class="fas fa-info-circle me-1"></i>
                                Tự động làm việc cho tất cả account
                            </small>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="control-card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-magic me-2"></i>
                            Auto Grab - Acc Chính 1
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="status-indicator mb-3">
                            <span class="status-badge {auto_grab_status}">
                                <i class="fas fa-circle me-1"></i>
                                {auto_grab_text}
                            </span>
                        </div>

                        <form method="POST" class="mb-4">
                            <div class="btn-group w-100" role="group">
                                <button name="toggle" value="on" type="submit" class="btn btn-success">
                                    <i class="fas fa-play me-1"></i>Bật
                                </button>
                                <button name="toggle" value="off" type="submit" class="btn btn-danger">
                                    <i class="fas fa-stop me-1"></i>Tắt
                                </button>
                            </div>
                        </form>

                        <div class="heart-threshold">
                            <h6 class="mb-3">Thiết lập mức tim tiêu chuẩn</h6>
                            <form method="POST">
                                <div class="input-group">
                                    <span class="input-group-text">
                                        <i class="fas fa-heart text-danger"></i>
                                    </span>
                                    <input type="number" 
                                           class="form-control" 
                                           name="heart_threshold" 
                                           value="{heart_threshold}" 
                                           min="0"
                                           placeholder="Mức tim">
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-save me-1"></i>Cập nhật
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="control-card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-magic me-2"></i>
                            Auto Grab - Acc Chính 2
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="status-indicator mb-3">
                            <span class="status-badge {auto_grab_status_2}">
                                <i class="fas fa-circle me-1"></i>
                                {auto_grab_text_2}
                            </span>
                        </div>

                        <form method="POST" class="mb-4">
                            <div class="btn-group w-100" role="group">
                                <button name="toggle_2" value="on" type="submit" class="btn btn-success">
                                    <i class="fas fa-play me-1"></i>Bật
                                </button>
                                <button name="toggle_2" value="off" type="submit" class="btn btn-danger">
                                    <i class="fas fa-stop me-1"></i>Tắt
                                </button>
                            </div>
                        </form>

                        <div class="heart-threshold">
                            <h6 class="mb-3">Thiết lập mức tim tiêu chuẩn</h6>
                            <form method="POST">
                                <div class="input-group">
                                    <span class="input-group-text">
                                        <i class="fas fa-heart text-danger"></i>
                                    </span>
                                    <input type="number" 
                                           class="form-control" 
                                           name="heart_threshold_2" 
                                           value="{heart_threshold_2}" 
                                           min="0"
                                           placeholder="Mức tim">
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-save me-1"></i>Cập nhật
                                    </button>
                                </div>
                            </form>
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">
                                <i class="fas fa-info-circle me-1"></i>
                                Delay grab chậm hơn 0.3s so với Acc chính 1
                            </small>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-12">
                <div class="control-card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-code me-2"></i>
                            Gửi danh sách mã theo acc chọn
                        </h5>
                    </div>
                    <div class="card-body">
                        <form method="POST">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label">Chọn acc:</label>
                                    <select name="acc_index" class="form-select">
                                        {acc_options}
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Thời gian cách nhau (giây):</label>
                                    <input type="number" 
                                           step="0.1" 
                                           name="delay" 
                                           class="form-control" 
                                           value="11" 
                                           placeholder="11">
                                </div>
                                <div class="col-12">
                                    <label class="form-label">Nội dung mẫu:</label>
                                    <input type="text" 
                                           name="prefix" 
                                           class="form-control" 
                                           placeholder="vd: kt n">
                                </div>
                                <div class="col-12">
                                    <label class="form-label">Danh sách mã:</label>
                                    <textarea name="codes" 
                                              class="form-control" 
                                              rows="4" 
                                              placeholder="Danh sách mã, cách nhau dấu phẩy"></textarea>
                                </div>
                                <div class="col-12">
                                    <button type="submit" name="send_codes" value="1" class="btn btn-primary btn-lg">
                                        <i class="fas fa-paper-plane me-2"></i>Gửi danh sách mã
                                    </button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <div class="col-12">
                <div class="control-card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-repeat me-2"></i>
                            Spam Control
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="status-indicator mb-3">
                            <span class="status-badge {spam_status}">
                                <i class="fas fa-circle me-1"></i>
                                {spam_text}
                            </span>
                        </div>

                        <form method="POST">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label">Nội dung spam:</label>
                                    <input type="text" 
                                           name="spammsg" 
                                           class="form-control" 
                                           placeholder="Nội dung spam" 
                                           value="{spam_message}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label">Thời gian lặp (giây):</label>
                                    <input type="number" 
                                           name="spam_delay" 
                                           class="form-control" 
                                           value="{spam_delay}" 
                                           min="1"
                                           placeholder="10">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label">Điều khiển:</label>
                                    <div class="btn-group w-100" role="group">
                                        <button name="spamtoggle" value="on" type="submit" class="btn btn-success">
                                            <i class="fas fa-play me-1"></i>Bật
                                        </button>
                                        <button name="spamtoggle" value="off" type="submit" class="btn btn-danger">
                                            <i class="fas fa-stop me-1"></i>Tắt
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
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
        msg = request.form.get("message")
        quickmsg = request.form.get("quickmsg")
        toggle = request.form.get("toggle")
        toggle_2 = request.form.get("toggle_2")
        send_codes = request.form.get("send_codes")
        spamtoggle = request.form.get("spamtoggle")
        spammsg = request.form.get("spammsg", "")
        spam_delay_form = request.form.get("spam_delay")
        heart_threshold_form = request.form.get("heart_threshold")
        heart_threshold_2_form = request.form.get("heart_threshold_2")
        auto_work_toggle = request.form.get("auto_work_toggle")

        if msg:
            all_active_bots = []
            if main_bot:
                all_active_bots.append(main_bot)
            if main_bot_2:
                all_active_bots.append(main_bot_2)
            all_active_bots.extend(bots) # Add all additional bots

            for idx, bot_instance in enumerate(all_active_bots):
                try:
                    threading.Timer(2 * idx, bot_instance.sendMessage, args=(other_channel_id, msg)).start()
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn thủ công: {e}")
            msg_status = "Đã gửi thủ công thành công!"

        if quickmsg:
            all_active_bots = []
            if main_bot:
                all_active_bots.append(main_bot)
            if main_bot_2:
                all_active_bots.append(main_bot_2)
            all_active_bots.extend(bots) # Add all additional bots
            
            for idx, bot_instance in enumerate(all_active_bots):
                try:
                    threading.Timer(2 * idx, bot_instance.sendMessage, args=(other_channel_id, quickmsg)).start()
                except Exception as e:
                    print(f"Lỗi gửi lệnh nhanh: {e}")
            msg_status = f"Đã gửi lệnh {quickmsg} thành công!"

        if toggle:
            auto_grab_enabled = toggle == "on"
            msg_status = f"Tự grab Acc chính 1 {'đã bật' if auto_grab_enabled else 'đã tắt'}"

        if toggle_2:
            auto_grab_enabled_2 = toggle_2 == "on"
            msg_status = f"Tự grab Acc chính 2 {'đã bật' if auto_grab_enabled_2 else 'đã tắt'}"

        if heart_threshold_form is not None:
            try:
                new_threshold = int(heart_threshold_form)
                if new_threshold >= 0:
                    heart_threshold = new_threshold
                    msg_status = f"Đã cập nhật mức tim Acc chính 1: {heart_threshold}"
                else:
                    msg_status = "Mức tim Acc chính 1 không hợp lệ! Phải là số không âm."
            except ValueError:
                msg_status = "Mức tim Acc chính 1 không hợp lệ!"

        if heart_threshold_2_form is not None:
            try:
                new_threshold_2 = int(heart_threshold_2_form)
                if new_threshold_2 >= 0:
                    heart_threshold_2 = new_threshold_2
                    msg_status = f"Đã cập nhật mức tim Acc chính 2: {heart_threshold_2}"
                else:
                    msg_status = "Mức tim Acc chính 2 không hợp lệ! Phải là số không âm."
            except ValueError:
                msg_status = "Mức tim Acc chính 2 không hợp lệ!"

        if send_codes:
            acc_index_str = request.form.get("acc_index")
            delay_str = request.form.get("delay")
            prefix = request.form.get("prefix", "").strip()
            codes = request.form.get("codes", "").strip()

            if acc_index_str and delay_str and codes:
                try:
                    acc_idx = int(acc_index_str)
                    delay_val = float(delay_str)
                    codes_list = [code.strip() for code in codes.split(",") if code.strip()]
                    
                    target_bot = None
                    if acc_idx == 0 and main_bot:
                        target_bot = main_bot
                    elif acc_idx == 1 and main_bot_2:
                        target_bot = main_bot_2
                    elif acc_idx >= 2 and (acc_idx - 2) < len(bots): # Adjusted for `bots` list
                        target_bot = bots[acc_idx - 2]
                    
                    if target_bot:
                        for i, code in enumerate(codes_list):
                            final_msg = f"{prefix} {code}" if prefix else code
                            threading.Timer(delay_val * i, target_bot.sendMessage, args=(other_channel_id, final_msg)).start()
                        msg_status = f"Đã bắt đầu gửi mã cho acc {acc_names[acc_idx]}!"
                    else:
                        msg_status = "Không tìm thấy bot cho tài khoản đã chọn hoặc tài khoản đó không được khởi tạo!"
                except ValueError:
                    msg_status = "Lỗi: Thời gian delay hoặc định dạng mã không hợp lệ."
                except Exception as e:
                    print(f"Lỗi khi gửi danh sách mã: {e}")
                    msg_status = f"Đã xảy ra lỗi khi gửi mã: {str(e)}"
            else:
                msg_status = "Vui lòng điền đầy đủ thông tin để gửi mã."

        if spamtoggle:
            spam_enabled = (spamtoggle == "on")
            spam_message = spammsg.strip()
            msg_status = f"Spam {'đã bật' if spam_enabled else 'đã tắt'}"

        if spam_delay_form is not None:
            try:
                new_spam_delay = int(spam_delay_form)
                if new_spam_delay >= 1:
                    spam_delay = new_spam_delay
                    msg_status = f"Đã cập nhật thời gian spam: {spam_delay} giây"
                else:
                    msg_status = "Thời gian spam không hợp lệ! Phải là số dương."
            except ValueError:
                msg_status = "Thời gian spam không hợp lệ!"

        if auto_work_toggle:
            auto_work_enabled = (auto_work_toggle == "on")
            msg_status = f"Auto Work {'đã bật' if auto_work_enabled else 'đã tắt'}"

    if msg_status:
        alert_section = f'<div class="row"><div class="col-12"><div class="alert alert-success">{msg_status}</div></div></div>'
    else:
        alert_section = ""

    auto_grab_status = "status-active" if auto_grab_enabled else "status-inactive"
    auto_grab_text = "Đang bật" if auto_grab_enabled else "Đang tắt"
    
    auto_grab_status_2 = "status-active" if auto_grab_enabled_2 else "status-inactive"
    auto_grab_text_2 = "Đang bật" if auto_grab_enabled_2 else "Đang tắt"
    
    spam_status = "status-active" if spam_enabled else "status-inactive"
    spam_text = "Đang bật" if spam_enabled else "Đang tắt"

    auto_work_status = "status-active" if auto_work_enabled else "status-inactive"
    auto_work_text = "Đang bật" if auto_work_enabled else "Đang tắt"

    current_acc_options = []
    if main_bot:
        current_acc_options.append('<option value="0">Blacklist (Acc Chính 1)</option>')
    if main_bot_2:
        current_acc_options.append('<option value="1">Khanh bang (Acc Chính 2)</option>')
    
    for i, _ in enumerate(tokens):
        acc_name_for_dropdown = acc_names[i + 2] if (i + 2) < len(acc_names) else f"Acc phụ {i+1}"
        current_acc_options.append(f'<option value="{i + 2}">{acc_name_for_dropdown}</option>')
    
    acc_options_html = "".join(current_acc_options)

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
        acc_options=acc_options_html
    ))

def spam_loop():
    global spam_enabled, spam_message, spam_delay
    while True:
        if spam_enabled and spam_message:
            all_spam_bots = []
            if main_bot:
                all_spam_bots.append(main_bot)
            if main_bot_2:
                all_spam_bots.append(main_bot_2)
            all_spam_bots.extend(bots)

            for idx, bot_instance in enumerate(all_spam_bots):
                try:
                    bot_instance.sendMessage(spam_channel_id, spam_message)
                    log_name = acc_names[idx] if idx < len(acc_names) else f"Bot {idx + 1}"
                    print(f"[{log_name}] đã gửi: {spam_message}")
                    time.sleep(2)
                except Exception as e:
                    print(f"Lỗi gửi spam từ bot {idx}: {e}")
        time.sleep(spam_delay)

def keep_alive():
    while True:
        try:
            if main_bot:
                pass
            time.sleep(random.randint(60, 120))
        except Exception as e:
            print(f"Lỗi trong keep_alive: {e}")

if __name__ == "__main__":
    threading.Thread(target=spam_loop, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)