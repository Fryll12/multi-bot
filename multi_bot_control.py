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
        self.bots = [None] * len(tokens) # Initialize list with placeholders
        
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

    def create_bot(self, token, bot_index=-1, is_main=False, is_main_2=False):
        try:
            bot = discum.Client(token=token, log=False)
            bot_type = "(Main 1)" if is_main else "(Main 2)" if is_main_2 else f"(Sub {bot_index})"
            
            @bot.gateway.command
            def on_ready(resp):
                if resp.event.ready:
                    user = resp.raw.get("user", {})
                    logging.info(f"Bot {user.get('username')}#{user.get('discriminator')} {bot_type} is ready.")

            if is_main:
                @bot.gateway.command
                def on_message_main(resp):
                    if not resp.event.message: return
                    msg = resp.parsed.auto()
                    author_id = msg.get("author", {}).get("id")
                    channel_id = msg.get("channel_id")
                    if author_id == self.karuta_id and channel_id == self.main_channel_id:
                        if "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and self.auto_grab_enabled:
                            self.last_drop_msg_id = msg.get("id")
                            # ... grab logic here ...

            threading.Thread(target=bot.gateway.run, daemon=True).start()
            return bot
        except Exception as e:
            logging.error(f"Error creating bot {bot_type}: {e}")
            return None

    def initialize_all_bots(self):
        with self.bots_lock:
            logging.info("Initializing/refreshing all bots...")
            if self.main_bot: self.main_bot.gateway.close()
            if self.main_bot_2: self.main_bot_2.gateway.close()
            for bot in self.bots:
                if bot: bot.gateway.close()
            
            time.sleep(2)

            self.main_bot = self.create_bot(self.main_token, is_main=True) if self.main_token else None
            self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True) if self.main_token_2 else None
            
            self.bots = [None] * len(self.tokens)
            for i, token in enumerate(self.tokens):
                if token.strip():
                    self.bots[i] = self.create_bot(token.strip(), i)
            logging.info("All bots initialization process completed.")

    def _spam_loop(self):
        logging.info("[Spam] Spam thread started.")
        while self.spam_enabled:
            if self.spam_message.strip():
                with self.bots_lock:
                    bots_to_spam = self.bots[:]
                for bot in bots_to_spam:
                    if not self.spam_enabled: break
                    if bot and bot.gateway.ws:
                        try:
                            bot.sendMessage(self.spam_channel_id, self.spam_message)
                            time.sleep(0.5)
                        except Exception: pass
            time.sleep(self.spam_delay)
        logging.info("[Spam] Spam thread finished.")

    def _auto_work_loop(self):
        logging.info("[Auto Work] Auto work thread started.")
        while self.auto_work_enabled:
            logging.info("[Auto Work] Starting new work cycle for all accounts...")
            for acc_index, token in enumerate(self.tokens):
                if not self.auto_work_enabled:
                    logging.info("[Auto Work] Cycle interrupted by user.")
                    break
                
                logging.info(f"[Auto Work] Starting work for account {acc_index}...")
                self._run_work_for_account(token.strip(), acc_index)
                if not self.auto_work_enabled: break
                time.sleep(10) # Delay between each account's work session
            
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
            bot = discum.Client(token=token, log={"console": False, "file": False})

            headers = {"Authorization": token, "Content-Type": "application/json"}
            step = {"value": 0}

            def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
                try:
                    payload = {"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "a", "data": {"component_type": 2, "custom_id": custom_id}}
                    r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
                    if r.status_code == 204: logging.info(f"{log_prefix} Click tick thành công!")
                    else: logging.error(f"{log_prefix} Click thất bại! Mã lỗi: {r.status_code}")
                except Exception as e:
                    logging.error(f"{log_prefix} Lỗi click tick: {str(e)}")

            @bot.gateway.command
            def on_message(resp):
                nonlocal step
                if not resp.event.message or step["value"] == 3: return
                m = resp.parsed.auto()
                if str(m.get('channel_id')) != self.work_channel_id: return
                author_id = str(m.get('author', {}).get('id', ''))
                if author_id != self.karuta_id: return

                guild_id = m.get('guild_id')
                embeds = m.get('embeds')

                if step["value"] == 0 and embeds:
                    desc = embeds[0].get('description', '')
                    card_codes = re.findall(r'\bv[a-zA-Z0-9]{6}\b', desc)
                    if len(card_codes) >= 10:
                        first_5, last_5 = card_codes[:5], card_codes[-5:]
                        logging.info(f"{log_prefix} Mã đầu: {', '.join(first_5)}")
                        logging.info(f"{log_prefix} Mã cuối: {', '.join(last_5)}")
                        for i, code in enumerate(last_5): bot.sendMessage(self.work_channel_id, f"kjw {code} {chr(97 + i)}"); time.sleep(1.5)
                        for i, code in enumerate(first_5): bot.sendMessage(self.work_channel_id, f"kjw {code} {chr(97 + i)}"); time.sleep(1.5)
                        time.sleep(1); bot.sendMessage(self.work_channel_id, "kn")
                        step["value"] = 1

                elif step["value"] == 1 and embeds:
                    desc = embeds[0].get('description', '')
                    lines = desc.split('\n')
                    if len(lines) >= 2:
                        match = re.search(r'\d+\.\s*`([^`]+)`', lines[1])
                        if match:
                            resource = match.group(1)
                            logging.info(f"{log_prefix} Tài nguyên chọn: {resource}")
                            time.sleep(2); bot.sendMessage(self.work_channel_id, f"kjn `{resource}` a b c d e")
                            time.sleep(1); bot.sendMessage(self.work_channel_id, "kw")
                            step["value"] = 2

                elif step["value"] == 2 and 'components' in m:
                    message_id = m['id']
                    application_id = m.get('application_id', self.karuta_id)
                    for comp_row in m.get('components', []):
                        for btn in comp_row.get('components', []):
                            if btn.get('type') == 2:
                                logging.info(f"{log_prefix} Phát hiện button, custom_id: {btn['custom_id']}")
                                click_tick(self.work_channel_id, message_id, btn['custom_id'], application_id, guild_id)
                                step["value"] = 3
                                bot.gateway.close()
                                return
            
            def start_work_thread():
                bot.gateway.run()

            logging.info(f"{log_prefix} Bắt đầu hoạt động...")
            threading.Thread(target=start_work_thread, daemon=True).start()
            time.sleep(4)
            if not bot.gateway.ws:
                logging.error(f"{log_prefix} Kết nối gateway thất bại. Hủy bỏ work.")
                return

            bot.sendMessage(self.work_channel_id, "kc o:ef")
            logging.info(f"{log_prefix} Gửi lệnh 'kc o:ef'...")

            timeout = time.time() + 90
            while step["value"] != 3 and time.time() < timeout: time.sleep(1)

            if step["value"] != 3: logging.warning(f"{log_prefix} Hết thời gian chờ.")
            else: logging.info(f"{log_prefix} Đã hoàn thành.")
            bot.gateway.close()
            
        except Exception as e:
            logging.error(f"{log_prefix} Xảy ra lỗi không mong muốn: {e}", exc_info=True)

    def toggle_feature(self, feature_name, enable, **kwargs):
        with self.feature_lock:
            if feature_name == "spam":
                if enable and not self.spam_enabled:
                    self.spam_message = kwargs.get('message', '')
                    self.spam_delay = kwargs.get('delay', 10)
                    self.spam_enabled = True
                    self.spam_thread = threading.Thread(target=self._spam_loop, daemon=True)
                    self.spam_thread.start()
                elif not enable and self.spam_enabled:
                    self.spam_enabled = False
                return self.spam_enabled
            
            elif feature_name == "auto_work":
                if enable and not self.auto_work_enabled:
                    self.auto_work_enabled = True
                    self.work_thread = threading.Thread(target=self._auto_work_loop, daemon=True)
                    self.work_thread.start()
                elif not enable and self.auto_work_enabled:
                    self.auto_work_enabled = False
                return self.auto_work_enabled
        return False

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
        'sub_bots': {'statuses': sub_bot_statuses, 'names': acc_names[:len(tokens)]},
        'features': {
            'auto_grab_enabled': bot_controller.auto_grab_enabled,
            'auto_grab_enabled_2': bot_controller.auto_grab_enabled_2,
            'spam_enabled': bot_controller.spam_enabled,
            'spam_message': bot_controller.spam_message,
            'spam_delay': bot_controller.spam_delay,
            'auto_work_enabled': bot_controller.auto_work_enabled,
        }
    })

@app.route('/api/initialize_bots', methods=['POST'])
def initialize_bots_endpoint():
    threading.Thread(target=bot_controller.initialize_all_bots).start()
    return jsonify({'success': True, 'message': 'Bot initialization process started.'})

@app.route('/api/toggle_feature', methods=['POST'])
def toggle_feature_endpoint():
    data = request.json
    feature = data.get('feature')
    enable = data.get('enable')
    params = data.get('params', {})
    
    if feature in ["spam", "auto_work"]:
        new_state = bot_controller.toggle_feature(feature, enable, **params)
        return jsonify({'success': True, 'newState': new_state})

    elif feature == "auto_grab_1":
        bot_controller.auto_grab_enabled = enable
        return jsonify({'success': True, 'newState': bot_controller.auto_grab_enabled})
    
    elif feature == "auto_grab_2":
        bot_controller.auto_grab_enabled_2 = enable
        return jsonify({'success': True, 'newState': bot_controller.auto_grab_enabled_2})
        
    return jsonify({'success': False, 'message': 'Invalid feature.'})

# --- HTML & JavaScript Template ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Deep - Control Center</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.1.1/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #101010; --bg-secondary: #181818; --bg-tertiary: #282828;
            --text-primary: #00ff00; --text-secondary: #00cc00; --border: #333;
            --success: #00ff00; --danger: #ff4040; --active-glow: 0 0 8px rgba(0, 255, 0, 0.7);
        }
        body { font-family: 'Courier New', monospace; background: var(--bg-primary); color: var(--text-primary); margin: 0; }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        .header h1 { font-size: 2.5rem; text-align: center; margin-bottom: 20px; text-shadow: var(--active-glow); }
        .grid-layout { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .card-title { font-size: 1.2rem; font-weight: bold; }
        .status-indicator { display: flex; align-items: center; gap: 8px; }
        .status-indicator.online { color: var(--success); }
        .status-indicator.offline { color: var(--danger); }
        .control-group { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;}
        .toggle-btn { padding: 8px 15px; cursor: pointer; border: 1px solid var(--border); background: var(--danger); color: white; border-radius: 5px; font-weight: bold; }
        .toggle-btn.active { background: var(--success); color: black; box-shadow: var(--active-glow); }
        .action-btn { padding: 10px 15px; cursor: pointer; border: 1px solid var(--text-primary); background: var(--bg-tertiary); color: var(--text-primary); border-radius: 5px; width: 100%; }
        .form-group { margin-bottom: 10px; }
        label { display: block; margin-bottom: 5px; color: var(--text-secondary); }
        input, textarea, select { width: 100%; padding: 8px; background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border); border-radius: 5px; }
        .sub-bot-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; margin-top: 15px; }
        .sub-bot-item { background: var(--bg-tertiary); padding: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        .sub-bot-status.online { color: var(--success); }
        .sub-bot-status.offline { color: var(--danger); }
    </style>
</head>
<body>
    <div class="container">
        <header class="header"><h1><i class="fas fa-terminal"></i> KARUTA DEEP CONTROL</h1></header>
        <div class="grid-layout">
            <div class="card" id="mainBotCard1"><div class="card-header"><div class="card-title"><i class="fas fa-crown"></i> ACC CHÍNH 1</div><div class="status-indicator offline" id="mainBot1Status"><i class="fas fa-circle"></i><span>NGOẠI TUYẾN</span></div></div></div>
            <div class="card" id="mainBotCard2"><div class="card-header"><div class="card-title"><i class="fas fa-crown"></i> ACC CHÍNH 2</div><div class="status-indicator offline" id="mainBot2Status"><i class="fas fa-circle"></i><span>NGOẠI TUYẾN</span></div></div></div>
        </div>
        <div class="card">
            <div class="card-header"><div class="card-title"><i class="fas fa-users"></i> ACC PHỤ</div><div class="status-indicator offline" id="subBotsStatus"><span>0/0 TRỰC TUYẾN</span></div></div>
            <div class="sub-bot-list" id="subBotList"></div>
            <button class="action-btn" onclick="dashboard.initializeBots()" style="margin-top: 15px;"><i class="fas fa-play"></i> KHỞI ĐỘNG / LÀM MỚI TẤT CẢ BOT</button>
        </div>
        <div class="grid-layout">
            <div class="card">
                <h3><i class="fas fa-comment-dots"></i> AUTO SPAM</h3>
                <div class="control-group"><label>Trạng thái</label><button class="toggle-btn" id="spamToggle" onclick="dashboard.toggleSpam()">TẮT</button></div>
                <div class="form-group"><label>Tin nhắn</label><textarea id="spamMessage" rows="2"></textarea></div>
                <div class="form-group"><label>Delay (giây)</label><input type="number" id="spamDelay" value="10"></div>
            </div>
            <div class="card">
                <h3><i class="fas fa-hammer"></i> AUTO WORK</h3>
                <div class="control-group"><label>Trạng thái</label><button class="toggle-btn" id="autoWorkToggle" onclick="dashboard.toggleAutoWork()">TẮT</button></div>
                <p style="font-size: 0.9rem; margin-top: 10px;">Tự động work cho tất cả acc phụ mỗi 12 tiếng.</p>
            </div>
        </div>
    </div>
    <script>
        class DashboardController {
            constructor() {
                this.statusUpdateInterval = null;
                this.init();
            }

            init() {
                this.startStatusUpdates();
            }

            startStatusUpdates() {
                this.updateStatus();
                this.statusUpdateInterval = setInterval(() => this.updateStatus(), 5000);
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
                    console.error(`API call to ${endpoint} failed:`, error);
                    return null;
                }
            }

            async updateStatus() {
                const data = await this.apiPost('/api/status');
                if (!data) return;
                
                this.updateBotCard('mainBot1Status', data.main_bot_1.connected);
                this.updateBotCard('mainBot2Status', data.main_bot_2.connected);
                this.updateSubBotList(data.sub_bots.statuses, data.sub_bots.names);
                this.updateFeatureToggles(data.features);
            }
            
            updateBotCard(elementId, isConnected) {
                const statusEl = document.getElementById(elementId);
                if (!statusEl) return;
                statusEl.className = `status-indicator ${isConnected ? 'online' : 'offline'}`;
                statusEl.innerHTML = `<i class="fas fa-circle"></i><span>${isConnected ? 'TRỰC TUYẾN' : 'NGOẠI TUYẾN'}</span>`;
            }

            updateSubBotList(statuses = [], names = []) {
                const subBotList = document.getElementById('subBotList');
                if (!subBotList) return;
                subBotList.innerHTML = '';
                let connectedCount = 0;
                
                statuses.forEach((isOnline, i) => {
                    if (isOnline) connectedCount++;
                    const item = document.createElement('div');
                    item.className = 'sub-bot-item';
                    item.innerHTML = `
                        <div class="sub-bot-name">Acc ${i} (${names[i] || 'N/A'})</div>
                        <div class="sub-bot-status ${isOnline ? 'online' : 'offline'}">
                            <i class="fas fa-circle"></i>
                            <span>${isOnline ? 'TRỰC TUYẾN' : 'NGOẠI TUYẾN'}</span>
                        </div>`;
                    subBotList.appendChild(item);
                });
                document.getElementById('subBotsStatus').innerHTML = `<span>${connectedCount}/${statuses.length || names.length} TRỰC TUYẾN</span>`;
            }

            updateFeatureToggles(features) {
                this.updateToggleButton('spamToggle', features.spam_enabled);
                document.getElementById('spamMessage').value = features.spam_message;
                document.getElementById('spamDelay').value = features.spam_delay;
                this.updateToggleButton('autoWorkToggle', features.auto_work_enabled);
            }

            updateToggleButton(buttonId, isEnabled) {
                const button = document.getElementById(buttonId);
                if (!button) return;
                if (isEnabled) {
                    button.classList.add('active');
                    button.textContent = 'BẬT';
                } else {
                    button.classList.remove('active');
                    button.textContent = 'TẮT';
                }
            }

            async initializeBots() {
                console.log('Initializing bots...');
                await this.apiPost('/api/initialize_bots');
                setTimeout(() => this.updateStatus(), 3000);
            }

            async toggleFeature(featureName, buttonId, params = {}) {
                const button = document.getElementById(buttonId);
                const wantsToEnable = !button.classList.contains('active');
                
                const data = await this.apiPost('/api/toggle_feature', { feature: featureName, enable: wantsToEnable, params });
                
                if (data && data.success) {
                    this.updateToggleButton(buttonId, data.newState);
                } else {
                    this.updateStatus();
                }
            }

            async toggleSpam() {
                const button = document.getElementById('spamToggle');
                const message = document.getElementById('spamMessage').value;
                if (!button.classList.contains('active') && !message.trim()) {
                    alert('Vui lòng nhập tin nhắn spam trước khi bật.');
                    return;
                }
                const params = { message, delay: parseInt(document.getElementById('spamDelay').value, 10) };
                await this.toggleFeature('spam', 'spamToggle', params);
            }

            async toggleAutoWork() {
                await this.toggleFeature('auto_work', 'autoWorkToggle');
            }
        }
        const dashboard = new DashboardController();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # Start the Flask app in a separate thread to be non-blocking
    app_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=os.getenv('PORT', 5000), use_reloader=False, debug=False),
        daemon=True
    )
    app_thread.start()
    
    # Optional: Initial bot startup
    # logging.info("Starting initial bot setup...")
    # bot_controller.initialize_all_bots()

    # Keep the main thread alive to allow daemon threads to run
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down application...")