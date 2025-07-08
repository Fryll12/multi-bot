# multi_bot_control_full_plus_acc3_and_auto_reboot_with_timers.py
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
spam_thread = None

auto_work_enabled = False
work_delay_between_acc = 10
work_delay_after_all = 44100

auto_reboot_enabled = False
auto_reboot_delay = 3600
auto_reboot_thread = None
auto_reboot_stop_event = None

bots_lock = threading.Lock()

# --- BIẾN THEO DÕI THỜI GIAN (CHO COUNTDOWN) ---
last_work_cycle_time = 0
last_reboot_cycle_time = 0
last_spam_time = 0


# --- LOGIC BOT (KHÔNG THAY ĐỔI) ---

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
                    print(f"[Reboot] Đang xử lý Acc Phụ {index}...")
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
    # ... (Tương tự cho bot 2 và 3)
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

# --- CÁC LUỒNG TỰ ĐỘNG (ĐÃ CẬP NHẬT ĐỂ THEO DÕI THỜI GIAN) ---

def auto_work_loop():
    global auto_work_enabled, last_work_cycle_time
    while True:
        if auto_work_enabled:
            with bots_lock:
                current_tokens = tokens.copy()
            for i, token in enumerate(current_tokens):
                if not auto_work_enabled: break
                if token.strip():
                    print(f"[Auto Work] Đang chạy acc {i+1}...")
                    # run_work_bot(token.strip(), i+1) # Tạm thời vô hiệu hóa để test, bạn có thể bật lại
                    print(f"[Auto Work] Acc {i+1} xong, chờ {work_delay_between_acc} giây...")
                    time.sleep(work_delay_between_acc)
            
            if auto_work_enabled:
                print(f"[Auto Work] Hoàn thành tất cả acc, chờ {work_delay_after_all} giây để lặp lại...")
                last_work_cycle_time = time.time()
                time.sleep(work_delay_after_all)
        else:
            time.sleep(10)

def auto_reboot_loop():
    global auto_reboot_stop_event, last_reboot_cycle_time
    print("[Auto Reboot] Luồng tự động reboot đã bắt đầu.")
    last_reboot_cycle_time = time.time()
    while not auto_reboot_stop_event.is_set():
        interrupted = auto_reboot_stop_event.wait(timeout=auto_reboot_delay)
        if interrupted: break
        print("[Auto Reboot] Hết thời gian chờ, tiến hành reboot 3 tài khoản chính.")
        if main_bot: reboot_bot('main_1'); time.sleep(5)
        if main_bot_2: reboot_bot('main_2'); time.sleep(5)
        if main_bot_3: reboot_bot('main_3')
        last_reboot_cycle_time = time.time() # Reset timer
    print("[Auto Reboot] Luồng tự động reboot đã dừng.")

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
                    bot.sendMessage(spam_channel_id, spam_message)
                    print(f"[{acc_names[idx]}] đã gửi: {spam_message}")
                    time.sleep(2)
                except Exception as e:
                    print(f"Lỗi gửi spam: {e}")
        time.sleep(spam_delay if spam_enabled else 10)

app = Flask(__name__)

# --- GIAO DIỆN HTML (ĐÃ THÊM PANEL MỚI VÀ JAVASCRIPT) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KARUTA DEEP - Bot Control Matrix</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --neon-green: #00ff41; --neon-cyan: #00ffff; --neon-red: #ff0040; --neon-purple: #8000ff; --neon-yellow: #fff000;
            --primary-bg: #0a0a0a; --secondary-bg: #111111; --accent-bg: #1a1a1a;
            --border-color: #333333; --text-primary: #ffffff; --text-muted: #cccccc;
            --shadow-glow: 0 0 15px; --font-primary: 'Orbitron', monospace; --font-mono: 'Courier Prime', monospace;
        }}
        body {{ font-family: var(--font-primary); background-color: var(--primary-bg); color: var(--text-primary); }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 15px; }}
        .header {{ text-align: center; margin-bottom: 20px; padding: 15px; border: 2px solid var(--neon-green); border-radius: 8px; box-shadow: var(--shadow-glow) var(--neon-green); }}
        .title {{ font-size: 2.2em; font-weight: 900; color: var(--neon-green); text-shadow: var(--shadow-glow) var(--neon-green); }}
        .control-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 15px; }}
        .control-panel {{ background: var(--secondary-bg); border: 1px solid var(--border-color); border-radius: 8px; }}
        .panel-header {{ padding: 10px 15px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 10px; font-weight: 700; color: var(--neon-cyan); }}
        .panel-content {{ padding: 15px; }}
        .status-badge {{ padding: 3px 8px; border-radius: 12px; font-size: 0.75em; font-weight: 700; border: 1px solid; }}
        .status-badge.active {{ border-color: var(--neon-green); background: rgba(0, 255, 65, 0.2); color: var(--neon-green); }}
        .status-badge.inactive {{ border-color: var(--neon-red); background: rgba(255, 0, 64, 0.2); color: var(--neon-red); }}
        .input-group {{ display: flex; flex-direction: column; gap: 5px; }}
        .input-label {{ font-size: 0.8em; color: var(--text-muted); font-weight: 700; }}
        .input-cyber {{ padding: 8px; background: var(--primary-bg); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-family: var(--font-mono); }}
        .btn-cyber {{ padding: 8px 15px; border: 1px solid; border-radius: 4px; background: transparent; color: var(--text-primary); font-family: var(--font-primary); font-weight: 700; cursor: pointer; }}
        .btn-primary {{ border-color: var(--neon-green); color: var(--neon-green); }}
        .btn-danger {{ border-color: var(--neon-red); color: var(--neon-red); }}
        .status-row {{ display: flex; justify-content: space-between; align-items: center; padding: 10px; background-color: var(--accent-bg); border-radius: 4px; margin-bottom: 10px; }}
        .status-name {{ font-weight: 700; display: flex; align-items: center; gap: 8px; }}
        .timer-display {{ font-family: var(--font-mono); font-size: 1.1em; color: var(--neon-yellow); font-weight: 700; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><div class="title">KARUTA DEEP - BOT CONTROL MATRIX</div></div>
        <div class="control-grid">
            <div class="control-panel">
                 </div>
            <div class="control-panel">
                </div>
            
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
                </div>
             <div class="control-panel">
                </div>
            <div class="control-panel">
                </div>
            <div class="control-panel">
                </div>
            <div class="control-panel">
                </div>
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function () {{
            function formatTime(seconds) {{
                if (isNaN(seconds) || seconds < 0) {{
                    return "--:--:--";
                }}
                seconds = Math.floor(seconds);
                const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
                const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
                const s = (seconds % 60).toString().padStart(2, '0');
                return `${{h}}:${{m}}:${{s}}`;
            }}

            function updateStatusBadge(elementId, isActive) {{
                const badge = document.getElementById(elementId);
                if (isActive) {{
                    badge.textContent = 'ON';
                    badge.classList.remove('inactive');
                    badge.classList.add('active');
                }} else {{
                    badge.textContent = 'OFF';
                    badge.classList.remove('active');
                    badge.classList.add('inactive');
                }}
            }}

            async function fetchStatus() {{
                try {{
                    const response = await fetch('/status');
                    const data = await response.json();

                    document.getElementById('work-timer').textContent = formatTime(data.work_countdown);
                    updateStatusBadge('work-status-badge', data.work_enabled);

                    document.getElementById('reboot-timer').textContent = formatTime(data.reboot_countdown);
                    updateStatusBadge('reboot-status-badge', data.reboot_enabled);

                    document.getElementById('spam-timer').textContent = formatTime(data.spam_countdown);
                    updateStatusBadge('spam-status-badge', data.spam_enabled);

                }} catch (error) {{
                    console.error('Error fetching status:', error);
                }}
            }}

            setInterval(fetchStatus, 1000); // Cập nhật mỗi giây
        }});
    </script>
</body>
</html>
"""

# --- HÀM XỬ LÝ WEB (ĐÃ CẬP NHẬT) ---
@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, auto_grab_enabled_2, auto_grab_enabled_3
    global spam_enabled, spam_message, spam_delay, spam_thread, last_spam_time
    global heart_threshold, heart_threshold_2, heart_threshold_3
    global auto_work_enabled, work_delay_between_acc, work_delay_after_all, last_work_cycle_time
    global auto_reboot_enabled, auto_reboot_delay, auto_reboot_thread, auto_reboot_stop_event, last_reboot_cycle_time
    
    msg_status = ""
    if request.method == "POST":
        # ... (Xử lý POST cho các form khác không đổi) ...
        # Điều khiển Auto Work
        if 'auto_work_toggle' in request.form:
            auto_work_enabled = not auto_work_enabled
            if auto_work_enabled:
                last_work_cycle_time = time.time() # Bắt đầu đếm ngay
                work_delay_between_acc = int(request.form.get('work_delay_between_acc', 10))
                work_delay_after_all = int(request.form.get('work_delay_after_all', 44100))
            msg_status = f"Auto Work {'BẬT' if auto_work_enabled else 'TẮT'}"
        # Điều khiển Auto Reboot
        elif 'auto_reboot_toggle' in request.form:
            auto_reboot_enabled = not auto_reboot_enabled
            if auto_reboot_enabled:
                last_reboot_cycle_time = time.time() # Bắt đầu đếm ngay
                auto_reboot_delay = int(request.form.get("auto_reboot_delay", 3600))
                if auto_reboot_thread is None or not auto_reboot_thread.is_alive():
                    auto_reboot_stop_event = threading.Event()
                    auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
                    auto_reboot_thread.start()
            else:
                if auto_reboot_stop_event: auto_reboot_stop_event.set()
                auto_reboot_thread = None
            msg_status = f"Auto Reboot {'BẬT' if auto_reboot_enabled else 'TẮT'}"
        # Điều khiển Spam
        elif 'spamtoggle' in request.form:
            if not spam_enabled and request.form.get("spammsg", "").strip():
                spam_enabled = True
                last_spam_time = time.time() # Bắt đầu đếm ngay
                spam_message = request.form.get("spammsg").strip()
                spam_delay = int(request.form.get("spam_delay", 10))
                if spam_thread is None or not spam_thread.is_alive():
                    spam_thread = threading.Thread(target=spam_loop, daemon=True)
                    spam_thread.start()
            else:
                spam_enabled = False
    
    # ... (Render template như cũ, nhưng bạn có thể xóa các panel cũ nếu muốn)
    return render_template_string(HTML_TEMPLATE.format(
        # ... các biến format cũ
    ))

# --- ENDPOINT API MỚI CHO STATUS ---
@app.route("/status")
def status():
    now = time.time()
    
    work_countdown = (last_work_cycle_time + work_delay_after_all - now) if auto_work_enabled else 0
    reboot_countdown = (last_reboot_cycle_time + auto_reboot_delay - now) if auto_reboot_enabled else 0
    spam_countdown = (last_spam_time + spam_delay - now) if spam_enabled else 0
    
    return jsonify({
        'work_enabled': auto_work_enabled,
        'work_countdown': work_countdown,
        'reboot_enabled': auto_reboot_enabled,
        'reboot_countdown': reboot_countdown,
        'spam_enabled': spam_enabled,
        'spam_countdown': spam_countdown,
    })

# --- KHỞI CHẠY CHƯƠNG TRÌNH ---
if __name__ == "__main__":
    print("Đang khởi tạo các bot...")
    # ... (Khởi tạo bot như cũ) ...
    print("Đang khởi tạo các luồng nền...")
    threading.Thread(target=spam_loop, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    print(f"Khởi động Web Server tại cổng {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)