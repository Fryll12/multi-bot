import discum
import time
import threading
import requests
import os
import sys
import random
from collections import deque
from flask import Flask, jsonify, render_template_string, request

# ===================================================================
# CẤU HÌNH VÀ BIẾN TOÀN CỤC
# ===================================================================

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
KARUTA_ID = "646937666251915264"

if not TOKEN or not CHANNEL_ID:
    print("LỖI: Vui lòng cung cấp DISCORD_TOKEN và CHANNEL_ID trong biến môi trường.", flush=True)
    sys.exit(1)

bot_thread = None
hourly_loop_thread = None
bot_instance = None
is_bot_running = False
is_hourly_loop_enabled = False
loop_delay_seconds = 3600
lock = threading.Lock()

# ===================================================================
# LOGIC BOT CHƠI EVENT (TÍCH HỢP TỪ FILE THAM KHẢO)
# ===================================================================

def run_event_bot_thread():
    """Hàm này chứa toàn bộ logic bot, chạy trong một luồng riêng."""
    global is_bot_running, bot_instance

    active_message_id = None
    action_queue = deque()

    bot = discum.Client(token=TOKEN, log=False)
    with lock:
        bot_instance = bot

    # --- LOGIC CLICK LẤY TỪ FILE THAM KHẢO CỦA BẠN (với fix session_id) ---
    def click_button_by_index(message_data, index):
        try:
            rows = [comp['components'] for comp in message_data.get('components', []) if 'components' in comp]
            all_buttons = [button for row in rows for button in row]
            if index >= len(all_buttons):
                print(f"LỖI: Không tìm thấy button ở vị trí {index}", flush=True)
                return

            button_to_click = all_buttons[index]
            custom_id = button_to_click.get("custom_id")
            if not custom_id: return

            # Dùng session id của gateway, đúng như code tham khảo
            session_id = bot.gateway.session_id

            headers = {"Authorization": TOKEN}
            payload = {
                "type": 3, "guild_id": message_data.get("guild_id"),
                "channel_id": message_data.get("channel_id"), "message_id": message_data.get("id"),
                "application_id": KARUTA_ID, "session_id": session_id,
                "data": {"component_type": 2, "custom_id": custom_id}
            }
            
            emoji_name = button_to_click.get('emoji', {}).get('name', 'Không có')
            print(f"INFO: Chuẩn bị click button ở vị trí {index} (Emoji: {emoji_name})", flush=True)
            
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
            
            if 200 <= r.status_code < 300:
                print(f"INFO: Click thành công! (Status: {r.status_code})", flush=True)
            else:
                print(f"LỖI: Click thất bại! (Status: {r.status_code}, Response: {r.text})", flush=True)
        except Exception as e:
            print(f"LỖI NGOẠI LỆ khi click button: {e}", flush=True)

    def perform_final_confirmation(message_data):
        print("ACTION: Chờ 2 giây để nút xác nhận cuối cùng load...", flush=True)
        time.sleep(2.0)
        click_button_by_index(message_data, 2)
        print("INFO: Đã hoàn thành lượt. Chờ game tự động cập nhật để bắt đầu lượt mới...", flush=True)

    # --- LOGIC CHƠI SỰ KIỆN LẤY TỪ FILE THAM KHẢO CỦA BẠN ---
    @bot.gateway.command
    def on_message(resp):
        nonlocal active_message_id, action_queue
        if not is_bot_running:
            bot.gateway.close()
            return
        
        if not (resp.event.message or resp.event.message_updated): return
        m = resp.parsed.auto()
        if not (m.get("author", {}).get("id") == KARUTA_ID and m.get("channel_id") == CHANNEL_ID): return
        
        action_to_perform = None
        
        with lock:
            if resp.event.message and "Takumi's Solisfair Stand" in m.get("embeds", [{}])[0].get("title", ""):
                if active_message_id is not None: return
                active_message_id = m.get("id")
                action_queue.clear()
                print(f"\nINFO: Bắt đầu game mới trên tin nhắn ID: {active_message_id}", flush=True)
            if m.get("id") != active_message_id: return

            embed_desc = m.get("embeds", [{}])[0].get("description", "")
            all_buttons_flat = [b for row in m.get('components', []) for b in row.get('components', []) if row.get('type') == 1]
            is_movement_phase = any(b.get('emoji', {}).get('name') == '▶️' for b in all_buttons_flat)
            is_final_confirm_phase = any(b.get('emoji', {}).get('name') == '❌' for b in all_buttons_flat)
            found_good_move = "If placed here, you will receive the following fruit:" in embed_desc
            has_received_fruit = "You received the following fruit:" in embed_desc

            if is_final_confirm_phase:
                action_to_perform = {"type": "final_confirm", "data": m}
            elif has_received_fruit:
                action_to_perform = {"type": "click", "index": 0, "data": m}
            elif is_movement_phase:
                if found_good_move:
                    action_queue.clear()
                    action_queue.append(0)
                elif not action_queue:
                    # Lấy đúng logic random 7-14 từ file tham khảo
                    num_moves = random.randint(7, 14)
                    movement_indices = [1, 2, 3, 4]
                    for _ in range(num_moves):
                        action_queue.append(random.choice(movement_indices))
                    action_queue.append(0)
                if action_queue:
                    next_action_index = action_queue.popleft()
                    action_to_perform = {"type": "click", "index": next_action_index, "data": m}
        
        if action_to_perform:
            action_type = action_to_perform["type"]
            if action_type == "final_confirm":
                threading.Thread(target=perform_final_confirmation, args=(action_to_perform["data"],)).start()
            elif action_type == "click":
                threading.Thread(target=click_button_by_index, args=(action_to_perform["data"], action_to_perform["index"])).start()
            
            # Khoảng nghỉ 2 giây giữa các hành động để tránh rate limit
            time.sleep(1.0)

    # Gửi lệnh đầu tiên khi luồng bắt đầu
    def send_initial_command():
        time.sleep(7)
        print("[EVENT BOT] Gửi lệnh 'kevent' đầu tiên...", flush=True)
        bot.sendMessage(CHANNEL_ID, "kevent")
    
    threading.Thread(target=send_initial_command).start()

    print("[EVENT BOT] Luồng bot đã khởi động và đang lắng nghe tin nhắn.", flush=True)
    bot.gateway.run(auto_reconnect=True)
    print("[EVENT BOT] Luồng bot đã dừng.", flush=True)


# ===================================================================
# CÁC HÀM TIỆN ÍCH VÀ VÒNG LẶP NỀN
# ===================================================================

def run_hourly_loop_thread():
    """Hàm này chứa vòng lặp gửi kevent, chạy trong một luồng riêng."""
    global is_hourly_loop_enabled, loop_delay_seconds
    print("[HOURLY LOOP] Luồng vòng lặp đã khởi động.", flush=True)
    while is_hourly_loop_enabled:
        for _ in range(loop_delay_seconds):
            if not is_hourly_loop_enabled:
                break
            time.sleep(1)
        with lock:
            if is_hourly_loop_enabled and bot_instance and is_bot_running:
                print(f"\n[HOURLY LOOP] Hết {loop_delay_seconds} giây. Tự động gửi lại lệnh 'kevent'...", flush=True)
                bot_instance.sendMessage(CHANNEL_ID, "kevent")
            else:
                break
    print("[HOURLY LOOP] Luồng vòng lặp đã dừng.", flush=True)

# ===================================================================
# WEB SERVER (FLASK) ĐỂ ĐIỀU KHIỂN
# ===================================================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solis-Fair Bot Control</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #121212; color: #e0e0e0; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; flex-direction: column; gap: 20px;}
        .panel { text-align: center; background-color: #1e1e1e; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.5); width: 400px; }
        h1, h2 { color: #bb86fc; } .status { font-size: 1.1em; margin: 15px 0; }
        .status-on { color: #03dac6; } .status-off { color: #cf6679; }
        button { background-color: #bb86fc; color: #121212; border: none; padding: 12px 24px; font-size: 1em; border-radius: 5px; cursor: pointer; transition: background-color 0.3s; font-weight: bold; }
        button:hover { background-color: #a050f0; } button.off-button { background-color: #444; color: #ccc; } button.off-button:hover { background-color: #555; }
        .input-group { display: flex; margin-top: 15px; } .input-group label { padding: 10px; background-color: #333; border-radius: 5px 0 0 5px; }
        .input-group input { flex-grow: 1; border: 1px solid #333; background-color: #222; color: #eee; padding: 10px; border-radius: 0 5px 5px 0; }
    </style>
</head>
<body>
    <div class="panel">
        <h1>Bot Event Solis-Fair</h1>
        <div id="bot-status" class="status">Trạng thái: Đang tải...</div>
        <button id="toggleBotBtn">Bắt đầu</button>
    </div>
    <div class="panel">
        <h2>Vòng lặp tự động</h2>
        <div id="loop-status" class="status">Trạng thái: Đang tải...</div>
        <div class="input-group">
            <label for="delay-input">Delay (giây)</label>
            <input type="number" id="delay-input" value="3600">
        </div>
        <button id="toggleLoopBtn" style="margin-top: 15px;">Bắt đầu</button>
    </div>
    <script>
        const botStatusDiv = document.getElementById('bot-status'), toggleBotBtn = document.getElementById('toggleBotBtn');
        const loopStatusDiv = document.getElementById('loop-status'), toggleLoopBtn = document.getElementById('toggleLoopBtn'), delayInput = document.getElementById('delay-input');
        async function postData(url, data) { await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }); fetchStatus(); }
        async function fetchStatus() {
            try {
                const r = await fetch('/api/status'), data = await r.json();
                botStatusDiv.textContent = data.is_bot_running ? 'Trạng thái: ĐANG CHẠY' : 'Trạng thái: ĐÃ DỪNG';
                botStatusDiv.className = data.is_bot_running ? 'status status-on' : 'status status-off';
                toggleBotBtn.textContent = data.is_bot_running ? 'DỪNG BOT' : 'BẬT BOT';
                loopStatusDiv.textContent = data.is_hourly_loop_enabled ? 'Trạng thái: ĐANG CHẠY' : 'Trạng thái: ĐÃ DỪNG';
                loopStatusDiv.className = data.is_hourly_loop_enabled ? 'status status-on' : 'status status-off';
                toggleLoopBtn.textContent = data.is_hourly_loop_enabled ? 'TẮT VÒNG LẶP' : 'BẬT VÒNG LẶP';
                delayInput.value = data.loop_delay_seconds;
            } catch (e) { botStatusDiv.textContent = 'Lỗi kết nối đến server.'; botStatusDiv.className = 'status status-off'; }
        }
        toggleBotBtn.addEventListener('click', () => postData('/api/toggle_bot', {}));
        toggleLoopBtn.addEventListener('click', () => {
            const currentStatus = loopStatusDiv.textContent.includes('ĐANG CHẠY');
            postData('/api/toggle_hourly_loop', { enabled: !currentStatus, delay: parseInt(delayInput.value, 10) });
        });
        setInterval(fetchStatus, 5000); fetchStatus();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/status")
def status():
    return jsonify({
        "is_bot_running": is_bot_running,
        "is_hourly_loop_enabled": is_hourly_loop_enabled,
        "loop_delay_seconds": loop_delay_seconds
    })

@app.route("/api/toggle_bot", methods=['POST'])
def toggle_bot():
    global bot_thread, is_bot_running
    with lock:
        if is_bot_running:
            is_bot_running = False; print("[CONTROL] Nhận được lệnh DỪNG bot.", flush=True)
        else:
            is_bot_running = True; print("[CONTROL] Nhận được lệnh BẬT bot.", flush=True)
            bot_thread = threading.Thread(target=run_event_bot_thread, daemon=True)
            bot_thread.start()
    return jsonify({"status": "ok"})

@app.route("/api/toggle_hourly_loop", methods=['POST'])
def toggle_hourly_loop():
    global hourly_loop_thread, is_hourly_loop_enabled, loop_delay_seconds
    data = request.get_json()
    with lock:
        is_hourly_loop_enabled = data.get('enabled')
        loop_delay_seconds = data.get('delay', 3600)
        if is_hourly_loop_enabled and (hourly_loop_thread is None or not hourly_loop_thread.is_alive()):
            hourly_loop_thread = threading.Thread(target=run_hourly_loop_thread, daemon=True)
            hourly_loop_thread.start()
    return jsonify({"status": "ok"})

# ===================================================================
# KHỞI CHẠY WEB SERVER
# ===================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"[SERVER] Khởi động Web Server tại http://0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
