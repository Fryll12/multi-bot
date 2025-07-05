# karuta_deep_complete.py - Discord Multi-Bot Control System
import discum
import threading
import time
import os
import random
import re
import requests
import logging
from flask import Flask, request, render_template_string, jsonify
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)

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
acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", 
    "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent",
]

class BotController:
    def __init__(self):
        self.main_token = main_token
        self.main_token_2 = main_token_2
        self.tokens = tokens
        self.main_channel_id = main_channel_id
        self.other_channel_id = other_channel_id
        self.ktb_channel_id = ktb_channel_id
        self.spam_channel_id = spam_channel_id
        self.work_channel_id = work_channel_id
        self.karuta_id = karuta_id
        self.karibbit_id = karibbit_id
        self.acc_names = acc_names
        
        # Bot instances
        self.main_bot = None
        self.main_bot_2 = None
        self.bots = []
        
        # Auto grab settings
        self.auto_grab_enabled = False
        self.auto_grab_enabled_2 = False
        self.heart_threshold = 50
        self.heart_threshold_2 = 50
        self.last_drop_msg_id = ""
        
        # Spam settings
        self.spam_enabled = False
        self.spam_message = ""
        self.spam_delay = 10
        self.spam_thread_running = False
        
        # Auto work settings
        self.auto_work_enabled = False
        self.work_thread_running = False
        
        # Thread locks
        self.bots_lock = threading.Lock()
        
        # Connection monitoring
        self.reconnect_attempts = {"main_1": 0, "main_2": 0}
        self.last_reconnect_time = {"main_1": 0, "main_2": 0}
        
        logging.info("BotController initialized")

    def _run_work_for_account(self, token, acc_index):
        """Run work bot for a single account with proper sequence"""
        try:
            bot = discum.Client(token=token, log={"console": False, "file": False})

            headers = {
                "Authorization": token,
                "Content-Type": "application/json"
            }

            step = {"value": 0}

            def send_karuta_command():
                logging.info(f"[Work Acc {acc_index}] Gửi lệnh 'kc o:ef'...")
                bot.sendMessage(self.work_channel_id, "kc o:ef")

            def send_kn_command():
                logging.info(f"[Work Acc {acc_index}] Gửi lệnh 'kn'...")
                bot.sendMessage(self.work_channel_id, "kn")

            def send_kw_command():
                logging.info(f"[Work Acc {acc_index}] Gửi lệnh 'kw'...")
                bot.sendMessage(self.work_channel_id, "kw")
                step["value"] = 2

            def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
                try:
                    payload = {
                        "type": 3,
                        "guild_id": guild_id,
                        "channel_id": channel_id,
                        "message_id": message_id,
                        "application_id": application_id,
                        "session_id": "a",
                        "data": {
                            "component_type": 2,
                            "custom_id": custom_id
                        }
                    }
                    r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
                    if r.status_code == 204:
                        logging.info(f"[Work Acc {acc_index}] Click tick thành công!")
                    else:
                        logging.error(f"[Work Acc {acc_index}] Click thất bại! Mã lỗi: {r.status_code}, Nội dung: {r.text}")
                except Exception as e:
                    logging.error(f"[Work Acc {acc_index}] Lỗi click tick: {str(e)}")

            @bot.gateway.command
            def on_message(resp):
                if resp.event.message:
                    m = resp.parsed.auto()
                    if str(m.get('channel_id')) != self.work_channel_id:
                        return

                    author_id = str(m.get('author', {}).get('id', ''))
                    guild_id = m.get('guild_id')

                    if step["value"] == 0 and author_id == self.karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                        desc = m['embeds'][0].get('description', '')
                        card_codes = re.findall(r'\bv[a-zA-Z0-9]{6}\b', desc)
                        if card_codes and len(card_codes) >= 10:
                            first_5 = card_codes[:5]
                            last_5 = card_codes[-5:]

                            logging.info(f"[Work Acc {acc_index}] Mã đầu: {', '.join(first_5)}")
                            logging.info(f"[Work Acc {acc_index}] Mã cuối: {', '.join(last_5)}")

                            for i, code in enumerate(last_5):
                                suffix = chr(97 + i)
                                if i == 0:
                                    time.sleep(2)
                                else:
                                    time.sleep(1.5)
                                bot.sendMessage(self.work_channel_id, f"kjw {code} {suffix}")

                            for i, code in enumerate(first_5):
                                suffix = chr(97 + i)
                                time.sleep(1.5)
                                bot.sendMessage(self.work_channel_id, f"kjw {code} {suffix}")

                            time.sleep(1)
                            send_kn_command()
                            step["value"] = 1

                    elif step["value"] == 1 and author_id == self.karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                        desc = m['embeds'][0].get('description', '')
                        lines = desc.split('\n')
                        if len(lines) >= 2:
                            match = re.search(r'\d+\.\s*`([^`]+)`', lines[1])
                            if match:
                                resource = match.group(1)
                                logging.info(f"[Work Acc {acc_index}] Tài nguyên chọn: {resource}")
                                time.sleep(2)
                                bot.sendMessage(self.work_channel_id, f"kjn `{resource}` a b c d e")
                                time.sleep(1)
                                send_kw_command()

                    elif step["value"] == 2 and author_id == self.karuta_id and 'components' in m:
                        message_id = m['id']
                        application_id = m.get('application_id', self.karuta_id)
                        last_custom_id = None
                        for comp in m['components']:
                            if comp['type'] == 1:
                                for btn in comp['components']:
                                    if btn['type'] == 2:
                                        last_custom_id = btn['custom_id']
                                        logging.info(f"[Work Acc {acc_index}] Phát hiện button, custom_id: {last_custom_id}")

                        if last_custom_id:
                            click_tick(self.work_channel_id, message_id, last_custom_id, application_id, guild_id)
                            step["value"] = 3
                            bot.gateway.close()

            logging.info(f"[Work Acc {acc_index}] Bắt đầu hoạt động...")
            threading.Thread(target=bot.gateway.run, daemon=True).start()
            time.sleep(3)
            send_karuta_command()

            timeout = time.time() + 90
            while step["value"] != 3 and time.time() < timeout:
                time.sleep(1)

            try:
                bot.gateway.close()
            except:
                pass
            logging.info(f"[Work Acc {acc_index}] Đã hoàn thành, chuẩn bị tới acc tiếp theo.")
            return True
            
        except Exception as e:
            logging.error(f"[Work Acc {acc_index}] Lỗi trong quá trình work: {e}")
            return False

# [Phần còn lại của code giữ nguyên như gốc...]