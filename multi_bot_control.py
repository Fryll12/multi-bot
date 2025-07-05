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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            if current_time - self.last_reconnect_time["main_1"] > 60:
                self.reconnect_attempts["main_1"] += 1
                if self.reconnect_attempts["main_1"] <= 5:
                    logging.info(f"[Auto-Reconnect] Attempting to reconnect Main Bot 1 (attempt {self.reconnect_attempts['main_1']})")
                    try:
                        self.main_bot = self.create_bot(self.main_token, is_main=True)
                        self.last_reconnect_time["main_1"] = current_time
                        logging.info("[Auto-Reconnect] Main Bot 1 reconnected successfully")
                    except Exception as e:
                        logging.error(f"[Auto-Reconnect] Failed to reconnect Main Bot 1: {e}")
                        
        # Check Main Bot 2
        if self.main_token_2 and (not self.main_bot_2 or not hasattr(self.main_bot_2.gateway, 'ws') or not self.main_bot_2.gateway.ws):
            if current_time - self.last_reconnect_time["main_2"] > 60:
                self.reconnect_attempts["main_2"] += 1
                if self.reconnect_attempts["main_2"] <= 5:
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
                                logging.info("[Bot 1] Auto drop detected! Reading Karibbit message...")
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
                                logging.info("[Bot 2] Auto drop detected! Reading Karibbit message...")
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
                    logging.info(f"[Bot {bot_num}] ===== Karibbit Message =====\n{desc}\n[Bot {bot_num}] ===== End Message =====")

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
                        logging.info(f"[Bot {bot_num}] No hearts found, skipping.")
                    else:
                        max_num = max(heart_numbers)
                        threshold = self.heart_threshold if bot_num == 1 else self.heart_threshold_2
                        if max_num < threshold:
                            logging.info(f"[Bot {bot_num}] Max hearts {max_num} < {threshold}, not grabbing!")
                        else:
                            max_index = heart_numbers.index(max_num)
                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                            base_delays = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}
                            delay = base_delays[emoji] + (0.3 if bot_num == 2 else 0)
                            logging.info(f"[Bot {bot_num}] Choosing line {max_index+1} with {max_num} hearts → Emoji {emoji} after {delay}s")

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
                # No need for bots_lock here as _run_work_for_account creates its own bot instances
                for idx, token in enumerate(self.tokens):
                    if token.strip():
                        # Pass the actual index for logging
                        self._run_work_for_account(token.strip(), idx)
                        logging.info(f"[Auto Work] Account {idx} finished. Waiting 10s for the next one.")
                        time.sleep(10)  # 10s delay between accounts
                
                logging.info("[Auto Work] Completed a full cycle. Sleeping for ~12 hours (44100s).")
                time.sleep(44100)
            else:
                time.sleep(60)

    def _run_work_for_account(self, token, acc_index):
        """Run the complete work routine for a single account."""
        log_prefix = f"[Work Acc {acc_index}]"
        
        try:
            bot = discum.Client(token=token, log={"console": False, "file": False})

            headers = {"Authorization": token, "Content-Type": "application/json"}
            step = {"value": 0}

            def send_karuta_command():
                logging.info(f"{log_prefix} Sending command 'kc o:ef'...")
                bot.sendMessage(self.work_channel_id, "kc o:ef")

            def send_kn_command():
                logging.info(f"{log_prefix} Sending command 'kn'...")
                bot.sendMessage(self.work_channel_id, "kn")

            def send_kw_command():
                logging.info(f"{log_prefix} Sending command 'kw'...")
                bot.sendMessage(self.work_channel_id, "kw")
                step["value"] = 2

            def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
                try:
                    payload = {
                        "type": 3, "guild_id": guild_id, "channel_id": channel_id,
                        "message_id": message_id, "application_id": application_id,
                        "session_id": "a",
                        "data": {"component_type": 2, "custom_id": custom_id}
                    }
                    r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
                    if r.status_code == 204:
                        logging.info(f"{log_prefix} Successfully clicked the button.")
                    else:
                        logging.error(f"{log_prefix} Failed to click button! Status: {r.status_code}, Response: {r.text}")
                except Exception as e:
                    logging.error(f"{log_prefix} Exception during button click: {str(e)}")

            @bot.gateway.command
            def on_message(resp):
                if not resp.event.message: return
                
                m = resp.parsed.auto()
                if str(m.get('channel_id')) != self.work_channel_id: return

                author_id = str(m.get('author', {}).get('id', ''))
                guild_id = m.get('guild_id')

                if step["value"] == 0 and author_id == self.karuta_id and 'embeds' in m and m['embeds']:
                    desc = m['embeds'][0].get('description', '')
                    card_codes = re.findall(r'\bv[a-zA-Z0-9]{6}\b', desc)
                    if len(card_codes) >= 10:
                        first_5 = card_codes[:5]
                        last_5 = card_codes[-5:]

                        logging.info(f"{log_prefix} First 5 codes: {', '.join(first_5)}")
                        logging.info(f"{log_prefix} Last 5 codes: {', '.join(last_5)}")

                        for i, code in enumerate(last_5):
                            time.sleep(1.5)
                            bot.sendMessage(self.work_channel_id, f"kjw {code} {chr(97 + i)}")
                        for i, code in enumerate(first_5):
                            time.sleep(1.5)
                            bot.sendMessage(self.work_channel_id, f"kjw {code} {chr(97 + i)}")

                        time.sleep(1)
                        send_kn_command()
                        step["value"] = 1

                elif step["value"] == 1 and author_id == self.karuta_id and 'embeds' in m and m['embeds']:
                    desc = m['embeds'][0].get('description', '')
                    lines = desc.split('\n')
                    if len(lines) >= 2:
                        match = re.search(r'\d+\.\s*`([^`]+)`', lines[1])
                        if match:
                            resource = match.group(1)
                            logging.info(f"{log_prefix} Selected resource: {resource}")
                            time.sleep(2)
                            bot.sendMessage(self.work_channel_id, f"kjn `{resource}` a b c d e")
                            time.sleep(1)
                            send_kw_command()

                elif step["value"] == 2 and author_id == self.karuta_id and 'components' in m:
                    message_id = m['id']
                    last_custom_id = None
                    for comp in m.get('components', []):
                        if comp.get('type') == 1:
                            for btn in comp.get('components', []):
                                if btn.get('type') == 2:
                                    last_custom_id = btn.get('custom_id')
                    
                    if last_custom_id:
                        logging.info(f"{log_prefix} Found button with custom_id: {last_custom_id}")
                        click_tick(self.work_channel_id, message_id, last_custom_id, self.karuta_id, guild_id)
                        step["value"] = 3 # Mark as done
                        bot.gateway.close()

            logging.info(f"{log_prefix} Starting work routine...")
            threading.Thread(target=bot.gateway.run, daemon=True).start()
            time.sleep(3) # Wait for gateway to connect
            send_karuta_command()

            timeout = time.time() + 90  # 90-second timeout for the whole process
            while step["value"] != 3 and time.time() < timeout:
                time.sleep(1)

            if step["value"] != 3:
                logging.warning(f"{log_prefix} Timed out. Did not complete the full work cycle.")
            
            bot.gateway.close()
            logging.info(f"{log_prefix} Work routine finished.")

        except Exception as e:
            logging.error(f"{log_prefix} An unexpected error occurred: {e}", exc_info=True)


    def send_card_codes(self, acc_index, prefix, codes_list, delay):
        """Send card codes with prefix through specified account"""
        try:
            if acc_index >= len(self.bots):
                logging.error(f"[Card Code] Bot index {acc_index} not available")
                return False
                
            bot = self.bots[acc_index]
            if not bot:
                logging.error(f"[Card Code] Bot at index {acc_index} is None")
                return False
                
            acc_name = self.acc_names[acc_index] if acc_index < len(self.acc_names) else f"Acc {acc_index}"
            
            for i, code in enumerate(codes_list):
                if code.strip():
                    final_msg = f"{prefix} {code}" if prefix else code
                    
                    def send_delayed_code(bot_ref, msg, acc_name_ref):
                        try:
                            bot_ref.sendMessage(self.other_channel_id, msg)
                            logging.info(f"[Card Code] Sent via {acc_name_ref}: {msg}")
                        except Exception as e:
                            logging.error(f"[Card Code] Error sending code: {e}")
                    
                    threading.Timer(delay * i, send_delayed_code, args=(bot, final_msg, acc_name)).start()
            
            logging.info(f"[Card Code] Started sending {len(codes_list)} codes via {acc_name} with {delay}s delay")
            return True
            
        except Exception as e:
            logging.error(f"[Card Code] Error: {e}")
            return False

    def initialize_all_bots(self):
        """Initialize all bots"""
        with self.bots_lock:
            if self.main_token:
                self.main_bot = self.create_bot(self.main_token, is_main=True)
            if self.main_token_2:
                self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True)

            for token in self.tokens:
                if token.strip():
                    self.bots.append(self.create_bot(token.strip(), is_main=False))
        
        logging.info("All bots initialized successfully")

# Global bot controller instance
bot_controller = BotController()

# Flask Application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "karuta_deep_secret_key")

@app.route('/')
def index():
    """Main dashboard page"""
    # Dynamically generate the options for the select dropdown
    acc_options_html = ''.join(f'<option value="{i}">{acc_names[i] if i < len(acc_names) else f"Acc {i}"}</option>' for i in range(len(tokens)))
    # THE FIX IS HERE: Replace a specific placeholder, not an empty string.
    return render_template_string(HTML_TEMPLATE.replace('', acc_options_html))

@app.route('/api/status')
def api_status():
    """Get bot status information"""
    # Ensure bot list is not empty before checking attributes
    connected_main_1 = bot_controller.main_bot and hasattr(bot_controller.main_bot.gateway, 'ws') and bot_controller.main_bot.gateway.ws
    connected_main_2 = bot_controller.main_bot_2 and hasattr(bot_controller.main_bot_2.gateway, 'ws') and bot_controller.main_bot_2.gateway.ws
    connected_subs = sum(1 for bot in bot_controller.bots if bot and hasattr(bot.gateway, 'ws') and bot.gateway.ws)
    
    return jsonify({
        'main_bot_1': {
            'connected': bool(connected_main_1),
            'auto_grab': bot_controller.auto_grab_enabled,
            'heart_threshold': bot_controller.heart_threshold
        },
        'main_bot_2': {
            'connected': bool(connected_main_2),
            'auto_grab': bot_controller.auto_grab_enabled_2,
            'heart_threshold': bot_controller.heart_threshold_2
        },
        'sub_bots': {
            'count': len(bot_controller.bots),
            'connected': connected_subs
        },
        'features': {
            'spam_enabled': bot_controller.spam_enabled,
            'spam_message': bot_controller.spam_message,
            'spam_delay': bot_controller.spam_delay,
            'auto_work_enabled': bot_controller.auto_work_enabled
        }
    })

@app.route('/api/toggle_auto_grab', methods=['POST'])
def toggle_auto_grab():
    data = request.json
    bot_id = data.get('bot_id')
    if bot_id == 'main_1':
        bot_controller.auto_grab_enabled = not bot_controller.auto_grab_enabled
        return jsonify({'success': True, 'status': bot_controller.auto_grab_enabled})
    elif bot_id == 'main_2':
        bot_controller.auto_grab_enabled_2 = not bot_controller.auto_grab_enabled_2
        return jsonify({'success': True, 'status': bot_controller.auto_grab_enabled_2})
    return jsonify({'success': False, 'message': 'Invalid bot ID'})

@app.route('/api/set_heart_threshold', methods=['POST'])
def set_heart_threshold():
    data = request.json
    bot_id = data.get('bot_id')
    threshold = data.get('threshold')
    if bot_id == 'main_1':
        bot_controller.heart_threshold = int(threshold)
        return jsonify({'success': True})
    elif bot_id == 'main_2':
        bot_controller.heart_threshold_2 = int(threshold)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid bot ID'})

@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json
    message = data.get('message')
    if not message: return jsonify({'success': False, 'message': 'Message cannot be empty'})
    with bot_controller.bots_lock:
        for idx, bot in enumerate(bot_controller.bots):
            if bot:
                try:
                    threading.Timer(2 * idx, bot.sendMessage, args=(bot_controller.other_channel_id, message)).start()
                except Exception as e:
                    logging.error(f"Error sending message: {e}")
    return jsonify({'success': True, 'message': 'Sent message through ALL bots'})

@app.route('/api/send_quick_message', methods=['POST'])
def send_quick_message():
    data = request.json
    message = data.get('message')
    if not message: return jsonify({'success': False, 'message': 'Message cannot be empty'})
    with bot_controller.bots_lock:
        for idx, bot in enumerate(bot_controller.bots):
            if bot:
                try:
                    threading.Timer(2 * idx, bot.sendMessage, args=(bot_controller.other_channel_id, message)).start()
                except Exception as e:
                    logging.error(f"Error sending quick message: {e}")
    return jsonify({'success': True, 'message': 'Sent quick command through ALL bots'})

@app.route('/api/reboot_bot', methods=['POST'])
def reboot_bot_route():
    data = request.json
    bot_id = data.get('bot_id')
    result = bot_controller.reboot_bot(bot_id)
    if result: return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Reboot failed'})

@app.route('/api/toggle_spam', methods=['POST'])
def toggle_spam():
    bot_controller.spam_enabled = not bot_controller.spam_enabled
    if bot_controller.spam_enabled and not bot_controller.spam_thread_running:
        bot_controller.start_spam()
    return jsonify({'success': True, 'status': bot_controller.spam_enabled})

@app.route('/api/set_spam_config', methods=['POST'])
def set_spam_config():
    data = request.json
    bot_controller.spam_message = data.get('message', '')
    bot_controller.spam_delay = int(data.get('delay', 10))
    return jsonify({'success': True})

@app.route('/api/toggle_auto_work', methods=['POST'])
def toggle_auto_work():
    bot_controller.auto_work_enabled = not bot_controller.auto_work_enabled
    if bot_controller.auto_work_enabled and not bot_controller.work_thread_running:
        bot_controller.start_auto_work()
    return jsonify({'success': True, 'status': bot_controller.auto_work_enabled})

@app.route('/api/send_card_code', methods=['POST'])
def send_card_code_route():
    data = request.json
    acc_index = data.get('acc_index', 0)
    prefix = data.get('prefix', '')
    codes = data.get('codes', '')
    delay = data.get('delay', 11.0)
    try:
        codes_list = [code.strip() for code in codes.split(',') if code.strip()]
        if not codes_list: return jsonify({'success': False, 'message': 'Không tìm thấy mã hợp lệ'})
        result = bot_controller.send_card_codes(int(acc_index), prefix, codes_list, float(delay))
        if result: return jsonify({'success': True, 'message': f'Đã bắt đầu gửi {len(codes_list)} mã qua acc {acc_index}'})
        return jsonify({'success': False, 'message': f'Bot tại index {acc_index} không khả dụng'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def monitor_connections():
    """Monitor and auto-reconnect main bots when disconnected"""
    while True:
        try:
            bot_controller.check_and_reconnect_main_bots()
            time.sleep(30)
        except Exception as e:
            logging.error(f"[Monitor] Error: {e}")
            time.sleep(60)

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Deep - Control Center</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0a; --bg-secondary: #111111; --bg-tertiary: #1a1a1a;
            --text-primary: #00ff00; --text-secondary: #00cc00; --text-tertiary: #008800;
            --accent: #ff0080; --border: #333333; --success: #00ff00;
            --warning: #ffaa00; --danger: #ff0040; --primary-green: #00ff00;
            --danger-red: #ff0040; --glow-green: 0 0 20px rgba(0, 255, 0, 0.5);
            --glow-red: 0 0 20px rgba(255, 0, 64, 0.5); --glow-yellow: 0 0 20px rgba(255, 170, 0, 0.5);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Courier New', monospace; background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; position: relative; overflow-x: hidden; }
        body::before { content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(90deg, transparent 98%, rgba(0, 255, 0, 0.03) 100%), linear-gradient(0deg, transparent 98%, rgba(0, 255, 0, 0.03) 100%); background-size: 50px 50px; z-index: -1; animation: matrix-bg 20s linear infinite; }
        @keyframes matrix-bg { 0% { transform: translateY(0); } 100% { transform: translateY(50px); } }
        .scan-line { position: fixed; top: 0; left: 0; width: 100%; height: 2px; background: linear-gradient(90deg, transparent, var(--primary-green), transparent); z-index: 1000; animation: scan 3s linear infinite; }
        @keyframes scan { 0% { top: 0; opacity: 1; } 100% { top: 100vh; opacity: 0; } }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; position: relative; z-index: 10; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 10px; box-shadow: var(--glow-green); }
        .header h1 { font-size: 2.5rem; color: var(--text-primary); text-shadow: 0 0 10px var(--primary-green); margin-bottom: 10px; animation: glow-pulse 2s ease-in-out infinite alternate; }
        @keyframes glow-pulse { from { text-shadow: 0 0 10px var(--primary-green); } to { text-shadow: 0 0 20px var(--primary-green), 0 0 30px var(--primary-green); } }
        .header .subtitle { color: var(--text-secondary); font-size: 1.1rem; }
        .connection-status { display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 15px; padding: 10px; background: var(--bg-tertiary); border-radius: 5px; }
        .connection-status.online { color: var(--success); box-shadow: var(--glow-green); }
        .bot-status { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .bot-card { background: var(--bg-secondary); border: 2px solid var(--border); border-radius: 10px; padding: 20px; transition: all 0.3s ease; }
        .bot-card:hover { transform: translateY(-2px); box-shadow: var(--glow-green); }
        .bot-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .bot-title { font-size: 1.2rem; font-weight: bold; color: var(--text-primary); }
        .bot-status-indicator { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; }
        .bot-status-indicator.online { color: var(--success); }
        .bot-controls { display: flex; flex-direction: column; gap: 15px; }
        .control-group { display: flex; justify-content: space-between; align-items: center; }
        .control-group label { font-size: 0.9rem; color: var(--text-secondary); }
        .toggle-btn { background: var(--bg-tertiary); border: 1px solid var(--border); color: var(--text-primary); padding: 8px 15px; border-radius: 5px; cursor: pointer; transition: all 0.3s ease; display: flex; align-items: center; gap: 5px; }
        .toggle-btn:hover { border-color: var(--primary-green); box-shadow: var(--glow-green); }
        .toggle-btn.active { background: var(--primary-green); color: var(--bg-primary); box-shadow: var(--glow-green); }
        .form-group { display: flex; flex-direction: column; gap: 5px; }
        .form-group label { font-size: 0.9rem; color: var(--text-secondary); }
        .form-group input, .form-group select, .form-group textarea { background: var(--bg-tertiary); border: 1px solid var(--border); color: var(--text-primary); padding: 10px; border-radius: 5px; font-family: inherit; }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline: none; border-color: var(--primary-green); box-shadow: var(--glow-green); }
        .control-panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .control-panel { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 10px; padding: 20px; }
        .control-panel h3 { color: var(--text-primary); margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        .panel-content { display: flex; flex-direction: column; gap: 15px; }
        .action-btn { background: var(--bg-tertiary); border: 1px solid var(--primary-green); color: var(--text-primary); padding: 12px 20px; border-radius: 5px; cursor: pointer; transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; gap: 10px; font-family: inherit; }
        .action-btn:hover { background: var(--primary-green); color: var(--bg-primary); box-shadow: var(--glow-green); }
        .card-btn { border-color: var(--warning); }
        .card-btn:hover { background: var(--warning); color: var(--bg-primary); box-shadow: var(--glow-yellow); }
        .quick-commands { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 8px; }
        .quick-cmd-btn { background: var(--bg-tertiary); border: 1px solid var(--accent); color: var(--text-primary); padding: 10px; border-radius: 5px; cursor: pointer; transition: all 0.3s ease; font-family: inherit; font-size: 0.85rem; }
        .quick-cmd-btn:hover { background: var(--accent); color: white; }
        .sub-bots-section { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .sub-bot-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; margin-top: 15px; }
        .sub-bot-item { background: var(--bg-tertiary); border: 1px solid var(--border); border-radius: 5px; padding: 10px; display: flex; justify-content: space-between; align-items: center; }
        .sub-bot-reboot { background: var(--warning); color: var(--bg-primary); border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; font-size: 0.8rem; }
        .terminal { background: var(--bg-primary); border: 1px solid var(--primary-green); border-radius: 10px; padding: 20px; height: 300px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.9rem; margin-top: 20px; box-shadow: var(--glow-green); }
        .terminal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .terminal-header h3 { color: var(--primary-green); }
        .clear-btn { background: var(--danger); color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; font-size: 0.8rem; }
        .terminal-line { margin-bottom: 5px; animation: type 0.1s ease-out; }
        @keyframes type { from { opacity: 0; } to { opacity: 1; } }
        .timestamp { color: var(--text-tertiary); }
        .message { margin-left: 10px; }
        .message.success { color: var(--success); }
        .message.error { color: var(--danger); }
        .message.warning { color: var(--warning); }
        .message.info { color: var(--text-primary); }
        .cursor { animation: blink 1s infinite; }
        @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
        @media (max-width: 768px) { .container { padding: 10px; } .header h1 { font-size: 2rem; } .bot-status, .control-panels { grid-template-columns: 1fr; } .quick-commands { grid-template-columns: repeat(2, 1fr); } }
    </style>
</head>
<body>
    <div class="scan-line"></div>
    <div class="container">
        <header class="header"><h1><i class="fas fa-terminal"></i> KARUTA DEEP</h1><p class="subtitle">Discord Multi-Bot Control Center</p><div class="connection-status" id="connectionStatus"><i class="fas fa-circle"></i><span>ĐANG KẾT NỐI...</span></div></header>
        <section class="bot-status">
            <div class="bot-card" id="mainBot1"><div class="bot-header"><div class="bot-title"><i class="fas fa-crown"></i> ACC CHÍNH 1</div><div class="bot-status-indicator" id="mainBot1Status"><i class="fas fa-circle"></i><span>NGOẠI TUYẾN</span></div></div><div class="bot-controls"><div class="control-group"><label>Auto Grab</label><button class="toggle-btn" id="autoGrab1" onclick="toggleAutoGrab('main_1')"><i class="fas fa-power-off"></i><span>TẮT</span></button></div><div class="form-group"><label>Ngưỡng Tim</label><input type="number" id="heartThreshold1" value="50" min="1" onchange="setHeartThreshold('main_1', this.value)"></div><button class="action-btn" onclick="rebootBot('main_1')"><i class="fas fa-redo"></i> KHỞI ĐỘNG LẠI</button></div></div>
            <div class="bot-card" id="mainBot2"><div class="bot-header"><div class="bot-title"><i class="fas fa-crown"></i> ACC CHÍNH 2</div><div class="bot-status-indicator" id="mainBot2Status"><i class="fas fa-circle"></i><span>NGOẠI TUYẾN</span></div></div><div class="bot-controls"><div class="control-group"><label>Auto Grab</label><button class="toggle-btn" id="autoGrab2" onclick="toggleAutoGrab('main_2')"><i class="fas fa-power-off"></i><span>TẮT</span></button></div><div class="form-group"><label>Ngưỡng Tim</label><input type="number" id="heartThreshold2" value="50" min="1" onchange="setHeartThreshold('main_2', this.value)"></div><button class="action-btn" onclick="rebootBot('main_2')"><i class="fas fa-redo"></i> KHỞI ĐỘNG LẠI</button></div></div>
        </section>
        <section class="sub-bots-section"><div class="bot-header"><div class="bot-title"><i class="fas fa-users"></i> ACC PHỤ</div><div class="bot-status-indicator" id="subBotsStatus"><i class="fas fa-circle"></i><span>0/0 TRỰC TUYẾN</span></div></div><div class="sub-bot-list" id="subBotList"></div></section>
        <section class="control-panels">
            <div class="control-panel"><h3><i class="fas fa-comments"></i> ĐIỀU KHIỂN TIN NHẮN</h3><div class="panel-content"><div class="form-group"><label>Tin Nhắn (Gửi qua TẤT CẢ acc vào Other Channel)</label><textarea id="messageContent" placeholder="Nhập tin nhắn của bạn..."></textarea></div><button class="action-btn send-btn" onclick="sendMessage()"><i class="fas fa-paper-plane"></i> GỬI QUA TẤT CẢ BOT</button></div></div>
            <div class="control-panel"><h3><i class="fas fa-bolt"></i> LỆNH NHANH (Gửi vào Other Channel)</h3><div class="panel-content"><div class="quick-commands"><button class="quick-cmd-btn" onclick="sendQuickCommand('kc o:w')"><i class="fas fa-hammer"></i> kc o:w</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc o:ef')"><i class="fas fa-tools"></i> kc o:ef</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc o:p')"><i class="fas fa-cog"></i> kc o:p</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc e:1')"><i class="fas fa-gem"></i> kc e:1</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc e:2')"><i class="fas fa-gem"></i> kc e:2</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc e:3')"><i class="fas fa-gem"></i> kc e:3</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc e:4')"><i class="fas fa-gem"></i> kc e:4</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc e:5')"><i class="fas fa-gem"></i> kc e:5</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc e:6')"><i class="fas fa-gem"></i> kc e:6</button><button class="quick-cmd-btn" onclick="sendQuickCommand('kc e:7')"><i class="fas fa-gem"></i> kc e:7</button></div></div></div>
            <div class="control-panel"><h3><i class="fas fa-id-card"></i> GỬI MÃ CARD</h3><div class="panel-content"><div class="form-group"><label>Chọn Acc</label><select id="cardAccIndex"></select></div><div class="form-group"><label>Delay (giây)</label><input type="number" id="cardDelay" value="11" min="1"></div><div class="form-group"><label>Prefix (vd: kt n)</label><input type="text" id="cardPrefix" placeholder="kt n"></div><div class="form-group"><label>Danh sách mã (cách nhau dấu phẩy)</label><textarea id="cardCodes" rows="4" placeholder="mã1,mã2,mã3..."></textarea></div><button class="action-btn card-btn" onclick="sendCardCode()"><i class="fas fa-credit-card"></i> GỬI DANH SÁCH MÃ</button></div></div>
            <div class="control-panel"><h3><i class="fas fa-repeat"></i> SPAM CONTROL</h3><div class="panel-content"><div class="control-group"><label>Spam Status</label><button class="toggle-btn" id="spamToggle" onclick="toggleSpam()"><i class="fas fa-power-off"></i><span>TẮT</span></button></div><div class="form-group"><label>Spam Message</label><input type="text" id="spamMessage" placeholder="Nhập tin nhắn spam..."></div><div class="form-group"><label>Spam Delay (giây)</label><input type="number" id="spamDelay" value="10" min="1"></div><button class="action-btn" onclick="setSpamConfig()"><i class="fas fa-save"></i> CẬP NHẬT CONFIG</button></div></div>
            <div class="control-panel"><h3><i class="fas fa-robot"></i> AUTO WORK</h3><div class="panel-content"><div class="control-group"><label>Auto Work Status</label><button class="toggle-btn" id="autoWorkToggle" onclick="toggleAutoWork()"><i class="fas fa-power-off"></i><span>TẮT</span></button></div><p style="font-size: 0.9rem; color: var(--text-secondary);">Tự động chạy lệnh work cho tất cả acc phụ mỗi 12 tiếng</p></div></div>
        </section>
        <div class="terminal"><div class="terminal-header"><h3><i class="fas fa-terminal"></i> SYSTEM LOGS</h3><button class="clear-btn" onclick="clearTerminal()"><i class="fas fa-trash"></i> CLEAR</button></div><div id="terminal"><div class="terminal-line"><span class="timestamp">[SYSTEM]</span><span class="message">Karuta Deep Control Center initialized</span><span class="cursor">█</span></div></div></div>
    </div>
    <script>
        class DashboardController {
            constructor() {
                this.statusUpdateInterval = null;
                this.init();
            }

            init() {
                this.startStatusUpdates();
                this.logToTerminal('System initialized successfully', 'success');
            }

            startStatusUpdates() {
                this.updateStatus();
                this.statusUpdateInterval = setInterval(() => {
                    this.updateStatus();
                }, 5000); // Vẫn giữ lại để đồng bộ định kỳ
            }

            async apiCall(endpoint, body) {
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    return await response.json();
                } catch (e) {
                    this.logToTerminal(`API call to ${endpoint} failed: ${e.message}`, 'error');
                    return { success: false, message: e.message };
                }
            }
            
            async updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    const data = await response.json();
                    this.updateBotStatus(data);
                    this.updateConnectionIndicator(data);
                } catch (error) {
                    console.error('Error updating status:', error);
                    this.logToTerminal(`Failed to fetch status: ${error.message}`, 'error');
                }
            }

            updateBotStatus(data) {
                // Update Main Bot 1
                const mainBot1Status = document.getElementById('mainBot1Status');
                const mainBot1Card = document.getElementById('mainBot1');
                const autoGrab1 = document.getElementById('autoGrab1');
                const heartThreshold1 = document.getElementById('heartThreshold1');
                
                if (data.main_bot_1.connected) {
                    mainBot1Status.innerHTML = '<i class="fas fa-circle"></i><span>TRỰC TUYẾN</span>';
                    mainBot1Status.classList.add('online');
                    mainBot1Card.style.borderColor = 'var(--primary-green)';
                    mainBot1Card.style.boxShadow = 'var(--glow-green)';
                } else {
                    mainBot1Status.innerHTML = '<i class="fas fa-circle"></i><span>NGOẠI TUYẾN</span>';
                    mainBot1Status.classList.remove('online');
                    mainBot1Card.style.borderColor = 'var(--danger-red)';
                    mainBot1Card.style.boxShadow = 'var(--glow-red)';
                }

                if (data.main_bot_1.auto_grab) {
                    autoGrab1.classList.add('active');
                    autoGrab1.innerHTML = '<i class="fas fa-power-off"></i><span>BẬT</span>';
                } else {
                    autoGrab1.classList.remove('active');
                    autoGrab1.innerHTML = '<i class="fas fa-power-off"></i><span>TẮT</span>';
                }
                heartThreshold1.value = data.main_bot_1.heart_threshold;

                // Update Main Bot 2
                const mainBot2Status = document.getElementById('mainBot2Status');
                const mainBot2Card = document.getElementById('mainBot2');
                const autoGrab2 = document.getElementById('autoGrab2');
                const heartThreshold2 = document.getElementById('heartThreshold2');
                
                if (data.main_bot_2.connected) {
                    mainBot2Status.innerHTML = '<i class="fas fa-circle"></i><span>TRỰC TUYẾN</span>';
                    mainBot2Status.classList.add('online');
                    mainBot2Card.style.borderColor = 'var(--primary-green)';
                    mainBot2Card.style.boxShadow = 'var(--glow-green)';
                } else {
                    mainBot2Status.innerHTML = '<i class="fas fa-circle"></i><span>NGOẠI TUYẾN</span>';
                    mainBot2Status.classList.remove('online');
                    mainBot2Card.style.borderColor = 'var(--danger-red)';
                    mainBot2Card.style.boxShadow = 'var(--glow-red)';
                }

                if (data.main_bot_2.auto_grab) {
                    autoGrab2.classList.add('active');
                    autoGrab2.innerHTML = '<i class="fas fa-power-off"></i><span>BẬT</span>';
                } else {
                    autoGrab2.classList.remove('active');
                    autoGrab2.innerHTML = '<i class="fas fa-power-off"></i><span>TẮT</span>';
                }
                heartThreshold2.value = data.main_bot_2.heart_threshold;

                // Update Sub Bots
                document.getElementById('subBotsStatus').innerHTML = `<i class="fas fa-circle"></i><span>${data.sub_bots.connected}/${data.sub_bots.count} TRỰC TUYẾN</span>`;
                this.updateSubBotList(data.sub_bots);
                
                // Update feature toggles
                this.updateFeatureToggles(data.features);
            }

            updateSubBotList(subBots) {
                const subBotList = document.getElementById('subBotList');
                subBotList.innerHTML = '';
                for (let i = 0; i < subBots.count; i++) {
                    const item = document.createElement('div');
                    item.className = 'sub-bot-item';
                    item.innerHTML = `<div class="sub-bot-name">Acc Phụ ${i}</div><button class="sub-bot-reboot" onclick="rebootBot('sub_${i}')"><i class="fas fa-redo"></i></button>`;
                    subBotList.appendChild(item);
                }
            }

            updateFeatureToggles(features) {
                const spamToggle = document.getElementById('spamToggle');
                const autoWorkToggle = document.getElementById('autoWorkToggle');
                if (features.spam_enabled) {
                    spamToggle.classList.add('active');
                    spamToggle.innerHTML = '<i class="fas fa-power-off"></i><span>BẬT</span>';
                } else {
                    spamToggle.classList.remove('active');
                    spamToggle.innerHTML = '<i class="fas fa-power-off"></i><span>TẮT</span>';
                }
                if (features.auto_work_enabled) {
                    autoWorkToggle.classList.add('active');
                    autoWorkToggle.innerHTML = '<i class="fas fa-power-off"></i><span>BẬT</span>';
                } else {
                    autoWorkToggle.classList.remove('active');
                    autoWorkToggle.innerHTML = '<i class="fas fa-power-off"></i><span>TẮT</span>';
                }
                document.getElementById('spamMessage').value = features.spam_message;
                document.getElementById('spamDelay').value = features.spam_delay;
            }

            updateConnectionIndicator(data) {
                const connStatus = document.getElementById('connectionStatus');
                const totalBots = 2 + data.sub_bots.count;
                const connectedBots = (data.main_bot_1.connected ? 1 : 0) + (data.main_bot_2.connected ? 1 : 0) + data.sub_bots.connected;
                if (connectedBots === totalBots) {
                    connStatus.innerHTML = '<i class="fas fa-circle"></i><span>TẤT CẢ HỆ THỐNG TRỰC TUYẾN</span>';
                    connStatus.classList.add('online');
                } else {
                    connStatus.innerHTML = `<i class="fas fa-circle"></i><span>${connectedBots}/${totalBots} BOT TRỰC TUYẾN</span>`;
                    connStatus.classList.remove('online');
                }
            }
            
            async toggleAutoGrab(botId) {
                const data = await this.apiCall('/api/toggle_auto_grab', { bot_id: botId });
                if (data.success) {
                    this.logToTerminal(`Auto grab ${data.status ? 'bật' : 'tắt'} cho ${botId}`, 'success');
                    this.updateStatus();
                } else {
                    this.logToTerminal(`Lỗi toggle auto grab: ${data.message}`, 'error');
                }
            }

            async setHeartThreshold(botId, threshold) {
                const data = await this.apiCall('/api/set_heart_threshold', { bot_id: botId, threshold: parseInt(threshold) });
                if (data.success) {
                    this.logToTerminal(`Ngưỡng tim đặt thành ${threshold} cho ${botId}`, 'success');
                    this.updateStatus();
                } else {
                    this.logToTerminal(`Lỗi đặt ngưỡng tim: ${data.message}`, 'error');
                }
            }

            async sendMessage() {
                const message = document.getElementById('messageContent').value;
                if (!message.trim()) { this.logToTerminal('Tin nhắn không thể trống', 'warning'); return; }
                const data = await this.apiCall('/api/send_message', { message: message });
                if (data.success) {
                    this.logToTerminal(`${data.message}: "${message}"`, 'success');
                    document.getElementById('messageContent').value = '';
                } else {
                    this.logToTerminal(`Gửi tin nhắn thất bại: ${data.message}`, 'error');
                }
            }

            async sendQuickCommand(command) {
                const data = await this.apiCall('/api/send_quick_message', { message: command });
                if (data.success) this.logToTerminal(`${data.message}: "${command}"`, 'success');
                else this.logToTerminal(`Gửi lệnh nhanh thất bại: ${data.message}`, 'error');
            }

            async rebootBot(botId) {
                this.logToTerminal(`Đang khởi động lại ${botId}...`, 'info');
                const data = await this.apiCall('/api/reboot_bot', { bot_id: botId });
                if (data.success) this.logToTerminal(`${botId} khởi động lại thành công`, 'success');
                else this.logToTerminal(`Lỗi khởi động lại ${botId}: ${data.message}`, 'error');
            }

            async sendCardCode() {
                const payload = {
                    acc_index: parseInt(document.getElementById('cardAccIndex').value),
                    delay: parseFloat(document.getElementById('cardDelay').value),
                    prefix: document.getElementById('cardPrefix').value,
                    codes: document.getElementById('cardCodes').value
                };
                if (!payload.codes.trim()) { this.logToTerminal('Danh sách mã không thể trống', 'warning'); return; }
                const data = await this.apiCall('/api/send_card_code', payload);
                if (data.success) {
                    this.logToTerminal(data.message, 'success');
                    document.getElementById('cardCodes').value = '';
                } else {
                    this.logToTerminal(`Lỗi gửi mã card: ${data.message}`, 'error');
                }
            }

            async toggleSpam() {
                const data = await this.apiCall('/api/toggle_spam', {});
                if (data.success) {
                    this.logToTerminal(`Spam ${data.status ? 'bật' : 'tắt'}`, 'success');
                    this.updateStatus();
                } else {
                    this.logToTerminal(`Lỗi toggle spam: ${data.message}`, 'error');
                }
            }

            async setSpamConfig() {
                const payload = {
                    message: document.getElementById('spamMessage').value,
                    delay: parseInt(document.getElementById('spamDelay').value)
                };
                const data = await this.apiCall('/api/set_spam_config', payload);
                if (data.success) {
                    this.logToTerminal(`Cập nhật config spam: "${payload.message}" với delay ${payload.delay}s`, 'success');
                    this.updateStatus();
                } else {
                    this.logToTerminal(`Lỗi cập nhật config spam: ${data.message}`, 'error');
                }
            }

            async toggleAutoWork() {
                const data = await this.apiCall('/api/toggle_auto_work', {});
                if (data.success) {
                    this.logToTerminal(`Auto work ${data.status ? 'bật' : 'tắt'}`, 'success');
                    this.updateStatus();
                } else {
                    this.logToTerminal(`Lỗi toggle auto work: ${data.message}`, 'error');
                }
            }

            logToTerminal(msg, type = 'info') {
                const terminal = document.getElementById('terminal');
                const line = document.createElement('div');
                line.className = 'terminal-line';
                line.innerHTML = `<span class="timestamp">[${new Date().toLocaleTimeString()}]</span><span class="message ${type}">${msg}</span>`;
                terminal.appendChild(line);
                terminal.scrollTop = terminal.scrollHeight;
                if (terminal.children.length > 100) {
                    terminal.removeChild(terminal.children[0]);
                }
            }

            clearTerminal() {
                document.getElementById('terminal').innerHTML = `<div class="terminal-line"><span class="timestamp">[SYSTEM]</span><span class="message">Terminal cleared</span></div>`;
            }
        }

        // Initialize dashboard globally
        let dashboard = new DashboardController();

        // Global functions for button onclick handlers
        function toggleAutoGrab(id) { dashboard.toggleAutoGrab(id); }
        function setHeartThreshold(id, val) { dashboard.setHeartThreshold(id, val); }
        function sendMessage() { dashboard.sendMessage(); }
        function sendQuickCommand(cmd) { dashboard.sendQuickCommand(cmd); }
        function rebootBot(id) { dashboard.rebootBot(id); }
        function sendCardCode() { dashboard.sendCardCode(); }
        function toggleSpam() { dashboard.toggleSpam(); }
        function setSpamConfig() { dashboard.setSpamConfig(); }
        function toggleAutoWork() { dashboard.toggleAutoWork(); }
        function clearTerminal() { dashboard.clearTerminal(); }
    </script>
</body>
</html>
'''

def initialize_bots():
    """Initialize all bots when the app starts"""
    bot_controller.initialize_all_bots()

if __name__ == '__main__':
    logging.info("Starting Karuta Deep Control Center...")
    
    # Initialize bots
    initialize_bots()
    
    # Start monitoring thread
    threading.Thread(target=monitor_connections, daemon=True).start()
    logging.info("Connection monitoring started.")
    
    # Start spam thread
    bot_controller.start_spam()
    logging.info("Spam system initialized.")
    
    # Start auto work thread
    bot_controller.start_auto_work()
    logging.info("Auto work system initialized.")
    
    logging.info("Karuta Deep Control Center is ready! Access at http://localhost:5000")
    # For production, consider using a more robust WSGI server like gunicorn or waitress
    app.run(host="0.0.0.0", port=5000, debug=False)
}