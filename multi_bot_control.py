#!/usr/bin/env python3
"""
DEEP WEB BOT CONTROL - Complete System
Discord bot control với reconnect logic và giao diện deep web cyberpunk
Giữ nguyên 100% logic gốc, chỉ thay đổi giao diện
"""

import discum
import threading
import time
import os
import random
import re
import requests
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
import logging

# ============================================================================
# SETUP & CONFIG
# ============================================================================

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "deep_web_secret_key_666")

# Discord tokens và channels
main_token = os.getenv("MAIN_TOKEN", "")
main_token_2 = os.getenv("MAIN_TOKEN_2", "")
tokens = os.getenv("TOKENS", "").split(",") if os.getenv("TOKENS") else []

main_channel_id = "1386973916563767396"
other_channel_id = "1387406577040101417"
ktb_channel_id = "1376777071279214662"
spam_channel_id = "1388802151723302912"
work_channel_id = "1389250541590413363"
karuta_id = "646937666251915264"
karibbit_id = "1274445226064220273"

# Biến trạng thái hệ thống
bots = []
main_bot = None
main_bot_2 = None
auto_grab_enabled = False
auto_grab_enabled_2 = False
heart_threshold = 50
heart_threshold_2 = 50
last_drop_msg_id = ""

# 18 tên account
acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", 
    "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent",
]

# Spam & Work settings
spam_enabled = False
spam_message = ""
spam_delay = 10
auto_work_enabled = False
work_delay_between_acc = 10
work_delay_after_all = 44100

# Reconnect system
main_bot_reconnect_enabled = True
main_bot_2_reconnect_enabled = True
reconnect_delay = 5
max_reconnect_attempts = 10

bots_lock = threading.Lock()
system_logs = []

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def log_system(message):
    """Thêm log vào hệ thống"""
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    system_logs.append(log_entry)
    if len(system_logs) > 100:
        system_logs.pop(0)
    print(log_entry)

def check_bot_connection(bot, bot_name):
    """Kiểm tra kết nối của bot"""
    try:
        if bot and hasattr(bot, 'gateway') and bot.gateway:
            return True
        return False
    except Exception as e:
        log_system(f"[{bot_name}] Lỗi kiểm tra kết nối: {e}")
        return False

def reconnect_main_bot():
    """Reconnect cho main bot với retry logic"""
    global main_bot, main_bot_reconnect_enabled
    
    if not main_bot_reconnect_enabled:
        return
    
    attempts = 0
    while attempts < max_reconnect_attempts and main_bot_reconnect_enabled:
        try:
            log_system("[Main Bot 1] Đang thử reconnect...")
            
            if main_bot:
                try:
                    main_bot.gateway.close()
                except:
                    pass
            
            main_bot = create_bot(main_token, is_main=True)
            time.sleep(2)
            
            if check_bot_connection(main_bot, "Main Bot 1"):
                log_system("[Main Bot 1] Reconnect thành công!")
                return
            
            attempts += 1
            log_system(f"[Main Bot 1] Thử reconnect lần {attempts}/{max_reconnect_attempts}")
            time.sleep(reconnect_delay)
            
        except Exception as e:
            attempts += 1
            log_system(f"[Main Bot 1] Lỗi reconnect lần {attempts}: {e}")
            time.sleep(reconnect_delay)
    
    log_system("[Main Bot 1] Đã hết số lần thử reconnect!")

def reconnect_main_bot_2():
    """Reconnect cho main bot 2 với retry logic"""
    global main_bot_2, main_bot_2_reconnect_enabled
    
    if not main_bot_2_reconnect_enabled:
        return
    
    attempts = 0
    while attempts < max_reconnect_attempts and main_bot_2_reconnect_enabled:
        try:
            log_system("[Main Bot 2] Đang thử reconnect...")
            
            if main_bot_2:
                try:
                    main_bot_2.gateway.close()
                except:
                    pass
            
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
            time.sleep(2)
            
            if check_bot_connection(main_bot_2, "Main Bot 2"):
                log_system("[Main Bot 2] Reconnect thành công!")
                return
            
            attempts += 1
            log_system(f"[Main Bot 2] Thử reconnect lần {attempts}/{max_reconnect_attempts}")
            time.sleep(reconnect_delay)
            
        except Exception as e:
            attempts += 1
            log_system(f"[Main Bot 2] Lỗi reconnect lần {attempts}: {e}")
            time.sleep(reconnect_delay)
    
    log_system("[Main Bot 2] Đã hết số lần thử reconnect!")

def monitor_connections():
    """Thread để monitor kết nối của main bots"""
    while True:
        try:
            if auto_grab_enabled and main_bot_reconnect_enabled:
                if not check_bot_connection(main_bot, "Main Bot 1"):
                    log_system("[Main Bot 1] Phát hiện mất kết nối!")
                    threading.Thread(target=reconnect_main_bot, daemon=True).start()
            
            if auto_grab_enabled_2 and main_bot_2_reconnect_enabled:
                if not check_bot_connection(main_bot_2, "Main Bot 2"):
                    log_system("[Main Bot 2] Phát hiện mất kết nối!")
                    threading.Thread(target=reconnect_main_bot_2, daemon=True).start()
            
            time.sleep(30)
            
        except Exception as e:
            log_system(f"[Monitor] Lỗi monitor connections: {e}")
            time.sleep(60)

def reboot_bot(target_id):
    """Khởi động lại một bot dựa trên ID định danh"""
    global main_bot, main_bot_2, bots

    with bots_lock:
        log_system(f"[Reboot] Nhận được yêu cầu reboot cho target: {target_id}")
        
        if target_id == 'main_1':
            log_system("[Reboot] Đang xử lý Acc Chính 1...")
            try:
                if main_bot:
                    main_bot.gateway.close()
            except Exception as e:
                log_system(f"[Reboot] Lỗi khi đóng Acc Chính 1: {e}")
            main_bot = create_bot(main_token, is_main=True)
            log_system("[Reboot] Acc Chính 1 đã được khởi động lại.")

        elif target_id == 'main_2':
            log_system("[Reboot] Đang xử lý Acc Chính 2...")
            try:
                if main_bot_2:
                    main_bot_2.gateway.close()
            except Exception as e:
                log_system(f"[Reboot] Lỗi khi đóng Acc Chính 2: {e}")
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
            log_system("[Reboot] Acc Chính 2 đã được khởi động lại.")

        elif target_id.startswith('sub_'):
            try:
                index = int(target_id.split('_')[1])
                if 0 <= index < len(bots):
                    log_system(f"[Reboot] Đang xử lý Acc Phụ {index}...")
                    try:
                        if bots[index]:
                            bots[index].gateway.close()
                    except Exception as e:
                        log_system(f"[Reboot] Lỗi khi đóng Acc Phụ {index}: {e}")
                    
                    token_to_reboot = tokens[index]
                    bots[index] = create_bot(token_to_reboot.strip())
                    log_system(f"[Reboot] Acc Phụ {index} đã được khởi động lại.")
                else:
                    log_system(f"[Reboot] Index không hợp lệ: {index}")
            except (ValueError, IndexError) as e:
                log_system(f"[Reboot] Lỗi xử lý target Acc Phụ: {e}")
        else:
            log_system(f"[Reboot] Target không xác định: {target_id}")

def create_bot(token, is_main=False, is_main_2=False):
    """Tạo bot Discord với error handling"""
    try:
        bot = discum.Client(token=token, log=False)

        @bot.gateway.command
        def on_ready(resp):
            if resp.event.ready:
                try:
                    user_id = resp.raw["user"]["id"]
                    bot_type = "(Acc chính)" if is_main else "(Acc chính 2)" if is_main_2 else ""
                    log_system(f"Đã đăng nhập: {user_id} {bot_type}")
                except Exception as e:
                    log_system(f"Lỗi lấy user_id: {e}")

        # Auto grab logic cho main bot
        if is_main:
            @bot.gateway.command
            def on_message(resp):
                global auto_grab_enabled, heart_threshold, last_drop_msg_id

                if resp.event.message:
                    try:
                        msg = resp.parsed.auto()
                        author = msg.get("author", {}).get("id")
                        content = msg.get("content", "")
                        channel = msg.get("channel_id")
                        mentions = msg.get("mentions", [])

                        if author == karuta_id and channel == main_channel_id:
                            if "is dropping" not in content and not mentions and auto_grab_enabled:
                                log_system("\n[Bot 1] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                                last_drop_msg_id = msg["id"]

                                def read_karibbit():
                                    try:
                                        time.sleep(0.5)
                                        messages = bot.getMessages(main_channel_id, num=5).json()
                                        for msg in messages:
                                            author_id = msg.get("author", {}).get("id")
                                            if author_id == karibbit_id and "embeds" in msg and len(msg["embeds"]) > 0:
                                                desc = msg["embeds"][0].get("description", "")
                                                log_system(f"\n[Bot 1] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 1] ===== Kết thúc tin nhắn =====\n")

                                                lines = desc.split('\n')
                                                heart_numbers = []

                                                for i, line in enumerate(lines[:3]):
                                                    matches = re.findall(r'`([^`]*)`', line)
                                                    if len(matches) >= 2 and matches[1].isdigit():
                                                        num = int(matches[1])
                                                        heart_numbers.append(num)
                                                        log_system(f"[Bot 1] Dòng {i+1} số tim: {num}")
                                                    else:
                                                        heart_numbers.append(0)
                                                        log_system(f"[Bot 1] Dòng {i+1} không tìm thấy số tim, mặc định 0")

                                                if sum(heart_numbers) == 0:
                                                    log_system("[Bot 1] Không có số tim nào, bỏ qua.\n")
                                                else:
                                                    max_num = max(heart_numbers)
                                                    if max_num < heart_threshold:
                                                        log_system(f"[Bot 1] Số tim lớn nhất {max_num} < {heart_threshold}, không grab!\n")
                                                    else:
                                                        max_index = heart_numbers.index(max_num)
                                                        emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                                        delay = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}[emoji]
                                                        log_system(f"[Bot 1] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")

                                                        def grab():
                                                            try:
                                                                bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                                log_system("[Bot 1] Đã thả emoji grab!")
                                                                bot.sendMessage(ktb_channel_id, "kt b")
                                                                log_system("[Bot 1] Đã nhắn 'kt b'!")
                                                            except Exception as e:
                                                                log_system(f"[Bot 1] Lỗi khi grab hoặc nhắn kt b: {e}")

                                                        threading.Timer(delay, grab).start()
                                                break
                                    except Exception as e:
                                        log_system(f"[Bot 1] Lỗi trong read_karibbit: {e}")

                                threading.Thread(target=read_karibbit, daemon=True).start()
                    except Exception as e:
                        log_system(f"[Bot 1] Lỗi trong on_message: {e}")

        # Auto grab logic cho main bot 2
        if is_main_2:
            @bot.gateway.command
            def on_message(resp):
                global auto_grab_enabled_2, heart_threshold_2, last_drop_msg_id

                if resp.event.message:
                    try:
                        msg = resp.parsed.auto()
                        author = msg.get("author", {}).get("id")
                        content = msg.get("content", "")
                        channel = msg.get("channel_id")
                        mentions = msg.get("mentions", [])

                        if author == karuta_id and channel == main_channel_id:
                            if "is dropping" not in content and not mentions and auto_grab_enabled_2:
                                log_system("\n[Bot 2] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                                last_drop_msg_id = msg["id"]

                                def read_karibbit_2():
                                    try:
                                        time.sleep(0.5)
                                        messages = bot.getMessages(main_channel_id, num=5).json()
                                        for msg in messages:
                                            author_id = msg.get("author", {}).get("id")
                                            if author_id == karibbit_id and "embeds" in msg and len(msg["embeds"]) > 0:
                                                desc = msg["embeds"][0].get("description", "")
                                                log_system(f"\n[Bot 2] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 2] ===== Kết thúc tin nhắn =====\n")

                                                lines = desc.split('\n')
                                                heart_numbers = []

                                                for i, line in enumerate(lines[:3]):
                                                    matches = re.findall(r'`([^`]*)`', line)
                                                    if len(matches) >= 2 and matches[1].isdigit():
                                                        num = int(matches[1])
                                                        heart_numbers.append(num)
                                                        log_system(f"[Bot 2] Dòng {i+1} số tim: {num}")
                                                    else:
                                                        heart_numbers.append(0)
                                                        log_system(f"[Bot 2] Dòng {i+1} không tìm thấy số tim, mặc định 0")

                                                if sum(heart_numbers) == 0:
                                                    log_system("[Bot 2] Không có số tim nào, bỏ qua.\n")
                                                else:
                                                    max_num = max(heart_numbers)
                                                    if max_num < heart_threshold_2:
                                                        log_system(f"[Bot 2] Số tim lớn nhất {max_num} < {heart_threshold_2}, không grab!\n")
                                                    else:
                                                        max_index = heart_numbers.index(max_num)
                                                        emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                                        delay = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}[emoji]
                                                        log_system(f"[Bot 2] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")

                                                        def grab_2():
                                                            try:
                                                                bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                                log_system("[Bot 2] Đã thả emoji grab!")
                                                                bot.sendMessage(ktb_channel_id, "kt b")
                                                                log_system("[Bot 2] Đã nhắn 'kt b'!")
                                                            except Exception as e:
                                                                log_system(f"[Bot 2] Lỗi khi grab hoặc nhắn kt b: {e}")

                                                        threading.Timer(delay, grab_2).start()
                                                break
                                    except Exception as e:
                                        log_system(f"[Bot 2] Lỗi trong read_karibbit_2: {e}")

                                threading.Thread(target=read_karibbit_2, daemon=True).start()
                    except Exception as e:
                        log_system(f"[Bot 2] Lỗi trong on_message: {e}")

        @bot.gateway.command
        def on_error(resp):
            log_system(f"Bot error: {resp}")

        return bot

    except Exception as e:
        log_system(f"Lỗi tạo bot: {e}")
        return None

def auto_work_loop():
    """Vòng lặp auto work"""
    while True:
        try:
            if auto_work_enabled:
                with bots_lock:
                    for i, bot in enumerate(bots):
                        if bot:
                            try:
                                bot.sendMessage(work_channel_id, "kc o:ef")
                                log_system(f"[Auto Work] Bot {i} đã gửi lệnh work")
                                time.sleep(work_delay_between_acc)
                            except Exception as e:
                                log_system(f"[Auto Work] Lỗi bot {i}: {e}")
                
                log_system(f"[Auto Work] Hoàn thành chu kỳ, đợi {work_delay_after_all}s")
                time.sleep(work_delay_after_all)
            else:
                time.sleep(60)
        except Exception as e:
            log_system(f"[Auto Work] Lỗi trong loop: {e}")
            time.sleep(60)

def spam_loop():
    """Vòng lặp spam"""
    while True:
        try:
            if spam_enabled and spam_message:
                with bots_lock:
                    for i, bot in enumerate(bots):
                        if bot:
                            try:
                                bot.sendMessage(spam_channel_id, spam_message)
                                log_system(f"[Spam] Bot {i} đã gửi: {spam_message}")
                                time.sleep(1)
                            except Exception as e:
                                log_system(f"[Spam] Lỗi bot {i}: {e}")
                
                log_system(f"[Spam] Hoàn thành chu kỳ, đợi {spam_delay}s")
                time.sleep(spam_delay)
            else:
                time.sleep(60)
        except Exception as e:
            log_system(f"[Spam] Lỗi trong loop: {e}")
            time.sleep(60)

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Trang chủ với giao diện deep web"""
    return """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>◈ DEEP WEB BOT CONTROL ◈</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Orbitron', monospace; 
            background: #0a0a0a; 
            color: #00ff00; 
            overflow-x: hidden; 
            min-height: 100vh;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 20px; 
            position: relative; 
            z-index: 10; 
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            border: 2px solid #00ff00; 
            padding: 20px; 
            background: rgba(0,255,0,0.1); 
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow { 
            from { box-shadow: 0 0 20px #00ff00; } 
            to { box-shadow: 0 0 30px #00ff00, 0 0 40px #00ff00; } 
        }
        .logo { 
            font-size: 2.5em; 
            font-weight: 900; 
            text-shadow: 0 0 20px #00ff00; 
        }
        .panel { 
            background: rgba(0,20,0,0.8); 
            border: 1px solid #00ff00; 
            margin: 20px 0; 
            border-radius: 10px; 
            box-shadow: 0 0 15px rgba(0,255,0,0.3); 
        }
        .panel-header { 
            background: rgba(0,255,0,0.2); 
            padding: 15px; 
            border-bottom: 1px solid #00ff00; 
            font-weight: bold; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
        }
        .panel-content { 
            padding: 20px; 
        }
        .control-group { 
            margin: 15px 0; 
            display: flex; 
            align-items: center; 
            gap: 15px; 
            flex-wrap: wrap; 
        }
        .control-group label { 
            min-width: 200px; 
            font-weight: bold; 
        }
        .cyber-input, .cyber-select { 
            background: rgba(0,0,0,0.7); 
            border: 1px solid #00ff00; 
            color: #00ff00; 
            padding: 10px; 
            border-radius: 5px; 
            font-family: 'Courier Prime', monospace; 
        }
        .cyber-input:focus, .cyber-select:focus { 
            outline: none; 
            box-shadow: 0 0 10px #00ff00; 
        }
        .cyber-btn { 
            background: rgba(0,255,0,0.2); 
            border: 1px solid #00ff00; 
            color: #00ff00; 
            padding: 10px 20px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-family: 'Orbitron', monospace; 
            font-weight: bold; 
            transition: all 0.3s; 
        }
        .cyber-btn:hover { 
            background: rgba(0,255,0,0.4); 
            box-shadow: 0 0 15px #00ff00; 
        }
        .cyber-btn.danger { 
            border-color: #ff0000; 
            color: #ff0000; 
            background: rgba(255,0,0,0.2); 
        }
        .cyber-btn.danger:hover { 
            background: rgba(255,0,0,0.4); 
            box-shadow: 0 0 15px #ff0000; 
        }
        .cyber-btn.warning { 
            border-color: #ffff00; 
            color: #ffff00; 
            background: rgba(255,255,0,0.2); 
        }
        .cyber-btn.warning:hover { 
            background: rgba(255,255,0,0.4); 
            box-shadow: 0 0 15px #ffff00; 
        }
        .cyber-switch { 
            position: relative; 
            width: 60px; 
            height: 30px; 
        }
        .cyber-switch input { 
            opacity: 0; 
            width: 0; 
            height: 0; 
        }
        .slider { 
            position: absolute; 
            cursor: pointer; 
            top: 0; 
            left: 0; 
            right: 0; 
            bottom: 0; 
            background-color: rgba(255,0,0,0.3); 
            transition: .4s; 
            border-radius: 30px; 
            border: 1px solid #ff0000; 
        }
        .slider:before { 
            position: absolute; 
            content: ""; 
            height: 22px; 
            width: 22px; 
            left: 3px; 
            bottom: 3px; 
            background-color: #ff0000; 
            transition: .4s; 
            border-radius: 50%; 
        }
        input:checked + .slider { 
            background-color: rgba(0,255,0,0.3); 
            border-color: #00ff00; 
        }
        input:checked + .slider:before { 
            transform: translateX(26px); 
            background-color: #00ff00; 
        }
        .accounts-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 15px; 
            margin: 20px 0; 
        }
        .account-card { 
            background: rgba(0,0,0,0.5); 
            border: 1px solid #00ff00; 
            padding: 15px; 
            border-radius: 5px; 
            text-align: center; 
        }
        .account-card.offline { 
            border-color: #ff0000; 
            color: #ff0000; 
        }
        .terminal { 
            background: #000; 
            border: 1px solid #00ff00; 
            border-radius: 5px; 
            height: 300px; 
            overflow-y: auto; 
            padding: 10px; 
            font-family: 'Courier Prime', monospace; 
            font-size: 14px; 
        }
        .log-line { 
            margin: 2px 0; 
            opacity: 0.8; 
        }
        .log-line.error { 
            color: #ff0000; 
        }
        .log-line.warning { 
            color: #ffff00; 
        }
        .log-line.success { 
            color: #00ff00; 
        }
        .matrix-bg { 
            position: fixed; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%; 
            pointer-events: none; 
            opacity: 0.1; 
            z-index: 1; 
        }
        .code-list-group { 
            display: flex; 
            gap: 10px; 
            align-items: center; 
            flex-wrap: wrap; 
        }
        .reboot-group { 
            display: flex; 
            gap: 10px; 
            align-items: center; 
            flex-wrap: wrap; 
        }
        .heart-slider { 
            width: 200px; 
        }
        .status-online { 
            color: #00ff00; 
        }
        .status-offline { 
            color: #ff0000; 
        }
        .cursor { 
            animation: blink 1s infinite; 
        }
        @keyframes blink { 
            0%, 50% { opacity: 1; } 
            51%, 100% { opacity: 0; } 
        }
    </style>
</head>
<body>
    <div class="matrix-bg" id="matrix-bg"></div>
    
    <div class="container">
        <div class="header">
            <div class="logo">
                <i class="fas fa-skull"></i>
                DEEP WEB BOT CONTROL
                <i class="fas fa-skull"></i>
            </div>
            <div style="margin-top: 10px; font-size: 1.2em;">
                <span id="connection-status">SYSTEM OPERATIONAL</span>
            </div>
        </div>

        <!-- Main Accounts -->
        <div class="panel">
            <div class="panel-header">
                <span>◈ MAIN ACCOUNTS ◈</span>
            </div>
            <div class="panel-content">
                <div class="accounts-grid" id="main-accounts"></div>
            </div>
        </div>

        <!-- Sub Accounts -->
        <div class="panel">
            <div class="panel-header">
                <span>◈ SUB ACCOUNTS ◈</span>
            </div>
            <div class="panel-content">
                <div class="accounts-grid" id="sub-accounts"></div>
                <div class="control-group">
                    <label><i class="fas fa-power-off"></i> Reboot Account:</label>
                    <div class="reboot-group">
                        <select id="reboot_target" class="cyber-select">
                            <option value="main_1">ACC CHÍNH 1</option>
                            <option value="main_2">ACC CHÍNH 2</option>
                        </select>
                        <button class="cyber-btn danger" onclick="rebootSelected()">
                            <i class="fas fa-power-off"></i> REBOOT
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Controls -->
        <div class="panel">
            <div class="panel-header">
                <span>◈ SYSTEM CONTROLS ◈</span>
            </div>
            <div class="panel-content">
                <div class="control-group">
                    <label><i class="fas fa-broadcast-tower"></i> Auto Work:</label>
                    <div class="cyber-switch">
                        <input type="checkbox" id="auto-work" onchange="toggleAutoWork()">
                        <span class="slider"></span>
                    </div>
                </div>
                <div class="control-group">
                    <label><i class="fas fa-comment"></i> Spam:</label>
                    <div class="cyber-switch">
                        <input type="checkbox" id="spam-enabled" onchange="toggleSpam()">
                        <span class="slider"></span>
                    </div>
                    <input type="text" id="spam-message" class="cyber-input" placeholder="Spam message">
                    <button class="cyber-btn warning" onclick="setSpamMessage()">SET</button>
                </div>
                <div class="control-group">
                    <label><i class="fas fa-list"></i> Send Code List:</label>
                    <div class="code-list-group">
                        <select id="acc_index" class="cyber-select"></select>
                        <input type="number" id="delay" class="cyber-input" placeholder="Delay (s)" value="2" min="0.5" max="10" step="0.5">
                        <input type="text" id="prefix" class="cyber-input" placeholder="Prefix">
                        <input type="text" id="codes" class="cyber-input" placeholder="Codes (comma separated)" style="width: 300px;">
                        <button class="cyber-btn warning" onclick="sendCodeList()">
                            <i class="fas fa-code"></i> SEND
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Terminal -->
        <div class="panel">
            <div class="panel-header">
                <span>◈ SYSTEM TERMINAL ◈</span>
                <button class="cyber-btn danger" onclick="clearLogs()">CLEAR</button>
            </div>
            <div class="panel-content">
                <div class="terminal" id="terminal">
                    <div class="log-line">[SYSTEM] Deep Web Bot Control initialized...</div>
                    <div class="log-line"><span class="cursor">█</span></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let controller = {
            logs: [],
            
            async makeRequest(endpoint, data = {}) {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                return await response.json();
            },
            
            async updateStatus() {
                try {
                    const response = await fetch('/status');
                    const data = await response.json();
                    
                    this.updateMainAccounts(data.main_accounts);
                    this.updateSubAccounts(data.sub_accounts);
                    this.updateLogs(data.logs);
                } catch (error) {
                    console.error('Error updating status:', error);
                }
            },
            
            updateMainAccounts(accounts) {
                const container = document.getElementById('main-accounts');
                container.innerHTML = '';
                
                accounts.forEach(account => {
                    const card = document.createElement('div');
                    card.className = `account-card ${account.status.toLowerCase()}`;
                    card.innerHTML = `
                        <h3>${account.name}</h3>
                        <p class="status-${account.status.toLowerCase()}">${account.status}</p>
                        <div style="margin: 10px 0;">
                            <label>Auto Grab:</label>
                            <div class="cyber-switch">
                                <input type="checkbox" ${account.auto_grab ? 'checked' : ''} 
                                       onchange="toggleAutoGrab('${account.id}')">
                                <span class="slider"></span>
                            </div>
                        </div>
                        <div>
                            <label>Heart Threshold:</label>
                            <input type="range" class="heart-slider" min="1" max="100" 
                                   value="${account.heart_threshold}"
                                   onchange="setHeartThreshold('${account.id}', this.value)">
                            <span>${account.heart_threshold}</span>
                        </div>
                    `;
                    container.appendChild(card);
                });
            },
            
            updateSubAccounts(accounts) {
                const container = document.getElementById('sub-accounts');
                const select = document.getElementById('reboot_target');
                const accSelect = document.getElementById('acc_index');
                
                container.innerHTML = '';
                
                // Update dropdowns
                const currentOptions = Array.from(select.options).filter(opt => opt.value.startsWith('main_'));
                select.innerHTML = '';
                currentOptions.forEach(opt => select.appendChild(opt));
                
                accSelect.innerHTML = '';
                
                accounts.forEach((account, index) => {
                    // Account grid
                    const card = document.createElement('div');
                    card.className = `account-card ${account.status.toLowerCase()}`;
                    card.innerHTML = `
                        <h4>${account.name}</h4>
                        <p class="status-${account.status.toLowerCase()}">${account.status}</p>
                    `;
                    container.appendChild(card);
                    
                    // Reboot dropdown
                    const rebootOption = document.createElement('option');
                    rebootOption.value = account.id;
                    rebootOption.textContent = account.name;
                    select.appendChild(rebootOption);
                    
                    // Code list dropdown
                    const codeOption = document.createElement('option');
                    codeOption.value = index;
                    codeOption.textContent = account.name;
                    accSelect.appendChild(codeOption);
                });
            },
            
            updateLogs(logs) {
                const terminal = document.getElementById('terminal');
                const cursor = terminal.querySelector('.cursor');
                if (cursor) cursor.parentElement.remove();
                
                logs.slice(-20).forEach(log => {
                    const line = document.createElement('div');
                    line.className = 'log-line';
                    if (log.includes('ERROR') || log.includes('Lỗi')) line.className += ' error';
                    else if (log.includes('WARNING') || log.includes('Cảnh báo')) line.className += ' warning';
                    else if (log.includes('SUCCESS') || log.includes('thành công')) line.className += ' success';
                    
                    line.textContent = log;
                    terminal.appendChild(line);
                });
                
                const newCursor = document.createElement('div');
                newCursor.className = 'log-line';
                newCursor.innerHTML = '<span class="cursor">█</span>';
                terminal.appendChild(newCursor);
                
                terminal.scrollTop = terminal.scrollHeight;
            },
            
            start() {
                this.updateStatus();
                setInterval(() => this.updateStatus(), 2000);
            }
        };
        
        // Control functions
        async function toggleAutoGrab(botId) {
            await controller.makeRequest('/control', { action: 'toggle_auto_grab', bot_id: botId });
        }
        
        async function setHeartThreshold(botId, threshold) {
            await controller.makeRequest('/control', { action: 'set_heart_threshold', bot_id: botId, threshold: threshold });
        }
        
        async function rebootSelected() {
            const target = document.getElementById('reboot_target').value;
            await controller.makeRequest('/control', { action: 'reboot_bot', target_id: target });
        }
        
        async function toggleAutoWork() {
            await controller.makeRequest('/control', { action: 'toggle_auto_work' });
        }
        
        async function toggleSpam() {
            await controller.makeRequest('/control', { action: 'toggle_spam' });
        }
        
        async function setSpamMessage() {
            const message = document.getElementById('spam-message').value;
            await controller.makeRequest('/control', { action: 'set_spam_message', message: message });
        }
        
        async function sendCodeList() {
            const accIndex = document.getElementById('acc_index').value;
            const delay = document.getElementById('delay').value;
            const prefix = document.getElementById('prefix').value;
            const codes = document.getElementById('codes').value;
            
            if (!codes.trim()) return;
            
            await controller.makeRequest('/control', {
                action: 'send_code_list',
                acc_index: accIndex,
                delay: delay,
                prefix: prefix,
                codes: codes
            });
            
            document.getElementById('codes').value = '';
        }
        
        function clearLogs() {
            const terminal = document.getElementById('terminal');
            terminal.innerHTML = '<div class="log-line"><span class="cursor">█</span></div>';
        }
        
        // Start the controller
        controller.start();
    </script>
</body>
</html>
    """

@app.route('/status')
def status():
    """API endpoint để lấy trạng thái hệ thống"""
    main_accounts = [
        {
            "id": "main_1",
            "name": "ACC CHÍNH 1",
            "status": "ONLINE" if main_bot else "OFFLINE",
            "auto_grab": auto_grab_enabled,
            "heart_threshold": heart_threshold,
            "reconnect_enabled": main_bot_reconnect_enabled
        },
        {
            "id": "main_2",
            "name": "ACC CHÍNH 2",
            "status": "ONLINE" if main_bot_2 else "OFFLINE",
            "auto_grab": auto_grab_enabled_2,
            "heart_threshold": heart_threshold_2,
            "reconnect_enabled": main_bot_2_reconnect_enabled
        }
    ]
    
    sub_accounts = []
    for i in range(len(acc_names)):
        sub_accounts.append({
            "id": f"sub_{i}",
            "name": acc_names[i],
            "status": "ONLINE" if i < len(bots) and bots[i] else "OFFLINE"
        })
    
    return jsonify({
        "main_accounts": main_accounts,
        "sub_accounts": sub_accounts,
        "spam": {"enabled": spam_enabled, "message": spam_message, "delay": spam_delay},
        "auto_work": {"enabled": auto_work_enabled, "delay_between": work_delay_between_acc, "delay_after": work_delay_after_all},
        "logs": system_logs[-50:],
        "connected": True
    })

@app.route('/control', methods=['POST'])
def control():
    """API endpoint để điều khiển hệ thống"""
    try:
        data = request.get_json()
        action = data.get('action')
        
        global auto_grab_enabled, auto_grab_enabled_2, heart_threshold, heart_threshold_2
        global main_bot_reconnect_enabled, main_bot_2_reconnect_enabled
        global spam_enabled, spam_message, spam_delay
        global auto_work_enabled, work_delay_between_acc, work_delay_after_all
        
        if action == 'toggle_auto_grab':
            bot_id = data.get('bot_id')
            if bot_id == 'main_1':
                auto_grab_enabled = not auto_grab_enabled
                log_system(f"[Control] Auto grab Main Bot 1: {'ON' if auto_grab_enabled else 'OFF'}")
            elif bot_id == 'main_2':
                auto_grab_enabled_2 = not auto_grab_enabled_2
                log_system(f"[Control] Auto grab Main Bot 2: {'ON' if auto_grab_enabled_2 else 'OFF'}")
        
        elif action == 'set_heart_threshold':
            bot_id = data.get('bot_id')
            threshold = int(data.get('threshold', 50))
            if bot_id == 'main_1':
                heart_threshold = threshold
                log_system(f"[Control] Heart threshold Main Bot 1: {threshold}")
            elif bot_id == 'main_2':
                heart_threshold_2 = threshold
                log_system(f"[Control] Heart threshold Main Bot 2: {threshold}")
        
        elif action == 'reboot_bot':
            target_id = data.get('target_id')
            threading.Thread(target=reboot_bot, args=(target_id,), daemon=True).start()
            log_system(f"[Control] Reboot request for {target_id}")
        
        elif action == 'toggle_spam':
            spam_enabled = not spam_enabled
            log_system(f"[Control] Spam: {'ON' if spam_enabled else 'OFF'}")
        
        elif action == 'set_spam_message':
            spam_message = data.get('message', '')
            log_system(f"[Control] Spam message: {spam_message}")
        
        elif action == 'toggle_auto_work':
            auto_work_enabled = not auto_work_enabled
            log_system(f"[Control] Auto work: {'ON' if auto_work_enabled else 'OFF'}")
        
        elif action == 'send_code_list':
            acc_index = data.get('acc_index')
            delay = data.get('delay', 2.0)
            prefix = data.get('prefix', '')
            codes = data.get('codes', '')
            
            if acc_index is not None and codes:
                try:
                    acc_idx = int(acc_index)
                    delay_val = float(delay)
                    codes_list = codes.split(",")
                    
                    if acc_idx < len(bots) and bots[acc_idx]:
                        with bots_lock:
                            for i, code in enumerate(codes_list):
                                code = code.strip()
                                if code:
                                    final_msg = f"{prefix} {code}" if prefix else code
                                    threading.Timer(delay_val * i, bots[acc_idx].sendMessage, args=(other_channel_id, final_msg)).start()
                        log_system(f"[Control] Sent code list to account {acc_idx}")
                    else:
                        log_system(f"[Control] Account index {acc_idx} not available")
                except Exception as e:
                    log_system(f"[Control] Error sending codes: {e}")
        
        return jsonify({"success": True})
        
    except Exception as e:
        log_system(f"[Control] Error: {e}")
        return jsonify({"success": False, "error": str(e)})

def initialize_system():
    """Khởi tạo hệ thống"""
    global main_bot, main_bot_2, bots
    
    log_system("=== KHỞI TẠO DEEP WEB BOT CONTROL ===")
    
    # Tạo main bots
    if main_token:
        main_bot = create_bot(main_token, is_main=True)
        log_system("Main Bot 1 đã được tạo")
    
    if main_token_2:
        main_bot_2 = create_bot(main_token_2, is_main_2=True)
        log_system("Main Bot 2 đã được tạo")
    
    # Tạo sub bots
    for i, token in enumerate(tokens):
        if token.strip():
            bot = create_bot(token.strip())
            if bot:
                bots.append(bot)
                log_system(f"Sub Bot {i} đã được tạo")
            else:
                bots.append(None)
        else:
            bots.append(None)
    
    log_system(f"Đã khởi tạo {len([b for b in bots if b])} sub bots")
    
    # Khởi động các threads
    threading.Thread(target=auto_work_loop, daemon=True).start()
    threading.Thread(target=spam_loop, daemon=True).start()
    threading.Thread(target=monitor_connections, daemon=True).start()
    
    log_system("=== HỆ THỐNG READY ===")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    initialize_system()
    app.run(host='0.0.0.0', port=5000, debug=True)