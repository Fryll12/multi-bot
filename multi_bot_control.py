# multi_bot_control_final_fix_reconnect.py
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
acc_names = [
     "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent",
]

spam_enabled = False
spam_message = ""
spam_delay = 10

auto_work_enabled = False
work_delay_between_acc = 10
work_delay_after_all = 44100

bots_lock = threading.Lock()

# <<< SỬA ĐỔI: Hàm reboot được đơn giản hóa cho 2 acc chính
def reboot_bot(target_id):
    """Khởi động lại một bot. Với acc chính, chỉ cần đóng kết nối, luồng quản lý sẽ tự reconnect."""
    global main_bot, main_bot_2, bots

    with bots_lock:
        print(f"[Reboot] Nhận được yêu cầu reboot cho target: {target_id}")
        if target_id == 'main_1' and main_bot:
            print("[Reboot] Đang đóng kết nối Acc Chính 1 để hệ thống tự khởi động lại...")
            try:
                main_bot.gateway.close()
            except Exception as e:
                print(f"[Reboot] Lỗi khi đóng Acc Chính 1: {e}")

        elif target_id == 'main_2' and main_bot_2:
            print("[Reboot] Đang đóng kết nối Acc Chính 2 để hệ thống tự khởi động lại...")
            try:
                main_bot_2.gateway.close()
            except Exception as e:
                print(f"[Reboot] Lỗi khi đóng Acc Chính 2: {e}")

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
                    # Acc phụ không có auto-reconnect nên cần tạo lại thủ công
                    bots[index] = create_bot(token_to_reboot.strip(), is_main=False)
                    print(f"[Reboot] Acc Phụ {index} đã được khởi động lại.")
                else:
                    print(f"[Reboot] Index không hợp lệ: {index}")
            except (ValueError, IndexError) as e:
                print(f"[Reboot] Lỗi xử lý target Acc Phụ: {e}")
        else:
            print(f"[Reboot] Target không xác định: {target_id}")

# <<< SỬA ĐỔI: Hàm create_bot không tự chạy bot nữa
def create_bot(token, is_main=False, is_main_2=False):
    if not token or not token.strip():
        print(f"[Lỗi Tạo Bot] Token trống hoặc không hợp lệ.")
        return None
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            user = resp.raw.get("user", {})
            user_id = user.get("id", "Không xác định")
            username = user.get("username", "Không xác định")
            bot_type = "(Acc chính 1)" if is_main else "(Acc chính 2)" if is_main_2 else ""
            print(f"Đã đăng nhập: {username} ({user_id}) {bot_type}")

    # ... Logic on_message của 2 acc chính giữ nguyên y hệt ...
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
                                            heart_numbers.append(int(matches[1]))
                                        else:
                                            heart_numbers.append(0)
                                    if sum(heart_numbers) > 0:
                                        max_num = max(heart_numbers)
                                        if max_num >= heart_threshold:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}[emoji]
                                            print(f"[Bot 1] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
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
                                            heart_numbers.append(int(matches[1]))
                                        else:
                                            heart_numbers.append(0)
                                    if sum(heart_numbers) > 0:
                                        max_num = max(heart_numbers)
                                        if max_num >= heart_threshold_2:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 0.8, "2️⃣": 1.8, "3️⃣": 2.5}[emoji]
                                            print(f"[Bot 2] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                            def grab_2():
                                                bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                bot.sendMessage(ktb_channel_id, "kt b")
                                            threading.Timer(delay, grab_2).start()
                                    break
                        threading.Thread(target=read_karibbit_2).start()

    # Bot phụ vẫn được tự chạy khi tạo ra
    if not is_main and not is_main_2:
        threading.Thread(target=bot.gateway.run, daemon=True).start()

    return bot

# <<< MỚI: Hàm quản lý kết nối cho Acc Chính 1
def manage_main_bot_1():
    """Luồng này quản lý vòng đời của Acc Chính 1, tự động kết nối lại khi có lỗi."""
    global main_bot
    while True:
        try:
            print("[Quản lý] Đang khởi tạo và kết nối Acc Chính 1...")
            main_bot = create_bot(main_token, is_main=True)
            if main_bot:
                main_bot.gateway.run(auto_reconnect=True) # Chạy và chặn luồng này
            else:
                print("[Quản lý] Lỗi nghiêm trọng: Không thể tạo Acc Chính 1, token có thể sai. Dừng luồng.")
                break # Thoát vòng lặp nếu không tạo được bot
        except Exception as e:
            print(f"[Quản lý] Acc Chính 1 mất kết nối hoặc gặp lỗi: {e}")
            main_bot = None # Xóa đối tượng bot cũ
            print("[Quản lý] Sẽ thử kết nối lại Acc Chính 1 sau 30 giây...")
            time.sleep(30)

# <<< MỚI: Hàm quản lý kết nối cho Acc Chính 2
def manage_main_bot_2():
    """Luồng này quản lý vòng đời của Acc Chính 2, tự động kết nối lại khi có lỗi."""
    global main_bot_2
    while True:
        try:
            print("[Quản lý] Đang khởi tạo và kết nối Acc Chính 2...")
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
            if main_bot_2:
                main_bot_2.gateway.run(auto_reconnect=True) # Chạy và chặn luồng này
            else:
                print("[Quản lý] Lỗi nghiêm trọng: Không thể tạo Acc Chính 2, token có thể sai. Dừng luồng.")
                break # Thoát vòng lặp nếu không tạo được bot
        except Exception as e:
            print(f"[Quản lý] Acc Chính 2 mất kết nối hoặc gặp lỗi: {e}")
            main_bot_2 = None # Xóa đối tượng bot cũ
            print("[Quản lý] Sẽ thử kết nối lại Acc Chính 2 sau 30 giây...")
            time.sleep(30)

# Các hàm auto work, spam, flask app... giữ nguyên

def run_work_bot(token, acc_index):
    # ... code y hệt, không thay đổi
    pass

def auto_work_loop():
    # ... code y hệt, không thay đổi
    pass

app = Flask(__name__)
HTML = """
... Toàn bộ HTML của bạn giữ nguyên, không thay đổi ...
"""

@app.route("/", methods=["GET", "POST"])
def index():
    # ... code y hệt, không thay đổi
    global auto_grab_enabled, auto_grab_enabled_2, spam_enabled, spam_message, spam_delay, heart_threshold, heart_threshold_2, auto_work_enabled
    msg_status = ""

    if request.method == "POST":
        # ... logic xử lý form giữ nguyên
        pass

    # ... logic hiển thị trang web giữ nguyên
    return render_template_string(HTML.format(
        # ... các biến format giữ nguyên
    ))

def spam_loop():
    # ... code y hệt, không thay đổi
    pass

def keep_alive():
    # ... code y hệt, không thay đổi
    pass

if __name__ == "__main__":
    print("--- BẮT ĐẦU KHỞI TẠO HỆ THỐNG ---")

    # <<< SỬA ĐỔI: Khởi tạo các luồng quản lý cho acc chính
    print("1. Khởi tạo các luồng quản lý cho tài khoản chính (có tự động reconnect)...")
    if main_token:
        threading.Thread(target=manage_main_bot_1, daemon=True).start()
    else:
        print("   - Không tìm thấy MAIN_TOKEN, bỏ qua Acc Chính 1.")
    
    if main_token_2:
        threading.Thread(target=manage_main_bot_2, daemon=True).start()
    else:
        print("   - Không tìm thấy MAIN_TOKEN_2, bỏ qua Acc Chính 2.")

    # Khởi tạo các bot phụ (không có auto-reconnect)
    print("\n2. Khởi tạo các tài khoản phụ...")
    with bots_lock:
        for token in tokens:
            if token.strip():
                bots.append(create_bot(token.strip(), is_main=False))
    print(f"   - Đã khởi tạo {len(bots)} tài khoản phụ.")

    print("\n3. Khởi tạo các luồng nền khác (Spam, Auto Work)...")
    threading.Thread(target=spam_loop, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    print("   - Các luồng nền đã sẵn sàng.")

    port = int(os.environ.get("PORT", 8080))
    print(f"\n4. Khởi động Web Server tại cổng {port}...")
    print("--- HỆ THỐNG SẴN SÀNG ---")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)