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
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", "sly_dd"
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
        if resp.parsed.get("t") == "READY":
            print(f"Bot {'chính' if is_main else 'chính 2' if is_main_2 else 'phụ'} đã sẵn sàng!")
        
        @bot.gateway.command
        def on_message(resp):
            if resp.parsed.get("t") == "MESSAGE_CREATE":
                m = resp.parsed.get("d")
                if m and m.get("channel_id") == main_channel_id:
                    msg_content = m.get("content", "")
                    author_id = m.get("author", {}).get("id")
                    
                    if author_id == karuta_id:
                        print(f"Nhận tin nhắn Karuta: {msg_content}")
                        
                        if "wished for" in msg_content and "<a:kl_droplet:1176552325968949268>" in msg_content:
                            global last_drop_msg_id
                            last_drop_msg_id = m.get("id")
                            print(f"Tìm thấy drop - ID: {last_drop_msg_id}")
                        
                        if is_main and auto_grab_enabled:
                            def read_karibbit():
                                try:
                                    channel = bot.getMessages(main_channel_id, limit=1)
                                    if channel:
                                        msg_id = channel[0].get("id")
                                        if msg_id:
                                            response = bot.getReactions(main_channel_id, msg_id)
                                            if response and isinstance(response, list):
                                                for user_data in response:
                                                    if user_data.get("id") == karibbit_id:
                                                        def grab():
                                                            try:
                                                                bot.sendMessage(main_channel_id, "kc o:ef")
                                                                time.sleep(1)
                                                                bot.sendMessage(main_channel_id, "kc o:ef")
                                                            except Exception as e:
                                                                print(f"Lỗi grab: {e}")
                                                        
                                                        pattern = r'<a:kl_droplet:1176552325968949268> \*\*(\d+)\*\*'
                                                        match = re.search(pattern, msg_content)
                                                        if match:
                                                            heart_count = int(match.group(1))
                                                            if heart_count >= heart_threshold:
                                                                grab()
                                                        break
                                except Exception as e:
                                    print(f"Lỗi read_karibbit: {e}")
                            
                            threading.Thread(target=read_karibbit).start()

        @bot.gateway.command
        def on_message(resp):
            if resp.parsed.get("t") == "MESSAGE_CREATE":
                m = resp.parsed.get("d")
                if m and m.get("channel_id") == main_channel_id:
                    msg_content = m.get("content", "")
                    author_id = m.get("author", {}).get("id")
                    
                    if author_id == karuta_id and is_main_2 and auto_grab_enabled_2:
                        def read_karibbit_2():
                            try:
                                channel = bot.getMessages(main_channel_id, limit=1)
                                if channel:
                                    msg_id = channel[0].get("id")
                                    if msg_id:
                                        response = bot.getReactions(main_channel_id, msg_id)
                                        if response and isinstance(response, list):
                                            for user_data in response:
                                                if user_data.get("id") == karibbit_id:
                                                    def grab_2():
                                                        try:
                                                            bot.sendMessage(main_channel_id, "kc o:ef")
                                                            time.sleep(1)
                                                            bot.sendMessage(main_channel_id, "kc o:ef")
                                                        except Exception as e:
                                                            print(f"Lỗi grab 2: {e}")
                                                    
                                                    pattern = r'<a:kl_droplet:1176552325968949268> \*\*(\d+)\*\*'
                                                    match = re.search(pattern, msg_content)
                                                    if match:
                                                        heart_count = int(match.group(1))
                                                        if heart_count >= heart_threshold_2:
                                                            grab_2()
                                                    break
                            except Exception as e:
                                print(f"Lỗi read_karibbit_2: {e}")
                        
                        threading.Thread(target=read_karibbit_2).start()

    return bot

def run_work_bot(token, acc_index):
    work_bot = discum.Client(token=token, log=False)
    
    def send_karuta_command():
        try:
            work_bot.sendMessage(work_channel_id, "kc o:ef")
            print(f"Acc {acc_index + 1}: Gửi kc o:ef")
        except Exception as e:
            print(f"Lỗi gửi kc o:ef cho acc {acc_index + 1}: {e}")
    
    def send_kn_command():
        try:
            work_bot.sendMessage(work_channel_id, "kn")
            print(f"Acc {acc_index + 1}: Gửi kn")
        except Exception as e:
            print(f"Lỗi gửi kn cho acc {acc_index + 1}: {e}")
    
    def send_kw_command():
        try:
            work_bot.sendMessage(work_channel_id, "kw")
            print(f"Acc {acc_index + 1}: Gửi kw")
        except Exception as e:
            print(f"Lỗi gửi kw cho acc {acc_index + 1}: {e}")
    
    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            url = "https://discord.com/api/v9/interactions"
            headers = {
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json"
            }
            data = {
                "type": 3,
                "application_id": application_id,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "message_id": message_id,
                "data": {
                    "custom_id": custom_id,
                    "component_type": 2
                }
            }
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 204:
                print(f"Acc {acc_index + 1}: Click thành công")
            else:
                print(f"Acc {acc_index + 1}: Click thất bại - {response.status_code}")
        except Exception as e:
            print(f"Lỗi click cho acc {acc_index + 1}: {e}")
    
    @work_bot.gateway.command
    def on_message(resp):
        if resp.parsed.get("t") == "MESSAGE_CREATE":
            m = resp.parsed.get("d")
            if m and m.get("channel_id") == work_channel_id:
                msg_content = m.get("content", "")
                author_id = m.get("author", {}).get("id")
                
                if author_id == karuta_id:
                    if "kjw codes" in msg_content.lower():
                        time.sleep(1)
                        send_kn_command()
                    elif "you earned" in msg_content.lower() and "tokens" in msg_content.lower():
                        time.sleep(1)
                        send_kw_command()
                    elif "components" in str(m.get("components", [])):
                        components = m.get("components", [])
                        if components:
                            for component in components:
                                if component.get("type") == 1:
                                    action_rows = component.get("components", [])
                                    for action_row in action_rows:
                                        if action_row.get("type") == 2:
                                            custom_id = action_row.get("custom_id")
                                            if custom_id:
                                                application_id = m.get("application_id")
                                                guild_id = m.get("guild_id")
                                                message_id = m.get("id")
                                                
                                                time.sleep(1)
                                                click_tick(work_channel_id, message_id, custom_id, application_id, guild_id)
                                                break
                                    break
    
    # Sequence: kc o:ef -> kjw codes -> kn -> kjn -> kw -> click button
    send_karuta_command()
    
    return work_bot

def auto_work_loop():
    global auto_work_enabled
    while True:
        if auto_work_enabled:
            print("Bắt đầu auto work...")
            work_bots = []
            
            for i, token in enumerate(tokens):
                if token.strip():
                    print(f"Khởi tạo work bot cho acc {i + 1}")
                    work_bot = run_work_bot(token.strip(), i)
                    work_bots.append(work_bot)
                    
                    if i < len(tokens) - 1:
                        time.sleep(work_delay_between_acc)
            
            # Chờ hoàn thành tất cả
            print(f"Chờ {work_delay_after_all} giây trước khi lặp lại...")
            time.sleep(work_delay_after_all)
            
            # Đóng tất cả work bots
            for work_bot in work_bots:
                try:
                    work_bot.gateway.close()
                except:
                    pass
        else:
            time.sleep(10)

# Khởi tạo bots
if main_token:
    main_bot = create_bot(main_token, is_main=True)
if main_token_2:
    main_bot_2 = create_bot(main_token_2, is_main_2=True)

for token in tokens:
    if token.strip():
        bot = create_bot(token.strip())
        bots.append(bot)

# Khởi động auto work thread
auto_work_thread = threading.Thread(target=auto_work_loop, daemon=True)
auto_work_thread.start()

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Deep</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px 0;
        }}
        .glass-container {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            padding: 30px;
            margin: 20px 0;
        }}
        .title {{
            text-align: center;
            color: white;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            background: linear-gradient(45deg, #FFD700, #FFA500, #FF6B6B);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .section-title {{
            color: #FFD700;
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 20px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        .form-control, .form-select {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            border-radius: 10px;
            padding: 12px;
        }}
        .form-control::placeholder {{
            color: rgba(255, 255, 255, 0.7);
        }}
        .form-control:focus, .form-select:focus {{
            background: rgba(255, 255, 255, 0.2);
            border-color: #FFD700;
            box-shadow: 0 0 0 0.2rem rgba(255, 215, 0, 0.25);
            color: white;
        }}
        .btn-primary {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            border: none;
            border-radius: 10px;
            padding: 12px 30px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        .btn-primary:hover {{
            background: linear-gradient(45deg, #764ba2, #667eea);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }}
        .btn-success {{
            background: linear-gradient(45deg, #4CAF50, #45a049);
            border: none;
            border-radius: 10px;
            padding: 12px 30px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        .btn-success:hover {{
            background: linear-gradient(45deg, #45a049, #4CAF50);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }}
        .btn-danger {{
            background: linear-gradient(45deg, #f44336, #da190b);
            border: none;
            border-radius: 10px;
            padding: 12px 30px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        .btn-danger:hover {{
            background: linear-gradient(45deg, #da190b, #f44336);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }}
        .btn-warning {{
            background: linear-gradient(45deg, #ff9800, #f57c00);
            border: none;
            border-radius: 10px;
            padding: 12px 30px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        .btn-warning:hover {{
            background: linear-gradient(45deg, #f57c00, #ff9800);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }}
        .status-active {{
            color: #4CAF50;
            font-weight: 600;
        }}
        .status-inactive {{
            color: #f44336;
            font-weight: 600;
        }}
        .alert {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            border-radius: 10px;
            backdrop-filter: blur(5px);
        }}
        .form-label {{
            color: white;
            font-weight: 500;
            margin-bottom: 8px;
        }}
        .row {{
            margin-bottom: 20px;
        }}
        .icon {{
            margin-right: 8px;
        }}
        .form-select option {{
            background: #2c3e50;
            color: white;
        }}
        @media (max-width: 768px) {{
            .title {{
                font-size: 1.8rem;
            }}
            .glass-container {{
                padding: 20px;
                margin: 10px 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">
            <i class="fas fa-robot icon"></i>
            Karuta Deep
        </h1>
        
        {alert_section}
        
        <div class="row">
            <!-- Điều khiển bot nhắn tin -->
            <div class="col-md-6">
                <div class="glass-container">
                    <h3 class="section-title">
                        <i class="fas fa-comments icon"></i>
                        Điều khiển bot nhắn tin
                    </h3>
                    <form method="POST">
                        <div class="mb-3">
                            <label for="spam_message" class="form-label">Nội dung tin nhắn:</label>
                            <input type="text" class="form-control" id="spam_message" name="spam_message" placeholder="Nhập nội dung tin nhắn...">
                        </div>
                        <div class="mb-3">
                            <label for="spam_delay" class="form-label">Delay (giây):</label>
                            <input type="number" class="form-control" id="spam_delay" name="spam_delay" placeholder="10" min="1">
                        </div>
                        <div class="d-grid gap-2">
                            <button type="submit" name="start_spam" class="btn btn-success">
                                <i class="fas fa-play icon"></i>
                                Bắt đầu nhắn tin
                            </button>
                            <button type="submit" name="stop_spam" class="btn btn-danger">
                                <i class="fas fa-stop icon"></i>
                                Dừng nhắn tin
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            
            <!-- Auto Work -->
            <div class="col-md-6">
                <div class="glass-container">
                    <h3 class="section-title">
                        <i class="fas fa-cog icon"></i>
                        Auto Work
                    </h3>
                    <p class="text-light">Trạng thái: <span class="{auto_work_status}">{auto_work_text}</span></p>
                    <form method="POST">
                        <div class="d-grid gap-2">
                            <button type="submit" name="toggle_auto_work" class="btn btn-warning">
                                <i class="fas fa-power-off icon"></i>
                                Bật/Tắt Auto Work
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Auto Grab Acc chính 1 -->
            <div class="col-md-6">
                <div class="glass-container">
                    <h3 class="section-title">
                        <i class="fas fa-hand-paper icon"></i>
                        Auto Grab Acc chính 1
                    </h3>
                    <p class="text-light">Trạng thái: <span class="{auto_grab_status}">{auto_grab_text}</span></p>
                    <p class="text-light">Mức tim hiện tại: <span class="text-warning">{heart_threshold}</span></p>
                    <form method="POST">
                        <div class="mb-3">
                            <label for="heart_threshold" class="form-label">Mức tim tối thiểu:</label>
                            <input type="number" class="form-control" id="heart_threshold" name="heart_threshold" placeholder="{heart_threshold}" min="1">
                        </div>
                        <div class="d-grid gap-2">
                            <button type="submit" name="toggle_auto_grab" class="btn btn-warning">
                                <i class="fas fa-power-off icon"></i>
                                Bật/Tắt Auto Grab
                            </button>
                            <button type="submit" name="update_heart_threshold" class="btn btn-primary">
                                <i class="fas fa-heart icon"></i>
                                Cập nhật mức tim
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            
            <!-- Auto Grab Acc chính 2 -->
            <div class="col-md-6">
                <div class="glass-container">
                    <h3 class="section-title">
                        <i class="fas fa-hand-paper icon"></i>
                        Auto Grab Acc chính 2
                    </h3>
                    <p class="text-light">Trạng thái: <span class="{auto_grab_status_2}">{auto_grab_text_2}</span></p>
                    <p class="text-light">Mức tim hiện tại: <span class="text-warning">{heart_threshold_2}</span></p>
                    <form method="POST">
                        <div class="mb-3">
                            <label for="heart_threshold_2" class="form-label">Mức tim tối thiểu:</label>
                            <input type="number" class="form-control" id="heart_threshold_2" name="heart_threshold_2" placeholder="{heart_threshold_2}" min="1">
                        </div>
                        <div class="d-grid gap-2">
                            <button type="submit" name="toggle_auto_grab_2" class="btn btn-warning">
                                <i class="fas fa-power-off icon"></i>
                                Bật/Tắt Auto Grab
                            </button>
                            <button type="submit" name="update_heart_threshold_2" class="btn btn-primary">
                                <i class="fas fa-heart icon"></i>
                                Cập nhật mức tim
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <!-- Gửi danh sách mã -->
        <div class="row">
            <div class="col-12">
                <div class="glass-container">
                    <h3 class="section-title">
                        <i class="fas fa-list icon"></i>
                        Gửi danh sách mã theo acc chọn
                    </h3>
                    <form method="POST">
                        <div class="row">
                            <div class="col-md-3">
                                <div class="mb-3">
                                    <label for="acc_index" class="form-label">Chọn acc:</label>
                                    <select class="form-select" id="acc_index" name="acc_index">
                                        {acc_options}
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="mb-3">
                                    <label for="delay" class="form-label">Delay (giây):</label>
                                    <input type="number" class="form-control" id="delay" name="delay" placeholder="2" min="0" step="0.1">
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="mb-3">
                                    <label for="prefix" class="form-label">Prefix (tùy chọn):</label>
                                    <input type="text" class="form-control" id="prefix" name="prefix" placeholder="kt">
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="mb-3">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <button type="submit" name="send_codes" class="btn btn-primary">
                                            <i class="fas fa-paper-plane icon"></i>
                                            Gửi mã
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label for="codes" class="form-label">Danh sách mã (cách nhau bởi dấu phẩy):</label>
                            <textarea class="form-control" id="codes" name="codes" rows="3" placeholder="mã1, mã2, mã3, ..."></textarea>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <!-- Spam Control -->
        <div class="row">
            <div class="col-12">
                <div class="glass-container">
                    <h3 class="section-title">
                        <i class="fas fa-repeat icon"></i>
                        Spam Control
                    </h3>
                    <p class="text-light">Trạng thái spam: <span class="{spam_status}">{spam_text}</span></p>
                    <p class="text-light">Tin nhắn spam: <span class="text-info">"{spam_message_display}"</span></p>
                    <p class="text-light">Delay: <span class="text-warning">{spam_delay} giây</span></p>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, auto_grab_enabled_2, heart_threshold, heart_threshold_2
    global spam_enabled, spam_message, spam_delay
    global auto_work_enabled
    
    msg_status = ""
    
    if request.method == "POST":
        toggle_auto_grab = request.form.get("toggle_auto_grab")
        toggle_auto_grab_2 = request.form.get("toggle_auto_grab_2")
        update_heart_threshold = request.form.get("update_heart_threshold")
        update_heart_threshold_2 = request.form.get("update_heart_threshold_2")
        start_spam = request.form.get("start_spam")
        stop_spam = request.form.get("stop_spam")
        send_codes = request.form.get("send_codes")
        toggle_auto_work = request.form.get("toggle_auto_work")

        if toggle_auto_grab:
            auto_grab_enabled = not auto_grab_enabled
            msg_status = f"Auto Grab Acc chính 1: {'Bật' if auto_grab_enabled else 'Tắt'}"
        
        if toggle_auto_grab_2:
            auto_grab_enabled_2 = not auto_grab_enabled_2
            msg_status = f"Auto Grab Acc chính 2: {'Bật' if auto_grab_enabled_2 else 'Tắt'}"
        
        if toggle_auto_work:
            auto_work_enabled = not auto_work_enabled
            msg_status = f"Auto Work: {'Bật' if auto_work_enabled else 'Tắt'}"

        if update_heart_threshold:
            try:
                heart_threshold = int(request.form.get("heart_threshold"))
                msg_status = f"Đã cập nhật mức tim Acc chính 1: {heart_threshold}"
            except:
                msg_status = "Mức tim Acc chính 1 không hợp lệ!"

        if update_heart_threshold_2:
            try:
                heart_threshold_2 = int(request.form.get("heart_threshold_2"))
                msg_status = f"Đã cập nhật mức tim Acc chính 2: {heart_threshold_2}"
            except:
                msg_status = "Mức tim Acc chính 2 không hợp lệ!"

        if send_codes:
            acc_index = request.form.get("acc_index")
            delay = request.form.get("delay")
            prefix = request.form.get("prefix")
            codes = request.form.get("codes")

            if acc_index and delay and codes:
                try:
                    acc_idx = int(acc_index)
                    delay_val = float(delay)
                    codes_list = codes.split(",")
                    
                    # Sử dụng logic cũ - acc cuối cùng là main bot
                    if acc_idx < len(bots):
                        # Sử dụng bot phụ
                        selected_bot = bots[acc_idx]
                    elif acc_idx == len(bots) and main_bot:
                        # Sử dụng main bot (acc cuối cùng)
                        selected_bot = main_bot
                    else:
                        selected_bot = None
                    
                    if selected_bot:
                        for i, code in enumerate(codes_list):
                            code = code.strip()
                            if code:
                                final_msg = f"{prefix} {code}" if prefix else code
                                try:
                                    threading.Timer(delay_val * i, selected_bot.sendMessage, args=(other_channel_id, final_msg)).start()
                                except Exception as e:
                                    print(f"Lỗi gửi mã: {e}")
                except Exception as e:
                    print(f"Lỗi xử lý codes: {e}")

            msg_status = "Đã bắt đầu gửi mã!"

        if start_spam:
            spam_message = request.form.get("spam_message", "")
            spam_delay = int(request.form.get("spam_delay", 10))
            if spam_message:
                spam_enabled = True
                threading.Thread(target=spam_loop, daemon=True).start()
                msg_status = "Đã bắt đầu spam!"
            else:
                msg_status = "Vui lòng nhập nội dung tin nhắn!"

        if stop_spam:
            spam_enabled = False
            msg_status = "Đã dừng spam!"

    alert_section = f'<div class="alert alert-info" role="alert">{msg_status}</div>' if msg_status else ""
    
    auto_grab_status = "status-active" if auto_grab_enabled else "status-inactive"
    auto_grab_text = "Đang bật" if auto_grab_enabled else "Đang tắt"
    
    auto_grab_status_2 = "status-active" if auto_grab_enabled_2 else "status-inactive"
    auto_grab_text_2 = "Đang bật" if auto_grab_enabled_2 else "Đang tắt"
    
    spam_status = "status-active" if spam_enabled else "status-inactive"
    spam_text = "Đang bật" if spam_enabled else "Đang tắt"
    spam_message_display = spam_message if spam_message else "Chưa có"

    auto_work_status = "status-active" if auto_work_enabled else "status-inactive"
    auto_work_text = "Đang bật" if auto_work_enabled else "Đang tắt"

    # Tạo acc_options với tên gốc
    acc_options = "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names))

    return render_template_string(HTML.format(
        alert_section=alert_section,
        auto_grab_status=auto_grab_status,
        auto_grab_text=auto_grab_text,
        auto_grab_status_2=auto_grab_status_2,
        auto_grab_text_2=auto_grab_text_2,
        heart_threshold=heart_threshold,
        heart_threshold_2=heart_threshold_2,
        spam_status=spam_status,
        spam_text=spam_text,
        spam_message_display=spam_message_display,
        spam_delay=spam_delay,
        auto_work_status=auto_work_status,
        auto_work_text=auto_work_text,
        acc_options=acc_options
    ))

def spam_loop():
    global spam_enabled
    while spam_enabled:
        for bot in bots:
            if spam_enabled:
                try:
                    bot.sendMessage(spam_channel_id, spam_message)
                except Exception as e:
                    print(f"Lỗi spam: {e}")
        time.sleep(spam_delay)

def keep_alive():
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False), daemon=True).start()

if __name__ == "__main__":
    keep_alive()
    
    # Kết nối tất cả bots
    if main_bot:
        threading.Thread(target=main_bot.gateway.run, daemon=True).start()
    if main_bot_2:
        threading.Thread(target=main_bot_2.gateway.run, daemon=True).start()
    for bot in bots:
        threading.Thread(target=bot.gateway.run, daemon=True).start()
    
    # Giữ cho chương trình chạy
    while True:
        time.sleep(1)