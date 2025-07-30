import discum
import time
import threading
import json
import random
import requests
import os
import sys
from collections import deque

# ===================================================================
# LẤY CẤU HÌNH TỪ BIẾN MÔI TRƯỜNG
# ===================================================================

# !!! TOKEN VÀ CHANNEL ID SẼ ĐƯỢC LẤY TỪ BIẾN MÔI TRƯỜNG TRÊN RENDER !!!
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
KARUTA_ID = "646937666251915264"

# --- Kiểm tra các biến môi trường bắt buộc ---
if not TOKEN or not CHANNEL_ID:
    print("LỖI: Vui lòng cung cấp DISCORD_TOKEN và CHANNEL_ID trong biến môi trường.")
    sys.exit(1) # Dừng chương trình nếu thiếu

# --- Cấu hình tùy chọn với giá trị mặc định ---
# Bật/tắt tính năng gửi kevent hàng giờ (mặc định là "true")
HOURLY_KEVENT_ENABLED = os.getenv("HOURLY_KEVENT_ENABLED", "true").lower() == "true"

# Tùy chỉnh thời gian lặp lại (mặc định là 3600 giây = 1 giờ)
try:
    KEVENT_INTERVAL_SECONDS = int(os.getenv("KEVENT_INTERVAL_SECONDS", "3600"))
except ValueError:
    print("LỖI: KEVENT_INTERVAL_SECONDS phải là một con số. Sử dụng giá trị mặc định 3600.")
    KEVENT_INTERVAL_SECONDS = 3600

# ===================================================================
# KHAI BÁO BIẾN TOÀN CỤC
# ===================================================================
bot = discum.Client(token=TOKEN, log=False)
active_message_id = None
action_queue = deque()
lock = threading.Lock()

# ===================================================================
# HÀM LOGIC (Không thay đổi)
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
        time.sleep(2.5)
    except Exception as e:
        print(f"LỖI NGOẠI LỆ khi click button: {e}")

def perform_final_confirmation(message_data):
    """Chờ 2 giây rồi mới nhấn nút xác nhận cuối cùng."""
    print("ACTION: Chờ 2 giây để nút xác nhận cuối cùng load...")
    time.sleep(2)
    click_button_by_index(message_data, 2)
    print("INFO: Đã hoàn thành lượt. Chờ game tự động cập nhật để bắt đầu lượt mới...")

# ===================================================================
# HÀM TỰ ĐỘNG GỬI LỆNH THEO THỜI GIAN
# ===================================================================

def send_kevent_periodically(interval_seconds):
    """Gửi lệnh 'kevent' theo chu kỳ và reset trạng thái game."""
    global active_message_id
    while True:
        # Chờ khoảng thời gian đã được cấu hình
        time.sleep(interval_seconds)
        try:
            print(f"\nINFO: Đã hết {interval_seconds} giây. Tự động gửi lại lệnh 'kevent'...")
            
            with lock:
                active_message_id = None
                action_queue.clear()
            
            bot.sendMessage(CHANNEL_ID, "kevent")
            print("INFO: Đã gửi 'kevent' và reset trạng thái game.")
            
        except Exception as e:
            print(f"LỖI NGOẠI LỆ khi gửi 'kevent' định kỳ: {e}")

# ===================================================================
# BỘ XỬ LÝ TIN NHẮN (GATEWAY - Không thay đổi)
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
    has_received_fruit = "You received the following fruit:" in embed_desc

    if is_final_confirm_phase:
        print("INFO: Phát hiện giai đoạn xác nhận cuối cùng. Thực hiện click cuối.")
        with lock:
            action_queue.clear() 
        threading.Thread(target=perform_final_confirmation, args=(m,)).start()
    elif has_received_fruit:
        print("INFO: Phát hiện đã nhận được trái cây. Nhấn nút 0 để tiếp tục...")
        threading.Thread(target=click_button_by_index, args=(m, 0)).start()
    elif is_movement_phase:
        with lock:
            if found_good_move:
                print("INFO: NGẮT QUÃNG - Phát hiện nước đi có kết quả. Xóa hàng đợi và xác nhận ngay.")
                action_queue.clear()
                action_queue.append(0)
            elif not action_queue:
                print("INFO: Bắt đầu lượt mới. Tạo chuỗi hành động ngẫu nhiên...")
                num_moves = random.randint(10, 20)
                movement_indices = [1, 2, 3, 4]
                for _ in range(num_moves):
                    action_queue.append(random.choice(movement_indices))
                action_queue.append(0)
                print(f"INFO: Chuỗi hành động mới ({len(action_queue)} bước): {list(action_queue)}")
            if action_queue:
                next_action_index = action_queue.popleft()
                threading.Thread(target=click_button_by_index, args=(m, next_action_index)).start()

def main_gateway():
    print("Đang kết nối với Discord Gateway...")
    bot.gateway.run(auto_reconnect=True)

# ===================================================================
# KHỞI CHẠY BOT
# ===================================================================

if __name__ == "__main__":
    gateway_thread = threading.Thread(target=main_gateway, daemon=True)
    gateway_thread.start()
    
    # Chỉ bắt đầu luồng gửi định kỳ nếu được bật
    if HOURLY_KEVENT_ENABLED:
        print(f"INFO: Tính năng tự động gửi 'kevent' mỗi {KEVENT_INTERVAL_SECONDS} giây đã được BẬT.")
        periodic_thread = threading.Thread(target=send_kevent_periodically, args=(KEVENT_INTERVAL_SECONDS,), daemon=True)
        periodic_thread.start()
    else:
        print("INFO: Tính năng tự động gửi 'kevent' đã được TẮT.")

    time.sleep(7)
    
    print("--- BOT TỰ ĐỘNG CHƠI EVENT SOLISFAIR (LOGIC CUỐI CÙNG) ---")
    print("INFO: Gửi lệnh 'kevent' đầu tiên để bắt đầu.")
    bot.sendMessage(CHANNEL_ID, "kevent")

    try:
        while True:
            time.sleep(1) # Giữ chương trình chính chạy
    except KeyboardInterrupt:
        print("\nĐang đóng kết nối...")
        bot.gateway.close()
