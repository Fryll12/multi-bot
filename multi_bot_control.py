# PHIÊN BẢN CUỐI CÙNG - HOÀN CHỈNH VÀ ỔN ĐỊNH
import discum
import threading
import time
import os
import random
import re
import requests
import json
from flask import Flask, request, render_template_string, jsonify
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
main_token = os.getenv("MAIN_TOKEN")
extra_main_tokens = os.getenv("MAIN_TOKENS_EXTRA").split(",") if os.getenv("MAIN_TOKENS_EXTRA") else []
tokens = os.getenv("TOKENS").split(",") if os.getenv("TOKENS") else []
main_channel_id = os.getenv("MAIN_CHANNEL_ID")
other_channel_id = os.getenv("OTHER_CHANNEL_ID")
ktb_channel_id = os.getenv("KTB_CHANNEL_ID")
spam_channel_id = os.getenv("SPAM_CHANNEL_ID")
work_channel_id = os.getenv("WORK_CHANNEL_ID")
daily_channel_id = os.getenv("DAILY_CHANNEL_ID")
kvi_channel_id = os.getenv("KVI_CHANNEL_ID")
karuta_id = "646937666251915264"
yoru_bot_id = "1311684840462225440"
HATSUNE_ID= "974973431252680714"
# --- BIẾN TRẠNG THÁI (đây là các giá trị mặc định nếu không có file settings.json) ---
bots = []
# Lấy danh sách tên phụ từ biến môi trường (nếu có)
sub_acc_names_str = os.getenv("SUB_ACC_NAMES")
acc_names = [name.strip() for name in sub_acc_names_str.split(',')] if sub_acc_names_str else []

# Danh sách tên Hy Lạp
GREEK_ALPHABET = ["Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda"]

# Bot Alpha
main_bot = None
auto_grab_enabled = False
heart_threshold = 15

# Các bot Main phụ (Beta, Gamma...)
extra_main_bots = []
auto_grab_enabled_extra = False # Một công tắc chung cho tất cả
heart_threshold_extra = 10      # Một ngưỡng tim chung cho tất cả

# Các trạng thái khác
event_grab_enabled = False
spam_enabled, auto_work_enabled, auto_reboot_enabled = False, False, False
spam_message, spam_delay, work_delay_between_acc, work_delay_after_all, auto_reboot_delay = "", 10, 10, 44100, 3600
auto_daily_enabled = False
daily_delay_after_all = 87000 
daily_delay_between_acc = 3
auto_kvi_enabled = False
kvi_click_count = 10
kvi_click_delay = 3
kvi_loop_delay = 7500 
kvi_target_account = 'main_1'

# Timestamps - sẽ được load từ file
last_work_cycle_time, last_daily_cycle_time, last_kvi_cycle_time, last_reboot_cycle_time, last_spam_time = 0, 0, 0, 0, 0

# Các biến điều khiển luồng
auto_reboot_stop_event = threading.Event()
spam_thread, auto_reboot_thread = None, None
bots_lock = threading.Lock()
server_start_time = time.time()
bot_active_states = {}
farm_servers = []
# Biến trạng thái cho KVI (Dán vào dưới các biến khác)
visit_data = {} 
kvi_session_state = {"last_attempt_num": None, "last_question": None, "last_character_name": None, "message_id": None, "guild_id": None}
# --- HÀM LƯU VÀ TẢI CÀI ĐẶT ---
def save_settings():
    """Lưu cài đặt lên JSONBin.io"""
    api_key = os.getenv("JSONBIN_API_KEY")
    bin_id = os.getenv("JSONBIN_BIN_ID")
    if not api_key or not bin_id:
        # print("[Settings] Thiếu API Key hoặc Bin ID của JSONBin.", flush=True)
        return

    settings = {
        'auto_grab_enabled': auto_grab_enabled, 'heart_threshold': heart_threshold,
        'auto_grab_enabled_2': auto_grab_enabled_2, 'heart_threshold_2': heart_threshold_2,
        'auto_grab_enabled_3': auto_grab_enabled_3, 'heart_threshold_3': heart_threshold_3,
        'auto_grab_enabled_4': auto_grab_enabled_4, 'heart_threshold_4': heart_threshold_4,
        'event_grab_enabled': event_grab_enabled,
        'spam_enabled': spam_enabled, 'spam_message': spam_message, 'spam_delay': spam_delay,
        'auto_work_enabled': auto_work_enabled, 'work_delay_between_acc': work_delay_between_acc, 'work_delay_after_all': work_delay_after_all,
        'auto_daily_enabled': auto_daily_enabled, 'daily_delay_between_acc': daily_delay_between_acc, 'daily_delay_after_all': daily_delay_after_all,
        'auto_kvi_enabled': auto_kvi_enabled, 'kvi_click_count': kvi_click_count, 'kvi_click_delay': kvi_click_delay, 'kvi_loop_delay': kvi_loop_delay,
        'kvi_target_account': kvi_target_account,
        'auto_reboot_enabled': auto_reboot_enabled, 'auto_reboot_delay': auto_reboot_delay,
        'bot_active_states': bot_active_states,
        'last_work_cycle_time': last_work_cycle_time,
        'last_daily_cycle_time': last_daily_cycle_time,
        'last_kvi_cycle_time': last_kvi_cycle_time,
        'last_reboot_cycle_time': last_reboot_cycle_time,
        'last_spam_time': last_spam_time,
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-Master-Key': api_key
    }
    url = f"https://api.jsonbin.io/v3/b/{bin_id}"
    
    try:
        req = requests.put(url, json=settings, headers=headers, timeout=10)
        if req.status_code == 200:
            print("[Settings] Đã lưu cài đặt lên JSONBin.io thành công.", flush=True)
        else:
            print(f"[Settings] Lỗi khi lưu cài đặt lên JSONBin.io: {req.status_code} - {req.text}", flush=True)
    except Exception as e:
        print(f"[Settings] Exception khi lưu cài đặt: {e}", flush=True)


def load_settings():
    """Tải cài đặt từ JSONBin.io"""
    api_key = os.getenv("JSONBIN_API_KEY")
    bin_id = os.getenv("JSONBIN_BIN_ID")
    if not api_key or not bin_id:
        print("[Settings] Thiếu API Key hoặc Bin ID của JSONBin. Sử dụng cài đặt mặc định.", flush=True)
        return

    headers = {
        'X-Master-Key': api_key
    }
    url = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"

    try:
        req = requests.get(url, headers=headers, timeout=10)
        if req.status_code == 200:
            settings = req.json().get("record", {})
            if settings: # Chỉ load nếu bin không rỗng
                globals().update(settings)
                global event_grab_enabled
                event_grab_enabled = settings.get('event_grab_enabled', False)
                print("[Settings] Đã tải cài đặt từ JSONBin.io.", flush=True)
            else:
                print("[Settings] JSONBin rỗng, bắt đầu với cài đặt mặc định và lưu lại.", flush=True)
                save_settings() # Lưu cài đặt mặc định lên bin lần đầu
        else:
            print(f"[Settings] Lỗi khi tải cài đặt từ JSONBin.io: {req.status_code} - {req.text}", flush=True)
    except Exception as e:
        print(f"[Settings] Exception khi tải cài đặt: {e}", flush=True)
def save_visit_data():
    """Lưu dữ liệu học của KVI vào một Bin riêng"""
    api_key = os.getenv("KVI_JSONBIN_API_KEY")
    kvi_bin_id = os.getenv("KVI_JSONBIN_BIN_ID") # Dùng Bin ID riêng
    if not api_key or not kvi_bin_id: return
    headers = {'Content-Type': 'application/json', 'X-Master-Key': api_key}
    url = f"https://api.jsonbin.io/v3/b/{kvi_bin_id}"
    def do_save():
        try:
            req = requests.put(url, json=visit_data, headers=headers, timeout=10)
            if req.status_code != 200: print(f"[KVI Settings] Lỗi khi lưu dữ liệu KVI: {req.status_code}", flush=True)
        except Exception as e: print(f"[KVI Settings] Exception khi lưu dữ liệu KVI: {e}", flush=True)
    threading.Thread(target=do_save, daemon=True).start()

def load_visit_data():
    """Tải dữ liệu học của KVI từ Bin riêng"""
    global visit_data
    api_key = os.getenv("KVI_JSONBIN_API_KEY")
    kvi_bin_id = os.getenv("KVI_JSONBIN_BIN_ID")
    if not api_key or not kvi_bin_id: return
    headers = {'X-Master-Key': api_key, 'X-Bin-Meta': 'false'}
    url = f"https://api.jsonbin.io/v3/b/{kvi_bin_id}/latest"
    try:
        req = requests.get(url, headers=headers, timeout=10)
        if req.status_code == 200:
            data = req.json()
            if data: visit_data = data; print("[KVI Settings] Đã tải dữ liệu KVI.", flush=True)
    except Exception: pass
        
def kvi_click_button(token, channel_id, guild_id, message_id, application_id, button_data):
    """Hàm click nút dành riêng cho KVI"""
    custom_id = button_data.get("custom_id");
    if not custom_id: return
    headers = {"Authorization": token, "Content-Type": "application/json"}
    session_id = 'a' + ''.join(random.choices('0123456789abcdef', k=31))
    payload = { "type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": session_id, "data": {"component_type": 2, "custom_id": custom_id} }
    try: requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload, timeout=10)
    except Exception as e: print(f"🔥 [KVI CLICK LỖI] {e}", flush=True)

def start_kvi_session(bot_instance):
    """Gửi lệnh kvi để bắt đầu"""
    print("🚀 [KVI] Gửi lệnh 'kvi'...", flush=True)
    if kvi_channel_id:
        bot_instance.sendMessage(kvi_channel_id, "kvi")

def parse_kvi_embed_data(embed):
    """Phân tích embed để lấy tên nhân vật và câu hỏi"""
    description = embed.get("description", "")
    char_name_match = re.search(r"Character · \*\*([^\*]+)\*\*", description)
    character_name = char_name_match.group(1).strip() if char_name_match else None
    question_match = re.search(r'“([^”]*)”', description)
    question = question_match.group(1).strip() if question_match else None
    num_choices = len([line for line in description.split('\n') if re.match(r'^\d️⃣', line)])
    return character_name, question, num_choices

def parse_hatsune_suggestion(embed):
    """Phân tích embed của Hatsune để lấy gợi ý tốt nhất."""
    description = embed.get("description", "")
    print("🔍 [HATSUNE PARSE] Bắt đầu phân tích nội dung embed:", flush=True)
    print("------------------- NỘI DUNG EMBED -------------------")
    print(description)
    print("----------------------------------------------------")
    lines = description.split('\n')
    suggestions = []
    pattern = re.compile(r"<:(\d).+?>\s+\*\*(\d+)%\*\*")
    for line in lines:
        match = pattern.search(line)
        if match:
            line_num = int(match.group(1))
            percentage = int(match.group(2))
            suggestions.append((percentage, line_num))
    if not suggestions:
        print("    -> ❌ Không tìm thấy dòng gợi ý hợp lệ nào.", flush=True)
        return None
    print(f"    -> ✅ Tìm thấy các gợi ý: {suggestions}", flush=True)
    best_suggestion = max(suggestions, key=lambda item: item[0])
    print(f"    -> ✨ Gợi ý tốt nhất là: Nút số {best_suggestion[1]} với {best_suggestion[0]}%", flush=True)
    return best_suggestion[1]
    
def handle_kvi_message(bot, msg, token_for_click):
    """
    Hàm xử lý logic KVI tập trung, có thể được gọi bởi bất kỳ bot nào.
    bot: instance của bot đang lắng nghe.
    msg: tin nhắn nhận được.
    token_for_click: token của bot đó để thực hiện click.
    """
    global visit_data, kvi_session_state
    
    HATSUNE_ID = os.getenv("HATSUNE_ID")
    if msg.get("author", {}).get("id") == karuta_id and msg.get("embeds"):
        kvi_session_state.update({"message_id": msg.get("id"), "guild_id": msg.get("guild_id")})
        embed, description, buttons = msg["embeds"][0], msg["embeds"][0].get("description", ""), msg.get("components")

        if "Your Affection Rating has" in description and kvi_session_state["last_attempt_num"]:
            char_name, question, attempted_num = kvi_session_state["last_character_name"], kvi_session_state["last_question"], kvi_session_state["last_attempt_num"]
            if char_name and question:
                if char_name not in visit_data: visit_data[char_name] = {}
                if question not in visit_data[char_name]: visit_data[char_name][question] = {"correct_answer": None, "incorrect_answers": []}
                db_entry = visit_data[char_name][question]
                if "increased" in description:
                    if db_entry["correct_answer"] != attempted_num:
                        print(f"✅ [KVI HỌC] ĐÚNG! Đáp án cho '{question}' là nút số {attempted_num}", flush=True)
                        db_entry["correct_answer"] = attempted_num; save_visit_data()
                elif ("decreased" in description or "not changed" in description):
                    if attempted_num not in db_entry["incorrect_answers"]:
                        print(f"❌ [KVI HỌC] SAI! Loại trừ nút số {attempted_num}.", flush=True)
                        db_entry["incorrect_answers"].append(attempted_num); save_visit_data()
            kvi_session_state["last_attempt_num"] = None
        
        if not buttons: return
        time.sleep(random.uniform(1.8, 2.5))
        
        if "1️⃣" in description:
            character_name, question, num_choices = parse_kvi_embed_data(embed)
            if not all([character_name, question, num_choices > 0]): return
            if question == kvi_session_state["last_question"] and kvi_session_state["last_attempt_num"]: return

            print(f"\n[KVI] Nhân vật: {character_name}\n[KVI] Câu hỏi: {question}", flush=True)
            kvi_session_state.update({"last_question": question, "last_character_name": character_name})
            
            db_entry = visit_data.get(character_name, {}).get(question, {})
            correct_answer, incorrect_answers = db_entry.get("correct_answer"), db_entry.get("incorrect_answers", [])
            chosen_button_num = None
            if correct_answer:
                print(f"💡 [KVI BIẾT] Dùng đáp án đã học từ JSON: Nút số {correct_answer}", flush=True)
                chosen_button_num = correct_answer
            else:
                print("⏳ [KVI] Không có đáp án đã học, bắt đầu tìm gợi ý từ Hatsune...", flush=True)
                hatsune_suggestion = None
                try:
                    print("    -> Bắt đầu 'săn' tin nhắn của Hatsune trong 5 giây...", flush=True)
                    HATSUNE_ID = "974973431252680714"
                    end_time = time.time() + 5
                    while time.time() < end_time:
                        recent_messages = bot.getMessages(kvi_channel_id, num=5).json()
                        for msg_item in recent_messages:
                            if msg_item.get("author", {}).get("id") == HATSUNE_ID and msg_item.get("embeds"):
                                if "Talking Helper" in msg_item["embeds"][0].get("title", ""):
                                    hatsune_suggestion = parse_hatsune_suggestion(msg_item["embeds"][0])
                                    break
                        if hatsune_suggestion: break
                        time.sleep(0.5)
                except Exception as e: 
                    print(f"🔥 [HATSUNE] Lỗi khi tìm tin nhắn Hatsune: {e}", flush=True)

                if hatsune_suggestion:
                    print(f"🎯 [KVI HATSUNE] QUYẾT ĐỊNH: Dùng gợi ý từ Hatsune -> Chọn nút số {hatsune_suggestion}", flush=True)
                    chosen_button_num = hatsune_suggestion
                else:
                    print("🎲 [KVI THỬ] KHÔNG CÓ GỢI Ý. QUYẾT ĐỊNH: Chọn ngẫu nhiên.", flush=True)
                    all_button_nums = list(range(1, num_choices + 1))
                    possible_button_nums = [num for num in all_button_nums if num not in incorrect_answers]
                    if not possible_button_nums:
                        print("⚠️ [KVI] Đã loại trừ hết. Thử lại từ đầu.", flush=True)
                        if question in visit_data.get(character_name, {}): visit_data[character_name][question]["incorrect_answers"] = []
                        possible_button_nums = all_button_nums
                    chosen_button_num = random.choice(possible_button_nums)
            
            try:
                button_to_click = buttons[0]['components'][chosen_button_num - 1]
                kvi_session_state["last_attempt_num"] = chosen_button_num
                kvi_click_button(token_for_click, kvi_channel_id, kvi_session_state["guild_id"], kvi_session_state["message_id"], karuta_id, button_to_click)
            except (ValueError, IndexError, TypeError) as e:
                print(f"🔥 [KVI LỖI] Không tìm thấy/chọn được nút. Lỗi: {e}", flush=True)
        else:
            print("\n▶️  [KVI] Bắt đầu/Tiếp tục...", flush=True)
            button_to_click = buttons[0]['components'][0]
            kvi_click_button(token_for_click, kvi_channel_id, kvi_session_state["guild_id"], kvi_session_state["message_id"], karuta_id, button_to_click)
            
def save_farm_settings():
    """Lưu cài đặt của các server farm vào Bin riêng."""
    api_key = os.getenv("JSONBIN_API_KEY")
    farm_bin_id = os.getenv("FARM_JSONBIN_BIN_ID")
    if not api_key or not farm_bin_id: return

    headers = {'Content-Type': 'application/json', 'X-Master-Key': api_key}
    url = f"https://api.jsonbin.io/v3/b/{farm_bin_id}"
    
    try:
        req = requests.put(url, json=farm_servers, headers=headers, timeout=10)
        if req.status_code == 200:
            print("[Farm Settings] Đã lưu cài đặt farm thành công.", flush=True)
        else:
            print(f"[Farm Settings] Lỗi khi lưu cài đặt farm: {req.status_code} - {req.text}", flush=True)
    except Exception as e:
        print(f"[Farm Settings] Exception khi lưu cài đặt farm: {e}", flush=True)

def load_farm_settings():
    """Tải cài đặt của các server farm từ Bin riêng."""
    global farm_servers
    api_key = os.getenv("JSONBIN_API_KEY")
    farm_bin_id = os.getenv("FARM_JSONBIN_BIN_ID")
    if not api_key or not farm_bin_id: return

    headers = {'X-Master-Key': api_key, 'X-Bin-Meta': 'false'}
    url = f"https://api.jsonbin.io/v3/b/{farm_bin_id}/latest"

    try:
        req = requests.get(url, headers=headers, timeout=10)
        if req.status_code == 200:
            data = req.json()
            if isinstance(data, list): farm_servers = data
            else: farm_servers = []
            print(f"[Farm Settings] Đã tải {len(farm_servers)} cấu hình farm.", flush=True)
        else:
            farm_servers = []
    except Exception:
        farm_servers = []
        
def kvi_click_button(token, channel_id, guild_id, message_id, application_id, button_data):
    """Hàm click nút dành riêng cho KVI"""
    custom_id = button_data.get("custom_id");
    if not custom_id: return
    headers = {"Authorization": token, "Content-Type": "application/json"}
    session_id = 'a' + ''.join(random.choices('0123456789abcdef', k=31))
    payload = { "type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": session_id, "data": {"component_type": 2, "custom_id": custom_id} }
    try: requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload, timeout=10)
    except Exception as e: print(f"🔥 [KVI CLICK LỖI] {e}", flush=True)

def start_kvi_session(bot_instance):
    """Gửi lệnh kvi để bắt đầu"""
    print("🚀 [KVI] Gửi lệnh 'kvi'...", flush=True)
    if kvi_channel_id:
        bot_instance.sendMessage(kvi_channel_id, "kvi")

def parse_kvi_embed_data(embed):
    """Phân tích embed để lấy tên nhân vật và câu hỏi"""
    description = embed.get("description", "")
    char_name_match = re.search(r"Character · \*\*([^\*]+)\*\*", description)
    character_name = char_name_match.group(1).strip() if char_name_match else None
    question_match = re.search(r'“([^”]*)”', description)
    question = question_match.group(1).strip() if question_match else None
    num_choices = len([line for line in description.split('\n') if re.match(r'^\d️⃣', line)])
    return character_name, question, num_choices

def handle_farm_grab(bot, msg, bot_num):
    """Xử lý logic grab dành RIÊNG cho các farm panel mới."""
    channel_id = msg.get("channel_id")
    target_server = next((s for s in farm_servers if s.get('main_channel_id') == channel_id), None)
    if not target_server: return

    # KIỂM TRA DROP TRƯỚC TIÊN
    if msg.get("author", {}).get("id") == karuta_id and 'dropping 3' in msg.get("content", ""):
        last_drop_msg_id = msg["id"]

        # 1. Luồng nhặt thẻ (độc lập)
        grab_map = {1: 'auto_grab_enabled_1', 2: 'auto_grab_enabled_2', 3: 'auto_grab_enabled_3', 4: 'auto_grab_enabled_4'}
        is_card_grab_enabled = target_server.get(grab_map.get(bot_num), False)
        ktb_channel_id = target_server.get('ktb_channel_id')

        if is_card_grab_enabled and ktb_channel_id:
            thresh_map = {1: 'heart_threshold_1', 2: 'heart_threshold_2', 3: 'heart_threshold_3', 4: 'heart_threshold_4'}
            heart_threshold = int(target_server.get(thresh_map[bot_num], 50))
            def read_yoru_bot():
                time.sleep(0.6)
                try:
                    messages = bot.getMessages(channel_id, num=5).json()
                    for msg_item in messages:
                        if msg_item.get("author", {}).get("id") == yoru_bot_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                            desc = msg_item["embeds"][0].get("description", "")
                            lines = desc.split('\n')
                            heart_numbers = [int(match.group(1)) if (match := re.search(r'♡(\d+)', line)) else 0 for line in lines[:3]]
                            if not any(heart_numbers): break
                            max_num = max(heart_numbers)
                            if max_num >= heart_threshold:
                                max_index = heart_numbers.index(max_num)
                                delays = {1: [0.2, 1.2, 2.0], 2: [1, 2, 2.8], 3: [1, 2, 2.8], 4: [1, 2, 2.8]}
                                emojis = ["1️⃣", "2️⃣", "3️⃣"]
                                emoji = emojis[max_index]
                                delay = delays.get(bot_num, [0.7, 1.7, 2.4])[max_index]
                                print(f"[FARM: {target_server['name']} | Bot {bot_num}] Chọn dòng {max_index+1} với {max_num} tim -> Emoji {emoji} sau {delay}s", flush=True)
                                def grab_action():
                                    bot.addReaction(channel_id, last_drop_msg_id, emoji)
                                    time.sleep(2)
                                    bot.sendMessage(ktb_channel_id, "kt b")
                                threading.Timer(delay, grab_action).start()
                            break
                except Exception as e:
                    print(f"Lỗi khi đọc Yoru Bot (FARM: {target_server['name']} | Bot {bot_num}): {e}", flush=True)
            threading.Thread(target=read_yoru_bot).start()

        # 2. Luồng nhặt event (độc lập và chỉ cho bot 1)
        if event_grab_enabled and bot_num == 1:
            def check_farm_event():
                try:
                    time.sleep(5)
                    full_msg_obj = bot.getMessage(channel_id, last_drop_msg_id).json()
                    if isinstance(full_msg_obj, list) and len(full_msg_obj) > 0:
                        full_msg_obj = full_msg_obj[0]
                    if 'reactions' in full_msg_obj:
                        if any(reaction['emoji']['name'] == '🍉' for reaction in full_msg_obj['reactions']):
                            print(f"[EVENT GRAB | FARM: {target_server['name']}] Phát hiện dưa hấu! Bot 1 tiến hành nhặt.", flush=True)
                            bot.addReaction(channel_id, last_drop_msg_id, "🍉")
                except Exception as e:
                    print(f"Lỗi khi kiểm tra event tại farm (Bot 1): {e}", flush=True)
            threading.Thread(target=check_farm_event).start()
        
# --- CÁC HÀM LOGIC BOT ---
def reboot_bot(target_id):
    global main_bot, extra_main_bots, bots
    with bots_lock:
        print(f"[Reboot] Nhận được yêu cầu reboot cho target: {target_id}", flush=True)

        # Xử lý Bot Alpha (main_1) - Không thay đổi
        if target_id == 'main_1' and main_token:
            try: 
                if main_bot: main_bot.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Alpha: {e}", flush=True)
            main_bot = create_bot(main_token, bot_type='alpha', bot_name='Alpha')
            print("[Reboot] Acc Alpha đã được khởi động lại.", flush=True)

        # --- LOGIC MỚI: XỬ LÝ CÁC BOT MAIN PHỤ ĐỘNG ---
        elif target_id.startswith('main_'): # Bắt các target như 'main_2', 'main_3'...
            try:
                # Chuyển 'main_2' -> index 0, 'main_3' -> index 1, ...
                list_index = int(target_id.split('_')[1]) - 2 

                if 0 <= list_index < len(extra_main_bots):
                    # Đóng bot cũ
                    try: extra_main_bots[list_index].gateway.close()
                    except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Main phụ {list_index + 2}: {e}", flush=True)
                    
                    # Tạo lại bot mới
                    token_to_reboot = extra_main_tokens[list_index].strip()
                    bot_name = GREEK_ALPHABET[list_index] if list_index < len(GREEK_ALPHABET) else f"Main {list_index + 2}"
                    
                    extra_main_bots[list_index] = create_bot(token_to_reboot, bot_type='extra_main', bot_name=bot_name)
                    print(f"[Reboot] Acc {bot_name} đã được khởi động lại.", flush=True)
            except (ValueError, IndexError) as e: 
                print(f"[Reboot] Lỗi xử lý target Acc Main phụ: {e}", flush=True)

        # Xử lý các Bot phụ (sub) - Không thay đổi
        elif target_id.startswith('sub_'):
            try:
                index = int(target_id.split('_')[1])
                if 0 <= index < len(bots):
                    try: bots[index].gateway.close()
                    except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Phụ {index}: {e}", flush=True)
                    token_to_reboot = tokens[index].strip()
                    bots[index] = create_bot(token_to_reboot, is_main=False)
                    print(f"[Reboot] Acc Phụ {index} đã được khởi động lại.", flush=True)
            except (ValueError, IndexError) as e: print(f"[Reboot] Lỗi xử lý target Acc Phụ: {e}", flush=True)

def create_bot(token, bot_type='sub', bot_name='Sub Account'):
    bot = discum.Client(token=token, log=False)
    
    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            user_data = resp.raw.get("user")
            if isinstance(user_data, dict):
                user_id = user_data.get("id")
                if user_id:
                    print(f"Đã đăng nhập: {user_id} ({bot_name})", flush=True)

    if bot_type == 'alpha':
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled, heart_threshold, event_grab_enabled
            if not (resp.event.message or (resp.raw and resp.raw.get('t') == 'MESSAGE_UPDATE')):
                return
            
            msg = resp.parsed.auto()
            channel_id = msg.get("channel_id")
            
            # --- 1. ALPHA GRAB TẠI KÊNH CHÍNH ---
            if channel_id == main_channel_id:
                if msg.get("author", {}).get("id") == karuta_id and 'dropping 3' in msg.get("content", ""):
                    last_drop_msg_id = msg["id"]
                    if auto_grab_enabled:
                        def read_yoru_bot_alpha():
                            time.sleep(0.6)
                            try:
                                messages = bot.getMessages(main_channel_id, num=5).json()
                                for msg_item in messages:
                                    if msg_item.get("author", {}).get("id") == yoru_bot_id and "embeds" in msg_item and len(msg_item["embeds"]) > 0:
                                        desc = msg_item["embeds"][0].get("description", "")
                                        lines = desc.split('\n')
                                        heart_numbers = [int(match.group(1)) if (match := re.search(r'♡(\d+)', line)) else 0 for line in lines[:3]]
                                        max_num = max(heart_numbers)
                                        if sum(heart_numbers) > 0 and max_num >= heart_threshold:
                                            max_index = heart_numbers.index(max_num)
                                            emoji, delay = [("1️⃣", 0.2), ("2️⃣", 1.2), ("3️⃣", 2)][max_index]
                                            print(f"[ALPHA] Chọn dòng {max_index+1} với {max_num} tim -> Emoji {emoji} sau {delay}s", flush=True)
                                            def grab():
                                                bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                time.sleep(1)
                                                bot.sendMessage(ktb_channel_id, "kt b")
                                            threading.Timer(delay, grab).start()
                                        break
                            except Exception as e: 
                                print(f"Lỗi khi đọc Yoru Bot (ALPHA): {e}", flush=True)
                        threading.Thread(target=read_yoru_bot_alpha).start()
                        
                    if event_grab_enabled:
                        def check_and_grab_event():
                            try:
                                time.sleep(5) 
                                full_msg_obj = bot.getMessage(main_channel_id, last_drop_msg_id).json()
                                if isinstance(full_msg_obj, list) and len(full_msg_obj) > 0:
                                    full_msg_obj = full_msg_obj[0]
                                if 'reactions' in full_msg_obj:
                                    if any(reaction['emoji']['name'] == '🍉' for reaction in full_msg_obj['reactions']):
                                        print(f"[EVENT GRAB | Bot 1] Phát hiện dưa hấu! Tiến hành nhặt.", flush=True)
                                        bot.addReaction(main_channel_id, last_drop_msg_id, "🍉")
                            except Exception as e:
                                print(f"Lỗi khi kiểm tra event (Bot 1): {e}", flush=True)
                        threading.Thread(target=check_and_grab_event).start()            

            # --- 2. XỬ LÝ KÊNH KVI ---
            # Lưu ý: kvi_target_account giờ sẽ dùng tên như 'Alpha', 'Beta'...
            if auto_kvi_enabled and kvi_target_account == 'Alpha' and channel_id == kvi_channel_id:
                handle_kvi_message(bot, msg, main_token)
                
            # --- 3. BỘ ĐIỀU PHỐI FARM TRUNG TÂM (PHIÊN BẢN ĐỘNG) ---
            target_server = next((s for s in farm_servers if s.get('main_channel_id') == channel_id), None)
            
            if target_server and msg.get("author", {}).get("id") == karuta_id and 'dropping 3' in msg.get("content", ""):
                last_drop_msg_id = msg["id"]
                
                def central_farm_handler():
                    try:
                        time.sleep(0.6)
                        messages = bot.getMessages(channel_id, num=5).json()
                        yoru_msg_desc = next((item["embeds"][0].get("description", "") for item in messages if item.get("author", {}).get("id") == yoru_bot_id and item.get("embeds")), None)
                        
                        if not yoru_msg_desc: return

                        lines = yoru_msg_desc.split('\n')
                        heart_numbers = [int(match.group(1)) if (match := re.search(r'♡(\d+)', line)) else 0 for line in lines[:3]]
                        if not any(heart_numbers): return
                            
                        bots_to_check = []
                        bots_to_check.append({
                            "name": "Alpha", "instance": main_bot, "num": 1,
                            "enabled": target_server.get('auto_grab_enabled_1', False),
                            "threshold": int(target_server.get('heart_threshold_1', heart_threshold))
                        })
                        for i, bot_instance in enumerate(extra_main_bots):
                            bot_num = i + 2
                            bot_name_greek = GREEK_ALPHABET[i] if i < len(GREEK_ALPHABET) else f"Main {bot_num}"
                            bots_to_check.append({
                                "name": bot_name_greek, "instance": bot_instance, "num": bot_num,
                                "enabled": target_server.get(f'auto_grab_enabled_{bot_num}', False),
                                "threshold": int(target_server.get(f'heart_threshold_{bot_num}', heart_threshold_extra))
                            })

                        max_num = max(heart_numbers)
                        max_index = heart_numbers.index(max_num)
                        emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]

                        for bot_info in bots_to_check:
                            if bot_info["enabled"] and bot_info["instance"] and max_num >= bot_info["threshold"]:
                                def grab_action(target_bot, target_ktb_channel, b_info):
                                    print(f"[FARM DISPATCHER] Lệnh grab cho {b_info['name']} tại farm '{target_server['name']}'", flush=True)
                                    target_bot.addReaction(channel_id, last_drop_msg_id, emoji)
                                    if target_ktb_channel:
                                        time.sleep(2)
                                        target_bot.sendMessage(target_ktb_channel, "kt b")
                                
                                delay = random.uniform(0.5, 1.5)
                                threading.Timer(delay, grab_action, args=(bot_info["instance"], target_server.get('ktb_channel_id'), bot_info)).start()

                    except Exception as e:
                        print(f"Lỗi trong bộ điều phối farm trung tâm: {e}", flush=True)

                threading.Thread(target=central_farm_handler).start()

    elif bot_type == 'extra_main':
        @bot.gateway.command
        def on_message(resp):
            # Các bot này chỉ cần nghe lệnh KVI nếu được chỉ định
            if not resp.event.message: return
            msg = resp.parsed.auto()
            channel_id = msg.get("channel_id")
            
            current_token = token 
            
            # kvi_target_account sẽ so sánh với tên Hy Lạp của bot (Beta, Gamma...)
            if auto_kvi_enabled and kvi_target_account == bot_name and channel_id == kvi_channel_id:
                handle_kvi_message(bot, msg, current_token)

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot
    
# HÀM RUN_WORK_BOT PHIÊN BẢN SỬA LỖI GỬI KJN
def run_work_bot(token, acc_name, shared_resource=None):
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    bot = discum.Client(token=token, log=False, user_agent=ua)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    found_resource = None
    step = {"value": 0}

    def send_karuta_command(): bot.sendMessage(work_channel_id, "kc o:ef")
    def send_kn_command(): bot.sendMessage(work_channel_id, "kn")
    def send_kw_command(): bot.sendMessage(work_channel_id, "kw"); step["value"] = 2
    
    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            session_id_thuc = bot.gateway.session_id
            payload = {
                "type": 3,"guild_id": guild_id,"channel_id": channel_id,
                "message_id": message_id,"application_id": application_id,
                "session_id": session_id_thuc,
                "data": {"component_type": 2,"custom_id": custom_id}
            }
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
            print(f"[Work][{acc_name}] Click tick: Status {r.status_code}", flush=True)
        except Exception as e: print(f"[Work][{acc_name}] Lỗi click tick: {e}", flush=True)

    @bot.gateway.command
    def on_message(resp):
        if not (resp.event.message or (resp.raw and resp.raw.get('t') == 'MESSAGE_UPDATE')): return
        
        try:
            m = resp.parsed.auto()
        except:
            return

        if str(m.get("channel_id")) != work_channel_id: return
        author_id = str(m.get("author", {}).get("id", ""))
        guild_id = m.get("guild_id")
        
        if step["value"] == 0 and author_id == karuta_id and "embeds" in m and len(m["embeds"]) > 0:
            desc = m["embeds"][0].get("description", "")
            card_codes = re.findall(r"\bv[a-zA-Z0-9]{6}\b", desc)
            if len(card_codes) >= 10:
                print(f"[{acc_name}] Phát hiện {len(card_codes)} card, bắt đầu pick...", flush=True)
                first_5 = card_codes[:5]; last_5 = card_codes[-5:]
                def pick_cards_thread():
                    for i, code in enumerate(last_5): time.sleep(1.5); bot.sendMessage(work_channel_id, f"kjw {code} {chr(97+i)}")
                    for i, code in enumerate(first_5): time.sleep(1.5); bot.sendMessage(work_channel_id, f"kjw {code} {chr(97+i)}")
                    time.sleep(1)

                    def send_kjn_kw_thread(resource_to_use):
                        time.sleep(2)
                        bot.sendMessage(work_channel_id, f"kjn `{resource_to_use}` a b c d e")
                        time.sleep(1)
                        send_kw_command()

                    if shared_resource:
                        print(f"[{acc_name}] Sử dụng tài nguyên đã có: '{shared_resource}'")
                        threading.Thread(target=send_kjn_kw_thread, args=(shared_resource,)).start()
                    else:
                        print(f"[{acc_name}] Bot đầu tiên, đang tìm tài nguyên...")
                        send_kn_command()
                        step["value"] = 1
                threading.Thread(target=pick_cards_thread).start()

        elif step["value"] == 1 and author_id == karuta_id and "embeds" in m and len(m["embeds"]) > 0:
            desc = m["embeds"][0].get("description", ""); lines = desc.split("\n")
            if len(lines) >= 2:
                match = re.search(r"\d+\.\s*`([^`]+)`", lines[1])
                if match:
                    nonlocal found_resource
                    resource = match.group(1)
                    found_resource = resource
                    print(f"[{acc_name}] Resource: {resource}", flush=True)
                    
                    # --- SỬA LỖI GỬI LỆNH KHÔNG ĐÁNG TIN CẬY ---
                    def send_kjn_kw_thread():
                        time.sleep(2)
                        bot.sendMessage(work_channel_id, f"kjn `{resource}` a b c d e")
                        time.sleep(1)
                        send_kw_command()
                    threading.Thread(target=send_kjn_kw_thread).start()
        
        elif step["value"] == 2 and author_id == karuta_id and "components" in m:
                message_id = m['id']
                application_id = m.get('application_id', karuta_id)
                last_custom_id = None
                for comp in m['components']:
                    if comp['type'] == 1:
                        for btn in comp['components']:
                            if btn['type'] == 2:
                                last_custom_id = btn['custom_id']
                
                if last_custom_id:
                    print(f"[{acc_name}] Tìm thấy nút cuối cùng: '{last_custom_id}'. Bắt đầu click...", flush=True)
                    click_tick(work_channel_id, message_id, last_custom_id, application_id, guild_id)
                    step["value"] = 3
                    bot.gateway.close()
                    return

    # Khối chạy chính
    print(f"[{acc_name}] Bắt đầu...", flush=True)
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    
    time.sleep(7) 
    send_karuta_command()
    
    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout:
        time.sleep(1)
        
    bot.gateway.close()
    if step["value"] == 3:
        print(f"[{acc_name}] Đã hoàn thành.", flush=True)
    else:
        print(f"[{acc_name}] KHÔNG hoàn thành (hết 90s timeout).", flush=True)
    return found_resource
    
def run_daily_bot(token, acc_name):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = {"Authorization": token, "Content-Type": "application/json"}
    state = {"step": 0, "message_id": None, "guild_id": None}
    def click_button(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json={"type": 3,"guild_id": guild_id,"channel_id": channel_id,"message_id": message_id,"application_id": application_id,"session_id": "aaa","data": {"component_type": 2, "custom_id": custom_id}})
            print(f"[Daily][{acc_name}] Click: {custom_id} - Status {r.status_code}", flush=True)
        except Exception as e: print(f"[Daily][{acc_name}] Click Error: {e}", flush=True)
    @bot.gateway.command
    def on_event(resp):
        if not (resp.event.message or resp.raw.get("t") == "MESSAGE_UPDATE"): return
        m = resp.parsed.auto()
        channel_id, author_id, message_id, guild_id, app_id = str(m.get("channel_id")), str(m.get("author", {}).get("id", "")), m.get("id", ""), m.get("guild_id", ""), m.get("application_id", karuta_id)
        if channel_id != daily_channel_id or author_id != karuta_id or "components" not in m or not m["components"]: return
        btn = next((b for comp in m["components"] if comp["type"] == 1 and comp["components"] for b in comp["components"] if b["type"] == 2), None)
        if not btn: return
        if resp.event.message and state["step"] == 0:
            print(f"[Daily][{acc_name}] Click lần 1...", flush=True); state["message_id"], state["guild_id"], state["step"] = message_id, guild_id, 1; click_button(channel_id, message_id, btn["custom_id"], app_id, guild_id)
        elif resp.raw.get("t") == "MESSAGE_UPDATE" and message_id == state["message_id"] and state["step"] == 1:
            print(f"[Daily][{acc_name}] Click lần 2...", flush=True); state["step"] = 2; click_button(channel_id, message_id, btn["custom_id"], app_id, guild_id); bot.gateway.close()
    print(f"[Daily][{acc_name}] Bắt đầu...", flush=True); threading.Thread(target=bot.gateway.run, daemon=True).start(); time.sleep(1); bot.sendMessage(daily_channel_id, "kdaily")
    timeout = time.time() + 15
    while state["step"] != 2 and time.time() < timeout: time.sleep(1)
    bot.gateway.close(); print(f"[Daily][{acc_name}] {'SUCCESS: Click xong 2 lần.' if state['step'] == 2 else 'FAIL: Không click đủ 2 lần.'}", flush=True)

def run_kvi_bot(token):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers, state = {"Authorization": token, "Content-Type": "application/json"}, {"step": 0, "click_count": 0, "message_id": None, "guild_id": None}
    def click_button(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json={"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "aaa", "data": {"component_type": 2, "custom_id": custom_id}})
            print(f"[KVI] Click {state['click_count']+1}: {custom_id} - Status {r.status_code}", flush=True)
        except Exception as e: print(f"[KVI] Click Error: {e}", flush=True)
    @bot.gateway.command
    def on_event(resp):
        if not (resp.event.message or resp.raw.get("t") == "MESSAGE_UPDATE"): return
        m = resp.parsed.auto()
        channel_id, author_id, message_id, guild_id, app_id = str(m.get("channel_id")), str(m.get("author", {}).get("id", "")), m.get("id", ""), m.get("guild_id", ""), m.get("application_id", karuta_id)
        if channel_id != kvi_channel_id or author_id != karuta_id or "components" not in m or not m["components"]: return
        btn = next((b for comp in m["components"] if comp["type"] == 1 and comp["components"] for b in comp["components"] if b["type"] == 2), None)
        if not btn: return
        if resp.event.message and state["step"] == 0:
            state["message_id"], state["guild_id"], state["step"] = message_id, guild_id, 1; click_button(channel_id, message_id, btn["custom_id"], app_id, guild_id); state["click_count"] += 1
        elif resp.raw.get("t") == "MESSAGE_UPDATE" and message_id == state["message_id"] and state["click_count"] < kvi_click_count:
            time.sleep(kvi_click_delay); click_button(channel_id, message_id, btn["custom_id"], app_id, guild_id); state["click_count"] += 1
            if state["click_count"] >= kvi_click_count: print("[KVI] DONE. Đã click đủ.", flush=True); state["step"] = 2; bot.gateway.close()
    print("[KVI] Bắt đầu...", flush=True); threading.Thread(target=bot.gateway.run, daemon=True).start(); time.sleep(1); bot.sendMessage(kvi_channel_id, "kvi")
    timeout = time.time() + (kvi_click_count * kvi_click_delay) + 15
    while state["step"] != 2 and time.time() < timeout: time.sleep(0.5)
    bot.gateway.close(); print(f"[KVI] {'SUCCESS. Đã click xong.' if state['click_count'] >= kvi_click_count else f'FAIL. Chỉ click được {state['click_count']} / {kvi_click_count} lần.'}", flush=True)

# --- CÁC VÒNG LẶP NỀN (ĐÃ VIẾT LẠI CHO ỔN ĐỊNH) ---
def auto_work_loop():
    global last_work_cycle_time
    while True:
        try:
            if auto_work_enabled and (time.time() - last_work_cycle_time) >= work_delay_after_all:
                print("[Work] Đã đến giờ chạy Auto Work...", flush=True)
                shared_resource_for_cycle = None
                work_items = []
                if main_token_2 and bot_active_states.get('main_2', False): work_items.append({"name": "BETA NODE", "token": main_token_2})
                if main_token_3 and bot_active_states.get('main_3', False): work_items.append({"name": "GAMMA NODE", "token": main_token_3})
                if main_token_4 and bot_active_states.get('main_4', False): work_items.append({"name": "DELTA NODE", "token": main_token_4})
                with bots_lock:
                    sub_account_items = [{"name": acc_names[i] if i < len(acc_names) else f"Sub {i+1}", "token": token} for i, token in enumerate(tokens) if token.strip() and bot_active_states.get(f'sub_{i}', False)]
                    work_items.extend(sub_account_items)
                for item in work_items:
                    if not auto_work_enabled: break
                    print(f"[Work] Đang chạy acc '{item['name']}'...", flush=True)
                    # Truyền tài nguyên đã lưu vào hàm, và nhận lại tài nguyên mới nếu có
                    found_resource = run_work_bot(item['token'].strip(), item['name'], shared_resource=shared_resource_for_cycle)
                    
                    # Nếu đây là bot đầu tiên và nó tìm thấy tài nguyên, hãy lưu lại
                    if found_resource and shared_resource_for_cycle is None:
                        print(f"✅ [Work] Đã lấy được tài nguyên '{found_resource}' cho chu kỳ này.", flush=True)
                        shared_resource_for_cycle = found_resource
                    print(f"[Work] Acc '{item['name']}' xong, chờ {work_delay_between_acc or 10} giây...", flush=True); time.sleep(work_delay_between_acc or 10)
                if auto_work_enabled:
                    print(f"[Work] Hoàn thành chu kỳ.", flush=True)
                    last_work_cycle_time = time.time();
            time.sleep(60)
        except Exception as e:
            print(f"[ERROR in auto_work_loop] {e}", flush=True); time.sleep(60)

def auto_daily_loop():
    global last_daily_cycle_time
    while True:
        try:
            if auto_daily_enabled and (time.time() - last_daily_cycle_time) >= daily_delay_after_all:
                print("[Daily] Đã đến giờ chạy Auto Daily...", flush=True)
                daily_items = []
                if main_token_2 and bot_active_states.get('main_2', False): daily_items.append({"name": "BETA NODE", "token": main_token_2})
                if main_token_3 and bot_active_states.get('main_3', False): daily_items.append({"name": "GAMMA NODE", "token": main_token_3})
                if main_token_4 and bot_active_states.get('main_4', False): daily_items.append({"name": "DELTA NODE", "token": main_token_4})
                with bots_lock:
                    daily_items.extend([{"name": acc_names[i] if i < len(acc_names) else f"Sub {i+1}", "token": token} for i, token in enumerate(tokens) if token.strip() and bot_active_states.get(f'sub_{i}', False)])
                for item in daily_items:
                    if not auto_daily_enabled: break
                    print(f"[Daily] Đang chạy acc '{item['name']}'...", flush=True); run_daily_bot(item['token'].strip(), item['name']); print(f"[Daily] Acc '{item['name']}' xong, chờ {daily_delay_between_acc} giây...", flush=True); time.sleep(daily_delay_between_acc)
                if auto_daily_enabled:
                    print(f"[Daily] Hoàn thành chu kỳ.", flush=True)
                    last_daily_cycle_time = time.time();
            time.sleep(60)
        except Exception as e:
            print(f"[ERROR in auto_daily_loop] {e}", flush=True); time.sleep(60)

def auto_kvi_loop():
    global last_kvi_cycle_time
    time.sleep(20) 
    while True:
        try:
            target_bot = None
            if kvi_target_account == 'main_1': 
                target_bot = main_bot
            elif kvi_target_account == 'main_2': 
                target_bot = main_bot_2
            elif kvi_target_account == 'main_3': 
                target_bot = main_bot_3
            elif kvi_target_account == 'main_4': 
                target_bot = main_bot_4
            
            if auto_kvi_enabled and target_bot and bot_active_states.get(kvi_target_account, False):
                if (time.time() - last_kvi_cycle_time) >= kvi_loop_delay:
                    start_kvi_session(target_bot) # <-- Gọi hàm với 1 tham số
                    last_kvi_cycle_time = time.time()
            time.sleep(60)
        except Exception as e: 
            print(f"[ERROR in auto_kvi_loop] {e}", flush=True)
            time.sleep(60)
            
def auto_reboot_loop():
    global auto_reboot_enabled, last_reboot_cycle_time, auto_reboot_stop_event
    while not auto_reboot_stop_event.is_set():
        try:
            if auto_reboot_enabled and (time.time() - last_reboot_cycle_time) >= auto_reboot_delay:
                print("[Reboot] Hết thời gian chờ, tiến hành reboot 3 tài khoản chính.", flush=True)
                if main_bot: reboot_bot('main_1'); time.sleep(5)
                if main_bot_2: reboot_bot('main_2'); time.sleep(5)
                if main_bot_3: reboot_bot('main_3'); time.sleep(5)
                if main_bot_4: reboot_bot('main_4')
                last_reboot_cycle_time = time.time();
            interrupted = auto_reboot_stop_event.wait(timeout=60)
            if interrupted: break
        except Exception as e:
            print(f"[ERROR in auto_reboot_loop] {e}", flush=True); time.sleep(60)
    print("[Reboot] Luồng tự động reboot đã dừng.", flush=True)

# =====================================================================
# ===== THAY THẾ TOÀN BỘ HÀM SPAM_LOOP BẰNG PHIÊN BẢN HOÀN THIỆN NÀY =====

# Thêm biến này vào khu vực "Các biến điều khiển luồng" ở đầu file của bạn
spam_tasks_running = set()

def spam_loop():
    global last_spam_time, spam_tasks_running

    # Hàm này là một "chuyên viên spam", nhận một nhiệm vụ và thực hiện tuần tự
    def run_spam_cycle(task_id, channel_id, message, bots_to_use, inter_bot_delay):
        global spam_tasks_running
        try:
            print(f"[Spam Cycle] Bắt đầu nhiệm vụ '{task_id}' với {len(bots_to_use)} bot.", flush=True)
            for bot in bots_to_use:
                try:
                    bot.sendMessage(channel_id, message)
                    time.sleep(inter_bot_delay)
                except Exception as e:
                    print(f"Lỗi khi bot gửi spam (Nhiệm vụ: {task_id}): {e}", flush=True)
        finally:
            # Rất quan trọng: Sau khi làm xong (kể cả khi có lỗi), phải gỡ bỏ biển báo "Đang Bận"
            spam_tasks_running.remove(task_id)
            print(f"[Spam Cycle] Hoàn thành nhiệm vụ '{task_id}'.", flush=True)

    while True:
        try:
            now = time.time()
            with bots_lock:
                active_bots = [bot for i, bot in enumerate(bots) if bot and bot_active_states.get(f'sub_{i}', False)]

            # --- Điều phối Spam Toàn Cục (GLOBAL) ---
            if spam_enabled and spam_message and spam_channel_id and (now - last_spam_time) >= spam_delay:
                # Chỉ bắt đầu nếu không có nhiệm vụ "global" nào đang chạy
                if 'global' not in spam_tasks_running:
                    spam_tasks_running.add('global') # Bật biển báo "Đang Bận"
                    last_spam_time = now # Reset đồng hồ
                    threading.Thread(target=run_spam_cycle, args=('global', spam_channel_id, spam_message, active_bots, 2)).start()

            # --- Điều phối Spam Multi-Farm ---
            for server in farm_servers:
                server_id = server.get('id', 'unknown_farm')
                if server.get('spam_enabled') and server.get('spam_message') and server.get('spam_channel_id'):
                    last_farm_spam_time = server.get('last_spam_time', 0)
                    farm_spam_delay = server.get('spam_delay', 10)

                    if (now - last_farm_spam_time) >= farm_spam_delay:
                        # Chỉ bắt đầu nếu không có nhiệm vụ của farm này đang chạy
                        if server_id not in spam_tasks_running:
                            spam_tasks_running.add(server_id) # Bật biển báo "Đang Bận" cho farm này
                            server['last_spam_time'] = now # Reset đồng hồ của farm
                            threading.Thread(target=run_spam_cycle, args=(server_id, server['spam_channel_id'], server['spam_message'], active_bots, 2)).start()
            
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR in spam_loop] {e}", flush=True)
            time.sleep(1)
            
def periodic_save_loop():
    """Vòng lặp nền để tự động lưu cài đặt 5 phút một lần."""
    while True:
        time.sleep(600)
        
        print("[Settings] Bắt đầu lưu định kỳ...", flush=True)
        save_settings()
        
app = Flask(__name__)

# --- GIAO DIỆN WEB ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Deep - Shadow Network Control</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Creepster&family=Orbitron:wght@400;700;900&family=Courier+Prime:wght@400;700&family=Nosifer&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-bg: #0a0a0a; --secondary-bg: #1a1a1a; --panel-bg: #111111; --border-color: #333333;
            --shadow-color: #660000; --blood-red: #8b0000; --dark-red: #550000; --bone-white: #f8f8ff;
            --ghost-gray: #666666; --void-black: #000000; --deep-purple: #2d1b69; --necro-green: #228b22;
            --shadow-cyan: #008b8b; --text-primary: #f0f0f0; --text-secondary: #cccccc; --text-muted: #888888;
            --neon-yellow: #fff000;
            --shadow-red: 0 0 20px rgba(139, 0, 0, 0.5); --shadow-purple: 0 0 20px rgba(45, 27, 105, 0.5);
            --shadow-green: 0 0 20px rgba(34, 139, 34, 0.5); --shadow-cyan: 0 0 20px rgba(0, 139, 139, 0.5);
        }
        body { font-family: 'Courier Prime', monospace; background: var(--primary-bg); color: var(--text-primary); margin: 0; padding: 0;}
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; padding: 30px; background: linear-gradient(135deg, var(--void-black), rgba(139, 0, 0, 0.3)); border: 2px solid var(--blood-red); border-radius: 15px; box-shadow: var(--shadow-red), inset 0 0 20px rgba(139, 0, 0, 0.1); }
        .skull-icon { font-size: 4rem; color: var(--blood-red); margin-bottom: 15px; }
        .title { font-family: 'Nosifer', cursive; font-size: 3.5rem; letter-spacing: 4px; }
        .title-main { color: var(--blood-red); text-shadow: 0 0 30px var(--blood-red); }
        .title-sub { color: var(--deep-purple); text-shadow: 0 0 30px var(--deep-purple); }
        .subtitle { font-size: 1.3rem; color: var(--text-secondary); letter-spacing: 2px; margin-bottom: 15px; font-family: 'Orbitron', monospace; }
        .main-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .panel { position: relative; background: linear-gradient(135deg, var(--panel-bg), rgba(26, 26, 26, 0.9)); border: 1px solid var(--border-color); border-radius: 10px; padding: 25px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); }
        .panel h2 { font-family: 'Nosifer', cursive; font-size: 1.4rem; margin-bottom: 20px; text-transform: uppercase; border-bottom: 2px solid; padding-bottom: 10px; position: relative; animation: glitch-skew 1s infinite linear alternate-reverse; }
        .panel h2 i { margin-right: 10px; }
        .blood-panel { border-color: var(--blood-red); box-shadow: var(--shadow-red); }
        .blood-panel h2 { color: var(--blood-red); border-color: var(--blood-red); }
        .dark-panel { border-color: var(--deep-purple); box-shadow: var(--shadow-purple); }
        .dark-panel h2 { color: var(--deep-purple); border-color: var(--deep-purple); }
        .void-panel { border-color: var(--ghost-gray); box-shadow: 0 0 20px rgba(102, 102, 102, 0.3); }
        .void-panel h2 { color: var(--ghost-gray); border-color: var(--ghost-gray); }
        .necro-panel { border-color: var(--necro-green); box-shadow: var(--shadow-green); }
        .necro-panel h2 { color: var(--necro-green); border-color: var(--necro-green); }
        .status-panel { border-color: var(--bone-white); box-shadow: 0 0 20px rgba(248, 248, 255, 0.2); grid-column: 1 / -1; }
        .status-panel h2 { color: var(--bone-white); border-color: var(--bone-white); }
        .code-panel { border-color: var(--shadow-cyan); box-shadow: var(--shadow-cyan); }
        .code-panel h2 { color: var(--shadow-cyan); border-color: var(--shadow-cyan); }
        .ops-panel { border-color: var(--neon-yellow, #fff000); box-shadow: 0 0 20px rgba(255, 240, 0, 0.4); }
        .ops-panel h2 { color: var(--neon-yellow, #fff000); border-color: var(--neon-yellow, #fff000); }
        .btn { background: linear-gradient(135deg, var(--secondary-bg), #333); border: 1px solid var(--border-color); color: var(--text-primary); padding: 10px 15px; border-radius: 4px; cursor: pointer; font-family: 'Orbitron', monospace; font-weight: 700; text-transform: uppercase; }
        .btn-blood { border-color: var(--blood-red); color: var(--blood-red); } .btn-blood:hover { background: var(--blood-red); color: var(--primary-bg); box-shadow: var(--shadow-red); }
        .btn-necro { border-color: var(--necro-green); color: var(--necro-green); } .btn-necro:hover { background: var(--necro-green); color: var(--primary-bg); box-shadow: var(--shadow-green); }
        .btn-primary { border-color: var(--shadow-cyan); color: var(--shadow-cyan); } .btn-primary:hover { background: var(--shadow-cyan); color: var(--primary-bg); box-shadow: var(--shadow-cyan); }
        .btn-sm { padding: 8px 12px; font-size: 0.8rem; }
        .input-group { display: flex; align-items: stretch; gap: 10px; margin-bottom: 15px; }
        .input-group label { color: var(--text-secondary); font-weight: 600; font-family: 'Orbitron', monospace; padding: 10px; background: rgba(0,0,0,0.4); border: 1px solid var(--border-color); border-right: none; border-radius: 5px 0 0 5px;}
        .input-group input, .input-group textarea, .input-group select { flex-grow: 1; background: rgba(0, 0, 0, 0.8); border: 1px solid var(--border-color); color: var(--text-primary); padding: 10px 15px; border-radius: 0 5px 5px 0; font-family: 'Courier Prime', monospace; }
        .grab-section { margin-bottom: 15px; padding: 15px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px;}
        .grab-section h3 { color: var(--text-secondary); margin-top:0; margin-bottom: 15px; font-family: 'Orbitron', monospace; text-shadow: 0 0 10px var(--text-secondary); display: flex; justify-content: space-between; align-items: center;}
        .reboot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; }
        .msg-status { text-align: center; color: var(--shadow-cyan); font-family: 'Courier Prime', monospace; padding: 12px; border: 1px dashed var(--border-color); border-radius: 4px; margin-bottom: 20px; background: rgba(0, 139, 139, 0.1); display: none; }
        .status-grid { display: flex; flex-direction: column; gap: 15px; }
        .status-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(0,0,0,0.6); border: 1px solid var(--border-color); border-radius: 8px; }
        .status-label { font-weight: 600; font-family: 'Orbitron'; }
        .timer-display { font-family: 'Courier Prime', monospace; font-size: 1.2em; font-weight: 700; }
        .status-badge { padding: 4px 10px; border-radius: 15px; text-transform: uppercase; font-size: 0.8em; }
        .status-badge.active { background: var(--necro-green); color: var(--primary-bg); box-shadow: var(--shadow-green); }
        .status-badge.inactive { background: var(--dark-red); color: var(--text-secondary); }
        .quick-cmd-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 10px; }
        .bot-status-container { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; margin-top: 15px; border-top: 1px solid var(--border-color); padding-top: 15px; }
        .bot-status-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .bot-status-item { display: flex; justify-content: space-between; align-items: center; padding: 5px 8px; background: rgba(0,0,0,0.3); border-radius: 4px; font-family: 'Courier Prime', monospace; border: 1px solid var(--blood-red); }
        .status-indicator { font-weight: 700; text-transform: uppercase; font-size: 0.9em; }
        .status-indicator.online { color: var(--necro-green); } .status-indicator.offline { color: var(--blood-red); }
        .btn-toggle-state { padding: 3px 5px; font-size: 0.9em; font-family: 'Courier Prime', monospace; border-radius: 4px; cursor: pointer; text-transform: uppercase; background: transparent; font-weight: 700; border: none; }
        .btn-rise { color: var(--necro-green); }
        .btn-rest { color: var(--blood-red); }
        .panel h2::before, .panel h2::after { content: attr(data-text); position: absolute; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden; }
        .panel h2::before { left: 2px; text-shadow: -2px 0 red; clip: rect(44px, 450px, 56px, 0); animation: glitch-anim 2s infinite linear alternate-reverse; }
        .panel h2::after { left: -2px; text-shadow: -2px 0 blue; clip: rect(85px, 450px, 140px, 0); animation: glitch-anim2 3s infinite linear alternate-reverse; }
        @keyframes glitch-skew { 0% { transform: skew(0deg); } 100% { transform: skew(1.5deg); } }
        @keyframes glitch-anim{0%{clip:rect(42px,9999px,44px,0);transform:skew(.3deg)}5%{clip:rect(17px,9999px,94px,0);transform:skew(.5deg)}10%{clip:rect(40px,9999px,90px,0);transform:skew(.2deg)}15%{clip:rect(37px,9999px,20px,0);transform:skew(.8deg)}20%{clip:rect(67px,9999px,80px,0);transform:skew(.1deg)}25%{clip:rect(30px,9999px,50px,0);transform:skew(.6deg)}30%{clip:rect(50px,9999px,75px,0);transform:skew(.4deg)}35%{clip:rect(22px,9999px,69px,0);transform:skew(.2deg)}40%{clip:rect(80px,9999px,100px,0);transform:skew(.7deg)}45%{clip:rect(10px,9999px,95px,0);transform:skew(.1deg)}50%{clip:rect(85px,9999px,40px,0);transform:skew(.3deg)}55%{clip:rect(5px,9999px,80px,0);transform:skew(.9deg)}60%{clip:rect(30px,9999px,90px,0);transform:skew(.2deg)}65%{clip:rect(90px,9999px,10px,0);transform:skew(.5deg)}70%{clip:rect(10px,9999px,55px,0);transform:skew(.3deg)}75%{clip:rect(55px,9999px,25px,0);transform:skew(.6deg)}80%{clip:rect(25px,9999px,75px,0);transform:skew(.4deg)}85%{clip:rect(75px,9999px,50px,0);transform:skew(.2deg)}90%{clip:rect(50px,9999px,30px,0);transform:skew(.7deg)}95%{clip:rect(30px,9999px,10px,0);transform:skew(.1deg)}100%{clip:rect(10px,9999px,90px,0);transform:skew(.4deg)}}
        @keyframes glitch-anim2{0%{clip:rect(85px,9999px,140px,0);transform:skew(.8deg)}5%{clip:rect(20px,9999px,70px,0);transform:skew(.1deg)}10%{clip:rect(70px,9999px,10px,0);transform:skew(.4deg)}15%{clip:rect(30px,9999px,90px,0);transform:skew(.7deg)}20%{clip:rect(90px,9999px,20px,0);transform:skew(.2deg)}25%{clip:rect(40px,9999px,80px,0);transform:skew(.5deg)}30%{clip-path:inset(50% 0 30% 0);transform:skew(.3deg)}35%{clip:rect(80px,9999px,40px,0);transform:skew(.1deg)}40%{clip:rect(10px,9999px,70px,0);transform:skew(.9deg)}45%{clip:rect(70px,9999px,30px,0);transform:skew(.2deg)}50%{clip:rect(30px,9999px,90px,0);transform:skew(.6deg)}55%{clip:rect(90px,9999px,10px,0);transform:skew(.4deg)}60%{clip:rect(10px,9999px,60px,0);transform:skew(.1deg)}65%{clip:rect(60px,9999px,20px,0);transform:skew(.8deg)}70%{clip:rect(20px,9999px,80px,0);transform:skew(.2deg)}75%{clip:rect(80px,9999px,40px,0);transform:skew(.5deg)}80%{clip:rect(40px,9999px,60px,0);transform:skew(.3deg)}85%{clip:rect(60px,9999px,30px,0);transform:skew(.7deg)}90%{clip:rect(30px,9999px,70px,0);transform:skew(.1deg)}95%{clip:rect(70px,9999px,10px,0);transform:skew(.4deg)}100%{clip:rect(10px,9999px,80px,0);transform:skew(.9deg)}}
        .bot-main { border-color: var(--blood-red) !important; box-shadow: var(--shadow-red); }
        .bot-main span:first-child { color: #FF4500; text-shadow: 0 0 8px #FF4500; font-weight: 700; }
        .panel h2.farm-title::before, .panel h2.farm-title::after {
            content: none !important;
            animation: none !important;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="skull-icon">💀</div>
            <h1 class="title"><span class="title-main">KARUTA</span> <span class="title-sub">DEEP</span></h1>
            <p class="subtitle">Shadow Network Control Interface</p>
            <p class="creepy-subtitle">The Abyss Gazes Back...</p>
        </div>
        
        <div id="msg-status-container" class="msg-status"><i class="fas fa-info-circle"></i> <span id="msg-status-text"></span></div>

        <div class="main-grid">
            <div class="panel status-panel">
                <h2 data-text="System Status"><i class="fas fa-heartbeat"></i> System Status</h2>
                <div class="bot-status-container">
                    <div class="status-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="status-row"><span class="status-label"><i class="fas fa-cogs"></i> Auto Work</span><div><span id="work-timer" class="timer-display">--:--:--</span> <span id="work-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-calendar-check"></i> Auto Daily</span><div><span id="daily-timer" class="timer-display">--:--:--</span> <span id="daily-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-gem"></i> Auto KVI</span><div><span id="kvi-timer" class="timer-display">--:--:--</span> <span id="kvi-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-broadcast-tower"></i> Auto Spam</span><div><span id="spam-timer" class="timer-display">--:--:--</span><span id="spam-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-redo"></i> Auto Reboot</span><div><span id="reboot-timer" class="timer-display">--:--:--</span> <span id="reboot-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-server"></i> Deep Uptime</span><div><span id="uptime-timer" class="timer-display">--:--:--</span></div></div> 
                    </div>
                    <div id="bot-status-list" class="bot-status-grid"></div>
                </div>
            </div>
                
            <div class="panel blood-panel">
                <h2 data-text="Soul Harvest"><i class="fas fa-crosshairs"></i> Soul Harvest</h2>
                <div class="grab-section"><h3>ALPHA NODE <span id="harvest-status-1" class="status-badge {{ grab_status }}">{{ grab_text }}</span></h3><div class="input-group"><input type="number" id="heart-threshold-1" value="{{ heart_threshold }}" min="0"><button type="button" id="harvest-toggle-1" class="btn {{ grab_button_class }}">{{ grab_action }}</button></div></div>
                <div class="grab-section"><h3>BETA NODE <span id="harvest-status-2" class="status-badge {{ grab_status_2 }}">{{ grab_text_2 }}</span></h3><div class="input-group"><input type="number" id="heart-threshold-2" value="{{ heart_threshold_2 }}" min="0"><button type="button" id="harvest-toggle-2" class="btn {{ grab_button_class_2 }}">{{ grab_action_2 }}</button></div></div>
                <div class="grab-section"><h3>GAMMA NODE <span id="harvest-status-3" class="status-badge {{ grab_status_3 }}">{{ grab_text_3 }}</span></h3><div class="input-group"><input type="number" id="heart-threshold-3" value="{{ heart_threshold_3 }}" min="0"><button type="button" id="harvest-toggle-3" class="btn {{ grab_button_class_3 }}">{{ grab_action_3 }}</button></div></div>
                <div class="grab-section"><h3>DELTA NODE <span id="harvest-status-4" class="status-badge {{ grab_status_4 }}">{{ grab_text_4 }}</span></h3><div class="input-group"><input type="number" id="heart-threshold-4" value="{{ heart_threshold_4 }}" min="0"><button type="button" id="harvest-toggle-4" class="btn {{ grab_button_class_4 }}">{{ grab_action_4 }}</button></div></div>
            </div>

            <div class="panel ops-panel">
                <h2 data-text="Manual Operations"><i class="fas fa-keyboard"></i> Manual Operations</h2>
                <div style="display: flex; flex-direction: column; gap: 15px;">
                    <div class="input-group"><input type="text" id="manual-message-input" placeholder="Enter manual message for slaves..." style="border-radius: 5px;"><button type="button" id="send-manual-message-btn" class="btn" style="flex-shrink: 0; border-color: var(--neon-yellow, #fff000); color: var(--neon-yellow, #fff000);">SEND</button></div>
                    <div id="quick-cmd-container" class="quick-cmd-grid">
                        <button type="button" data-cmd="kc o:w" class="btn">KC O:W</button>
                        <button type="button" data-cmd="kc o:ef" class="btn">KC O:EF</button>
                        <button type="button" data-cmd="kc o:p" class="btn">KC O:P</button>
                        <button type="button" data-cmd="kc e:1" class="btn">KC E:1</button>
                        <button type="button" data-cmd="kc e:2" class="btn">KC E:2</button>
                        <button type="button" data-cmd="kc e:3" class="btn">KC E:3</button>
                        <button type="button" data-cmd="kc e:4" class="btn">KC E:4</button>
                        <button type="button" data-cmd="kc e:5" class="btn">KC E:5</button>
                        <button type="button" data-cmd="kc e:6" class="btn">KC E:6</button>
                        <button type="button" data-cmd="kc e:7" class="btn">KC E:7</button>
                        <button type="button" data-cmd="kjb" class="btn">KJB</button>
                        <button type="button" data-cmd="kc o:w t:b" class="btn">KC O:W T:B</button>
                    </div>

                    <hr style="border-color: var(--border-color); margin: 25px 0;">
                    <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">
                        MAIN ACCOUNTS COMMAND (2, 3, 4)
                    </h3>
                    <div class="input-group">
                        <input type="text" id="manual-main-message-input" placeholder="Enter message for main accounts 2, 3, 4...">
                        <button type="button" id="send-manual-main-message-btn" class="btn btn-primary">SEND TO MAINS</button>
                    </div>                  
                </div>
            </div>
            
            <div class="panel code-panel">
                <h2 data-text="Code Injection"><i class="fas fa-code"></i> Code Injection</h2>
                <div class="input-group"><label>Target</label><select id="inject-acc-index">{{ acc_options|safe }}</select></div>
                <div class="input-group"><label>Prefix</label><input type="text" id="inject-prefix" placeholder="e.g. kt n"></div>
                <div class="input-group"><label>Delay</label><input type="number" id="inject-delay" value="1.0" step="0.1"></div>
                <div class="input-group" style="flex-direction: column; align-items: stretch;"><label style="border-radius: 5px 5px 0 0; border-bottom: none;">Code List (comma-separated)</label><textarea id="inject-codes" placeholder="paste codes here, separated by commas" rows="3" style="border-radius: 0 0 5px 5px;"></textarea></div>
                <button type="button" id="inject-codes-btn" class="btn btn-primary" style="width: 100%; margin-top:10px;">Inject Codes</button>
                <hr style="border-color: var(--border-color); margin: 20px 0;">
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">
                    EVENT GRAB (ALPHA NODE)
                </h3>
                <button type="button" id="event-grab-toggle-btn" class="btn {{ event_grab_button_class }}" style="width:100%;">
                    <i class="fas fa-star"></i> {{ event_grab_action }} EVENT GRAB
                </button>
            </div>

            <div class="panel void-panel">
                <h2 data-text="Shadow Labor"><i class="fas fa-cogs"></i> Shadow Labor</h2>
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">AUTO WORK</h3>
                <div class="input-group"><label>Node Delay</label><input type="number" id="work-delay-between-acc" value="{{ work_delay_between_acc }}"></div>
                <div class="input-group"><label>Cycle Delay</label><input type="number" id="work-delay-after-all" value="{{ work_delay_after_all }}"></div>
                <button type="button" id="auto-work-toggle-btn" class="btn {{ work_button_class }}" style="width:100%;">{{ work_action }} WORK</button>
                <hr style="border-color: var(--border-color); margin: 25px 0;">
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">DAILY RITUAL</h3>
                <div class="input-group"><label>Node Delay</label><input type="number" id="daily-delay-between-acc" value="{{ daily_delay_between_acc }}"></div>
                <div class="input-group"><label>Cycle Delay</label><input type="number" id="daily-delay-after-all" value="{{ daily_delay_after_all }}"></div>
                <button type="button" id="auto-daily-toggle-btn" class="btn {{ daily_button_class }}" style="width:100%;">{{ daily_action }} DAILY</button>
            </div>

            <div class="panel necro-panel">
                 <h2 data-text="Shadow Resurrection"><i class="fas fa-skull"></i> Shadow Resurrection</h2>
                <div class="input-group"><label>Interval (s)</label><input type="number" id="auto-reboot-delay" value="{{ auto_reboot_delay }}"></div>
                <button type="button" id="auto-reboot-toggle-btn" class="btn {{ reboot_button_class }}" style="width:100%;">{{ reboot_action }} AUTO REBOOT</button>
                <hr style="border-color: var(--border-color); margin: 20px 0;">
                <h3 style="text-align:center; font-family: 'Orbitron';">MANUAL OVERRIDE</h3>
                <div id="reboot-grid-container" class="reboot-grid" style="margin-top: 15px;">
                    <button type="button" data-reboot-target="main_1" class="btn btn-necro btn-sm">ALPHA</button>
                    <button type="button" data-reboot-target="main_2" class="btn btn-necro btn-sm">BETA</button>
                    <button type="button" data-reboot-target="main_3" class="btn btn-necro btn-sm">GAMMA</button>
                    {{ sub_account_buttons|safe }}
                </div>
                 <button type="button" id="reboot-all-btn" class="btn btn-blood" style="width:100%; margin-top: 15px;">REBOOT ALL SYSTEMS</button>
            </div>
            
             <div class="panel dark-panel">
                <h2 data-text="Shadow Broadcast"><i class="fas fa-broadcast-tower"></i> Shadow Broadcast</h2>
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">AUTO SPAM</h3>
                <div class="input-group"><label>Message</label><textarea id="spam-message" rows="2">{{ spam_message }}</textarea></div>
                <div class="input-group"><label>Delay (s)</label><input type="number" id="spam-delay" value="{{ spam_delay }}"></div>
                <button type="button" id="spam-toggle-btn" class="btn {{ spam_button_class }}" style="width:100%;">{{ spam_action }} SPAM</button>
                <hr style="border-color: var(--border-color); margin: 25px 0;">
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">AUTO KVI (MAIN ACC 1)</h3>
                <div class="input-group">
                    <label>Account</label>
                    <select id="kvi-target-account">
                        <option value="main_1" {{ 'selected' if kvi_target_account == 'main_1' }}>ALPHA NODE (Main 1)</option>
                        <option value="main_2" {{ 'selected' if kvi_target_account == 'main_2' }}>BETA NODE (Main 2)</option>
                        <option value="main_3" {{ 'selected' if kvi_target_account == 'main_3' }}>GAMMA NODE (Main 3)</option>
                        <option value="main_4" {{ 'selected' if kvi_target_account == 'main_4' }}>DELTA NODE (Main 4)</option>
                    </select>
                </div>
                <div class="input-group"><label>Clicks</label><input type="number" id="kvi-click-count" value="{{ kvi_click_count }}"></div>
                <div class="input-group"><label>Click Delay</label><input type="number" id="kvi-click-delay" value="{{ kvi_click_delay }}"></div>
                <div class="input-group"><label>Cycle Delay</label><input type="number" id="kvi-loop-delay" value="{{ kvi_loop_delay }}"></div>
                <button type="button" id="auto-kvi-toggle-btn" class="btn {{ kvi_button_class }}" style="width:100%;">{{ kvi_action }} KVI</button>    
            </div>
        </div>
    </div>
    
    <div class="panel" style="border-color: #FF69B4; box-shadow: 0 0 20px rgba(255, 215, 0, 0.4); margin-top: 20px;"> 
    
    <h2 data-text="Multi-Farm Control" style="color: #FF69B4; border-color: #FFD700; font-family: 'Nosifer', cursive; font-size: 1.4rem; margin-bottom: 20px; text-transform: uppercase; border-bottom: 2px solid; padding-bottom: 10px; position: relative;">
        <i class="fas fa-network-wired"></i> Multi-Farm Control
    </h2>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <button id="sync-all-farms-btn" class="btn btn-primary" style="font-size: 1rem; padding: 12px 25px;">
            <i class="fas fa-sync-alt"></i> Đồng Bộ Cài Đặt Harvest Với Panel Chính
        </button>
    </div>
    <div id="farm-grid" class="main-grid">

    <div id="farm-grid" class="main-grid">
        
        {% for server in farm_servers %}
        <div class="panel server-farm-panel" data-farm-id="{{ server.id }}" style="background: rgba(0,0,0,0.4); box-shadow: 0 0 10px rgba(255, 105, 180, 0.6); border: none;">
            <button class="btn-delete-farm" title="Delete Farm" style="position: absolute; top: 10px; right: 10px; background: var(--dark-red); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer; line-height: 30px; text-align: center; padding: 0;">
                <i class="fas fa-times"></i>
            </button>
            <h2 class="farm-title" style="color: #FF1493; font-family: 'Nosifer', cursive; margin-top: 0; padding-right: 30px; font-size: 1.2rem; border-bottom: none; margin-bottom: 15px; animation: none;">{{ server.name }}</h2>
            
            <div style="padding-top: 15px; margin-top: 15px; border-top: 1px solid #444;">
                <div class="input-group"><label>Main CH</label><input type="text" class="farm-channel-input" data-field="main_channel_id" value="{{ server.main_channel_id or '' }}"></div>
                <div class="input-group"><label>KTB CH</label><input type="text" class="farm-channel-input" data-field="ktb_channel_id" value="{{ server.ktb_channel_id or '' }}"></div>
                <div class="input-group"><label>Spam CH</label><input type="text" class="farm-channel-input" data-field="spam_channel_id" value="{{ server.spam_channel_id or '' }}"></div>
            </div>
            
            <div style="padding-top: 15px; margin-top: 15px; border-top: 1px solid #444;">
                <div style="display: flex; flex-direction:column; gap: 10px;">
                    {% for i in range(1, 5) %}
                    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                        <span style="font-family: 'Orbitron';">{{ ['ALPHA', 'BETA', 'GAMMA', 'DELTA'][i-1] }}</span>
                        <div class="input-group" style="margin: 0; flex-grow: 1; margin-left: 10px;">
                            <input type="number" class="farm-harvest-threshold" data-node="{{ i }}" value="{{ server['heart_threshold_' ~ i] or 50 }}" min="0">
                            <button type="button" class="btn btn-sm farm-harvest-toggle" data-node="{{ i }}">{{ 'TẮT' if server['auto_grab_enabled_' ~ i] else 'BẬT' }}</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div style="padding-top: 15px; margin-top: 15px; border-top: 1px solid #444;">
                <textarea class="farm-spam-message" rows="2" placeholder="Nội dung spam cho farm..." style="width: calc(100% - 30px); margin-bottom: 10px;">{{ server.spam_message or '' }}</textarea>
                <div class="input-group"><label>Delay</label><input type="number" class="farm-spam-delay" value="{{ server.spam_delay or 10 }}"><span class="timer-display farm-spam-timer">--:--:--</span></div>
                <button type="button" class="btn farm-broadcast-toggle">{{ 'TẮT SPAM' if server.spam_enabled else 'BẬT SPAM' }}</button>
            </div>
        </div>
        {% endfor %}

        <div id="add-farm-btn" class="panel" style="display: flex; align-items: center; justify-content: center; min-height: 200px; border-style: dashed; border-color: #888; cursor: pointer; background: rgba(0,0,0,0.2);">
            <i class="fas fa-plus" style="font-size: 3rem; color: #888;"></i>
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        function initGlitches() {
            document.querySelectorAll('.panel h2').forEach(header => {
                const textContent = header.childNodes[header.childNodes.length - 1].textContent.trim();
                header.setAttribute('data-text', textContent);
            });
        }
        initGlitches();

        const msgStatusContainer = document.getElementById('msg-status-container');
        const msgStatusText = document.getElementById('msg-status-text');

        function showStatusMessage(message) {
            if (!message) return;
            msgStatusText.textContent = message;
            msgStatusContainer.style.display = 'block';
            setTimeout(() => { msgStatusContainer.style.display = 'none'; }, 4000);
        }

        async function postData(url = '', data = {}) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                showStatusMessage(result.message);

                setTimeout(() => {
                    fetchStatus();
                }, 1000); // 1000ms = 1 giây

                return result;
            } catch (error) {
                console.error('Error posting data:', error);
                showStatusMessage('Error communicating with server.');
            }
        }

        function formatTime(seconds) {
            if (isNaN(seconds) || seconds < 0) return "--:--:--";
            seconds = Math.floor(seconds);
            const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
            const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
            const s = (seconds % 60).toString().padStart(2, '0');
            return `${h}:${m}:${s}`;
        }

        function updateElement(id, { textContent, className, value, innerHTML }) {
            const el = document.getElementById(id);
            if (!el) return;
            if (textContent !== undefined) el.textContent = textContent;
            if (className !== undefined) el.className = className;
            if (value !== undefined) el.value = value;
            if (innerHTML !== undefined) el.innerHTML = innerHTML;
        }

        async function fetchStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                
                updateElement('work-timer', { textContent: formatTime(data.work_countdown) });
                updateElement('work-status-badge', { textContent: data.work_enabled ? 'ON' : 'OFF', className: `status-badge ${data.work_enabled ? 'active' : 'inactive'}` });
                updateElement('daily-timer', { textContent: formatTime(data.daily_countdown) });
                updateElement('daily-status-badge', { textContent: data.daily_enabled ? 'ON' : 'OFF', className: `status-badge ${data.daily_enabled ? 'active' : 'inactive'}` });
                updateElement('kvi-timer', { textContent: formatTime(data.kvi_countdown) });
                updateElement('kvi-status-badge', { textContent: data.kvi_enabled ? 'ON' : 'OFF', className: `status-badge ${data.kvi_enabled ? 'active' : 'inactive'}` });
                updateElement('reboot-timer', { textContent: formatTime(data.reboot_countdown) });
                updateElement('reboot-status-badge', { textContent: data.reboot_enabled ? 'ON' : 'OFF', className: `status-badge ${data.reboot_enabled ? 'active' : 'inactive'}` });
                updateElement('spam-timer', { textContent: formatTime(data.spam_countdown) });
                updateElement('spam-status-badge', { textContent: data.spam_enabled ? 'ON' : 'OFF', className: `status-badge ${data.spam_enabled ? 'active' : 'inactive'}` });
                const serverUptimeSeconds = (Date.now() / 1000) - data.server_start_time;
                updateElement('uptime-timer', { textContent: formatTime(serverUptimeSeconds) });
                updateElement('event-grab-toggle-btn', { 
                textContent: `${data.ui_states.event_grab_action} EVENT GRAB`, 
                className: `btn ${data.ui_states.event_grab_button_class}` 
                });

                updateElement('harvest-toggle-1', { textContent: data.ui_states.grab_action, className: `btn ${data.ui_states.grab_button_class}` });
                updateElement('harvest-status-1', { textContent: data.ui_states.grab_text, className: `status-badge ${data.ui_states.grab_status}` });
                updateElement('harvest-toggle-2', { textContent: data.ui_states.grab_action_2, className: `btn ${data.ui_states.grab_button_class_2}` });
                updateElement('harvest-status-2', { textContent: data.ui_states.grab_text_2, className: `status-badge ${data.ui_states.grab_status_2}` });
                updateElement('harvest-toggle-3', { textContent: data.ui_states.grab_action_3, className: `btn ${data.ui_states.grab_button_class_3}` });
                updateElement('harvest-status-3', { textContent: data.ui_states.grab_text_3, className: `status-badge ${data.ui_states.grab_status_3}` });
                updateElement('harvest-toggle-4', { textContent: data.ui_states.grab_action_4, className: `btn ${data.ui_states.grab_button_class_4}` });
                updateElement('harvest-status-4', { textContent: data.ui_states.grab_text_4, className: `status-badge ${data.ui_states.grab_status_4}` });
                updateElement('auto-work-toggle-btn', { textContent: `${data.ui_states.work_action} WORK`, className: `btn ${data.ui_states.work_button_class}` });
                updateElement('auto-daily-toggle-btn', { textContent: `${data.ui_states.daily_action} DAILY`, className: `btn ${data.ui_states.daily_button_class}` });
                updateElement('auto-reboot-toggle-btn', { textContent: `${data.ui_states.reboot_action} AUTO REBOOT`, className: `btn ${data.ui_states.reboot_button_class}` });
                updateElement('spam-toggle-btn', { textContent: `${data.ui_states.spam_action} SPAM`, className: `btn ${data.ui_states.spam_button_class}` });
                updateElement('auto-kvi-toggle-btn', { textContent: `${data.ui_states.kvi_action} KVI`, className: `btn ${data.ui_states.kvi_button_class}` });

                const listContainer = document.getElementById('bot-status-list');
                listContainer.innerHTML = ''; 
                const allBots = [...data.bot_statuses.main_bots, ...data.bot_statuses.sub_accounts];
                allBots.forEach(bot => {
                    const item = document.createElement('div');
                    item.className = 'bot-status-item';
                    if (bot.type === 'main') item.classList.add('bot-main');
                    const buttonText = bot.is_active ? 'ONLINE' : 'OFFLINE';
                    const buttonClass = bot.is_active ? 'btn-rise' : 'btn-rest';
                    item.innerHTML = `<span>${bot.name}</span><button type="button" data-target="${bot.reboot_id}" class="btn-toggle-state ${buttonClass}">${buttonText}</button>`;
                    listContainer.appendChild(item);
                });
                if (data.farm_servers) {
                    data.farm_servers.forEach(s => {
                        const p = document.querySelector(`.server-farm-panel[data-farm-id="${s.id}"]`);
                        if (!p) return;
                        for(let i=1; i<=4; i++) { p.querySelector(`.farm-harvest-toggle[data-node="${i}"]`).textContent = s[`auto_grab_enabled_${i}`] ? 'TẮT' : 'BẬT'; }
                        p.querySelector('.farm-broadcast-toggle').textContent = s.spam_enabled ? 'TẮT SPAM' : 'BẬT SPAM';
                        let countdown = s.spam_enabled ? (s.last_spam_time + s.spam_delay) - (Date.now()/1000) : 0;
                        p.querySelector('.farm-spam-timer').textContent = formatTime(countdown);
                    });
                 }
            } catch (error) { console.error('Error fetching status:', error); }
        }
        setInterval(fetchStatus, 1000);

        

        // --- Event Listeners for Buttons ---

        document.getElementById('sync-all-farms-btn').addEventListener('click', () => {
            // Chỉ cần gọi API mới đã tạo, không cần gửi dữ liệu gì thêm
            postData('/api/farm/sync_harvest_all', {}); 
        });
        // Soul Harvest
        document.getElementById('harvest-toggle-1').addEventListener('click', () => postData('/api/harvest_toggle', { node: 1, threshold: document.getElementById('heart-threshold-1').value }));
        document.getElementById('harvest-toggle-2').addEventListener('click', () => postData('/api/harvest_toggle', { node: 2, threshold: document.getElementById('heart-threshold-2').value }));
        document.getElementById('harvest-toggle-3').addEventListener('click', () => postData('/api/harvest_toggle', { node: 3, threshold: document.getElementById('heart-threshold-3').value }));
        document.getElementById('harvest-toggle-4').addEventListener('click', () => postData('/api/harvest_toggle', { node: 4, threshold: document.getElementById('heart-threshold-4').value }));
        
        // Manual Operations
        document.getElementById('send-manual-message-btn').addEventListener('click', () => {
            postData('/api/manual_ops', { message: document.getElementById('manual-message-input').value })
                .then(() => {
                    document.getElementById('manual-message-input').value = '';
                });
        });

        document.getElementById('send-manual-main-message-btn').addEventListener('click', () => {
            postData('/api/manual_ops_main', {
                message: document.getElementById('manual-main-message-input').value
            }).then(() => {
                document.getElementById('manual-main-message-input').value = '';
            });
        });
        
        document.getElementById('quick-cmd-container').addEventListener('click', (e) => {
            if (e.target.matches('button[data-cmd]')) {
                postData('/api/manual_ops', { quickmsg: e.target.dataset.cmd });
            }
        });

        // Code Injection
        document.getElementById('inject-codes-btn').addEventListener('click', () => {
            postData('/api/inject_codes', {
                acc_index: document.getElementById('inject-acc-index').value,
                prefix: document.getElementById('inject-prefix').value,
                delay: document.getElementById('inject-delay').value,
                codes: document.getElementById('inject-codes').value,
            }).then(() => {
                 document.getElementById('inject-prefix').value = '';
                 document.getElementById('inject-codes').value = '';
            });
        });
        document.getElementById('event-grab-toggle-btn').addEventListener('click', () => postData('/api/event_grab_toggle', {}));
        // Shadow Labor
        document.getElementById('auto-work-toggle-btn').addEventListener('click', () => {
            postData('/api/labor_toggle', {
                type: 'work',
                delay_between: document.getElementById('work-delay-between-acc').value,
                delay_after: document.getElementById('work-delay-after-all').value
            });
        });
        document.getElementById('auto-daily-toggle-btn').addEventListener('click', () => {
            postData('/api/labor_toggle', {
                type: 'daily',
                delay_between: document.getElementById('daily-delay-between-acc').value,
                delay_after: document.getElementById('daily-delay-after-all').value
            });
        });

        // Shadow Resurrection
        document.getElementById('auto-reboot-toggle-btn').addEventListener('click', () => {
            postData('/api/reboot_toggle_auto', { delay: document.getElementById('auto-reboot-delay').value });
        });
        document.getElementById('reboot-all-btn').addEventListener('click', () => {
            postData('/api/reboot_manual', { target: 'all' });
        });
        document.getElementById('reboot-grid-container').addEventListener('click', e => {
            if(e.target.matches('button[data-reboot-target]')) {
                postData('/api/reboot_manual', { target: e.target.dataset.reboot_target });
            }
        });
        
        // Shadow Broadcast
        document.getElementById('spam-toggle-btn').addEventListener('click', () => {
            postData('/api/broadcast_toggle', {
                type: 'spam',
                message: document.getElementById('spam-message').value,
                delay: document.getElementById('spam-delay').value
            });
        });
        document.getElementById('auto-kvi-toggle-btn').addEventListener('click', () => {
             postData('/api/broadcast_toggle', {
                type: 'kvi',
                target_account: document.getElementById('kvi-target-account').value,
                clicks: document.getElementById('kvi-click-count').value,
                click_delay: document.getElementById('kvi-click-delay').value,
                loop_delay: document.getElementById('kvi-loop-delay').value
            });
        });
        
        // Bot State Toggle (in status list)
        document.getElementById('bot-status-list').addEventListener('click', e => {
            if(e.target.matches('button[data-target]')) {
                postData('/api/toggle_bot_state', { target: e.target.dataset.target });
            }
        });
        const farmGrid = document.getElementById('farm-grid');
        if (farmGrid) {
            document.getElementById('add-farm-btn').addEventListener('click', () => { const name = prompt("Nhập tên cho farm mới:", "Farm Mới"); if (name) postData('/api/farm/add', { name: name }); });
            farmGrid.addEventListener('click', e => {
                const p = e.target.closest('.server-farm-panel'); if (!p) return; const id = p.dataset.farmId;
                if (e.target.closest('.btn-delete-farm')) { if (confirm('Xóa farm này?')) postData('/api/farm/delete', { farm_id: id }); }
                if (e.target.classList.contains('farm-harvest-toggle')) { const n = e.target.dataset.node; const t = p.querySelector(`.farm-harvest-threshold[data-node="${n}"]`); postData('/api/farm/harvest_toggle', { farm_id: id, node: n, threshold: t.value });}
                if (e.target.classList.contains('farm-broadcast-toggle')) { const m = p.querySelector('.farm-spam-message').value; const d = p.querySelector('.farm-spam-delay').value; postData('/api/farm/broadcast_toggle', { farm_id: id, message: m, delay: d }); }
            });
            farmGrid.addEventListener('change', e => {
                const p = e.target.closest('.server-farm-panel'); if (!p) return; const id = p.dataset.farmId;
                if(e.target.classList.contains('farm-channel-input')) { const d = {}; d[e.target.dataset.field] = e.target.value; postData('/api/farm/update_channels', {farm_id: id, ...d}); }
            });
        }
        
    });
</script>
</body>
</html>
"""

# --- FLASK ROUTES ---
@app.route("/")
def index():
    # This function is now very simple. It just prepares the data for the initial render.
    grab_status, grab_text, grab_action, grab_button_class = ("active", "ON", "DISABLE", "btn btn-blood") if auto_grab_enabled else ("inactive", "OFF", "ENABLE", "btn btn-necro")
    grab_status_2, grab_text_2, grab_action_2, grab_button_class_2 = ("active", "ON", "DISABLE", "btn btn-blood") if auto_grab_enabled_2 else ("inactive", "OFF", "ENABLE", "btn btn-necro")
    grab_status_3, grab_text_3, grab_action_3, grab_button_class_3 = ("active", "ON", "DISABLE", "btn btn-blood") if auto_grab_enabled_3 else ("inactive", "OFF", "ENABLE", "btn btn-necro")
    grab_status_4, grab_text_4, grab_action_4, grab_button_class_4 = ("active", "ON", "DISABLE", "btn btn-blood") if auto_grab_enabled_4 else ("inactive", "OFF", "ENABLE", "btn btn-necro")
    event_grab_action, event_grab_button_class = ("DISABLE", "btn-blood") if event_grab_enabled else ("ENABLE", "btn-necro")
    spam_action, spam_button_class = ("DISABLE", "btn-blood") if spam_enabled else ("ENABLE", "btn-necro")
    work_action, work_button_class = ("DISABLE", "btn-blood") if auto_work_enabled else ("ENABLE", "btn-necro")
    daily_action, daily_button_class = ("DISABLE", "btn-blood") if auto_daily_enabled else ("ENABLE", "btn-necro")
    kvi_action, kvi_button_class = ("DISABLE", "btn-blood") if auto_kvi_enabled else ("ENABLE", "btn-necro")
    reboot_action, reboot_button_class = ("DISABLE", "btn-blood") if auto_reboot_enabled else ("ENABLE", "btn-necro")
    
    acc_options = "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names[:len(bots)]))
    if main_bot: acc_options += '<option value="main_1">ALPHA NODE (Main)</option>'
    if main_bot_2: acc_options += '<option value="main_2">BETA NODE (Main)</option>'
    if main_bot_3: acc_options += '<option value="main_3">GAMMA NODE (Main)</option>'
    if main_bot_4: acc_options += '<option value="main_4">DELTA NODE (Main)</option>'
    sub_account_buttons = "".join(f'<button type="button" data-reboot-target="sub_{i}" class="btn btn-necro btn-sm">{name}</button>' for i, name in enumerate(acc_names[:len(bots)]))

    return render_template_string(HTML_TEMPLATE, 
        grab_status=grab_status, grab_text=grab_text, grab_action=grab_action, grab_button_class=grab_button_class, heart_threshold=heart_threshold,
        grab_status_2=grab_status_2, grab_text_2=grab_text_2, grab_action_2=grab_action_2, grab_button_class_2=grab_button_class_2, heart_threshold_2=heart_threshold_2,
        grab_status_3=grab_status_3, grab_text_3=grab_text_3, grab_action_3=grab_action_3, grab_button_class_3=grab_button_class_3, heart_threshold_3=heart_threshold_3,
        grab_status_4=grab_status_4, grab_text_4=grab_text_4, grab_action_4=grab_action_4, grab_button_class_4=grab_button_class_4, heart_threshold_4=heart_threshold_4,
        event_grab_action=event_grab_action,
        event_grab_button_class=event_grab_button_class,
        spam_message=spam_message, spam_delay=spam_delay, spam_action=spam_action, spam_button_class=spam_button_class,
        work_delay_between_acc=work_delay_between_acc, work_delay_after_all=work_delay_after_all, work_action=work_action, work_button_class=work_button_class,
        daily_delay_between_acc=daily_delay_between_acc, daily_delay_after_all=daily_delay_after_all, daily_action=daily_action, daily_button_class=daily_button_class,
        kvi_click_count=kvi_click_count, kvi_click_delay=kvi_click_delay, kvi_loop_delay=kvi_loop_delay, kvi_action=kvi_action, kvi_button_class=kvi_button_class, kvi_target_account=kvi_target_account,
        auto_reboot_delay=auto_reboot_delay, reboot_action=reboot_action, reboot_button_class=reboot_button_class,
        acc_options=acc_options, sub_account_buttons=sub_account_buttons, farm_servers=farm_servers
    )
@app.route("/api/farm/add", methods=['POST'])
def api_farm_add():
    data = request.get_json()
    name = data.get('name')
    if not name: return jsonify({'status': 'error', 'message': 'Tên farm là bắt buộc.'}), 400
    new_server = {
        "id": f"farm_{int(time.time())}", "name": name,
        "main_channel_id": "", "ktb_channel_id": "", "spam_channel_id": "",
        "auto_grab_enabled_1": False, "heart_threshold_1": 15,
        "auto_grab_enabled_2": False, "heart_threshold_2": 50,
        "auto_grab_enabled_3": False, "heart_threshold_3": 75,
        "auto_grab_enabled_4": False, "heart_threshold_4": 100,
        "spam_enabled": False, "spam_message": "", "spam_delay": 10, "last_spam_time": 0
    }
    farm_servers.append(new_server)
    save_farm_settings()
    return jsonify({'status': 'success', 'message': f'Farm "{name}" đã được thêm.', 'reload': True})

@app.route("/api/farm/delete", methods=['POST'])
def api_farm_delete():
    global farm_servers
    data = request.get_json(); farm_id = data.get('farm_id')
    initial_len = len(farm_servers)
    farm_servers = [s for s in farm_servers if s.get('id') != farm_id]
    if len(farm_servers) < initial_len:
        save_farm_settings()
        return jsonify({'status': 'success', 'message': 'Farm đã được xóa.', 'reload': True})
    return jsonify({'status': 'error', 'message': 'Không tìm thấy farm.'}), 404

@app.route("/api/farm/update_channels", methods=['POST'])
def api_farm_update_channels():
    data = request.get_json(); farm_id = data.get('farm_id')
    server = next((s for s in farm_servers if s.get('id') == farm_id), None)
    if not server: return jsonify({'status': 'error', 'message': 'Không tìm thấy farm.'}), 404
    for key in ['main_channel_id', 'ktb_channel_id', 'spam_channel_id']:
        if key in data: server[key] = data[key]
    save_farm_settings()
    return jsonify({'status': 'success', 'message': f'Đã cập nhật kênh cho farm {server["name"]}.'})

@app.route("/api/farm/harvest_toggle", methods=['POST'])
def api_farm_harvest_toggle():
    data = request.get_json(); farm_id = data.get('farm_id'); node = int(data.get('node')); threshold = int(data.get('threshold', 50))
    server = next((s for s in farm_servers if s.get('id') == farm_id), None)
    if not server: return jsonify({'status': 'error', 'message': 'Yêu cầu không hợp lệ.'}), 400
    grab_key = f'auto_grab_enabled_{node}'; thresh_key = f'heart_threshold_{node}'
    server[grab_key] = not server.get(grab_key, False)
    server[thresh_key] = threshold
    save_farm_settings()
    state = "BẬT" if server[grab_key] else "TẮT"
    return jsonify({'status': 'success', 'message': f"Grab Node {node} đã được {state} cho farm {server['name']}."})

@app.route("/api/farm/broadcast_toggle", methods=['POST'])
def api_farm_broadcast_toggle():
    data = request.get_json(); farm_id = data.get('farm_id')
    server = next((s for s in farm_servers if s.get('id') == farm_id), None)
    if not server: return jsonify({'status': 'error', 'message': 'Không tìm thấy farm.'}), 404
    server['spam_message'] = data.get("message", "").strip()
    server['spam_delay'] = int(data.get("delay", 10))
    server['spam_enabled'] = not server.get('spam_enabled', False)
    if server['spam_enabled']: server['last_spam_time'] = time.time()
    save_farm_settings()
    state = "BẬT" if server['spam_enabled'] else "TẮT"
    return jsonify({'status': 'success', 'message': f"Spam đã {state} cho farm {server['name']}."})

@app.route("/api/farm/sync_harvest_all", methods=['POST'])
def api_farm_sync_harvest_all():
    """
    API endpoint để đồng bộ cài đặt Harvest từ panel chính
    xuống tất cả các server farm.
    """
    global farm_servers
    print("[Farm Sync] Bắt đầu đồng bộ cài đặt Harvest cho tất cả farm.", flush=True)

    # Lặp qua từng server trong danh sách farm
    for server in farm_servers:
        # Sao chép cài đặt từ các biến global của panel chính
        server['auto_grab_enabled_1'] = auto_grab_enabled
        server['heart_threshold_1'] = heart_threshold
        
        server['auto_grab_enabled_2'] = auto_grab_enabled_2
        server['heart_threshold_2'] = heart_threshold_2

        server['auto_grab_enabled_3'] = auto_grab_enabled_3
        server['heart_threshold_3'] = heart_threshold_3

        server['auto_grab_enabled_4'] = auto_grab_enabled_4
        server['heart_threshold_4'] = heart_threshold_4
        
    save_farm_settings() # Lưu lại toàn bộ thay đổi
    
    return jsonify({'status': 'success', 'message': 'Đã đồng bộ cài đặt Harvest cho tất cả các farm.'})
    
# --- API ENDPOINTS ---
@app.route("/api/event_grab_toggle", methods=['POST'])
def api_event_grab_toggle():
    global event_grab_enabled
    event_grab_enabled = not event_grab_enabled
    msg = f"Event Grab for Main Acc 1 was {'ENABLED' if event_grab_enabled else 'DISABLED'}"
    save_settings() # Lưu lại trạng thái mới
    return jsonify({'status': 'success', 'message': msg})
    
@app.route("/api/harvest_toggle", methods=['POST'])
def api_harvest_toggle():
    global auto_grab_enabled, heart_threshold, auto_grab_enabled_2, heart_threshold_2, auto_grab_enabled_3, heart_threshold_3, auto_grab_enabled_4, heart_threshold_4
    data = request.get_json()
    node = data.get('node')
    threshold = int(data.get('threshold', 50))
    msg = ""
    if node == 1: auto_grab_enabled = not auto_grab_enabled; heart_threshold = threshold; msg = f"Auto Grab 1 was {'ENABLED' if auto_grab_enabled else 'DISABLED'}"
    elif node == 2: auto_grab_enabled_2 = not auto_grab_enabled_2; heart_threshold_2 = threshold; msg = f"Auto Grab 2 was {'ENABLED' if auto_grab_enabled_2 else 'DISABLED'}"
    elif node == 3: auto_grab_enabled_3 = not auto_grab_enabled_3; heart_threshold_3 = threshold; msg = f"Auto Grab 3 was {'ENABLED' if auto_grab_enabled_3 else 'DISABLED'}"
    elif node == 4: auto_grab_enabled_4 = not auto_grab_enabled_4; heart_threshold_4 = threshold; msg = f"Auto Grab 4 was {'ENABLED' if auto_grab_enabled_4 else 'DISABLED'}"
    save_settings()
    return jsonify({'status': 'success', 'message': msg})

@app.route("/api/manual_ops", methods=['POST'])
def api_manual_ops():
    data = request.get_json()
    msg = ""
    msg_to_send = data.get('message') or data.get('quickmsg')
    if msg_to_send:
        msg = f"Sent to slaves: {msg_to_send}"
        with bots_lock:
            for idx, bot in enumerate(bots): 
                if bot and bot_active_states.get(f'sub_{idx}', False):
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, msg_to_send)).start()
    else: msg = "No message provided."
    return jsonify({'status': 'success', 'message': msg})

@app.route("/api/manual_ops_main", methods=['POST'])
def api_manual_ops_main():
    data = request.get_json()
    msg_to_send = data.get('message')
    msg = "No message provided for main accounts."
    if msg_to_send:
        delay = 0
        # Gửi tin nhắn đến Acc 2 nếu đang hoạt động
        if main_bot_2 and bot_active_states.get('main_2', False):
            threading.Timer(delay, main_bot_2.sendMessage, args=(other_channel_id, msg_to_send)).start()
            delay += 2 # Thêm độ trễ 2 giây cho acc tiếp theo
        
        # Gửi tin nhắn đến Acc 3 nếu đang hoạt động
        if main_bot_3 and bot_active_states.get('main_3', False):
            threading.Timer(delay, main_bot_3.sendMessage, args=(other_channel_id, msg_to_send)).start()
            delay += 2
            
        # Gửi tin nhắn đến Acc 4 nếu đang hoạt động
        if main_bot_4 and bot_active_states.get('main_4', False):
            threading.Timer(delay, main_bot_4.sendMessage, args=(other_channel_id, msg_to_send)).start()
            
        msg = f"Sent to Main Accounts (2,3,4): {msg_to_send}"
        
    return jsonify({'status': 'success', 'message': msg})
    
@app.route("/api/inject_codes", methods=['POST'])
def api_inject_codes():
    global main_bot, main_bot_2, main_bot_3, main_bot_4, bots
    try:
        data = request.get_json()
        target_id_str, delay_val, prefix, codes_list = data.get("acc_index"), float(data.get("delay", 1.0)), data.get("prefix", ""), [c.strip() for c in data.get("codes", "").split(',') if c.strip()]
        target_bot, target_name = None, ""
        if target_id_str == 'main_1': target_bot, target_name = main_bot, "ALPHA"
        elif target_id_str == 'main_2': target_bot, target_name = main_bot_2, "BETA"
        elif target_id_str == 'main_3': target_bot, target_name = main_bot_3, "GAMMA"
        elif target_id_str == 'main_4': target_bot, target_name = main_bot_4, "DELTA"
        else:
            acc_idx = int(target_id_str)
            if acc_idx < len(bots): target_bot, target_name = bots[acc_idx], acc_names[acc_idx]
        if target_bot:
            with bots_lock:
                for i, code in enumerate(codes_list): threading.Timer(delay_val * i, target_bot.sendMessage, args=(other_channel_id, f"{prefix} {code}" if prefix else code)).start()
            msg = f"Injecting {len(codes_list)} codes to '{target_name}'."
        else: msg = "Error: Invalid account selected for injection."
    except Exception as e: msg = f"Code Injection Error: {e}"
    return jsonify({'status': 'success', 'message': msg})

@app.route("/api/labor_toggle", methods=['POST'])
def api_labor_toggle():
    global auto_work_enabled, work_delay_between_acc, work_delay_after_all, last_work_cycle_time
    global auto_daily_enabled, daily_delay_between_acc, daily_delay_after_all, last_daily_cycle_time
    data = request.get_json()
    msg = ""
    if data.get('type') == 'work':
        auto_work_enabled = not auto_work_enabled
        if auto_work_enabled and last_work_cycle_time == 0: last_work_cycle_time = time.time() - work_delay_after_all - 1
        work_delay_between_acc = int(data.get('delay_between', 10)); work_delay_after_all = int(data.get('delay_after', 44100))
        msg = f"Auto Work {'ENABLED' if auto_work_enabled else 'DISABLED'}."
    elif data.get('type') == 'daily':
        auto_daily_enabled = not auto_daily_enabled
        if auto_daily_enabled and last_daily_cycle_time == 0: last_daily_cycle_time = time.time() - daily_delay_after_all - 1
        daily_delay_between_acc = int(data.get('delay_between', 3)); daily_delay_after_all = int(data.get('delay_after', 87000))
        msg = f"Auto Daily {'ENABLED' if auto_daily_enabled else 'DISABLED'}."

    return jsonify({'status': 'success', 'message': msg})

@app.route("/api/reboot_manual", methods=['POST'])
def api_reboot_manual():
    data = request.get_json()
    target = data.get('target')
    msg = ""
    if target:
        try:
            if target == "all": msg = "Rebooting all systems... This may take a while."
            else:
                if target.startswith('main_'): bot_name = target.replace('main_','').upper() + " NODE"
                else: index = int(target.split('_')[1]); bot_name = acc_names[index] if index < len(acc_names) else target
                msg = f"Rebooting target: {bot_name}"
        except: msg = f"Rebooting target: {target.upper()}"
        if target == "all":
            if main_bot: reboot_bot('main_1'); time.sleep(5)
            if main_bot_2: reboot_bot('main_2'); time.sleep(5)
            if main_bot_3: reboot_bot('main_3'); time.sleep(5)
            with bots_lock:
                for i in range(len(bots)): reboot_bot(f'sub_{i}'); time.sleep(5)
        else: reboot_bot(target)
    return jsonify({'status': 'success', 'message': msg})

@app.route("/api/reboot_toggle_auto", methods=['POST'])
def api_reboot_toggle_auto():
    global auto_reboot_enabled, auto_reboot_delay, auto_reboot_thread, auto_reboot_stop_event
    data = request.get_json()
    auto_reboot_enabled = not auto_reboot_enabled
    auto_reboot_delay = int(data.get("delay", 3600))
    msg = ""
    if auto_reboot_enabled:
        if auto_reboot_thread is None or not auto_reboot_thread.is_alive():
            auto_reboot_stop_event = threading.Event()
            auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
            auto_reboot_thread.start()
        msg = "Auto Reboot ENABLED."
    else:
        if auto_reboot_stop_event: auto_reboot_stop_event.set()
        auto_reboot_thread = None
        msg = "Auto Reboot DISABLED."

    return jsonify({'status': 'success', 'message': msg})

@app.route("/api/broadcast_toggle", methods=['POST'])
def api_broadcast_toggle():
    global spam_enabled, spam_message, spam_delay, spam_thread, last_spam_time
    global auto_kvi_enabled, kvi_click_count, kvi_click_delay, kvi_loop_delay, last_kvi_cycle_time, kvi_target_account
    data = request.get_json()
    msg = ""
    if data.get('type') == 'spam':
        spam_message, spam_delay = data.get("message", "").strip(), int(data.get("delay", 10))
        if not spam_enabled and spam_message:
            spam_enabled = True; last_spam_time = time.time(); msg = "Spam ENABLED."
            if spam_thread is None or not spam_thread.is_alive():
                spam_thread = threading.Thread(target=spam_loop, daemon=True); spam_thread.start()
        else: spam_enabled = False; msg = "Spam DISABLED."
            
    elif data.get('type') == 'kvi':
        kvi_target_account = data.get('target_account') # Lấy target account từ request
        auto_kvi_enabled = not auto_kvi_enabled
        if auto_kvi_enabled and last_kvi_cycle_time == 0: last_kvi_cycle_time = time.time() - kvi_loop_delay - 1
        kvi_click_count, kvi_click_delay, kvi_loop_delay = int(data.get('clicks', 10)), int(data.get('click_delay', 3)), int(data.get('loop_delay', 7500))
        msg = f"Auto KVI {'ENABLED' if auto_kvi_enabled else 'DISABLED'} on {kvi_target_account.upper()}."
        save_settings()

    return jsonify({'status': 'success', 'message': msg})

@app.route("/api/toggle_bot_state", methods=['POST'])
def api_toggle_bot_state():
    data = request.get_json()
    target = data.get('target')
    msg = ""
    if target in bot_active_states:
        bot_active_states[target] = not bot_active_states[target]
        state_text = "AWAKENED" if bot_active_states[target] else "DORMANT"
        msg = f"Target {target.upper()} has been set to {state_text}."

    return jsonify({'status': 'success', 'message': msg})

@app.route("/status")
def status():
    now = time.time()
    work_countdown = (last_work_cycle_time + work_delay_after_all - now) if auto_work_enabled else 0
    daily_countdown = (last_daily_cycle_time + daily_delay_after_all - now) if auto_daily_enabled else 0
    kvi_countdown = (last_kvi_cycle_time + kvi_loop_delay - now) if auto_kvi_enabled else 0
    reboot_countdown = (last_reboot_cycle_time + auto_reboot_delay - now) if auto_reboot_enabled else 0
    spam_countdown = (last_spam_time + spam_delay - now) if spam_enabled else 0

    bot_statuses = {
        "main_bots": [
            {"name": "ALPHA", "status": main_bot is not None, "reboot_id": "main_1", "is_active": bot_active_states.get('main_1', False), "type": "main"},
            {"name": "BETA", "status": main_bot_2 is not None, "reboot_id": "main_2", "is_active": bot_active_states.get('main_2', False), "type": "main"},
            {"name": "GAMMA", "status": main_bot_3 is not None, "reboot_id": "main_3", "is_active": bot_active_states.get('main_3', False), "type": "main"},
            {"name": "DELTA", "status": main_bot_4 is not None, "reboot_id": "main_4", "is_active": bot_active_states.get('main_4', True), "type": "main"}
        ],
        "sub_accounts": []
    }
    with bots_lock:
        bot_statuses["sub_accounts"] = [
            {"name": acc_names[i] if i < len(acc_names) else f"Sub {i+1}", "status": bot is not None, "reboot_id": f"sub_{i}", "is_active": bot_active_states.get(f'sub_{i}', False), "type": "sub"}
            for i, bot in enumerate(bots)
        ]
    
    ui_states = {
        "grab_status": "active" if auto_grab_enabled else "inactive", "grab_text": "ON" if auto_grab_enabled else "OFF", "grab_action": "DISABLE" if auto_grab_enabled else "ENABLE", "grab_button_class": "btn-blood" if auto_grab_enabled else "btn-necro",
        "grab_status_2": "active" if auto_grab_enabled_2 else "inactive", "grab_text_2": "ON" if auto_grab_enabled_2 else "OFF", "grab_action_2": "DISABLE" if auto_grab_enabled_2 else "ENABLE", "grab_button_class_2": "btn-blood" if auto_grab_enabled_2 else "btn-necro",
        "grab_status_3": "active" if auto_grab_enabled_3 else "inactive", "grab_text_3": "ON" if auto_grab_enabled_3 else "OFF", "grab_action_3": "DISABLE" if auto_grab_enabled_3 else "ENABLE", "grab_button_class_3": "btn-blood" if auto_grab_enabled_3 else "btn-necro",
        "grab_status_4": "active" if auto_grab_enabled_4 else "inactive", "grab_text_4": "ON" if auto_grab_enabled_4 else "OFF", "grab_action_4": "DISABLE" if auto_grab_enabled_4 else "ENABLE", "grab_button_class_4": "btn-blood" if auto_grab_enabled_4 else "btn-necro",
        "spam_action": "DISABLE" if spam_enabled else "ENABLE", "spam_button_class": "btn-blood" if spam_enabled else "btn-necro",
        "work_action": "DISABLE" if auto_work_enabled else "ENABLE", "work_button_class": "btn-blood" if auto_work_enabled else "btn-necro",
        "daily_action": "DISABLE" if auto_daily_enabled else "ENABLE", "daily_button_class": "btn-blood" if auto_daily_enabled else "btn-necro",
        "kvi_action": "DISABLE" if auto_kvi_enabled else "ENABLE", "kvi_button_class": "btn-blood" if auto_kvi_enabled else "btn-necro",
        "reboot_action": "DISABLE" if auto_reboot_enabled else "ENABLE", "reboot_button_class": "btn-blood" if auto_reboot_enabled else "btn-necro",
        "event_grab_action": "DISABLE" if event_grab_enabled else "ENABLE", "event_grab_button_class": "btn-blood" if event_grab_enabled else "btn-necro",
    }

    return jsonify({
        'work_enabled': auto_work_enabled, 'work_countdown': work_countdown,
        'daily_enabled': auto_daily_enabled, 'daily_countdown': daily_countdown,
        'kvi_enabled': auto_kvi_enabled, 'kvi_countdown': kvi_countdown,
        'reboot_enabled': auto_reboot_enabled, 'reboot_countdown': reboot_countdown,
        'spam_enabled': spam_enabled, 'spam_countdown': spam_countdown,
        'bot_statuses': bot_statuses,
        'server_start_time': server_start_time,
        'ui_states': ui_states,
        'farm_servers': farm_servers
    })


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    load_settings()
    load_visit_data()
    load_farm_settings()
    print("Đang khởi tạo các bot...", flush=True)
    with bots_lock:
        # Khởi tạo Bot Alpha
        if main_token: 
            main_bot = create_bot(main_token, bot_type='alpha', bot_name='Alpha')
            if 'main_1' not in bot_active_states:
                bot_active_states['main_1'] = True

        # Khởi tạo các Bot Main phụ
        for i, tk in enumerate(extra_main_tokens):
            if tk.strip():
                bot_name = GREEK_ALPHABET[i] if i < len(GREEK_ALPHABET) else f"Main {i+2}"
                bot_instance = create_bot(tk.strip(), bot_type='extra_main', bot_name=bot_name)
                extra_main_bots.append(bot_instance)
                # Key state vẫn dùng số để tương thích với UI: main_2, main_3, ...
                if f'main_{i+2}' not in bot_active_states:
                    bot_active_states[f'main_{i+2}'] = True

        # Khởi tạo các Bot phụ
        for i, token in enumerate(tokens):
            if token.strip():
                bots.append(create_bot(token.strip(), bot_type='sub'))
                if f'sub_{i}' not in bot_active_states:
                    bot_active_states[f'sub_{i}'] = True

    print("Đang khởi tạo các luồng nền...", flush=True)
    if spam_thread is None or not spam_thread.is_alive():
        spam_thread = threading.Thread(target=spam_loop, daemon=True)
        spam_thread.start()

    threading.Thread(target=periodic_save_loop, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    threading.Thread(target=auto_daily_loop, daemon=True).start()
    threading.Thread(target=auto_kvi_loop, daemon=True).start()

    if auto_reboot_enabled and (auto_reboot_thread is None or not auto_reboot_thread.is_alive()):
        auto_reboot_stop_event = threading.Event()
        auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
        auto_reboot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"Khởi động Web Server tại http://0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
