import discum
import time
import threading
import requests
import os
import sys
import random
from collections import deque
from flask import Flask, jsonify, render_template_string

# ===================================================================
# CẤU HÌNH VÀ BIẾN TOÀN CỤC
# ===================================================================

# --- Lấy cấu hình từ biến môi trường ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
KARUTA_ID = "646937666251915264"

# --- Kiểm tra biến môi trường ---
if not TOKEN or not CHANNEL_ID:
    print("LỖI: Vui lòng cung cấp DISCORD_TOKEN và CHANNEL_ID trong biến môi trường.")
    sys.exit(1)

# --- Biến trạng thái của Bot ---
bot_thread = None
is_bot_running = False
bot_instance = None
lock = threading.Lock()

# ===================================================================
# LOGIC BOT CHƠI EVENT (Gói gọn trong một hàm)
# ===================================================================

def run_solisfair_bot():
    global is_bot_running, bot_instance

    # Khởi tạo các biến riêng cho luồng bot
    active_message_id = None
    action_queue = deque()

    # Tạo đối tượng bot
    bot = discum.Client(token=TOKEN, log=False)
    with lock:
        bot_instance = bot

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
        time.sleep(2)
        click_button_by_index(message_data, 2)

    @bot.gateway.command
    def on_message(resp):
        nonlocal active_message_id, action_queue
        
        if not is_bot_running:
            bot.gateway.close()
            return
            
        if not (resp.event.message or resp.event.message_updated): return
        m = resp.parsed.auto()
        if not (m.get("author", {}).get("id") == KARUTA_ID and m.get("channel_id") == CHANNEL_ID): return
        
        # Logic xử lý game
        with lock:
            if resp.event.message and "Takumi's Solisfair Stand" in m.get("embeds", [{}])[0].get("title", ""):
                if active_message_id is not None: return
                active_message_id = m.get("id")
                action_queue.clear()
                print(f"[EVENT BOT] INFO: Bắt đầu game mới trên tin nhắn ID: {active_message_id}")
            
            if m.get("id") != active_message_id: return

        embed_desc = m.get("embeds", [{}])[0].get("description", "")
        all_buttons_flat = [b for row in m.get('components', []) for b in row.get('components', []) if row.get('type') == 1]
        
        is_movement_phase = any(b.get('emoji', {}).get('name') == '▶️' for b in all_buttons_flat)
        is_final_confirm_phase = any(b.get('emoji', {}).get('name') == '❌' for b in all_buttons_flat)
        found_good_move = "If placed here, you will receive the following fruit:" in embed_desc
        has_received_fruit = "You received the following fruit:" in embed_desc

        if is_final_confirm_phase:
            threading.Thread(target=perform_final_confirmation, args=(m,)).start()
        elif has_received_fruit:
            threading.Thread(target=click_button_by_index, args=(m, 0)).start()
        elif is_movement_phase:
            with lock:
                if found_good_move:
                    action_queue.clear()
                    action_queue.append(0)
                elif not action_queue:
                    num_moves = random.randint(10, 20)
                    movement_indices = [1, 2, 3, 4]
                    for _ in range(num_moves):
                        action_queue.append(random.choice(movement_indices))
                    action_queue.append(0)
                if action_queue:
                    next_action_index = action_queue.popleft()
                    threading.Thread(target=click_button_by_index, args=(m, next_action_index)).start()

    # Vòng lặp chính của gateway
    print("[EVENT BOT] Luồng bot đã khởi động.")
    bot.gateway.run(auto_reconnect=True)
    print("[EVENT BOT] Luồng bot đã dừng.")


# ===================================================================
# WEB SERVER (FLASK) ĐỂ ĐIỀU KHIỂN
# ===================================================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Solis-Fair Bot Control</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #121212; color: #e0e0e0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { text-align: center; background-color: #1e1e1e; padding: 40px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.5); }
        h1 { color: #bb86fc; }
        #status { font-size: 1.2em; margin: 20px 0; }
        .status-on { color: #03dac6; }
        .status-off { color: #cf6679; }
        button { background-color: #bb86fc; color: #121212; border: none; padding: 15px 30px; font-size: 1em; border-radius: 5px; cursor: pointer; transition: background-color 0.3s; }
        button:hover { background-color: #3700b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Solis-Fair Event Bot Control</h1>
        <div id="status">Trạng thái: Đang tải...</div>
        <button id="toggleBtn">Bắt đầu</button>
    </div>
    <script>
        const statusDiv = document.getElementById('status');
        const toggleBtn = document.getElementById('toggleBtn');

        async function fetchStatus() {
            const response = await fetch('/api/status');
            const data = await response.json();
            if (data.is_running) {
                statusDiv.textContent = 'Trạng thái: ĐANG CHẠY';
                statusDiv.className = 'status-on';
                toggleBtn.textContent = 'DỪNG BOT';
            } else {
                statusDiv.textContent = 'Trạng thái: ĐÃ DỪNG';
                statusDiv.className = 'status-off';
                toggleBtn.textContent = 'BẬT BOT & GỬI KEVENT';
            }
        }

        toggleBtn.addEventListener('click', async () => {
            await fetch('/api/toggle', { method: 'POST' });
            fetchStatus();
        });

        setInterval(fetchStatus, 3000);
        fetchStatus();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/status")
def status():
    return jsonify({"is_running": is_bot_running})

@app.route("/api/toggle", methods=['POST'])
def toggle_bot():
    global bot_thread, is_bot_running, bot_instance
    with lock:
        if is_bot_running:
            print("[CONTROL] Nhận được lệnh DỪNG bot.")
            is_bot_running = False
            if bot_instance:
                bot_instance.gateway.close()
            bot_thread = None
        else:
            print("[CONTROL] Nhận được lệnh BẬT bot.")
            is_bot_running = True
            bot_thread = threading.Thread(target=run_solisfair_bot, daemon=True)
            bot_thread.start()
            # Chờ một chút để bot kết nối rồi mới gửi lệnh
            time.sleep(7)
            if bot_instance:
                bot_instance.sendMessage(CHANNEL_ID, "kevent")
                print("[CONTROL] Đã gửi lệnh 'kevent' đầu tiên.")

    return jsonify({"status": "ok"})


# ===================================================================
# KHỞI CHẠY WEB SERVER
# ===================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"[SERVER] Khởi động Web Server tại http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
