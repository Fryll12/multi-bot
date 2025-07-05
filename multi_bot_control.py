# karuta_deep_complete_final_fixed_v2.py - Discord Multi-Bot Control System
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
        
        # Feature settings
        self.auto_grab_enabled = False
        self.auto_grab_enabled_2 = False
        self.heart_threshold = 50
        self.heart_threshold_2 = 50
        self.last_drop_msg_id = ""
        self.spam_enabled = False
        self.spam_message = ""
        self.spam_delay = 10
        self.auto_work_enabled = False
        
        # Thread locks and state management
        self.bots_lock = threading.Lock()
        self.feature_lock = threading.Lock() # Lock for toggling features
        self.spam_thread = None
        self.work_thread = None
        
        logging.info("BotController initialized")

    def create_bot(self, token, is_main=False, is_main_2=False):
        try:
            bot = discum.Client(token=token, log=False)
            bot_type = "(Main 1)" if is_main else "(Main 2)" if is_main_2 else "(Sub)"
            
            @bot.gateway.command
            def on_ready(resp):
                if resp.event.ready:
                    user = resp.raw.get("user", {})
                    logging.info(f"Bot {user.get('username')}#{user.get('discriminator')} {bot_type} is ready.")

            if is_main:
                @bot.gateway.command
                def on_message_main(resp):
                    if resp.event.message:
                        msg = resp.parsed.auto()
                        author_id = msg.get("author", {}).get("id")
                        channel_id = msg.get("channel_id")
                        if author_id == self.karuta_id and channel_id == self.main_channel_id:
                            if "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and self.auto_grab_enabled:
                                self.last_drop_msg_id = msg.get("id")
                                threading.Thread(target=self._read_karibbit_and_grab, args=(bot, 1)).start()

            threading.Thread(target=bot.gateway.run, daemon=True).start()
            return bot
        except Exception as e:
            logging.error(f"Error creating bot: {e}")
            return None

    def initialize_all_bots(self):
        with self.bots_lock:
            logging.info("Initializing all bots...")
            # Close existing sub-bot connections first to prevent duplicates
            for bot in self.bots:
                if bot: bot.gateway.close()
            self.bots = []

            # Check and initialize main bots if they are not connected
            if self.main_token and not (self.main_bot and self.main_bot.gateway.ws):
                self.main_bot = self.create_bot(self.main_token, is_main=True)
            if self.main_token_2 and not (self.main_bot_2 and self.main_bot_2.gateway.ws):
                self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True)
            
            # Initialize sub bots
            for token in self.tokens:
                if token.strip():
                    self.bots.append(self.create_bot(token.strip()))
            logging.info("All bots initialization process completed.")

    def _read_karibbit_and_grab(self, bot, bot_num):
        # This function's internal logic remains the same
        pass

    def _spam_loop(self):
        logging.info("[Spam] Spam thread started.")
        while True:
            with self.feature_lock:
                if not self.spam_enabled:
                    break
                spam_message = self.spam_message
                spam_delay = self.spam_delay
            
            if spam_message.strip():
                with self.bots_lock:
                    current_bots = self.bots[:]
                for bot in current_bots:
                    if not self.spam_enabled: break
                    if bot and bot.gateway.ws:
                        try:
                            bot.sendMessage(self.spam_channel_id, spam_message)
                            time.sleep(0.5)
                        except Exception as e:
                            logging.error(f"[Spam] Error sending message: {e}")
            time.sleep(spam_delay)
        logging.info("[Spam] Spam thread finished.")

    def _auto_work_loop(self):
        logging.info("[Auto Work] Auto work thread started.")
        while True:
            with self.feature_lock:
                if not self.auto_work_enabled:
                    break
            
            logging.info("[Auto Work] Starting new work cycle for all accounts...")
            for acc_index, token in enumerate(self.tokens):
                if not self.auto_work_enabled:
                    logging.info("[Auto Work] Cycle interrupted by user.")
                    break
                
                logging.info(f"[Auto Work] Starting work for account {acc_index}...")
                self._run_work_for_account(token, acc_index)
                time.sleep(15)
            
            if self.auto_work_enabled:
                wait_time = 12 * 3600 + random.randint(0, 300)
                logging.info(f"[Auto Work] Cycle completed. Waiting for {wait_time/3600:.2f} hours...")
                for _ in range(wait_time):
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
                
                if step["value"] == 0 and 'embeds' in msg and msg['embeds']:
                    desc = msg['embeds'][0].get('description', '')
                    card_codes = re.findall(r'\bv[a-zA-Z0-9]{6}\b', desc)
                    if len(card_codes) >= 10:
                        first_5, last_5 = card_codes[:5], card_codes[-5:]
                        for i, code in enumerate(last_5):
                            time.sleep(1.5); work_bot.sendMessage(self.work_channel_id, f"kjw {code} {chr(97 + i)}")
                        for i, code in enumerate(first_5):
                            time.sleep(1.5); work_bot.sendMessage(self.work_channel_id, f"kjw {code} {chr(97 + i)}")
                        time.sleep(1); work_bot.sendMessage(self.work_channel_id, "kn")
                        step["value"] = 1
                elif step["value"] == 1 and 'embeds' in msg and msg['embeds']:
                    desc = msg['embeds'][0].get('description', '')
                    match = re.search(r'\d+\.\s*`([^`]+)`', desc.split('\n')[1] if len(desc.split('\n')) > 1 else "")
                    if match:
                        resource = match.group(1)
                        time.sleep(2); work_bot.sendMessage(self.work_channel_id, f"kjn `{resource}` a b c d e")
                        time.sleep(1); work_bot.sendMessage(self.work_channel_id, "kw")
                        step["value"] = 2
                elif step["value"] == 2 and 'components' in msg:
                    for comp_row in msg.get('components', []):
                        for btn in comp_row.get('components', []):
                            if btn.get('type') == 2:
                                work_bot.click(channel_id=channel_id, message_id=msg['id'], custom_id=btn['custom_id'], guild_id=msg.get('guild_id'))
                                logging.info(f"{log_prefix} Clicked work button. Work complete.")
                                step["value"] = 3
                                work_bot.gateway.close()
                                return

            def start_work_thread():
                work_bot.gateway.run()

            threading.Thread(target=start_work_thread, daemon=True).start()
            time.sleep(4) # Wait for gateway to connect
            logging.info(f"{log_prefix} Sending initial command 'kc o:ef'.")
            work_bot.sendMessage(self.work_channel_id, "kc o:ef")
            
            timeout = time.time() + 120 # 2 minute timeout
            while step["value"] != 3 and time.time() < timeout:
                time.sleep(1)
            
            if step["value"] != 3: logging.warning(f"{log_prefix} Timed out.")
            work_bot.gateway.close()

        except Exception as e:
            logging.error(f"{log_prefix} An exception occurred: {e}", exc_info=True)

    def toggle_feature(self, feature_name, enable, **kwargs):
        with self.feature_lock:
            if feature_name == "spam":
                current_state = self.spam_enabled
                if enable and not current_state:
                    self.spam_message = kwargs.get('message', '')
                    self.spam_delay = kwargs.get('delay', 10)
                    self.spam_enabled = True
                    self.spam_thread = threading.Thread(target=self._spam_loop, daemon=True)
                    self.spam_thread.start()
                elif not enable and current_state:
                    self.spam_enabled = False
                return self.spam_enabled
            
            elif feature_name == "auto_work":
                current_state = self.auto_work_enabled
                if enable and not current_state:
                    self.auto_work_enabled = True
                    self.work_thread = threading.Thread(target=self._auto_work_loop, daemon=True)
                    self.work_thread.start()
                elif not enable and current_state:
                    self.auto_work_enabled = False
                return self.auto_work_enabled
        return False

# Global bot controller instance
bot_controller = BotController()
app = Flask(__name__)

# --- API Endpoints ---
@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    with bot_controller.bots_lock:
        sub_bot_statuses = [(bot and bot.gateway.ws is not None) for bot in bot_controller.bots]
    
    return jsonify({
        'main_bot_1': {'connected': bool(bot_controller.main_bot and bot_controller.main_bot.gateway.ws)},
        'main_bot_2': {'connected': bool(bot_controller.main_bot_2 and bot_controller.main_bot_2.gateway.ws)},
        'sub_bots': {'statuses': sub_bot_statuses},
        'features': {
            'spam_enabled': bot_controller.spam_enabled,
            'spam_message': bot_controller.spam_message,
            'spam_delay': bot_controller.spam_delay,
            'auto_work_enabled': bot_controller.auto_work_enabled
        }
    })

@app.route('/api/initialize_bots', methods=['POST'])
def initialize_bots_endpoint():
    threading.Thread(target=bot_controller.initialize_all_bots).start()
    return jsonify({'success': True, 'message': 'Bot initialization process started.'})

@app.route('/api/toggle_feature', methods=['POST'])
def toggle_feature_endpoint():
    data = request.json
    feature_name = data.get('feature')
    enable = data.get('enable')
    kwargs = data.get('params', {})
    new_state = bot_controller.toggle_feature(feature_name, enable, **kwargs)
    return jsonify({'success': True, 'new_state': new_state})

# ... other endpoints for sending messages, etc. can be added here ...

# --- HTML & JavaScript Template ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Deep - Control Center</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        /* ... CSS code remains unchanged ... */
        .sub-bot-item.online .sub-bot-status { color: var(--success); }
        .sub-bot-item.offline .sub-bot-status { color: var(--danger-red); }
    </style>
</head>
<body>
    <div class="sub-bots-section">
        <div class="sub-bot-list" id="subBotList"></div>
        <button class="action-btn" onclick="dashboard.initializeBots()" style="margin-top: 15px;">
            <i class="fas fa-play"></i> KHỞI ĐỘNG/LÀM MỚI TẤT CẢ BOT
        </button>
    </div>
    <script>
        class DashboardController {
            constructor() {
                this.statusUpdateInterval = null;
                this.accNames = ["Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan", "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent"];
                this.init();
            }

            init() {
                this.startStatusUpdates();
                this.logToTerminal('System initialized successfully.', 'success');
            }

            startStatusUpdates() {
                this.updateStatus();
                this.statusUpdateInterval = setInterval(() => this.updateStatus(), 5000);
            }

            async updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    if (!response.ok) throw new Error('Network response was not ok.');
                    const data = await response.json();
                    
                    this.updateBotCard('mainBot1Status', data.main_bot_1.connected);
                    this.updateBotCard('mainBot2Status', data.main_bot_2.connected);
                    this.updateSubBotList(data.sub_bots.statuses);
                    this.updateFeatureToggles(data.features);
                } catch (error) {
                    this.logToTerminal('Failed to update status: ' + error.message, 'error');
                }
            }
            
            updateBotCard(elementId, isConnected) {
                const statusEl = document.getElementById(elementId);
                if (!statusEl) return;
                const cardEl = statusEl.closest('.bot-card');
                if (isConnected) {
                    statusEl.innerHTML = '<i class="fas fa-circle"></i><span>TRỰC TUYẾN</span>';
                    statusEl.classList.add('online');
                    cardEl.style.borderColor = 'var(--primary-green)';
                } else {
                    statusEl.innerHTML = '<i class="fas fa-circle"></i><span>NGOẠI TUYẾN</span>';
                    statusEl.classList.remove('online');
                    cardEl.style.borderColor = 'var(--danger-red)';
                }
            }

            updateSubBotList(statuses) {
                const subBotList = document.getElementById('subBotList');
                if (!subBotList) return;
                subBotList.innerHTML = '';
                let connectedCount = 0;
                
                statuses.forEach((isOnline, i) => {
                    if (isOnline) connectedCount++;
                    const subBotItem = document.createElement('div');
                    subBotItem.className = `sub-bot-item ${isOnline ? 'online' : 'offline'}`;
                    subBotItem.innerHTML = `
                        <div class="sub-bot-name">Acc ${i} (${this.accNames[i] || 'N/A'})</div>
                        <div class="sub-bot-status">
                            <i class="fas fa-circle"></i>
                            <span>${isOnline ? 'TRỰC TUYẾN' : 'NGOẠI TUYẾN'}</span>
                        </div>
                    `;
                    subBotList.appendChild(subBotItem);
                });

                const subBotsStatus = document.getElementById('subBotsStatus');
                if (subBotsStatus) {
                    subBotsStatus.innerHTML = `<i class="fas fa-circle"></i><span>${connectedCount}/${statuses.length} TRỰC TUYẾN</span>`;
                }
            }

            updateFeatureToggles(features) {
                this.updateToggleButton('spamToggle', features.spam_enabled);
                this.updateToggleButton('autoWorkToggle', features.auto_work_enabled);
                document.getElementById('spamMessage').value = features.spam_message;
                document.getElementById('spamDelay').value = features.spam_delay;
            }

            updateToggleButton(elementId, isEnabled) {
                const button = document.getElementById(elementId);
                if (!button) return;
                if (isEnabled) {
                    button.classList.add('active');
                    button.innerHTML = '<i class="fas fa-power-off"></i><span>BẬT</span>';
                } else {
                    button.classList.remove('active');
                    button.innerHTML = '<i class="fas fa-power-off"></i><span>TẮT</span>';
                }
            }

            async initializeBots() {
                this.logToTerminal('Starting initialization of all bots...', 'info');
                await this.apiPost('/api/initialize_bots');
                this.logToTerminal('Initialization command sent.', 'success');
                setTimeout(() => this.updateStatus(), 2000); // Poll for status after a delay
            }

            async toggleFeature(featureName, buttonId, params = {}) {
                const button = document.getElementById(buttonId);
                if (!button) return;
                const wantsToEnable = !button.classList.contains('active');

                this.logToTerminal(`${wantsToEnable ? 'Enabling' : 'Disabling'} ${featureName}...`, 'info');
                const data = await this.apiPost('/api/toggle_feature', { feature: featureName, enable: wantsToEnable, params });
                
                if (data && data.success) {
                    this.logToTerminal(`${featureName} has been ${data.new_state ? 'ENABLED' : 'DISABLED'}.`, 'success');
                    this.updateToggleButton(buttonId, data.new_state);
                } else {
                    this.logToTerminal(`Failed to toggle ${featureName}.`, 'error');
                    this.updateStatus(); // Re-sync with server state on failure
                }
            }

            async toggleSpam() {
                const message = document.getElementById('spamMessage').value;
                const delay = parseInt(document.getElementById('spamDelay').value, 10);
                if (!document.getElementById('spamToggle').classList.contains('active') && !message.trim()) {
                    this.logToTerminal('Please enter a spam message before enabling.', 'warning');
                    return;
                }
                await this.toggleFeature('spam', 'spamToggle', { message, delay });
            }

            async toggleAutoWork() {
                await this.toggleFeature('auto_work', 'autoWorkToggle');
            }

            async apiPost(endpoint, body = {}) {
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    if (!response.ok) throw new Error(`Server responded with ${response.status}`);
                    return await response.json();
                } catch (error) {
                    this.logToTerminal(`API call to ${endpoint} failed: ${error.message}`, 'error');
                    return null;
                }
            }

            logToTerminal(message, type = 'info') {
                const terminal = document.getElementById('terminal');
                if (!terminal) return;
                const timestamp = new Date().toLocaleTimeString();
                const line = document.createElement('div');
                line.className = 'terminal-line';
                line.innerHTML = `<span class="timestamp">[${timestamp}]</span> <span class="message ${type}">${message}</span>`;
                terminal.appendChild(line);
                terminal.scrollTop = terminal.scrollHeight;
                if (terminal.children.length > 100) {
                    terminal.removeChild(terminal.children[0]);
                }
            }
            
            clearTerminal() {
                document.getElementById('terminal').innerHTML = '';
            }
        }

        const dashboard = new DashboardController();
        // Event listeners can be added here if needed, e.g., for quick command buttons
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    logging.info("Starting Karuta Deep Control Center...")
    # Run Flask app in a separate thread
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()
    logging.info("Web server started.")
    # Initial bot startup can be done here if desired
    # bot_controller.initialize_all_bots()