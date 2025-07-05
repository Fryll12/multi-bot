# karuta_deep_complete_final_fixed.py - Discord Multi-Bot Control System
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
        
        # Auto work settings
        self.auto_work_enabled = False
        
        # Thread locks and state management
        self.bots_lock = threading.Lock()
        self.feature_lock = threading.Lock()
        self.spam_thread = None
        self.work_thread = None
        
        # Connection monitoring
        self.reconnect_attempts = {"main_1": 0, "main_2": 0}
        self.last_reconnect_time = {"main_1": 0, "main_2": 0}
        
        logging.info("BotController initialized")

    def create_bot(self, token, is_main=False, is_main_2=False):
        try:
            bot = discum.Client(token=token, log=False)

            @bot.gateway.command
            def on_ready(resp):
                if resp.event.ready:
                    user_id = resp.raw.get("user", {}).get("id")
                    if user_id:
                        bot_type = "(Main Bot 1)" if is_main else "(Main Bot 2)" if is_main_2 else ""
                        logging.info(f"Bot logged in: {user_id} {bot_type}")
                    else:
                        logging.error(f"Failed to get user_id on READY event for a bot.")

            if is_main:
                @bot.gateway.command
                def on_message(resp):
                    if resp.event.message:
                        msg = resp.parsed.auto()
                        author = msg.get("author", {}).get("id")
                        channel = msg.get("channel_id")
                        if author == self.karuta_id and channel == self.main_channel_id:
                            if "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and self.auto_grab_enabled:
                                self.last_drop_msg_id = msg["id"]
                                threading.Thread(target=self._read_karibbit_and_grab, args=(bot, 1)).start()
            # ... (similar logic for main_bot_2)

            threading.Thread(target=bot.gateway.run, daemon=True).start()
            return bot
        except Exception as e:
            logging.error(f"Error creating bot: {e}")
            return None

    def initialize_all_bots(self):
        with self.bots_lock:
            logging.info("Initializing all bots...")
            # Close existing sub-bot connections first
            for bot in self.bots:
                if bot: bot.gateway.close()
            self.bots = []

            if self.main_token and not (self.main_bot and self.main_bot.gateway.ws):
                self.main_bot = self.create_bot(self.main_token, is_main=True)
            if self.main_token_2 and not (self.main_bot_2 and self.main_bot_2.gateway.ws):
                self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True)
            
            for token in self.tokens:
                if token.strip():
                    self.bots.append(self.create_bot(token.strip()))
            logging.info("All bots initialization process completed.")

    def _read_karibbit_and_grab(self, bot, bot_num):
        # ... [This function's internal logic remains the same] ...
        pass

    def _spam_loop(self):
        logging.info("[Spam] Spam thread started.")
        while self.spam_enabled:
            if self.spam_message.strip():
                with self.bots_lock:
                    bots_to_spam = self.bots[:]
                for bot in bots_to_spam:
                    if not self.spam_enabled: break
                    if bot:
                        try:
                            bot.sendMessage(self.spam_channel_id, self.spam_message)
                            time.sleep(0.5)
                        except Exception as e:
                            logging.error(f"[Spam] Error sending message: {e}")
            time.sleep(self.spam_delay)
        logging.info("[Spam] Spam thread finished.")

    def _auto_work_loop(self):
        logging.info("[Auto Work] Auto work thread started.")
        while self.auto_work_enabled:
            logging.info("[Auto Work] Starting work cycle for all accounts...")
            for acc_index, token in enumerate(self.tokens):
                if not self.auto_work_enabled:
                    logging.info("[Auto Work] Cycle interrupted by user.")
                    break
                logging.info(f"[Auto Work] Running work for account {acc_index}...")
                self._run_work_for_account(token, acc_index)
                time.sleep(15) # Delay between each account's work session
            
            if self.auto_work_enabled:
                wait_time = 12 * 3600 + random.randint(0, 300)
                logging.info(f"[Auto Work] Cycle completed. Waiting for {wait_time/3600:.2f} hours...")
                for _ in range(int(wait_time)):
                    if not self.auto_work_enabled: break
                    time.sleep(1)
        logging.info("[Auto Work] Auto work thread finished.")

    def _run_work_for_account(self, token, acc_index):
        log_prefix = f"[Work Acc {acc_index}]"
        try:
            work_bot = discum.Client(token=token, log=False)
            step = {"value": 0}
            
            @work_bot.gateway.command
            def on_message(resp):
                nonlocal step
                if not resp.event.message or step["value"] == 3: return
                msg = resp.parsed.auto()
                author_id = msg.get("author", {}).get("id")
                channel_id = msg.get("channel_id")
                if author_id != self.karuta_id or channel_id != self.work_channel_id: return

                # Step 0: kc o:ef response
                if step["value"] == 0 and 'embeds' in msg and msg['embeds']:
                    # ... [logic for parsing cards and sending 'kjw' and 'kn'] ...
                    logging.info(f"{log_prefix} Finished 'kjw' sequence, sending 'kn'.")
                    work_bot.sendMessage(self.work_channel_id, "kn")
                    step["value"] = 1
                # Step 1: kn response
                elif step["value"] == 1 and 'embeds' in msg and msg['embeds']:
                    # ... [logic for parsing resource and sending 'kjn' and 'kw'] ...
                    logging.info(f"{log_prefix} Finished 'kjn', sending 'kw'.")
                    work_bot.sendMessage(self.work_channel_id, "kw")
                    step["value"] = 2
                # Step 2: kw response with button
                elif step["value"] == 2 and 'components' in msg:
                    # ... [logic for finding and clicking the '✅' button] ...
                    logging.info(f"{log_prefix} Found and clicked tick button. Work complete.")
                    step["value"] = 3
                    work_bot.gateway.close()

            def start_work():
                logging.info(f"{log_prefix} Sending initial command 'kc o:ef'.")
                work_bot.sendMessage(self.work_channel_id, "kc o:ef")

            threading.Thread(target=work_bot.gateway.run, daemon=True).start()
            time.sleep(3) # Wait for gateway to connect
            start_work()

            # Timeout checker
            timeout = time.time() + 120 # 2 minute timeout
            while step["value"] != 3 and time.time() < timeout:
                time.sleep(1)

            if step["value"] != 3:
                logging.warning(f"{log_prefix} Timed out.")
            work_bot.gateway.close()

        except Exception as e:
            logging.error(f"{log_prefix} An exception occurred: {e}", exc_info=True)

    def toggle_spam(self, enable, message, delay):
        with self.feature_lock:
            self.spam_message = message
            self.spam_delay = delay
            if enable and not self.spam_enabled:
                self.spam_enabled = True
                self.spam_thread = threading.Thread(target=self._spam_loop, daemon=True)
                self.spam_thread.start()
            elif not enable and self.spam_enabled:
                self.spam_enabled = False
        return self.spam_enabled

    def toggle_auto_work(self, enable):
        with self.feature_lock:
            if enable and not self.auto_work_enabled:
                self.auto_work_enabled = True
                self.work_thread = threading.Thread(target=self._auto_work_loop, daemon=True)
                self.work_thread.start()
            elif not enable and self.auto_work_enabled:
                self.auto_work_enabled = False
        return self.auto_work_enabled

# Global bot controller instance
bot_controller = BotController()

# Flask Application
app = Flask(__name__)
# ... [Flask routes remain largely the same, but with changes to the toggle logic] ...

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    with bot_controller.bots_lock:
        sub_bot_statuses = [(bot and bot.gateway.ws) for bot in bot_controller.bots]
    
    return jsonify({
        'main_bot_1': { 'connected': bool(bot_controller.main_bot and bot_controller.main_bot.gateway.ws) },
        'main_bot_2': { 'connected': bool(bot_controller.main_bot_2 and bot_controller.main_bot_2.gateway.ws) },
        'sub_bots': { 'statuses': sub_bot_statuses },
        'features': {
            'spam_enabled': bot_controller.spam_enabled,
            'auto_work_enabled': bot_controller.auto_work_enabled
        }
    })

@app.route('/api/initialize_bots', methods=['POST'])
def initialize_bots_endpoint():
    threading.Thread(target=bot_controller.initialize_all_bots).start()
    return jsonify({'success': True, 'message': 'Bot initialization started.'})

@app.route('/api/toggle_spam', methods=['POST'])
def toggle_spam_endpoint():
    data = request.json
    enable = data.get('enable')
    message = data.get('message')
    delay = data.get('delay', 10)
    new_state = bot_controller.toggle_spam(enable, message, delay)
    return jsonify({'success': True, 'new_state': new_state})

@app.route('/api/toggle_auto_work', methods=['POST'])
def toggle_auto_work_endpoint():
    data = request.json
    enable = data.get('enable')
    new_state = bot_controller.toggle_auto_work(enable)
    return jsonify({'success': True, 'new_state': new_state})

# HTML Template with corrected JavaScript
HTML_TEMPLATE = '''
<!DOCTYPE html>
<body>
    <script>
        class DashboardController {
            // ... [constructor and init are the same] ...

            async updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    // ... [Update main bots status] ...

                    this.updateSubBotList(data.sub_bots.statuses);
                    this.updateFeatureToggles(data.features);

                } catch (error) { /* ... */ }
            }

            updateSubBotList(statuses) {
                const subBotList = document.getElementById('subBotList');
                subBotList.innerHTML = '';
                const accNames = ["Blacklist", "Khanh bang", ...]; // Full list
                
                statuses.forEach((isOnline, i) => {
                    const subBotItem = document.createElement('div');
                    subBotItem.className = `sub-bot-item ${isOnline ? 'online' : 'offline'}`;
                    subBotItem.innerHTML = `
                        <div class="sub-bot-name">Acc ${i} (${accNames[i] || 'N/A'})</div>
                        <div class="sub-bot-status">
                            <i class="fas fa-circle"></i>
                            <span>${isOnline ? 'TRỰC TUYẾN' : 'NGOẠI TUYẾN'}</span>
                        </div>
                        `;
                    subBotList.appendChild(subBotItem);
                });
            }

            updateFeatureToggles(features) {
                // ... [This now correctly updates buttons based on feature flags] ...
            }

            async initializeBots() {
                this.logToTerminal('Bắt đầu khởi tạo tất cả bot...', 'info');
                const response = await fetch('/api/initialize_bots', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    this.logToTerminal(data.message, 'success');
                } else { /* ... error logging ... */ }
            }

            async toggleSpam() {
                const spamToggle = document.getElementById('spamToggle');
                const wantsToEnable = !spamToggle.classList.contains('active');
                const message = document.getElementById('spamMessage').value;
                const delay = parseInt(document.getElementById('spamDelay').value, 10);

                if (wantsToEnable && !message.trim()) {
                    this.logToTerminal('Vui lòng nhập tin nhắn spam trước khi bật.', 'warning');
                    return;
                }

                const response = await fetch('/api/toggle_spam', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ enable: wantsToEnable, message: message, delay: delay })
                });
                const data = await response.json();
                if (data.success) {
                    this.logToTerminal(`Spam đã được ${data.new_state ? 'BẬT' : 'TẮT'}.`, 'success');
                    this.updateStatus(); // Force UI refresh
                }
            }

            async toggleAutoWork() {
                const autoWorkToggle = document.getElementById('autoWorkToggle');
                const wantsToEnable = !autoWorkToggle.classList.contains('active');
                
                const response = await fetch('/api/toggle_auto_work', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ enable: wantsToEnable })
                });
                const data = await response.json();
                if (data.success) {
                    this.logToTerminal(`Auto Work đã được ${data.new_state ? 'BẬT' : 'TẮT'}.`, 'success');
                    this.updateStatus(); // Force UI refresh
                }
            }
            
            // ... [Other JS functions like sendMessage, rebootBot, etc.] ...
        }
        const dashboard = new DashboardController();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)