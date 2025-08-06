import discum
import time
import threading
import json
import random
import requests
import os
import sys
from collections import deque
from flask import Flask, jsonify, render_template_string, request
from dotenv import load_dotenv
from threading import Thread, RLock

# ===================================================================
# CẤU HÌNH VÀ BIẾN TOÀN CỤC
# ===================================================================

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
KARUTA_ID = "646937666251915264"

if not TOKEN or not CHANNEL_ID:
    print("LỖI: Vui lòng cung cấp DISCORD_TOKEN và CHANNEL_ID trong biến môi trường.", flush=True)
    sys.exit(1)

# --- Các biến trạng thái ---
bot_thread = None
hourly_loop_thread = None
bot_instance = None
is_bot_running = False
is_hourly_loop_enabled = False
loop_delay_seconds = 3600
lock = RLock()

# --- Biến cho Event Bot ---
active_message_id = None
action_queue = deque()

# --- Biến cho Spammer ---
spam_panels = []
panel_id_counter = 0
spam_thread = None

# --- Biến cho Auto Clicker ---
is_auto_clicker_running = False
auto_clicker_message_id = None
auto_clicker_button_index = 0
auto_clicker_clicks_left = 0

# ===================================================================
# HÀM LOGIC CHUNG
# ===================================================================

def reset_game_state():
    global active_message_id, action_queue
    with lock:
        print("[RESET] Đang reset trạng thái game event...", flush=True)
        active_message_id = None
        action_queue.clear()
        print("[RESET] Bot event đã sẵn sàng nhận game mới.", flush=True)

# ===================================================================
# LOGIC SPAMMER
# ===================================================================
def spam_loop():
    bot = discum.Client(token=TOKEN, log=False)
    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            print("[SPAM BOT] Gateway đã kết nối. Luồng spam đã sẵn sàng.", flush=True)
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    time.sleep(5)
    while True:
        try:
            with lock:
                panels_to_process = list(spam_panels)
            for panel in panels_to_process:
                if panel['is_active'] and panel['channel_id'] and panel['message']:
                    current_time = time.time()
                    if current_time - panel['last_spam_time'] >= panel['delay']:
                        print(f"INFO: Gửi spam tới kênh {panel['channel_id']} (ID Bảng: {panel['id']})", flush=True)
                        try:
                            bot.sendMessage(str(panel['channel_id']), str(panel['message']))
                            with lock:
                                for p in spam_panels:
                                    if p['id'] == panel['id']: p['last_spam_time'] = current_time
                        except Exception as e:
                            print(f"LỖI: Không thể gửi tin nhắn tới kênh {panel['channel_id']}. Lỗi: {e}", flush=True)
                            with lock:
                                for p in spam_panels:
                                    if p['id'] == panel['id']: p['is_active'] = False
            time.sleep(1)
        except Exception as e:
            print(f"LỖI NGOẠI LỆ trong vòng lặp spam: {e}", flush=True)
            time.sleep(5)

# ===================================================================
# LOGIC EVENT BOT
# ===================================================================
def run_event_bot_thread():
    global is_bot_running, bot_instance, active_message_id, action_queue
    global is_auto_clicker_running, auto_clicker_message_id, auto_clicker_button_index, auto_clicker_clicks_left

    bot = discum.Client(token=TOKEN, log=False)
    with lock:
        bot_instance = bot

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
            headers = {"Authorization": TOKEN}
            max_retries = 40
            for attempt in range(max_retries):
                session_id = bot.gateway.session_id
                if not session_id:
                    time.sleep(2)
                    continue
                payload = {"type": 3, "guild_id": message_data.get("guild_id"), "channel_id": message_data.get("channel_id"), "message_id": message_data.get("id"), "application_id": KARUTA_ID, "session_id": session_id, "data": {"component_type": 2, "custom_id": custom_id}}
                emoji_name = button_to_click.get('emoji', {}).get('name', 'Không có')
                print(f"INFO (Lần {attempt + 1}): Chuẩn bị click button ở vị trí {index} (Emoji: {emoji_name})", flush=True)
                try:
                    r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload, timeout=10)
                    if 200 <= r.status_code < 300:
                        print(f"INFO: Click thành công! (Status: {r.status_code})", flush=True)
                        time.sleep(2.5)
                        return
                    elif r.status_code == 429:
                        retry_after = r.json().get("retry_after", 1.5)
                        print(f"WARN: Bị rate limit! Sẽ thử lại sau {retry_after:.2f} giây...", flush=True)
                        time.sleep(retry_after)
                    else:
                        print(f"LỖI: Click thất bại! (Status: {r.status_code}, Response: {r.text})", flush=True)
                        return
                except requests.exceptions.RequestException as e:
                    print(f"LỖI KẾT NỐI: {e}. Sẽ thử lại sau 3 giây...", flush=True)
                    time.sleep(3)
            print(f"LỖI: Đã thử click {max_retries} lần mà không thành công.", flush=True)
            reset_game_state()
        except Exception as e:
            print(f"LỖI NGOẠI LỆ trong hàm click_button_by_index: {e}", flush=True)
            reset_game_state()

    def perform_final_confirmation(message_data):
        print("ACTION: Chờ 2 giây để nút xác nhận cuối cùng load...", flush=True)
        time.sleep(2)
        click_button_by_index(message_data, 2)
        print("INFO: Đã hoàn thành lượt.", flush=True)

    @bot.gateway.command
    def on_message(resp):
        global active_message_id, action_queue
        global is_auto_clicker_running, auto_clicker_message_id, auto_clicker_button_index, auto_clicker_clicks_left
        if not is_bot_running:
            bot.gateway.close()
            return
        if not (resp.event.message or resp.event.message_updated): return
        m = resp.parsed.auto()
        if not (m.get("author", {}).get("id") == KARUTA_ID and m.get("channel_id") == CHANNEL_ID): return

        # --- LOGIC MỚI CHO AUTO CLICKER (ƯU TIÊN HÀNG ĐẦU) ---
        with lock:
            if is_auto_clicker_running and m.get("id") == auto_clicker_message_id:
                if auto_clicker_clicks_left > 0:
                    print(f"[Auto Clicker] Còn lại {auto_clicker_clicks_left} lần click. Thực hiện click nút {auto_clicker_button_index}...", flush=True)
                    threading.Thread(target=click_button_by_index, args=(m, auto_clicker_button_index)).start()
                    auto_clicker_clicks_left -= 1
                if auto_clicker_clicks_left <= 0:
                    print("[Auto Clicker] Đã hoàn thành chuỗi click.", flush=True)
                    is_auto_clicker_running = False
                return

        # --- LOGIC CHƠI EVENT ---
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
            print("INFO: Phát hiện giai đoạn xác nhận cuối cùng. Thực hiện click cuối.", flush=True)
            with lock:
                action_queue.clear()
            threading.Thread(target=perform_final_confirmation, args=(m,)).start()
        elif has_received_fruit:
            print("INFO: Phát hiện đã nhận được trái cây. Nhấn nút 0 để tiếp tục...", flush=True)
            threading.Thread(target=click_button_by_index, args=(m, 0)).start()
        elif is_movement_phase:
            with lock:
                if found_good_move:
                    print("INFO: NGẮT QUÃNG - Phát hiện nước đi có kết quả. Xóa hàng đợi và xác nhận ngay.", flush=True)
                    action_queue.clear()
                    action_queue.append(0)
                elif not action_queue:
                    print("INFO: Bắt đầu lượt mới. Tạo chuỗi hành động kết hợp...", flush=True)
                    fixed_sequence = [1, 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 1, 1, 1, 1, 2, 2, 3, 3]
                    action_queue.extend(fixed_sequence)
                    num_moves = random.randint(4, 14)
                    movement_indices = [1, 2, 3, 4]
                    random_sequence = [random.choice(movement_indices) for _ in range(num_moves)]
                    action_queue.extend(random_sequence)
                    action_queue.append(0)
                    print(f"INFO: Chuỗi hành động mới có tổng cộng {len(action_queue)} bước.", flush=True)
                if action_queue:
                    next_action_index = action_queue.popleft()
                    threading.Thread(target=click_button_by_index, args=(m, next_action_index)).start()

    initial_kevent_sent = False
    @bot.gateway.command
    def on_ready(resp):
        nonlocal initial_kevent_sent
        if resp.event.ready_supplemental and not initial_kevent_sent:
            print("[EVENT BOT] Gateway đã sẵn sàng. Gửi lệnh 'kevent' đầu tiên...", flush=True)
            bot.sendMessage(CHANNEL_ID, "kevent")
            initial_kevent_sent = True

    print("[EVENT BOT] Luồng bot đã khởi động, đang kết nối gateway...", flush=True)
    bot.gateway.run(auto_reconnect=True)
    print("[EVENT BOT] Luồng bot đã dừng.", flush=True)

# ===================================================================
# VÒNG LẶP TỰ ĐỘNG
# ===================================================================
def run_hourly_loop_thread():
    global is_hourly_loop_enabled, loop_delay_seconds
    while is_hourly_loop_enabled:
        time.sleep(loop_delay_seconds)
        with lock:
            if is_hourly_loop_enabled and bot_instance and is_bot_running:
                print(f"\n[HOURLY LOOP] Hết {loop_delay_seconds} giây. Reset và gửi lại lệnh 'kevent'...", flush=True)
                reset_game_state()
                bot_instance.sendMessage(CHANNEL_ID, "kevent")
    print("[HOURLY LOOP] Luồng vòng lặp đã dừng.", flush=True)

# ===================================================================
# WEB SERVER (FLASK)
# ===================================================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot Control Panel</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #121212; color: #e0e0e0; display: flex; flex-direction: column; align-items: center; gap: 20px; padding: 20px;}
        .container { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; width: 100%; }
        .panel { text-align: center; background-color: #1e1e1e; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.5); width: 400px; }
        h1, h2 { color: #bb86fc; } .status { font-size: 1.1em; margin: 15px 0; }
        .status-on { color: #03dac6; } .status-off { color: #cf6679; }
        button { background-color: #bb86fc; color: #121212; border: none; padding: 12px 24px; font-size: 1em; border-radius: 5px; cursor: pointer; transition: background-color 0.3s; font-weight: bold; }
        button:hover { background-color: #a050f0; }
        .input-group { display: flex; margin-top: 15px; } .input-group label { padding: 10px; background-color: #333; border-radius: 5px 0 0 5px; min-width: 100px; text-align: left;}
        .input-group input { flex-grow: 1; border: 1px solid #333; background-color: #222; color: #eee; padding: 10px; border-radius: 0 5px 5px 0; }
        #panel-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; margin-top: 20px; width: 100%; }
        .spam-panel { background-color: #2a2a2a; padding: 20px; border-radius: 10px; display: flex; flex-direction: column; gap: 15px; border-left: 5px solid #333; }
        .spam-panel.active { border-left-color: #03dac6; }
        .spam-panel input, .spam-panel textarea { width: 100%; box-sizing: border-box; border: 1px solid #444; background-color: #333; color: #eee; padding: 10px; border-radius: 5px; font-size: 1em; }
        .spam-panel textarea { resize: vertical; min-height: 80px; }
        .spam-panel-controls { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
        .spam-panel-controls button { flex-grow: 1; }
        .delete-btn { background-color: #cf6679 !important; }
        .add-panel-btn { width: 100%; max-width: 840px; padding: 20px; font-size: 1.5em; margin-top: 20px; background-color: rgba(3, 218, 198, 0.2); border: 2px dashed #03dac6; color: #03dac6; cursor: pointer; border-radius: 10px;}
        .timer { font-size: 0.9em; color: #888; text-align: right; }
    </style>
</head>
<body>
    <div class="container">
        <div class="panel">
            <h1>Bot Event Solis-Fair</h1>
            <div id="bot-status" class="status">Trạng thái: Đang tải...</div>
            <button id="toggleBotBtn">Bắt đầu</button>
        </div>
        <div class="panel">
            <h2>Vòng lặp tự động Event</h2>
            <div id="loop-status" class="status">Trạng thái: Đang tải...</div>
            <div class="input-group">
                <label for="delay-input">Delay (giây)</label>
                <input type="number" id="delay-input" value="3600">
            </div>
            <button id="toggleLoopBtn" style="margin-top: 15px;">Bắt đầu</button>
        </div>
    </div>
    <div class="panel">
        <h2><i class="fas fa-mouse-pointer"></i> Auto Clicker</h2>
        <div class="input-group">
            <label for="clicker-button-index">Button Index</label>
            <input type="number" id="clicker-button-index" value="0" placeholder="Vị trí nút (từ 0)">
        </div>
        <div class="input-group">
            <label for="clicker-times">Số lần click</label>
            <input type="number" id="clicker-times" value="10" placeholder="Nhập số lần click">
        </div>
        <div id="auto-clicker-status" class="status">Trạng thái: ĐÃ DỪNG</div>
        <button id="toggle-auto-clicker-btn">BẬT</button>
    </div>
    <div class="panel" style="width: auto; max-width: 800px;">
        <h2>Bảng Điều Khiển Spam</h2>
        <div id="panel-container"></div>
        <button class="add-panel-btn" onclick="addPanel()">+</button>
    </div>
    <script>
        // --- SCRIPT CHUNG ---
        async function apiCall(endpoint, method = 'GET', body = null) {
            const options = { method, headers: {'Content-Type': 'application/json'} };
            if (body) options.body = JSON.stringify(body);
            const response = await fetch(endpoint, options);
            return response.json();
        }

        // --- SCRIPT CHO EVENT BOT ---
        const botStatusDiv = document.getElementById('bot-status'), toggleBotBtn = document.getElementById('toggleBotBtn');
        const loopStatusDiv = document.getElementById('loop-status'), toggleLoopBtn = document.getElementById('toggleLoopBtn'), delayInput = document.getElementById('delay-input');
        async function fetchStatus() {
            try {
                const r = await fetch('/api/status'), data = await r.json();
                botStatusDiv.textContent = data.is_bot_running ? 'Trạng thái: ĐANG CHẠY' : 'Trạng thái: ĐÃ DỪNG';
                botStatusDiv.className = data.is_bot_running ? 'status status-on' : 'status status-off';
                toggleBotBtn.textContent = data.is_bot_running ? 'DỪNG BOT' : 'BẬT BOT';
                loopStatusDiv.textContent = data.is_hourly_loop_enabled ? 'Trạng thái: ĐANG CHẠY' : 'Trạng thái: ĐÃ DỪNG';
                loopStatusDiv.className = data.is_hourly_loop_enabled ? 'status status-on' : 'status status-off';
                toggleLoopBtn.textContent = data.is_hourly_loop_enabled ? 'TẮT VÒNG LẶP' : 'BẬT VÒNG LẶP';
                if (document.activeElement !== delayInput) { delayInput.value = data.loop_delay_seconds; }
            } catch (e) { botStatusDiv.textContent = 'Lỗi kết nối đến server.'; }
        }
        toggleBotBtn.addEventListener('click', () => apiCall('/api/toggle_bot', 'POST').then(fetchStatus));
        toggleLoopBtn.addEventListener('click', () => {
            const currentStatus = loopStatusDiv.textContent.includes('ĐANG CHẠY');
            apiCall('/api/toggle_hourly_loop', 'POST', { enabled: !currentStatus, delay: parseInt(delayInput.value, 10) }).then(fetchStatus);
        });
        
        // --- SCRIPT CHO SPAMMER ---
        function createPanelElement(panel) {
            const div = document.createElement('div');
            div.className = `spam-panel ${panel.is_active ? 'active' : ''}`;
            div.dataset.id = panel.id;
            let countdown = panel.is_active ? panel.delay - (Date.now() / 1000 - panel.last_spam_time) : panel.delay;
            countdown = Math.max(0, Math.ceil(countdown));
            div.innerHTML = `<textarea class="message-input" placeholder="Nội dung spam...">${panel.message}</textarea><input type="text" class="channel-input" placeholder="ID Kênh..." value="${panel.channel_id}"><input type="number" class="delay-input" placeholder="Delay (giây)..." value="${panel.delay}"><div class="panel-controls"><button class="toggle-btn">${panel.is_active ? 'TẮT' : 'BẬT'}</button><button class="delete-btn">XÓA</button></div><div class="timer">Hẹn giờ: ${countdown}s</div>`;
            const updatePanelData = () => { const updatedPanel = { ...panel, message: div.querySelector('.message-input').value, channel_id: div.querySelector('.channel-input').value, delay: parseInt(div.querySelector('.delay-input').value, 10) || 60 }; apiCall('/api/panel/update', 'POST', updatedPanel); };
            div.querySelector('.toggle-btn').addEventListener('click', () => {
                const updatedPanel = { ...panel, message: div.querySelector('.message-input').value, channel_id: div.querySelector('.channel-input').value, delay: parseInt(div.querySelector('.delay-input').value, 10) || 60, is_active: !panel.is_active };
                apiCall('/api/panel/update', 'POST', updatedPanel).then(fetchPanels);
            });
            div.querySelector('.delete-btn').addEventListener('click', () => { if (confirm('Xóa bảng này?')) apiCall('/api/panel/delete', 'POST', { id: panel.id }).then(fetchPanels); });
            div.querySelector('.message-input').addEventListener('change', updatePanelData);
            div.querySelector('.channel-input').addEventListener('change', updatePanelData);
            div.querySelector('.delay-input').addEventListener('change', updatePanelData);
            return div;
        }
        async function fetchPanels() {
            const focusedElement = document.activeElement;
            if (focusedElement && (focusedElement.tagName === 'INPUT' || focusedElement.tagName === 'TEXTAREA')) {
                const panel = focusedElement.closest('.spam-panel');
                if (panel) return;
            }
            const data = await apiCall('/api/panels');
            const container = document.getElementById('panel-container');
            container.innerHTML = '';
            data.panels.forEach(panel => container.appendChild(createPanelElement(panel)));
        }
        async function addPanel() { await apiCall('/api/panel/add', 'POST'); fetchPanels(); }

        // --- SCRIPT MỚI CHO AUTO CLICKER ---
        const autoClickerStatus = document.getElementById('auto-clicker-status');
        const toggleAutoClickerBtn = document.getElementById('toggle-auto-clicker-btn');
        const clickerButtonIndexInput = document.getElementById('clicker-button-index');
        const clickerTimesInput = document.getElementById('clicker-times');

        async function fetchAutoClickerStatus() {
            try {
                const r = await fetch('/api/auto_clicker_status');
                const data = await r.json();
                autoClickerStatus.textContent = `Trạng thái: ${data.is_running ? `ĐANG CHẠY (${data.clicks_left} lần còn lại)` : 'ĐÃ DỪNG'}`;
                autoClickerStatus.className = data.is_running ? 'status status-on' : 'status status-off';
                toggleAutoClickerBtn.textContent = data.is_running ? 'DỪNG' : 'BẬT';
            } catch(e) {}
        }
        toggleAutoClickerBtn.addEventListener('click', () => {
            const payload = {
                button_index: parseInt(clickerButtonIndexInput.value, 10),
                times: parseInt(clickerTimesInput.value, 10)
            };
            apiCall('/api/toggle_auto_clicker', 'POST', payload);
        });

        // Chạy lần đầu khi load trang và cập nhật định kỳ
        document.addEventListener('DOMContentLoaded', () => {
            fetchStatus();
            fetchPanels();
            fetchAutoClickerStatus();
            setInterval(fetchStatus, 5000);
            setInterval(fetchPanels, 2000);
            setInterval(fetchAutoClickerStatus, 2000);
        });
    </script>
</body>
</html>
"""

# ===================================================================
# API Endpoints
# ===================================================================
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
            is_bot_running = False
            print("[CONTROL] Nhận được lệnh DỪNG bot.", flush=True)
        else:
            is_bot_running = True
            print("[CONTROL] Nhận được lệnh BẬT bot.", flush=True)
            bot_thread = threading.Thread(target=run_event_bot_thread, daemon=True)
            bot_thread.start()
    return jsonify({"status": "ok"})

@app.route("/api/toggle_hourly_loop", methods=['POST'])
def toggle_hourly_loop():
    global hourly_loop_thread, is_hourly_loop_enabled, loop_delay_seconds
    data = request.get_json()
    with lock:
        is_hourly_loop_enabled = data.get('enabled')
        loop_delay_seconds = int(data.get('delay', 3600))
        if is_hourly_loop_enabled:
            if hourly_loop_thread is None or not hourly_loop_thread.is_alive():
                hourly_loop_thread = threading.Thread(target=run_hourly_loop_thread, daemon=True)
                hourly_loop_thread.start()
            print(f"[CONTROL] Vòng lặp ĐÃ BẬT với delay {loop_delay_seconds} giây.", flush=True)
        else:
            print("[CONTROL] Vòng lặp ĐÃ TẮT.", flush=True)
    return jsonify({"status": "ok"})

@app.route("/api/panels")
def get_panels():
    with lock:
        return jsonify({"panels": spam_panels})

@app.route("/api/panel/add", methods=['POST'])
def add_panel():
    global panel_id_counter
    with lock:
        new_panel = { "id": panel_id_counter, "message": "", "channel_id": "", "delay": 60, "is_active": False, "last_spam_time": 0 }
        spam_panels.append(new_panel)
        panel_id_counter += 1
    return jsonify({"status": "ok", "new_panel": new_panel})

@app.route("/api/panel/update", methods=['POST'])
def update_panel():
    data = request.get_json()
    with lock:
        for i, panel in enumerate(spam_panels):
            if panel['id'] == data['id']:
                if data.get('is_active') and not panel.get('is_active'):
                    data['last_spam_time'] = 0
                panel.update(data)
                break
    return jsonify({"status": "ok"})

@app.route("/api/panel/delete", methods=['POST'])
def delete_panel():
    data = request.get_json()
    with lock:
        spam_panels[:] = [p for p in spam_panels if p['id'] != data['id']]
    return jsonify({"status": "ok"})

# --- API ENDPOINTS MỚI CHO AUTO CLICKER ---
@app.route("/api/auto_clicker_status")
def api_auto_clicker_status():
    with lock:
        return jsonify({
            "is_running": is_auto_clicker_running,
            "clicks_left": auto_clicker_clicks_left
        })

@app.route("/api/toggle_auto_clicker", methods=['POST'])
def api_toggle_auto_clicker():
    global is_auto_clicker_running, auto_clicker_message_id, auto_clicker_button_index, auto_clicker_clicks_left
    
    with lock:
        if is_auto_clicker_running:
            is_auto_clicker_running = False
            auto_clicker_clicks_left = 0
            msg = "Auto Clicker DISABLED."
        else:
            data = request.get_json()
            button_index = data.get('button_index', 0)
            times = data.get('times', 1)

            if times <= 0:
                return jsonify({'status': 'error', 'message': 'Số lần click phải lớn hơn 0.'})

            if bot_instance:
                try:
                    recent_messages = bot_instance.getMessages(CHANNEL_ID, num=25).json()
                    last_karuta_message = next((m for m in recent_messages if m.get("author", {}).get("id") == KARUTA_ID and m.get("components")), None)
                    
                    if last_karuta_message:
                        auto_clicker_message_id = last_karuta_message.get("id")
                        auto_clicker_button_index = button_index
                        auto_clicker_clicks_left = times
                        is_auto_clicker_running = True
                        msg = f"Auto Clicker ENABLED. Bắt đầu click nút {button_index}."
                        
                        # Kích hoạt cú click đầu tiên
                        print("[Auto Clicker] Kích hoạt cú click đầu tiên...", flush=True)
                        threading.Thread(target=click_button_by_index, args=(last_karuta_message, auto_clicker_button_index)).start()
                        auto_clicker_clicks_left -= 1
                    else:
                        msg = "LỖI: Không tìm thấy tin nhắn nào có button của Karuta trong kênh."
                except Exception as e:
                    msg = f"LỖI khi tìm tin nhắn: {e}"
            else:
                msg = "LỖI: Bot chính chưa được khởi động."
            
    return jsonify({'status': 'success', 'message': msg})

# ===================================================================
# KHỞI CHẠY WEB SERVER
# ===================================================================
if __name__ == "__main__":
    spam_thread = threading.Thread(target=spam_loop, daemon=True)
    spam_thread.start()
    port = int(os.environ.get("PORT", 10000))
    print(f"[SERVER] Khởi động Web Server tại http://0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
