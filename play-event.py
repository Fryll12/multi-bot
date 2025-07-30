from flask import Flask, request, render_template_string
import discum
import time
import threading
import json
import random
import requests
import os
from collections import deque
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# --- CẤU HÌNH ---
CHANNEL_ID = "1396508484203319447"
KARUTA_ID = "646937666251915264"

bot = discum.Client(token=TOKEN, log=False)
active_message_id = None
action_queue = deque()
lock = threading.Lock()
app = Flask(__name__)
kevent_enabled = True
kevent_delay = 3600

# ===================================================================
# HÀM LOGIC
# ===================================================================

def click_button_by_index(message_data, index):
    """Nhấn button bằng cách gửi request thủ công."""
    try:
        rows = [comp['components'] for comp in message_data.get('components', []) if 'components' in comp]
        all_buttons = [button for row in rows for button in row]
        if index >= len(all_buttons):
            print(f"LỖI: Không tìm thấy button ở vị trí {index}")
            return

        button_to_click = all_buttons[index]
        custom_id = button_to_click.get("custom_id")
        if not custom_id: return

        headers = {"Authorization": TOKEN}
        payload = {
            "type": 3, "guild_id": message_data.get("guild_id"),
            "channel_id": message_data.get("channel_id"), "message_id": message_data.get("id"),
            "application_id": KARUTA_ID, "session_id": bot.gateway.session_id,
            "data": {"component_type": 2, "custom_id": custom_id}
        }
        
        emoji_name = button_to_click.get('emoji', {}).get('name', 'Không có')
        print(f"INFO: Chuẩn bị click button ở vị trí {index} (Emoji: {emoji_name})")
        
        r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
        
        if 200 <= r.status_code < 300:
            print(f"INFO: Click thành công! (Status: {r.status_code})")
        else:
            print(f"LỖI: Click thất bại! (Status: {r.status_code}, Response: {r.text})")
        time.sleep(1.8)
    except Exception as e:
        print(f"LỖI NGOẠI LỆ khi click button: {e}")

def perform_final_confirmation(message_data):
    """Chờ 2 giây rồi mới nhấn nút xác nhận cuối cùng."""
    print("ACTION: Chờ 2 giây để nút xác nhận cuối cùng load...")
    time.sleep(2)
    click_button_by_index(message_data, 2)
    print("INFO: Đã hoàn thành lượt. Chờ game tự động cập nhật để bắt đầu lượt mới...")

# ===================================================================
# BỘ XỬ LÝ TIN NHẮN (GATEWAY)
# ===================================================================

@bot.gateway.command
def on_message(resp):
    global active_message_id, action_queue
    
    if not (resp.event.message or resp.event.message_updated): return
    m = resp.parsed.auto()
    if not (m.get("author", {}).get("id") == KARUTA_ID and m.get("channel_id") == CHANNEL_ID): return
    
    with lock:
        if resp.event.message and "Takumi's Solisfair Stand" in m.get("embeds", [{}])[0].get("title", ""):
            if active_message_id is not None: return
            active_message_id = m.get("id")
            action_queue.clear()
            print(f"\nINFO: Bắt đầu game mới trên tin nhắn ID: {active_message_id}")
        
        if m.get("id") != active_message_id: return

    embed_desc = m.get("embeds", [{}])[0].get("description", "")
    all_buttons_flat = [b for row in m.get('components', []) for b in row.get('components', []) if row.get('type') == 1]
    
    is_movement_phase = any(b.get('emoji', {}).get('name') == '▶️' for b in all_buttons_flat)
    is_final_confirm_phase = any(b.get('emoji', {}).get('name') == '❌' for b in all_buttons_flat)
    found_good_move = "If placed here, you will receive the following fruit:" in embed_desc
    has_received_fruit = "You received the following fruit:" in embed_desc # BIẾN MỚI

    # --- BỘ MÁY TRẠNG THÁI CUỐI CÙNG ---

    # ƯU TIÊN 1: Nếu là màn hình xác nhận cuối, thực hiện xác nhận.
    if is_final_confirm_phase:
        print("INFO: Phát hiện giai đoạn xác nhận cuối cùng. Thực hiện click cuối.")
        with lock:
            action_queue.clear() 
        threading.Thread(target=perform_final_confirmation, args=(m,)).start()

    # ƯU TIÊN 2 (MỚI): Nếu là màn hình đã nhận quả, nhấn nút 0.
    elif has_received_fruit:
        print("INFO: Phát hiện đã nhận được trái cây. Nhấn nút 0 để tiếp tục...")
        threading.Thread(target=click_button_by_index, args=(m, 0)).start()

    # ƯU TIÊN 3: Nếu là màn hình di chuyển, xử lý logic di chuyển.
    elif is_movement_phase:
        with lock:
            if found_good_move:
                print("INFO: NGẮT QUÃNG - Phát hiện nước đi có kết quả. Xóa hàng đợi và xác nhận ngay.")
                action_queue.clear()
                action_queue.append(0)
            
            elif not action_queue:
                print("INFO: Bắt đầu lượt mới. Tạo chuỗi hành động ngẫu nhiên...")
                num_moves = random.randint(4, 10)
                movement_indices = [1, 2, 3, 4] # Lên, Trái, Xuống, Phải
                for _ in range(num_moves):
                    action_queue.append(random.choice(movement_indices))
                action_queue.append(0)
                print(f"INFO: Chuỗi hành động mới ({len(action_queue)} bước): {list(action_queue)}")

            if action_queue:
                next_action_index = action_queue.popleft()
                threading.Thread(target=click_button_by_index, args=(m, next_action_index)).start()

def main():
    print("Đang kết nối với Discord Gateway...")
    bot.gateway.run(auto_reconnect=True)

@app.route("/", methods=["GET", "POST"])
def index():
    global kevent_enabled, kevent_delay
    msg = ""
    if request.method == "POST":
        if "toggle" in request.form:
            kevent_enabled = not kevent_enabled
        if "delay" in request.form:
            try:
                kevent_delay = int(request.form["delay"])
                msg = "Đã cập nhật thời gian delay!"
            except:
                msg = "Lỗi: Delay phải là số nguyên!"
    return render_template_string("""
    <h2>⚙️ Điều khiển Bot kevent</h2>
    <form method="post">
        <p>Trạng thái: <b style="color:{{'green' if enabled else 'red'}}">{{ 'BẬT' if enabled else 'TẮT' }}</b></p>
        <button name="toggle">Bật/Tắt</button><br><br>
        <label>Thời gian delay (giây):</label>
        <input type="text" name="delay" value="{{delay}}">
        <button type="submit">Cập nhật</button>
    </form>
    <p>{{msg}}</p>
    """, enabled=kevent_enabled, delay=kevent_delay, msg=msg)


def run_bot():
    print("Đang kết nối với Discord Gateway...")
    bot.gateway.run(auto_reconnect=True)

def kevent_loop():
    global kevent_enabled
    while True:
        if kevent_enabled:
            print(f"Gửi 'kevent' (delay: {kevent_delay} giây)")
            bot.sendMessage(CHANNEL_ID, "kevent")
        time.sleep(kevent_delay)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=kevent_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
