import discum
import threading
import time
import os
import random
import re
import requests
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

# --- Tải biến môi trường ---
load_dotenv()

# --- CẤU HÌNH ---
main_token = os.getenv("MAIN_TOKEN")
tokens = os.getenv("TOKENS").split(",") if os.getenv("TOKENS") else []

# --- ID KÊNH VÀ BOT ---
main_channel_id = "1386973916563767396"  # Kênh drop chính
other_channel_id = "1387406577040101417" # Kênh gửi mã card và lệnh thủ công
ktb_channel_id = "1376777071279214662"   # Kênh chat riêng với Karuta Bot
spam_channel_id = "1388802151723302912"  # Kênh để spam
karuta_id = "646937666251915264"
karibbit_id = "1274445226064220273"

# --- BIẾN TRẠNG THÁI TOÀN CỤC ---
bots = []           # Danh sách các bot phụ (worker bots)
main_bot = None     # Bot chính (chỉ để auto-grab và gửi mã khi được chọn)
bots_lock = threading.Lock() # Khóa để tránh xung đột khi truy cập danh sách bot

# Cài đặt Auto Grab
auto_grab_enabled = False
heart_threshold = 50
last_drop_msg_id = ""

# Cài đặt Spam
spam_enabled = False
spam_message = ""
spam_delay = 30

# Cài đặt Auto Work (ĐÃ THÊM LẠI)
auto_work_enabled = False
work_channel_id = "1390851619016671246" # ID kênh mặc định, có thể thay đổi trên UI
work_delay_between_acc = 10
work_delay_after_all = 44100

# Danh sách tên các acc, acc cuối cùng tương ứng với main_token
acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", 
    "sly_dd" # Tên này tương ứng với main_bot
]

# =================================================================
# === HÀM TỰ ĐỘNG KẾT NỐI LẠI (AUTO-RECONNECT) ===
# =================================================================
def run_bot_with_reconnect(bot, bot_name):
    """Chạy bot trong một vòng lặp vô tận để đảm bảo nó luôn hoạt động."""
    while True:
        try:
            print(f"[{bot_name}] Đang kết nối gateway...")
            bot.gateway.run(auto_reconnect=True)
        except Exception as e:
            print(f"[{bot_name}] LỖI GATEWAY NGHIÊM TRỌNG: {e}. Đang thử kết nối lại sau 5 giây...")
        time.sleep(5)

# =================================================================
# === HÀM TẠO BOT (KHÔNG THAY ĐỔI) ===
# =================================================================
def create_bot(token, bot_name, is_main=False):
    """Hàm tạo và khởi chạy một bot."""
    if not token or not token.strip():
        print(f"[{bot_name}] Bỏ qua vì token rỗng.")
        return None
        
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                print(f"Đã đăng nhập thành công: {user_id} ({bot_name})")
            except Exception as e:
                print(f"[{bot_name}] Lỗi lấy user_id từ ready event: {e}")

    # CHỈ BOT CHÍNH MỚI CÓ LOGIC AUTO GRAB
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
                if author == karuta_id and channel == main_channel_id and "is dropping" not in content and not mentions and auto_grab_enabled:
                    print(f"\n[{bot_name}] Phát hiện tự drop! Đọc tin nhắn Karibbit...")
                    last_drop_msg_id = msg["id"]
                    def read_karibbit():
                        time.sleep(0.4)
                        try:
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for k_msg in messages:
                                author_id = k_msg.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in k_msg and len(k_msg["embeds"]) > 0:
                                    desc = k_msg["embeds"][0].get("description", "")
                                    print(f"[{bot_name}] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[{bot_name}] ===== Kết thúc tin nhắn =====")
                                    lines = desc.split('\n')
                                    heart_numbers = [int(m[1]) for line in lines[:3] if (m := re.findall(r'`([^`]*)`', line)) and len(m) >= 2 and m[1].isdigit()]
                                    if not heart_numbers:
                                        print(f"[{bot_name}] Không có số tim nào, bỏ qua.\n")
                                    else:
                                        max_num = max(heart_numbers)
                                        if max_num < heart_threshold:
                                            print(f"[{bot_name}] Số tim lớn nhất {max_num} < {heart_threshold}, không grab!\n")
                                        else:
                                            max_index = [i for i, line in enumerate(lines[:3]) if str(max_num) in line][0]
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 0.5, "2️⃣": 1.7, "3️⃣": 2.2}[emoji]
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

    threading.Thread(target=run_bot_with_reconnect, args=(bot, bot_name), daemon=True).start()
    return bot

# =================================================================
# === LOGIC AUTO WORK (ĐÃ THÊM LẠI - KHÔNG THAY ĐỔI) ===
# =================================================================
def run_work_bot(token, acc_index):
    """
    Hàm logic để một tài khoản thực hiện chuỗi hành động 'work'.
    Hàm này tạo một client riêng và sẽ tự đóng khi hoàn thành.
    """
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = {"Authorization": token, "Content-Type": "application/json"}
    step = {"value": 0}

    def send_command(command):
        print(f"[Work Acc {acc_index}] Gửi lệnh '{command}'...")
        bot.sendMessage(work_channel_id, command)

    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            payload = {"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "a", "data": {"component_type": 2, "custom_id": custom_id}}
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
            if str(m.get('channel_id')) != work_channel_id: return
            author_id = str(m.get('author', {}).get('id', ''))
            guild_id = m.get('guild_id')

            if step["value"] == 0 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', '')
                card_codes = re.findall(r'\b\w{6}\b', desc) # Tìm mã 6 ký tự
                if card_codes and len(card_codes) >= 10:
                    first_5, last_5 = card_codes[:5], card_codes[-5:]
                    print(f"[Work Acc {acc_index}] Mã đầu: {', '.join(first_5)}, Mã cuối: {', '.join(last_5)}")
                    for i, code in enumerate(last_5 + first_5):
                        time.sleep(1.5 + (0.5 if i==0 else 0))
                        bot.sendMessage(work_channel_id, f"kjw {code} {chr(97 + i)}")
                    time.sleep(1)
                    send_command("kn")
                    step["value"] = 1
            elif step["value"] == 1 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', '')
                lines = desc.split('\n')
                if len(lines) >= 2 and (match := re.search(r'\d+\.\s*`([^`]+)`', lines[1])):
                    resource = match.group(1)
                    print(f"[Work Acc {acc_index}] Tài nguyên chọn: {resource}")
                    time.sleep(2)
                    bot.sendMessage(work_channel_id, f"kjn `{resource}` a b c d e")
                    time.sleep(1)
                    send_command("kw")
                    step["value"] = 2
            elif step["value"] == 2 and author_id == karuta_id and 'components' in m:
                message_id = m['id']
                application_id = m.get('application_id', karuta_id)
                for comp in m['components']:
                    if comp['type'] == 1 and (btn := next((b for b in comp['components'] if b['type'] == 2), None)):
                        print(f"[Work Acc {acc_index}] Phát hiện button, custom_id: {btn['custom_id']}")
                        click_tick(work_channel_id, message_id, btn['custom_id'], application_id, guild_id)
                        step["value"] = 3
                        bot.gateway.close()
                        return

    print(f"[Work Acc {acc_index}] Bắt đầu hoạt động...")
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    time.sleep(3)
    send_command("kc o:ef")
    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout:
        time.sleep(1)
    bot.gateway.close()
    print(f"[Work Acc {acc_index}] Đã hoàn thành hoặc hết thời gian, chuẩn bị tới acc tiếp theo.")

def auto_work_loop():
    """Vòng lặp để chạy 'work' cho tất cả các bot phụ."""
    global auto_work_enabled
    while True:
        if auto_work_enabled:
            print("\n[Auto Work] Bắt đầu chu trình làm việc cho các tài khoản phụ...")
            with bots_lock:
                # auto-work sử dụng danh sách tokens, không phải danh sách bots
                current_tokens = tokens.copy()
            for i, token in enumerate(current_tokens):
                if token.strip():
                    print(f"[Auto Work] Đang chạy acc {i+1}...")
                    run_work_bot(token.strip(), i+1)
                    if i < len(current_tokens) - 1:
                        print(f"[Auto Work] Acc {i+1} xong, chờ {work_delay_between_acc} giây...")
                        time.sleep(work_delay_between_acc)
            print(f"[Auto Work] Hoàn thành tất cả acc, chờ {work_delay_after_all / 3600:.2f} giờ để lặp lại...")
            time.sleep(work_delay_after_all)
        else:
            time.sleep(10)

# =================================================================
# === CÁC HÀM CHỨC NĂNG NỀN KHÁC ===
# =================================================================
def spam_loop():
    """Vòng lặp để gửi tin nhắn spam từ các bot phụ."""
    global spam_enabled, spam_message, spam_delay
    while True:
        if spam_enabled and spam_message:
            with bots_lock:
                bots_to_spam = bots.copy()
            print(f"\n[Spam] Bắt đầu vòng lặp spam với {len(bots_to_spam)} bot...")
            for idx, bot in enumerate(bots_to_spam):
                try:
                    bot_name = acc_names[idx] if idx < len(acc_names) else f"Bot Phụ {idx}"
                    bot.sendMessage(spam_channel_id, spam_message)
                    print(f"[{bot_name}] đã gửi spam: {spam_message}")
                    time.sleep(2)
                except Exception as e:
                    print(f"Lỗi khi gửi spam từ bot {idx}: {e}")
            print(f"[Spam] Hoàn thành vòng lặp, chờ {spam_delay} giây...")
            time.sleep(spam_delay)
        else:
            time.sleep(5)

def keep_alive():
    """Hàm giữ cho web server chạy."""
    port = int(os.environ.get("PORT", 8080))
    print(f"Khởi động Web Server tại http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# =================================================================
# === GIAO DIỆN WEB (FLASK) ===
# =================================================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot Control Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        body { background-color: #121212; color: #e0e0e0; }
        .card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 1rem; }
        .card-header { background-color: #252525; border-bottom: 1px solid #333; }
        .form-control, .form-select { background-color: #2a2a2a; border-color: #444; color: #e0e0e0; }
        .form-control:focus, .form-select:focus { background-color: #333; border-color: #0d6efd; color: #fff; box-shadow: none; }
        .btn-primary { background-color: #0d6efd; border-color: #0d6efd; }
        .status-badge { font-weight: 600; }
        .status-on { color: #198754; }
        .status-off { color: #dc3545; }
    </style>
</head>
<body>
<div class="container py-5">
    <h1 class="text-center mb-4"><i class="fas fa-robot"></i> Bot Control Panel</h1>
    {{alert_html|safe}}
    <div class="row g-4">
        <!-- Auto Work Control -->
        <div class="col-lg-12">
            <div class="card">
                <div class="card-header"><h5><i class="fas fa-briefcase"></i> Auto Work (Acc Phụ)</h5></div>
                <div class="card-body">
                    <p>Trạng thái: <b class="status-badge {{'status-on' if auto_work_enabled else 'status-off'}}">{{'Đang Bật' if auto_work_enabled else 'Đang Tắt'}}</b></p>
                    <form method="POST" class="d-flex gap-2 mb-3">
                        <button name="toggle_work" value="on" type="submit" class="btn btn-success w-100"><i class="fas fa-play"></i> Bật</button>
                        <button name="toggle_work" value="off" type="submit" class="btn btn-danger w-100"><i class="fas fa-stop"></i> Tắt</button>
                    </form>
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <label for="work_channel_id" class="form-label">Work Channel ID:</label>
                                <input type="text" name="work_channel_id" id="work_channel_id" class="form-control" value="{{work_channel_id}}">
                            </div>
                            <div class="col-md-4">
                                <label for="work_delay_between_acc" class="form-label">Delay giữa các acc (s):</label>
                                <input type="number" name="work_delay_between_acc" id="work_delay_between_acc" class="form-control" value="{{work_delay_between_acc}}">
                            </div>
                            <div class="col-md-4">
                                <label for="work_delay_after_all" class="form-label">Delay mỗi vòng lặp (s):</label>
                                <input type="number" name="work_delay_after_all" id="work_delay_after_all" class="form-control" value="{{work_delay_after_all}}">
                            </div>
                        </div>
                        <button type="submit" name="update_work_settings" value="1" class="btn btn-primary mt-3 w-100"><i class="fas fa-save"></i> Lưu Cài Đặt Work</button>
                    </form>
                </div>
            </div>
        </div>
        <!-- Auto Grab Control -->
        <div class="col-md-6">
            <div class="card">
                <div class="card-header"><h5><i class="fas fa-hand-sparkles"></i> Auto Grab (Acc Chính)</h5></div>
                <div class="card-body">
                    <p>Trạng thái: <b class="status-badge {{'status-on' if auto_grab_enabled else 'status-off'}}">{{'Đang Bật' if auto_grab_enabled else 'Đang Tắt'}}</b></p>
                    <form method="POST" class="d-flex gap-2 mb-3">
                        <button name="toggle_grab" value="on" type="submit" class="btn btn-success w-100"><i class="fas fa-play"></i> Bật</button>
                        <button name="toggle_grab" value="off" type="submit" class="btn btn-danger w-100"><i class="fas fa-stop"></i> Tắt</button>
                    </form>
                    <form method="POST">
                        <label for="heart_threshold" class="form-label">Mức tim tối thiểu:</label>
                        <div class="input-group">
                            <input type="number" name="heart_threshold" id="heart_threshold" class="form-control" value="{{heart_threshold}}" min="0">
                            <button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Lưu</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        <!-- Spam Control -->
        <div class="col-md-6">
            <div class="card">
                <div class="card-header"><h5><i class="fas fa-comment-dots"></i> Spam Control (Acc Phụ)</h5></div>
                <div class="card-body">
                    <p>Trạng thái: <b class="status-badge {{'status-on' if spam_enabled else 'status-off'}}">{{'Đang Bật' if spam_enabled else 'Đang Tắt'}}</b></p>
                    <form method="POST">
                        <div class="mb-3"><label for="spam_message" class="form-label">Nội dung spam:</label><input type="text" name="spam_message" id="spam_message" class="form-control" value="{{spam_message}}"></div>
                        <div class="mb-3"><label for="spam_delay" class="form-label">Delay mỗi vòng lặp (s):</label><input type="number" name="spam_delay" id="spam_delay" class="form-control" value="{{spam_delay}}" min="1"></div>
                        <div class="d-flex gap-2"><button name="toggle_spam" value="on" type="submit" class="btn btn-success w-100"><i class="fas fa-play"></i> Bật</button><button name="toggle_spam" value="off" type="submit" class="btn btn-danger w-100"><i class="fas fa-stop"></i> Tắt</button></div>
                    </form>
                </div>
            </div>
        </div>
        <!-- Send Codes by Account -->
        <div class="col-12">
            <div class="card">
                <div class="card-header"><h5><i class="fas fa-list-ol"></i> Gửi Danh Sách Mã Theo Acc</h5></div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label for="acc_index" class="form-label">Chọn tài khoản:</label><select name="acc_index" id="acc_index" class="form-select">{{acc_options|safe}}</select></div>
                            <div class="col-md-6"><label for="code_delay" class="form-label">Delay giữa các mã (s):</label><input type="number" step="0.1" name="code_delay" id="code_delay" class="form-control" value="11"></div>
                            <div class="col-12"><label for="code_prefix" class="form-label">Nội dung mẫu (tiền tố):</label><input type="text" name="code_prefix" id="code_prefix" class="form-control" placeholder="vd: kt n"></div>
                            <div class="col-12"><label for="codes" class="form-label">Danh sách mã (cách nhau bằng dấu phẩy hoặc xuống dòng):</label><textarea name="codes" id="codes" class="form-control" rows="5"></textarea></div>
                            <div class="col-12"><button type="submit" name="send_codes" value="1" class="btn btn-primary w-100">Bắt Đầu Gửi</button></div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, heart_threshold, spam_enabled, spam_message, spam_delay, auto_work_enabled, work_channel_id, work_delay_between_acc, work_delay_after_all
    alert_html = ""
    if request.method == "POST":
        if 'toggle_grab' in request.form:
            auto_grab_enabled = request.form['toggle_grab'] == 'on'
            alert_html = f'<div class="alert alert-info">Auto Grab đã {"Bật" if auto_grab_enabled else "Tắt"}.</div>'
        elif 'heart_threshold' in request.form:
            heart_threshold = int(request.form['heart_threshold'])
            alert_html = f'<div class="alert alert-success">Đã cập nhật mức tim tối thiểu thành {heart_threshold}.</div>'
        elif 'toggle_spam' in request.form:
            spam_enabled = request.form['toggle_spam'] == 'on'
            spam_message = request.form.get('spam_message', '').strip()
            spam_delay = int(request.form.get('spam_delay', 30))
            alert_html = f'<div class="alert alert-info">Spam đã {"Bật" if spam_enabled else "Tắt"}.</div>'
        elif 'toggle_work' in request.form:
            auto_work_enabled = request.form['toggle_work'] == 'on'
            alert_html = f'<div class="alert alert-info">Auto Work đã {"Bật" if auto_work_enabled else "Tắt"}.</div>'
        elif 'update_work_settings' in request.form:
            work_channel_id = request.form.get('work_channel_id', work_channel_id)
            work_delay_between_acc = int(request.form.get('work_delay_between_acc', work_delay_between_acc))
            work_delay_after_all = int(request.form.get('work_delay_after_all', work_delay_after_all))
            alert_html = '<div class="alert alert-success">Đã cập nhật cài đặt Auto Work.</div>'
        elif 'send_codes' in request.form:
            try:
                acc_index = int(request.form.get('acc_index'))
                code_delay = float(request.form.get('code_delay', 11))
                code_prefix = request.form.get('code_prefix', '').strip()
                codes = [c.strip() for c in re.split(r'[,\n]', request.form.get('codes', '')) if c.strip()]
                if not codes:
                    alert_html = '<div class="alert alert-warning">Vui lòng nhập danh sách mã.</div>'
                elif 0 <= acc_index < len(acc_names):
                    target_bot = main_bot if acc_index == len(bots) else bots[acc_index]
                    bot_name = acc_names[acc_index]
                    if target_bot:
                        for i, code in enumerate(codes):
                            final_msg = f"{code_prefix} {code}" if code_prefix else code
                            threading.Timer(code_delay * i, target_bot.sendMessage, args=(other_channel_id, final_msg)).start()
                        alert_html = f'<div class="alert alert-success">Đã bắt đầu gửi {len(codes)} mã từ tài khoản {bot_name}.</div>'
                    else:
                        alert_html = f'<div class="alert alert-danger">Không tìm thấy bot cho tài khoản {bot_name}.</div>'
                else:
                    alert_html = '<div class="alert alert-danger">Lựa chọn tài khoản không hợp lệ.</div>'
            except (ValueError, TypeError) as e:
                alert_html = f'<div class="alert alert-danger">Lỗi dữ liệu đầu vào: {e}</div>'

    acc_options = "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names))
    return render_template_string(HTML_TEMPLATE, **locals())

# =================================================================
# === KHỐI CHẠY CHÍNH ===
# =================================================================
if __name__ == "__main__":
    print("--- KHỞI TẠO HỆ THỐNG BOT ---")
    with bots_lock:
        main_bot = create_bot(main_token, "Acc Chính (Grab)", is_main=True)
        for i, token in enumerate(tokens):
            bot_name = acc_names[i] if i < len(acc_names) else f"Bot Phụ {i}"
            worker_bot = create_bot(token.strip(), bot_name, is_main=False)
            if worker_bot:
                bots.append(worker_bot)
    print("\n--- KHỞI TẠO CÁC LUỒNG NỀN ---")
    threading.Thread(target=spam_loop, daemon=True).start()
    print("-> Luồng Spam đã sẵn sàng.")
    threading.Thread(target=auto_work_loop, daemon=True).start()
    print("-> Luồng Auto Work đã sẵn sàng.")
    threading.Thread(target=keep_alive, daemon=True).start()
    print("-> Luồng Web Server đã sẵn sàng.")
    print("\n--- HỆ THỐNG ĐÃ SẴN SÀNG ---")
    while True:
        time.sleep(3600)
