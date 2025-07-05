# FULL CODE - Discord Multi-Bot Control System với Web Interface
# Giao diện matrix dark đẹp + logic auto-work chuẩn

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

    def reboot_bot(self, target_id):
        """Reboot a bot based on its target ID"""
        with self.bots_lock:
            logging.info(f"[Reboot] Received reboot request for target: {target_id}")
            
            if target_id == 'main_1':
                if not self.main_token:
                    logging.error("[Reboot] No main token available for Main Bot 1")
                    return False
                    
                logging.info("[Reboot] Processing Main Bot 1...")
                try:
                    if self.main_bot:
                        self.main_bot.gateway.close()
                except Exception as e:
                    logging.error(f"[Reboot] Error closing Main Bot 1: {e}")
                self.main_bot = self.create_bot(self.main_token, is_main=True)
                logging.info("[Reboot] Main Bot 1 rebooted successfully")
                return True

            elif target_id == 'main_2':
                if not self.main_token_2:
                    logging.error("[Reboot] No main token 2 available for Main Bot 2")
                    return False
                    
                logging.info("[Reboot] Processing Main Bot 2...")
                try:
                    if self.main_bot_2:
                        self.main_bot_2.gateway.close()
                except Exception as e:
                    logging.error(f"[Reboot] Error closing Main Bot 2: {e}")
                self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True)
                logging.info("[Reboot] Main Bot 2 rebooted successfully")
                return True

            elif target_id.startswith('sub_'):
                try:
                    index = int(target_id.split('_')[1])
                    if 0 <= index < len(self.bots):
                        logging.info(f"[Reboot] Processing Sub Bot {index}...")
                        try:
                            if self.bots[index]:
                                self.bots[index].gateway.close()
                        except Exception as e:
                            logging.error(f"[Reboot] Error closing Sub Bot {index}: {e}")
                        
                        if index < len(self.tokens):
                            token_to_reboot = self.tokens[index]
                            self.bots[index] = self.create_bot(token_to_reboot.strip(), is_main=False)
                            logging.info(f"[Reboot] Sub Bot {index} rebooted successfully")
                            return True
                    else:
                        logging.error(f"[Reboot] Invalid index: {index}")
                        return False
                except (ValueError, IndexError) as e:
                    logging.error(f"[Reboot] Error processing sub bot target: {e}")
                    return False
            else:
                logging.error(f"[Reboot] Unknown target: {target_id}")
                return False

    def check_and_reconnect_main_bots(self):
        """Check connection status and auto-reconnect main bots if needed"""
        current_time = time.time()
        
        # Check Main Bot 1
        if self.main_token and (not self.main_bot or not hasattr(self.main_bot.gateway, 'ws') or not self.main_bot.gateway.ws):
            if current_time - self.last_reconnect_time["main_1"] > 60:  # Wait 1 minute between attempts
                self.reconnect_attempts["main_1"] += 1
                if self.reconnect_attempts["main_1"] <= 5:  # Max 5 attempts
                    logging.info(f"[Auto-Reconnect] Attempting to reconnect Main Bot 1 (attempt {self.reconnect_attempts['main_1']})")
                    try:
                        self.main_bot = self.create_bot(self.main_token, is_main=True)
                        self.last_reconnect_time["main_1"] = current_time
                        logging.info("[Auto-Reconnect] Main Bot 1 reconnected successfully")
                    except Exception as e:
                        logging.error(f"[Auto-Reconnect] Failed to reconnect Main Bot 1: {e}")
                        
        # Check Main Bot 2
        if self.main_token_2 and (not self.main_bot_2 or not hasattr(self.main_bot_2.gateway, 'ws') or not self.main_bot_2.gateway.ws):
            if current_time - self.last_reconnect_time["main_2"] > 60:  # Wait 1 minute between attempts
                self.reconnect_attempts["main_2"] += 1
                if self.reconnect_attempts["main_2"] <= 5:  # Max 5 attempts
                    logging.info(f"[Auto-Reconnect] Attempting to reconnect Main Bot 2 (attempt {self.reconnect_attempts['main_2']})")
                    try:
                        self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True)
                        self.last_reconnect_time["main_2"] = current_time
                        logging.info("[Auto-Reconnect] Main Bot 2 reconnected successfully")
                    except Exception as e:
                        logging.error(f"[Auto-Reconnect] Failed to reconnect Main Bot 2: {e}")

    def create_bot(self, token, is_main=False, is_main_2=False):
        """Create a new bot instance"""
        try:
            bot = discum.Client(token=token, log=False)

            @bot.gateway.command
            def on_ready(resp):
                if resp.event.ready:
                    try:
                        user_id = resp.raw["user"]["id"]
                        bot_type = "(Main Bot 1)" if is_main else "(Main Bot 2)" if is_main_2 else ""
                        logging.info(f"Bot logged in: {user_id} {bot_type}")
                    except Exception as e:
                        logging.error(f"Error getting user_id: {e}")

            if is_main:
                @bot.gateway.command
                def on_message(resp):
                    if resp.event.message:
                        msg = resp.parsed.auto()
                        author = msg.get("author", {}).get("id")
                        content = msg.get("content", "")
                        channel = msg.get("channel_id")
                        mentions = msg.get("mentions", [])

                        if author == self.karuta_id and channel == self.main_channel_id:
                            if "is dropping" not in content and not mentions and self.auto_grab_enabled:
                                logging.info("\n[Bot 1] Auto drop detected! Reading Karibbit message...\n")
                                self.last_drop_msg_id = msg["id"]
                                threading.Thread(target=self._read_karibbit_and_grab, args=(bot, 1)).start()

            if is_main_2:
                @bot.gateway.command
                def on_message(resp):
                    if resp.event.message:
                        msg = resp.parsed.auto()
                        author = msg.get("author", {}).get("id")
                        content = msg.get("content", "")
                        channel = msg.get("channel_id")
                        mentions = msg.get("mentions", [])

                        if author == self.karuta_id and channel == self.main_channel_id:
                            if "is dropping" not in content and not mentions and self.auto_grab_enabled_2:
                                logging.info("\n[Bot 2] Auto drop detected! Reading Karibbit message...\n")
                                self.last_drop_msg_id = msg["id"]
                                threading.Thread(target=self._read_karibbit_and_grab, args=(bot, 2)).start()

            threading.Thread(target=bot.gateway.run, daemon=True).start()
            return bot
        except Exception as e:
            logging.error(f"Error creating bot: {e}")
            return None

    def _read_karibbit_and_grab(self, bot, bot_num):
        """Read Karibbit message and perform grab logic"""
        time.sleep(0.5)
        try:
            messages = bot.getMessages(self.main_channel_id, num=5).json()
            for msg in messages:
                author_id = msg.get("author", {}).get("id")
                if author_id == self.karibbit_id and "embeds" in msg and len(msg["embeds"]) > 0:
                    desc = msg["embeds"][0].get("description", "")
                    logging.info(f"\n[Bot {bot_num}] ===== Karibbit Message =====\n{desc}\n[Bot {bot_num}] ===== End Message =====\n")

                    lines = desc.split('\n')
                    heart_numbers = []

                    for i, line in enumerate(lines[:3]):
                        matches = re.findall(r'`([^`]*)`', line)
                        if len(matches) >= 2 and matches[1].isdigit():
                            num = int(matches[1])
                            heart_numbers.append(num)
                            logging.info(f"[Bot {bot_num}] Line {i+1} hearts: {num}")
                        else:
                            heart_numbers.append(0)
                            logging.info(f"[Bot {bot_num}] Line {i+1} no hearts found, default 0")

                    if sum(heart_numbers) == 0:
                        logging.info(f"[Bot {bot_num}] No hearts found, skipping.\n")
                    else:
                        max_num = max(heart_numbers)
                        threshold = self.heart_threshold if bot_num == 1 else self.heart_threshold_2
                        if max_num < threshold:
                            logging.info(f"[Bot {bot_num}] Max hearts {max_num} < {threshold}, not grabbing!\n")
                        else:
                            max_index = heart_numbers.index(max_num)
                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                            # Add delay for Bot 2
                            base_delays = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}
                            delay = base_delays[emoji] + (0.3 if bot_num == 2 else 0)
                            logging.info(f"[Bot {bot_num}] Choosing line {max_index+1} with {max_num} hearts → Emoji {emoji} after {delay}s\n")

                            def grab():
                                try:
                                    bot.addReaction(self.main_channel_id, self.last_drop_msg_id, emoji)
                                    logging.info(f"[Bot {bot_num}] Grab emoji sent!")
                                    bot.sendMessage(self.ktb_channel_id, "kt b")
                                    logging.info(f"[Bot {bot_num}] 'kt b' message sent!")
                                except Exception as e:
                                    logging.error(f"[Bot {bot_num}] Error during grab or kt b: {e}")

                            threading.Timer(delay, grab).start()
                    break
        except Exception as e:
            logging.error(f"[Bot {bot_num}] Error reading Karibbit: {e}")

    def start_spam(self):
        """Start spam functionality"""
        if not self.spam_thread_running:
            self.spam_thread_running = True
            threading.Thread(target=self._spam_loop, daemon=True).start()

    def _spam_loop(self):
        """Spam loop implementation"""
        while self.spam_thread_running:
            if self.spam_enabled and self.spam_message:
                with self.bots_lock:
                    for idx, bot in enumerate(self.bots):
                        if bot:
                            try:
                                bot.sendMessage(self.spam_channel_id, self.spam_message)
                                acc_name = self.acc_names[idx] if idx < len(self.acc_names) else f"Acc {idx}"
                                logging.info(f"[{acc_name}] Spam sent: {self.spam_message}")
                                time.sleep(2)
                            except Exception as e:
                                logging.error(f"Spam error: {e}")
            time.sleep(self.spam_delay)

    def start_auto_work(self):
        """Start auto work functionality"""
        if not self.work_thread_running:
            self.work_thread_running = True
            threading.Thread(target=self._auto_work_loop, daemon=True).start()

    def _auto_work_loop(self):
        """Auto work loop implementation"""
        while self.work_thread_running:
            if self.auto_work_enabled:
                with self.bots_lock:
                    for idx, token in enumerate(self.tokens):
                        if token.strip():
                            self._run_work_for_account(token.strip(), idx)
                            time.sleep(10)  # 10s delay between accounts
                
                logging.info("[Auto Work] Completed cycle, sleeping for 44100s")
                time.sleep(44100)  # ~12 hours
            else:
                time.sleep(60)

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

    def send_card_codes(self, acc_index, prefix, codes_list, delay):
        """Send card codes with prefix through specified account - like original code"""
        try:
            if acc_index >= len(self.bots):
                logging.error(f"[Card Code] Bot index {acc_index} not available")
                return False
                
            bot = self.bots[acc_index]
            if not bot:
                logging.error(f"[Card Code] Bot at index {acc_index} is None")
                return False
                
            acc_name = self.acc_names[acc_index] if acc_index < len(self.acc_names) else f"Acc {acc_index}"
            
            # Send codes with delay like original code
            for i, code in enumerate(codes_list):
                if code.strip():
                    final_msg = f"{prefix} {code}" if prefix else code
                    
                    def send_delayed_code(bot_ref, msg, acc_name_ref):
                        try:
                            bot_ref.sendMessage(self.other_channel_id, msg)
                            logging.info(f"[Card Code] Sent via {acc_name_ref}: {msg}")
                        except Exception as e:
                            logging.error(f"[Card Code] Error sending code: {e}")
                    
                    # Use timer for delay like original code  
                    threading.Timer(delay * i, send_delayed_code, args=(bot, final_msg, acc_name)).start()
            
            logging.info(f"[Card Code] Started sending {len(codes_list)} codes via {acc_name} with {delay}s delay")
            return True
            
        except Exception as e:
            logging.error(f"[Card Code] Error: {e}")
            return False

    def send_card_code(self, acc_name, code):
        """Send single card code - kept for compatibility"""
        try:
            if acc_name in self.acc_names:
                acc_index = self.acc_names.index(acc_name)
                if acc_index < len(self.bots) and self.bots[acc_index]:
                    self.bots[acc_index].sendMessage(self.other_channel_id, code)
                    logging.info(f"[Card Code] Sent '{code}' via {acc_name}")
                else:
                    raise Exception(f"Bot for {acc_name} not available")
            else:
                raise Exception(f"Account {acc_name} not found")
        except Exception as e:
            logging.error(f"[Card Code] Error: {e}")
            raise

    def initialize_all_bots(self):
        """Initialize all bots"""
        with self.bots_lock:
            logging.info("Initializing all bots...")
            
            # Initialize main bots
            if self.main_token:
                self.main_bot = self.create_bot(self.main_token, is_main=True)
                logging.info("Main Bot 1 initialized")
            
            if self.main_token_2:
                self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True)
                logging.info("Main Bot 2 initialized")
            
            # Initialize sub bots
            self.bots = []
            for i, token in enumerate(self.tokens):
                if token.strip():
                    bot = self.create_bot(token.strip(), is_main=False)
                    self.bots.append(bot)
                    logging.info(f"Sub Bot {i} initialized")
                else:
                    self.bots.append(None)
                    logging.info(f"Sub Bot {i} skipped (empty token)")

# Global bot controller
bot_controller = BotController()

# Flask app
app = Flask(__name__)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template_string("""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discord Bot Controller</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Courier New', monospace;
            background: #000;
            color: #00ff00;
            overflow-x: hidden;
            min-height: 100vh;
            position: relative;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                rgba(0, 255, 0, 0.03) 2px,
                rgba(0, 255, 0, 0.03) 4px
            );
            pointer-events: none;
            z-index: 1;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 2;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            border: 2px solid #00ff00;
            padding: 20px;
            background: rgba(0, 255, 0, 0.1);
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }
        
        .header h1 {
            font-size: 2.5em;
            text-shadow: 0 0 10px #00ff00;
            animation: glow 2s ease-in-out infinite alternate;
        }
        
        @keyframes glow {
            from { text-shadow: 0 0 10px #00ff00; }
            to { text-shadow: 0 0 20px #00ff00, 0 0 30px #00ff00; }
        }
        
        .status-bar {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            padding: 10px;
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #ff0000;
            animation: pulse 1s infinite;
        }
        
        .status-indicator.online {
            background: #00ff00;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(0, 255, 0, 0.1);
            border: 2px solid #00ff00;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.3);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            box-shadow: 0 0 25px rgba(0, 255, 0, 0.5);
            transform: translateY(-5px);
        }
        
        .card h3 {
            margin-bottom: 15px;
            font-size: 1.5em;
            text-shadow: 0 0 5px #00ff00;
            border-bottom: 1px solid #00ff00;
            padding-bottom: 10px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px;
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            color: #00ff00;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: none;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        }
        
        .btn {
            padding: 10px 20px;
            background: rgba(0, 255, 0, 0.2);
            border: 2px solid #00ff00;
            color: #00ff00;
            cursor: pointer;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            transition: all 0.3s ease;
            margin: 5px;
        }
        
        .btn:hover {
            background: rgba(0, 255, 0, 0.3);
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
        }
        
        .btn.active {
            background: #00ff00;
            color: #000;
        }
        
        .btn.danger {
            border-color: #ff0000;
            color: #ff0000;
        }
        
        .btn.danger:hover {
            background: rgba(255, 0, 0, 0.3);
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.5);
        }
        
        .bot-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .bot-item {
            background: rgba(0, 255, 0, 0.05);
            border: 1px solid #00ff00;
            padding: 15px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .bot-name {
            font-weight: bold;
        }
        
        .message {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px;
            border-radius: 5px;
            color: #fff;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }
        
        .message.success {
            background: rgba(0, 255, 0, 0.8);
            border: 1px solid #00ff00;
        }
        
        .message.error {
            background: rgba(255, 0, 0, 0.8);
            border: 1px solid #ff0000;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); }
            to { transform: translateX(0); }
        }
        
        .terminal {
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid #00ff00;
            padding: 20px;
            margin-top: 20px;
            border-radius: 10px;
            max-height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
        }
        
        .terminal-line {
            margin: 5px 0;
            word-wrap: break-word;
        }
        
        .work-status {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 10px;
        }
        
        .work-indicator {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #333;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
        }
        
        .work-indicator.working {
            background: #00ff00;
            color: #000;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DISCORD BOT CONTROLLER</h1>
            <p>Hệ thống điều khiển bot Discord đa năng</p>
        </div>
        
        <div class="status-bar">
            <div class="status-item">
                <div class="status-indicator" id="main-bot-1-status"></div>
                <span>Main Bot 1</span>
            </div>
            <div class="status-item">
                <div class="status-indicator" id="main-bot-2-status"></div>
                <span>Main Bot 2</span>
            </div>
            <div class="status-item">
                <div class="status-indicator" id="system-status"></div>
                <span id="system-status-text">System Ready</span>
            </div>
        </div>
        
        <div class="grid">
            <!-- Auto Grab Card -->
            <div class="card">
                <h3>🎯 Auto Grab</h3>
                <div class="form-group">
                    <label>Bot 1 Heart Threshold:</label>
                    <input type="number" id="heartThreshold1" value="50" min="1" max="1000">
                </div>
                <div class="form-group">
                    <label>Bot 2 Heart Threshold:</label>
                    <input type="number" id="heartThreshold2" value="50" min="1" max="1000">
                </div>
                <button class="btn" onclick="toggleAutoGrab(1)" id="autoGrab1">
                    Enable Auto Grab Bot 1
                </button>
                <button class="btn" onclick="toggleAutoGrab(2)" id="autoGrab2">
                    Enable Auto Grab Bot 2
                </button>
                <button class="btn" onclick="setHeartThreshold(1)">Set Bot 1 Threshold</button>
                <button class="btn" onclick="setHeartThreshold(2)">Set Bot 2 Threshold</button>
            </div>
            
            <!-- Auto Work Card -->
            <div class="card">
                <h3>⚙️ Auto Work</h3>
                <div class="work-status">
                    <div class="work-indicator" id="workIndicator"></div>
                    <span id="workStatus">Đang chờ...</span>
                </div>
                <button class="btn" onclick="toggleAutoWorkFunction()" id="autoWorkBtn">
                    Bật Auto Work
                </button>
                <div class="terminal" id="workTerminal">
                    <div class="terminal-line">System ready for auto work...</div>
                </div>
            </div>
            
            <!-- Spam Control Card -->
            <div class="card">
                <h3>📢 Spam Control</h3>
                <div class="form-group">
                    <label>Message:</label>
                    <input type="text" id="spamMessage" placeholder="Enter spam message">
                </div>
                <div class="form-group">
                    <label>Delay (seconds):</label>
                    <input type="number" id="spamDelay" value="10" min="1" max="3600">
                </div>
                <button class="btn" onclick="toggleSpamFunction()" id="spamBtn">
                    Enable Spam
                </button>
                <button class="btn" onclick="setSpamSettings()">Update Settings</button>
            </div>
            
            <!-- Message Control Card -->
            <div class="card">
                <h3>💬 Message Control</h3>
                <div class="form-group">
                    <label>Message:</label>
                    <input type="text" id="messageInput" placeholder="Enter message">
                </div>
                <div class="form-group">
                    <label>Quick Commands:</label>
                    <select id="quickCommands">
                        <option value="">Select a command</option>
                        <option value="kd">kd - Daily</option>
                        <option value="kt">kt - Top</option>
                        <option value="kw">kw - Work</option>
                        <option value="km">km - Multidrop</option>
                        <option value="kl">kl - Lookup</option>
                    </select>
                </div>
                <button class="btn" onclick="sendMessage()">Send to All Bots</button>
                <button class="btn" onclick="sendQuickMessage()">Send Quick Command</button>
            </div>
            
            <!-- Card Code Card -->
            <div class="card">
                <h3>🃏 Card Code</h3>
                <div class="form-group">
                    <label>Account:</label>
                    <select id="cardAccount">
                        <option value="0">Blacklist</option>
                        <option value="1">Khanh bang</option>
                        <option value="2">Dersale</option>
                        <option value="3">Venus</option>
                        <option value="4">WhyK</option>
                        <option value="5">Tan</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Prefix:</label>
                    <input type="text" id="cardPrefix" placeholder="kt" value="kt">
                </div>
                <div class="form-group">
                    <label>Codes (one per line):</label>
                    <textarea id="cardCodes" rows="5" placeholder="Enter card codes, one per line"></textarea>
                </div>
                <div class="form-group">
                    <label>Delay (seconds):</label>
                    <input type="number" id="cardDelay" value="2" min="1" max="60">
                </div>
                <button class="btn" onclick="sendCardCode()">Send Card Codes</button>
            </div>
            
            <!-- Bot Management Card -->
            <div class="card">
                <h3>🔧 Bot Management</h3>
                <div class="bot-list" id="botList">
                    <div class="bot-item">
                        <span class="bot-name">Main Bot 1</span>
                        <button class="btn danger" onclick="rebootBot('main_1')">Reboot</button>
                    </div>
                    <div class="bot-item">
                        <span class="bot-name">Main Bot 2</span>
                        <button class="btn danger" onclick="rebootBot('main_2')">Reboot</button>
                    </div>
                </div>
                <button class="btn" onclick="generateSubBots()">Generate Sub Bots</button>
            </div>
        </div>
    </div>
    
    <script>
        let statusUpdateInterval;
        let features = {
            auto_grab_enabled: false,
            auto_grab_enabled_2: false,
            auto_work_enabled: false,
            spam_enabled: false,
            heart_threshold: 50,
            heart_threshold_2: 50,
            spam_message: '',
            spam_delay: 10
        };
        
        function initializeEventListeners() {
            startStatusUpdates();
        }
        
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    }
                };
                
                if (data) {
                    options.body = JSON.stringify(data);
                }
                
                const response = await fetch(endpoint, options);
                const result = await response.json();
                
                if (result.success) {
                    showMessage('Thành công!', 'success');
                } else {
                    showMessage('Có lỗi xảy ra!', 'error');
                }
                
                return result;
            } catch (error) {
                console.error('API Error:', error);
                showMessage('Lỗi kết nối!', 'error');
                return { success: false, error: error.message };
            }
        }
        
        async function toggleAutoGrab(botNum) {
            const response = await fetch('/api/toggle_auto_grab', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    bot_num: botNum
                })
            });
            
            const result = await response.json();
            if (result.success) {
                const button = document.getElementById(`autoGrab${botNum}`);
                if (result.status) {
                    button.textContent = `Disable Auto Grab Bot ${botNum}`;
                    button.classList.add('active');
                } else {
                    button.textContent = `Enable Auto Grab Bot ${botNum}`;
                    button.classList.remove('active');
                }
                showMessage(`Auto Grab Bot ${botNum} ${result.status ? 'enabled' : 'disabled'}`, 'success');
            }
        }
        
        async function toggleAutoWorkFunction() {
            const response = await fetch('/api/toggle_auto_work', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });
            
            const result = await response.json();
            if (result.success) {
                const button = document.getElementById('autoWorkBtn');
                const indicator = document.getElementById('workIndicator');
                const status = document.getElementById('workStatus');
                
                if (result.status) {
                    button.textContent = 'Tắt Auto Work';
                    button.classList.add('active');
                    indicator.classList.add('working');
                    indicator.textContent = '⚡';
                    status.textContent = 'Đang chạy...';
                } else {
                    button.textContent = 'Bật Auto Work';
                    button.classList.remove('active');
                    indicator.classList.remove('working');
                    indicator.textContent = '';
                    status.textContent = 'Đang chờ...';
                }
                showMessage(`Auto Work ${result.status ? 'enabled' : 'disabled'}`, 'success');
            }
        }
        
        async function toggleSpamFunction() {
            const response = await fetch('/api/toggle_spam', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });
            
            const result = await response.json();
            if (result.success) {
                const button = document.getElementById('spamBtn');
                if (result.status) {
                    button.textContent = 'Disable Spam';
                    button.classList.add('active');
                } else {
                    button.textContent = 'Enable Spam';
                    button.classList.remove('active');
                }
                showMessage(`Spam ${result.status ? 'enabled' : 'disabled'}`, 'success');
            }
        }
        
        async function setHeartThreshold(botNum) {
            const threshold = document.getElementById(`heartThreshold${botNum}`).value;
            const response = await fetch('/api/set_heart_threshold', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    bot_num: botNum,
                    threshold: parseInt(threshold)
                })
            });
            
            const result = await response.json();
            if (result.success) {
                showMessage(`Heart threshold Bot ${botNum} set to ${threshold}`, 'success');
            }
        }
        
        async function setSpamSettings() {
            const message = document.getElementById('spamMessage').value;
            const delay = document.getElementById('spamDelay').value;
            
            const response = await fetch('/api/set_spam_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    delay: parseInt(delay)
                })
            });
            
            const result = await response.json();
            if (result.success) {
                showMessage('Spam settings updated', 'success');
            }
        }
        
        async function rebootBot(targetId) {
            const response = await fetch('/api/reboot_bot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    target_id: targetId
                })
            });
            
            const result = await response.json();
            if (result.success) {
                showMessage(`Bot ${targetId} rebooted successfully`, 'success');
            }
        }
        
        async function sendMessage() {
            const message = document.getElementById('messageInput').value;
            if (!message) {
                showMessage('Please enter a message', 'error');
                return;
            }
            
            const response = await fetch('/api/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message
                })
            });
            
            const result = await response.json();
            if (result.success) {
                showMessage('Message sent to all bots', 'success');
                document.getElementById('messageInput').value = '';
            }
        }
        
        async function sendQuickMessage() {
            const command = document.getElementById('quickCommands').value;
            if (!command) {
                showMessage('Please select a command', 'error');
                return;
            }
            
            const response = await fetch('/api/send_quick_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: command
                })
            });
            
            const result = await response.json();
            if (result.success) {
                showMessage(`Command ${command} sent to all bots`, 'success');
            }
        }
        
        async function sendCardCode() {
            const account = document.getElementById('cardAccount').value;
            const prefix = document.getElementById('cardPrefix').value;
            const codes = document.getElementById('cardCodes').value.split('\n').filter(code => code.trim());
            const delay = document.getElementById('cardDelay').value;
            
            if (!codes.length) {
                showMessage('Please enter card codes', 'error');
                return;
            }
            
            const response = await fetch('/api/send_card_code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    acc_index: parseInt(account),
                    prefix: prefix,
                    codes: codes,
                    delay: parseInt(delay)
                })
            });
            
            const result = await response.json();
            if (result.success) {
                showMessage(`Card codes sent via account ${account}`, 'success');
                document.getElementById('cardCodes').value = '';
            }
        }
        
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const status = await response.json();
                
                updateButtonState('autoGrab1', status.auto_grab_enabled);
                updateButtonState('autoGrab2', status.auto_grab_enabled_2);
                updateButtonState('autoWorkBtn', status.auto_work_enabled);
                updateButtonState('spamBtn', status.spam_enabled);
                
                updateInputValue('heartThreshold1', status.heart_threshold);
                updateInputValue('heartThreshold2', status.heart_threshold_2);
                updateInputValue('spamMessage', status.spam_message);
                updateInputValue('spamDelay', status.spam_delay);
                
                updateBotStatus('main-bot-1-status', status.main_bot_1_online);
                updateBotStatus('main-bot-2-status', status.main_bot_2_online);
                
                updateWorkStatus(status.auto_work_enabled, status.current_work_bot);
                updateSystemStatus(status.system_status);
                
                features = status;
                
                if (status.auto_work_enabled) {
                    const terminal = document.getElementById('workTerminal');
                    if (status.work_logs && status.work_logs.length > 0) {
                        terminal.innerHTML = status.work_logs.map(log => 
                            `<div class="terminal-line">${log}</div>`
                        ).join('');
                        terminal.scrollTop = terminal.scrollHeight;
                    }
                }
                
            } catch (error) {
                console.error('Status update error:', error);
            }
        }
        
        function updateButtonState(buttonId, isActive) {
            const button = document.getElementById(buttonId);
            if (button) {
                if (isActive) {
                    button.classList.add('active');
                } else {
                    button.classList.remove('active');
                }
            }
        }
        
        function updateInputValue(inputId, value) {
            const input = document.getElementById(inputId);
            if (input && input.value !== value.toString()) {
                input.value = value;
            }
        }
        
        function updateBotStatus(statusId, isOnline) {
            const indicator = document.getElementById(statusId);
            if (indicator) {
                if (isOnline) {
                    indicator.classList.add('online');
                } else {
                    indicator.classList.remove('online');
                }
            }
        }
        
        function updateWorkStatus(isWorking, currentBot) {
            const indicator = document.getElementById('workIndicator');
            const status = document.getElementById('workStatus');
            
            if (isWorking) {
                indicator.classList.add('working');
                indicator.textContent = '⚡';
                status.textContent = currentBot ? `Đang chạy Bot ${currentBot}` : 'Đang chạy...';
            } else {
                indicator.classList.remove('working');
                indicator.textContent = '';
                status.textContent = 'Đang chờ...';
            }
        }
        
        function updateSystemStatus(status) {
            const indicator = document.getElementById('system-status');
            const text = document.getElementById('system-status-text');
            
            if (status === 'active') {
                indicator.classList.add('online');
                text.textContent = 'System Active';
            } else {
                indicator.classList.remove('online');
                text.textContent = 'System Ready';
            }
        }
        
        function generateSubBots() {
            const botList = document.getElementById('botList');
            const existingBots = botList.innerHTML;
            
            const subBots = [];
            for (let i = 0; i < 18; i++) {
                subBots.push(`
                    <div class="bot-item">
                        <span class="bot-name">Sub Bot ${i}</span>
                        <button class="btn danger" onclick="rebootBot('sub_${i}')">Reboot</button>
                    </div>
                `);
            }
            
            botList.innerHTML = existingBots + subBots.join('');
            showMessage('Sub bots generated', 'success');
        }
        
        function showMessage(message, type = 'info') {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            messageDiv.textContent = message;
            document.body.appendChild(messageDiv);
            
            setTimeout(() => {
                messageDiv.remove();
            }, 3000);
        }
        
        function startStatusUpdates() {
            updateStatus();
            statusUpdateInterval = setInterval(updateStatus, 2000);
        }
        
        function stopStatusUpdates() {
            if (statusUpdateInterval) {
                clearInterval(statusUpdateInterval);
            }
        }
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initializeEventListeners();
            generateSubBots();
        });
    </script>
</body>
</html>
    """)

@app.route('/api/status')
def api_status():
    """Get bot status information"""
    try:
        return jsonify({
            'success': True,
            'auto_grab_enabled': bot_controller.auto_grab_enabled,
            'auto_grab_enabled_2': bot_controller.auto_grab_enabled_2,
            'auto_work_enabled': bot_controller.auto_work_enabled,
            'spam_enabled': bot_controller.spam_enabled,
            'heart_threshold': bot_controller.heart_threshold,
            'heart_threshold_2': bot_controller.heart_threshold_2,
            'spam_message': bot_controller.spam_message,
            'spam_delay': bot_controller.spam_delay,
            'main_bot_1_online': bot_controller.main_bot is not None,
            'main_bot_2_online': bot_controller.main_bot_2 is not None,
            'system_status': 'active' if (bot_controller.auto_grab_enabled or bot_controller.auto_work_enabled or bot_controller.spam_enabled) else 'ready',
            'current_work_bot': None,
            'work_logs': []
        })
    except Exception as e:
        logging.error(f"Status error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/toggle_auto_grab', methods=['POST'])
def toggle_auto_grab():
    """Toggle auto grab for main bots"""
    try:
        data = request.json
        bot_num = data.get('bot_num', 1)
        
        if bot_num == 1:
            bot_controller.auto_grab_enabled = not bot_controller.auto_grab_enabled
            return jsonify({'success': True, 'status': bot_controller.auto_grab_enabled})
        else:
            bot_controller.auto_grab_enabled_2 = not bot_controller.auto_grab_enabled_2
            return jsonify({'success': True, 'status': bot_controller.auto_grab_enabled_2})
    except Exception as e:
        logging.error(f"Toggle auto grab error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/set_heart_threshold', methods=['POST'])
def set_heart_threshold():
    """Set heart threshold for auto grab"""
    try:
        data = request.json
        bot_num = data.get('bot_num', 1)
        threshold = data.get('threshold', 50)
        
        if bot_num == 1:
            bot_controller.heart_threshold = threshold
        else:
            bot_controller.heart_threshold_2 = threshold
            
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Set heart threshold error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/toggle_spam', methods=['POST'])
def toggle_spam():
    """Toggle spam functionality"""
    try:
        bot_controller.spam_enabled = not bot_controller.spam_enabled
        if bot_controller.spam_enabled and not bot_controller.spam_thread_running:
            bot_controller.start_spam()
        return jsonify({'success': True, 'status': bot_controller.spam_enabled})
    except Exception as e:
        logging.error(f"Toggle spam error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/set_spam_config', methods=['POST'])
def set_spam_config():
    """Set spam configuration"""
    try:
        data = request.json
        bot_controller.spam_message = data.get('message', '')
        bot_controller.spam_delay = data.get('delay', 10)
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Set spam config error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/toggle_auto_work', methods=['POST'])
def toggle_auto_work():
    """Toggle auto work functionality"""
    try:
        bot_controller.auto_work_enabled = not bot_controller.auto_work_enabled
        if bot_controller.auto_work_enabled and not bot_controller.work_thread_running:
            bot_controller.start_auto_work()
        return jsonify({'success': True, 'status': bot_controller.auto_work_enabled})
    except Exception as e:
        logging.error(f"Toggle auto work error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """Send message through ALL bots like in original code"""
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'})
        
        sent_count = 0
        with bot_controller.bots_lock:
            # Send through main bots
            if bot_controller.main_bot:
                try:
                    bot_controller.main_bot.sendMessage(bot_controller.other_channel_id, message)
                    logging.info(f"[Main Bot 1] Message sent: {message}")
                    sent_count += 1
                except Exception as e:
                    logging.error(f"[Main Bot 1] Error sending message: {e}")
            
            if bot_controller.main_bot_2:
                try:
                    bot_controller.main_bot_2.sendMessage(bot_controller.other_channel_id, message)
                    logging.info(f"[Main Bot 2] Message sent: {message}")
                    sent_count += 1
                except Exception as e:
                    logging.error(f"[Main Bot 2] Error sending message: {e}")
            
            # Send through sub bots
            for idx, bot in enumerate(bot_controller.bots):
                if bot:
                    try:
                        bot.sendMessage(bot_controller.other_channel_id, message)
                        acc_name = bot_controller.acc_names[idx] if idx < len(bot_controller.acc_names) else f"Sub Bot {idx}"
                        logging.info(f"[{acc_name}] Message sent: {message}")
                        sent_count += 1
                    except Exception as e:
                        logging.error(f"[Sub Bot {idx}] Error sending message: {e}")
        
        return jsonify({'success': True, 'sent_count': sent_count})
    except Exception as e:
        logging.error(f"Send message error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_quick_message', methods=['POST'])
def send_quick_message():
    """Send quick command through ALL bots like in original code"""
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'})
        
        sent_count = 0
        with bot_controller.bots_lock:
            # Send through main bots
            if bot_controller.main_bot:
                try:
                    bot_controller.main_bot.sendMessage(bot_controller.other_channel_id, message)
                    logging.info(f"[Main Bot 1] Quick message sent: {message}")
                    sent_count += 1
                except Exception as e:
                    logging.error(f"[Main Bot 1] Error sending quick message: {e}")
            
            if bot_controller.main_bot_2:
                try:
                    bot_controller.main_bot_2.sendMessage(bot_controller.other_channel_id, message)
                    logging.info(f"[Main Bot 2] Quick message sent: {message}")
                    sent_count += 1
                except Exception as e:
                    logging.error(f"[Main Bot 2] Error sending quick message: {e}")
            
            # Send through sub bots
            for idx, bot in enumerate(bot_controller.bots):
                if bot:
                    try:
                        bot.sendMessage(bot_controller.other_channel_id, message)
                        acc_name = bot_controller.acc_names[idx] if idx < len(bot_controller.acc_names) else f"Sub Bot {idx}"
                        logging.info(f"[{acc_name}] Quick message sent: {message}")
                        sent_count += 1
                    except Exception as e:
                        logging.error(f"[Sub Bot {idx}] Error sending quick message: {e}")
        
        return jsonify({'success': True, 'sent_count': sent_count})
    except Exception as e:
        logging.error(f"Send quick message error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_card_code', methods=['POST'])
def send_card_code():
    """Send card codes with prefix through specified account"""
    try:
        data = request.json
        acc_index = data.get('acc_index', 0)
        prefix = data.get('prefix', '')
        codes = data.get('codes', [])
        delay = data.get('delay', 2)
        
        if not codes:
            return jsonify({'success': False, 'error': 'No codes provided'})
        
        result = bot_controller.send_card_codes(acc_index, prefix, codes, delay)
        return jsonify({'success': result})
    except Exception as e:
        logging.error(f"Send card code error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reboot_bot', methods=['POST'])
def reboot_bot():
    """Reboot specified bot"""
    try:
        data = request.json
        target_id = data.get('target_id', '')
        
        if not target_id:
            return jsonify({'success': False, 'error': 'Target ID is required'})
        
        result = bot_controller.reboot_bot(target_id)
        return jsonify({'success': result})
    except Exception as e:
        logging.error(f"Reboot bot error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/monitor')
def monitor_connections():
    """Monitor and auto-reconnect main bots when disconnected"""
    def monitor_connections():
        while True:
            try:
                bot_controller.check_and_reconnect_main_bots()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logging.error(f"Monitor connections error: {e}")
                time.sleep(60)  # Wait longer on error
    
    threading.Thread(target=monitor_connections, daemon=True).start()
    return "Connection monitoring started"

@app.route('/initialize')
def initialize_bots():
    """Initialize all bots when the app starts"""
    try:
        bot_controller.initialize_all_bots()
        return "Bots initialized successfully"
    except Exception as e:
        logging.error(f"Initialize bots error: {e}")
        return f"Error initializing bots: {e}"

# Start everything when app starts
if __name__ == "__main__":
    def monitor_connections():
        while True:
            try:
                bot_controller.check_and_reconnect_main_bots()
                time.sleep(30)
            except Exception as e:
                logging.error(f"Monitor error: {e}")
                time.sleep(60)
    
    # Start monitoring thread
    threading.Thread(target=monitor_connections, daemon=True).start()
    
    # Start spam thread
    bot_controller.start_spam()
    
    # Start auto work thread
    bot_controller.start_auto_work()
    
    # Initialize all bots
    bot_controller.initialize_all_bots()
    
    app.run(host='0.0.0.0', port=5000, debug=True)