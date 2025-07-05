#!/usr/bin/env python3
"""
Discord Bot Manager - Complete System
Hệ thống quản lý Discord bot Karuta hoàn chỉnh với web interface và auto work logic

Usage:
    python discord_bot_manager_complete.py

Web Interface: http://localhost:3000
"""

import discum
import threading
import time
import os
import random
import re
import requests
import logging
import json
import signal
import sys
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()

# --- CẤU HÌNH ---
MAIN_TOKEN = os.getenv("MAIN_TOKEN")
MAIN_TOKEN_2 = os.getenv("MAIN_TOKEN_2")
TOKENS = os.getenv("TOKENS").split(",") if os.getenv("TOKENS") else []

MAIN_CHANNEL_ID = "1386973916563767396"
OTHER_CHANNEL_ID = "1387406577040101417"
KTB_CHANNEL_ID = "1376777071279214662"
SPAM_CHANNEL_ID = "1388802151723302912"
WORK_CHANNEL_ID = "1389250541590413363"
KARUTA_ID = "646937666251915264"
KARIBBIT_ID = "1274445226064220273"

# Auto work settings
AUTO_WORK_DELAY_BETWEEN_ACC = 10  # Delay giữa các account (giây)
AUTO_WORK_DELAY_AFTER_ALL = 44100  # Delay sau khi hoàn thành tất cả account (12.25 giờ)
AUTO_WORK_TIMEOUT = 90  # Timeout cho mỗi account (giây)

# Account names
ACC_NAMES = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker", 
    "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Silent",
]

class CompleteDiscordBotManager:
    def __init__(self):
        self.main_token = MAIN_TOKEN
        self.main_token_2 = MAIN_TOKEN_2
        self.tokens = TOKENS
        self.acc_names = ACC_NAMES
        
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
        
        # Enhanced Auto work settings
        self.auto_work_enabled = False
        self.auto_work_thread = None
        self.auto_work_running = False
        self.auto_work_stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "current_account": 0,
            "last_run_time": None,
            "next_run_time": None
        }
        
        # Logs
        self.logs = []
        self.max_logs = 1000
        
        # Thread locks
        self.bots_lock = threading.Lock()
        self.work_lock = threading.Lock()
        self.logs_lock = threading.Lock()
        
        # Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'discord_bot_manager_secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self.setup_routes()
        self.setup_socketio()
        
        logging.info("Complete Discord Bot Manager initialized")

    def add_log(self, level, message, bot_id=None):
        """Add log entry"""
        with self.logs_lock:
            log_entry = {
                "id": f"{time.time()}_{random.randint(1000, 9999)}",
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
                "bot_id": bot_id
            }
            self.logs.insert(0, log_entry)
            
            # Keep only last max_logs entries
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[:self.max_logs]
            
            # Emit to web interface
            try:
                self.socketio.emit('log', log_entry)
            except:
                pass
            
            # Also log to console
            log_msg = f"[{bot_id}] {message}" if bot_id else message
            if level == "error":
                logging.error(log_msg)
            elif level == "warning":
                logging.warning(log_msg)
            else:
                logging.info(log_msg)

    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            return render_template_string(self.get_html_template())
        
        @self.app.route('/api/bots/status')
        def get_bot_status():
            statuses = []
            
            # Main bots
            if self.main_token:
                statuses.append({
                    "id": "main_1",
                    "name": "Main Bot 1",
                    "type": "main_1",
                    "connected": self._check_bot_connected(self.main_bot),
                    "lastSeen": datetime.now().isoformat(),
                    "autoGrabEnabled": self.auto_grab_enabled,
                    "heartThreshold": self.heart_threshold
                })
            
            if self.main_token_2:
                statuses.append({
                    "id": "main_2",
                    "name": "Main Bot 2",
                    "type": "main_2",
                    "connected": self._check_bot_connected(self.main_bot_2),
                    "lastSeen": datetime.now().isoformat(),
                    "autoGrabEnabled": self.auto_grab_enabled_2,
                    "heartThreshold": self.heart_threshold_2
                })
            
            # Sub bots
            for i, token in enumerate(self.tokens):
                if i < len(self.bots):
                    name = self.acc_names[i] if i < len(self.acc_names) else f"Account {i+1}"
                    statuses.append({
                        "id": f"sub_{i}",
                        "name": name,
                        "type": "sub",
                        "connected": self._check_bot_connected(self.bots[i]) if i < len(self.bots) else False,
                        "lastSeen": datetime.now().isoformat()
                    })
            
            return jsonify(statuses)
        
        @self.app.route('/api/auto-grab/<bot_type>')
        def get_auto_grab_settings(bot_type):
            if bot_type == "main_1":
                return jsonify({
                    "enabled": self.auto_grab_enabled,
                    "heartThreshold": self.heart_threshold,
                    "botType": "main_1"
                })
            elif bot_type == "main_2":
                return jsonify({
                    "enabled": self.auto_grab_enabled_2,
                    "heartThreshold": self.heart_threshold_2,
                    "botType": "main_2"
                })
            else:
                return jsonify({"error": "Invalid bot type"}), 400
        
        @self.app.route('/api/auto-grab', methods=['PATCH'])
        def update_auto_grab_settings():
            data = request.get_json()
            bot_type = data.get('botType')
            enabled = data.get('enabled', False)
            threshold = data.get('heartThreshold', 50)
            
            if bot_type == "main_1":
                self.auto_grab_enabled = enabled
                self.heart_threshold = threshold
                self.add_log("info", f"Auto grab Main Bot 1: {'enabled' if enabled else 'disabled'}, threshold: {threshold}")
            elif bot_type == "main_2":
                self.auto_grab_enabled_2 = enabled
                self.heart_threshold_2 = threshold
                self.add_log("info", f"Auto grab Main Bot 2: {'enabled' if enabled else 'disabled'}, threshold: {threshold}")
            else:
                return jsonify({"error": "Invalid bot type"}), 400
            
            return jsonify({"success": True})
        
        @self.app.route('/api/spam')
        def get_spam_settings():
            return jsonify({
                "enabled": self.spam_enabled,
                "message": self.spam_message,
                "delay": self.spam_delay
            })
        
        @self.app.route('/api/spam', methods=['PATCH'])
        def update_spam_settings():
            data = request.get_json()
            enabled = data.get('enabled', False)
            message = data.get('message', '')
            delay = data.get('delay', 10)
            
            self.spam_enabled = enabled
            self.spam_message = message
            self.spam_delay = delay
            
            if enabled and not self.spam_thread_running:
                self.start_spam()
            elif not enabled:
                self.spam_thread_running = False
            
            self.add_log("info", f"Spam settings updated: {'enabled' if enabled else 'disabled'}")
            return jsonify({"success": True})
        
        @self.app.route('/api/work')
        def get_work_settings():
            return jsonify({
                "enabled": self.auto_work_enabled
            })
        
        @self.app.route('/api/work', methods=['PATCH'])
        def update_work_settings():
            data = request.get_json()
            enabled = data.get('enabled', False)
            
            if enabled and not self.auto_work_running:
                result = self.start_auto_work()
                return jsonify({"success": result})
            elif not enabled and self.auto_work_running:
                result = self.stop_auto_work()
                return jsonify({"success": result})
            
            return jsonify({"success": True})
        
        @self.app.route('/api/work/stats')
        def get_work_stats():
            stats = self.auto_work_stats.copy()
            stats["running"] = self.auto_work_running
            stats["enabled"] = self.auto_work_enabled
            
            if stats["next_run_time"]:
                stats["time_until_next_run"] = max(0, stats["next_run_time"] - time.time())
            else:
                stats["time_until_next_run"] = None
            
            return jsonify(stats)
        
        @self.app.route('/api/logs')
        def get_logs():
            limit = request.args.get('limit', 100, type=int)
            with self.logs_lock:
                return jsonify(self.logs[:limit])
        
        @self.app.route('/api/logs', methods=['DELETE'])
        def clear_logs():
            with self.logs_lock:
                self.logs.clear()
            self.add_log("info", "Logs cleared")
            return jsonify({"success": True})
        
        @self.app.route('/api/bots/message', methods=['POST'])
        def send_message():
            data = request.get_json()
            message = data.get('message', '')
            
            if not message:
                return jsonify({"error": "Message is required"}), 400
            
            sent_count = self.send_message_all_bots(message)
            self.add_log("info", f"Sent message to {sent_count} bots: '{message}'")
            
            return jsonify({"success": True, "sent_count": sent_count})
        
        @self.app.route('/api/bots/reboot', methods=['POST'])
        def reboot_bot():
            data = request.get_json()
            bot_id = data.get('botId', '')
            
            if bot_id == 'all':
                self.reboot_all_bots()
                self.add_log("info", "Rebooting all bots")
            else:
                result = self.reboot_bot(bot_id)
                self.add_log("info", f"Reboot bot {bot_id}: {'success' if result else 'failed'}")
            
            return jsonify({"success": True})

    def setup_socketio(self):
        """Setup SocketIO events"""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.add_log("info", "Web client connected")
            
            # Send current bot status
            emit('bot-status', self.get_bot_statuses())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.add_log("info", "Web client disconnected")

    def get_bot_statuses(self):
        """Get current bot statuses"""
        statuses = []
        
        # Add logic to get actual bot statuses
        # This is a simplified version
        for i, name in enumerate(self.acc_names):
            statuses.append({
                "id": f"bot_{i}",
                "name": name,
                "connected": i < 3,  # Mock some as connected
                "lastSeen": datetime.now().isoformat()
            })
        
        return statuses

    def _check_bot_connected(self, bot):
        """Check if a bot is connected"""
        try:
            if bot and hasattr(bot, 'gateway') and hasattr(bot.gateway, 'ws'):
                return bot.gateway.ws is not None
            return False
        except:
            return False

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
                        self.add_log("info", f"Bot logged in: {user_id} {bot_type}")
                    except Exception as e:
                        self.add_log("error", f"Error getting user_id: {e}")

            # Auto grab logic for main bots
            if is_main:
                @bot.gateway.command
                def on_message(resp):
                    if resp.event.message:
                        msg = resp.parsed.auto()
                        author = msg.get("author", {}).get("id")
                        content = msg.get("content", "")
                        channel = msg.get("channel_id")
                        mentions = msg.get("mentions", [])

                        if author == KARUTA_ID and channel == MAIN_CHANNEL_ID:
                            if "is dropping" not in content and not mentions and self.auto_grab_enabled:
                                self.add_log("info", "Auto drop detected! Reading Karibbit message...", "Bot 1")
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

                        if author == KARUTA_ID and channel == MAIN_CHANNEL_ID:
                            if "is dropping" not in content and not mentions and self.auto_grab_enabled_2:
                                self.add_log("info", "Auto drop detected! Reading Karibbit message...", "Bot 2")
                                self.last_drop_msg_id = msg["id"]
                                threading.Thread(target=self._read_karibbit_and_grab, args=(bot, 2)).start()

            threading.Thread(target=bot.gateway.run, daemon=True).start()
            return bot
        except Exception as e:
            self.add_log("error", f"Error creating bot: {e}")
            return None

    def _read_karibbit_and_grab(self, bot, bot_num):
        """Read Karibbit message and perform grab logic"""
        time.sleep(0.5)
        try:
            messages = bot.getMessages(MAIN_CHANNEL_ID, num=5).json()
            for msg in messages:
                author_id = msg.get("author", {}).get("id")
                if author_id == KARIBBIT_ID and "embeds" in msg and len(msg["embeds"]) > 0:
                    desc = msg["embeds"][0].get("description", "")
                    self.add_log("info", f"Karibbit message found", f"Bot {bot_num}")

                    lines = desc.split('\n')
                    heart_numbers = []

                    for i, line in enumerate(lines[:3]):
                        matches = re.findall(r'`([^`]*)`', line)
                        if len(matches) >= 2 and matches[1].isdigit():
                            num = int(matches[1])
                            heart_numbers.append(num)
                            self.add_log("info", f"Line {i+1} hearts: {num}", f"Bot {bot_num}")
                        else:
                            heart_numbers.append(0)
                            self.add_log("info", f"Line {i+1} no hearts found, default 0", f"Bot {bot_num}")

                    if sum(heart_numbers) == 0:
                        self.add_log("info", "No hearts found, skipping", f"Bot {bot_num}")
                    else:
                        max_num = max(heart_numbers)
                        threshold = self.heart_threshold if bot_num == 1 else self.heart_threshold_2
                        if max_num < threshold:
                            self.add_log("info", f"Max hearts {max_num} < {threshold}, not grabbing!", f"Bot {bot_num}")
                        else:
                            max_index = heart_numbers.index(max_num)
                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                            base_delays = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}
                            delay = base_delays[emoji] + (0.3 if bot_num == 2 else 0)
                            self.add_log("info", f"Choosing line {max_index+1} with {max_num} hearts → Emoji {emoji} after {delay}s", f"Bot {bot_num}")

                            def grab():
                                try:
                                    bot.addReaction(MAIN_CHANNEL_ID, self.last_drop_msg_id, emoji)
                                    self.add_log("info", "Grab emoji sent!", f"Bot {bot_num}")
                                except Exception as e:
                                    self.add_log("error", f"Error sending grab emoji: {e}", f"Bot {bot_num}")

                            threading.Timer(delay, grab).start()
                    break
        except Exception as e:
            self.add_log("error", f"Error in grab logic: {e}", f"Bot {bot_num}")

    def start_auto_work(self):
        """Start enhanced auto work functionality"""
        with self.work_lock:
            if self.auto_work_running:
                self.add_log("info", "Auto work already running!")
                return False
            
            if not self.tokens:
                self.add_log("error", "No tokens available for auto work!")
                return False
            
            self.auto_work_enabled = True
            self.auto_work_running = True
            self.auto_work_thread = threading.Thread(target=self._enhanced_auto_work_loop, daemon=True)
            self.auto_work_thread.start()
            
            self.add_log("info", "Enhanced auto work started!")
            return True

    def stop_auto_work(self):
        """Stop auto work functionality"""
        with self.work_lock:
            self.auto_work_enabled = False
            self.auto_work_running = False
            
            if self.auto_work_thread:
                self.auto_work_thread.join(timeout=10)
            
            self.add_log("info", "Auto work stopped!")
            return True

    def _enhanced_auto_work_loop(self):
        """Enhanced auto work main loop"""
        self.add_log("info", "Starting enhanced auto work loop...")
        
        while self.auto_work_running:
            try:
                cycle_start_time = time.time()
                self.auto_work_stats["total_runs"] += 1
                self.auto_work_stats["last_run_time"] = cycle_start_time
                
                self.add_log("info", f"Starting auto work cycle #{self.auto_work_stats['total_runs']}")
                
                success_count = 0
                for i, token in enumerate(self.tokens):
                    if not self.auto_work_running:
                        break
                    
                    self.auto_work_stats["current_account"] = i + 1
                    acc_name = self.acc_names[i] if i < len(self.acc_names) else f"Account {i+1}"
                    
                    self.add_log("info", f"Running auto work for account {i+1}/{len(self.tokens)}: {acc_name}")
                    
                    # Emit progress update
                    try:
                        self.socketio.emit('work-progress', {
                            'current_account': i + 1,
                            'total_accounts': len(self.tokens),
                            'account_name': acc_name
                        })
                    except:
                        pass
                    
                    if self._run_work_for_account_enhanced(token.strip(), i + 1, acc_name):
                        success_count += 1
                        self.add_log("info", f"Account {i+1} ({acc_name}) completed successfully")
                    else:
                        self.add_log("error", f"Account {i+1} ({acc_name}) failed")
                    
                    # Delay giữa các account
                    if i < len(self.tokens) - 1 and self.auto_work_running:
                        self.add_log("info", f"Waiting {AUTO_WORK_DELAY_BETWEEN_ACC}s before next account...")
                        time.sleep(AUTO_WORK_DELAY_BETWEEN_ACC)
                
                # Update statistics
                if success_count == len(self.tokens):
                    self.auto_work_stats["successful_runs"] += 1
                else:
                    self.auto_work_stats["failed_runs"] += 1
                
                cycle_duration = time.time() - cycle_start_time
                self.add_log("info", f"Auto work cycle completed: {success_count}/{len(self.tokens)} successful, took {cycle_duration:.1f}s")
                
                if self.auto_work_running:
                    # Calculate next run time
                    next_run_time = time.time() + AUTO_WORK_DELAY_AFTER_ALL
                    self.auto_work_stats["next_run_time"] = next_run_time
                    
                    self.add_log("info", f"Waiting {AUTO_WORK_DELAY_AFTER_ALL}s ({AUTO_WORK_DELAY_AFTER_ALL/3600:.1f}h) before next cycle...")
                    
                    # Sleep in chunks to allow for stopping
                    sleep_chunks = AUTO_WORK_DELAY_AFTER_ALL // 60  # Sleep in 1-minute chunks
                    remainder = AUTO_WORK_DELAY_AFTER_ALL % 60
                    
                    for chunk in range(int(sleep_chunks)):
                        if not self.auto_work_running:
                            break
                        time.sleep(60)
                    
                    if self.auto_work_running and remainder > 0:
                        time.sleep(remainder)
            
            except Exception as e:
                self.add_log("error", f"Error in auto work main loop: {e}")
                self.auto_work_stats["failed_runs"] += 1
                time.sleep(300)  # Wait 5 minutes before retry
        
        self.add_log("info", "Enhanced auto work loop stopped")

    def _run_work_for_account_enhanced(self, token, acc_index, acc_name):
        """Enhanced work logic for a specific account"""
        try:
            self.add_log("info", f"Starting enhanced work for {acc_name}", f"Work-{acc_index}")
            
            bot = discum.Client(token=token, log={"console": False, "file": False})
            
            headers = {
                "Authorization": token,
                "Content-Type": "application/json"
            }
            
            step = {"value": 0}
            step_completed = {"value": False}
            
            def send_karuta_command():
                self.add_log("info", "Sending 'kc o:ef' command...", f"Work-{acc_index}")
                bot.sendMessage(WORK_CHANNEL_ID, "kc o:ef")

            def send_kn_command():
                self.add_log("info", "Sending 'kn' command...", f"Work-{acc_index}")
                bot.sendMessage(WORK_CHANNEL_ID, "kn")

            def send_kw_command():
                self.add_log("info", "Sending 'kw' command...", f"Work-{acc_index}")
                bot.sendMessage(WORK_CHANNEL_ID, "kw")
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
                        self.add_log("info", "Button click successful!", f"Work-{acc_index}")
                        return True
                    else:
                        self.add_log("error", f"Button click failed! Status: {r.status_code}", f"Work-{acc_index}")
                        return False
                except Exception as e:
                    self.add_log("error", f"Error clicking button: {str(e)}", f"Work-{acc_index}")
                    return False

            @bot.gateway.command
            def on_message(resp):
                if resp.event.message:
                    m = resp.parsed.auto()
                    if str(m.get('channel_id')) != WORK_CHANNEL_ID:
                        return

                    author_id = str(m.get('author', {}).get('id', ''))
                    guild_id = m.get('guild_id')

                    # Step 0: Process card codes from 'kc o:ef' response
                    if step["value"] == 0 and author_id == KARUTA_ID and 'embeds' in m and len(m['embeds']) > 0:
                        desc = m['embeds'][0].get('description', '')
                        card_codes = re.findall(r'\bv[a-zA-Z0-9]{6}\b', desc)
                        
                        if card_codes and len(card_codes) >= 10:
                            first_5 = card_codes[:5]
                            last_5 = card_codes[-5:]

                            self.add_log("info", f"Found {len(card_codes)} cards", f"Work-{acc_index}")
                            self.add_log("info", f"First 5: {', '.join(first_5)}", f"Work-{acc_index}")
                            self.add_log("info", f"Last 5: {', '.join(last_5)}", f"Work-{acc_index}")

                            # Send last 5 cards first
                            for i, code in enumerate(last_5):
                                suffix = chr(97 + i)  # a, b, c, d, e
                                if i == 0:
                                    time.sleep(2)
                                else:
                                    time.sleep(1.5)
                                bot.sendMessage(WORK_CHANNEL_ID, f"kjw {code} {suffix}")
                                self.add_log("info", f"Sent kjw {code} {suffix}", f"Work-{acc_index}")

                            # Then send first 5 cards
                            for i, code in enumerate(first_5):
                                suffix = chr(97 + i)  # a, b, c, d, e
                                time.sleep(1.5)
                                bot.sendMessage(WORK_CHANNEL_ID, f"kjw {code} {suffix}")
                                self.add_log("info", f"Sent kjw {code} {suffix}", f"Work-{acc_index}")

                            time.sleep(1)
                            send_kn_command()
                            step["value"] = 1

                    # Step 1: Process resource selection from 'kn' response
                    elif step["value"] == 1 and author_id == KARUTA_ID and 'embeds' in m and len(m['embeds']) > 0:
                        desc = m['embeds'][0].get('description', '')
                        lines = desc.split('\n')
                        
                        if len(lines) >= 2:
                            # Look for the second line with resource format
                            match = re.search(r'\d+\.\s*`([^`]+)`', lines[1])
                            if match:
                                resource = match.group(1)
                                self.add_log("info", f"Selected resource: {resource}", f"Work-{acc_index}")
                                time.sleep(2)
                                bot.sendMessage(WORK_CHANNEL_ID, f"kjn `{resource}` a b c d e")
                                self.add_log("info", f"Sent kjn `{resource}` a b c d e", f"Work-{acc_index}")
                                time.sleep(1)
                                send_kw_command()

                    # Step 2: Process button click from 'kw' response
                    elif step["value"] == 2 and author_id == KARUTA_ID and 'components' in m:
                        message_id = m['id']
                        application_id = m.get('application_id', KARUTA_ID)
                        last_custom_id = None
                        
                        # Find the last button custom_id
                        for comp in m['components']:
                            if comp['type'] == 1:  # Action Row
                                for btn in comp['components']:
                                    if btn['type'] == 2:  # Button
                                        last_custom_id = btn['custom_id']
                                        self.add_log("info", f"Found button with custom_id: {last_custom_id}", f"Work-{acc_index}")

                        if last_custom_id:
                            if click_tick(WORK_CHANNEL_ID, message_id, last_custom_id, application_id, guild_id):
                                step["value"] = 3
                                step_completed["value"] = True
                                self.add_log("info", "Work completed successfully!", f"Work-{acc_index}")
                            else:
                                self.add_log("error", "Failed to click button", f"Work-{acc_index}")
                                step_completed["value"] = False
                        
                        # Close bot connection
                        try:
                            bot.gateway.close()
                        except:
                            pass

            # Start bot and begin work sequence
            threading.Thread(target=bot.gateway.run, daemon=True).start()
            time.sleep(3)  # Wait for bot to connect
            
            send_karuta_command()

            # Wait for completion or timeout
            timeout = time.time() + AUTO_WORK_TIMEOUT
            while step["value"] != 3 and time.time() < timeout and self.auto_work_running:
                time.sleep(1)

            # Cleanup
            try:
                bot.gateway.close()
            except:
                pass

            success = step_completed["value"]
            if success:
                self.add_log("info", f"{acc_name} completed successfully", f"Work-{acc_index}")
            else:
                self.add_log("error", f"{acc_name} failed or timed out", f"Work-{acc_index}")
            
            return success

        except Exception as e:
            self.add_log("error", f"Error in enhanced work for {acc_name}: {e}", f"Work-{acc_index}")
            return False

    def start_spam(self):
        """Start spam functionality"""
        if self.spam_thread_running:
            self.add_log("info", "Spam already running!")
            return False
        
        self.spam_enabled = True
        self.spam_thread_running = True
        spam_thread = threading.Thread(target=self._spam_loop, daemon=True)
        spam_thread.start()
        
        self.add_log("info", "Spam started!")
        return True

    def _spam_loop(self):
        """Spam loop implementation"""
        self.add_log("info", "Starting spam loop...")
        
        while self.spam_enabled and self.spam_thread_running:
            try:
                if self.spam_message:
                    sent_count = self.send_message_all_bots(self.spam_message, SPAM_CHANNEL_ID)
                    if sent_count > 0:
                        self.add_log("info", f"Sent spam message through {sent_count} bots")
                    else:
                        self.add_log("warning", "No bots available to send spam")
                
                time.sleep(self.spam_delay)
            
            except Exception as e:
                self.add_log("error", f"Error in spam loop: {e}")
                time.sleep(self.spam_delay)
        
        self.spam_thread_running = False
        self.add_log("info", "Spam loop stopped")

    def send_message_all_bots(self, message, channel_id=None):
        """Send message through all available bots"""
        if not channel_id:
            channel_id = MAIN_CHANNEL_ID
        
        sent_count = 0
        
        if self.main_bot:
            try:
                self.main_bot.sendMessage(channel_id, message)
                sent_count += 1
            except Exception as e:
                self.add_log("error", f"Error with main bot: {e}")
        
        if self.main_bot_2:
            try:
                self.main_bot_2.sendMessage(channel_id, message)
                sent_count += 1
            except Exception as e:
                self.add_log("error", f"Error with main bot 2: {e}")
        
        for i, bot in enumerate(self.bots):
            if bot:
                try:
                    bot.sendMessage(channel_id, message)
                    sent_count += 1
                except Exception as e:
                    self.add_log("error", f"Error with sub bot {i}: {e}")
        
        return sent_count

    def reboot_bot(self, target_id):
        """Reboot a bot based on its target ID"""
        with self.bots_lock:
            self.add_log("info", f"Received reboot request for target: {target_id}")
            
            if target_id == 'main_1':
                if not self.main_token:
                    self.add_log("error", "No main token available for Main Bot 1")
                    return False
                    
                self.add_log("info", "Processing Main Bot 1...")
                try:
                    if self.main_bot:
                        self.main_bot.gateway.close()
                except Exception as e:
                    self.add_log("error", f"Error closing Main Bot 1: {e}")
                self.main_bot = self.create_bot(self.main_token, is_main=True)
                self.add_log("info", "Main Bot 1 rebooted successfully")
                return True

            elif target_id == 'main_2':
                if not self.main_token_2:
                    self.add_log("error", "No main token 2 available for Main Bot 2")
                    return False
                    
                self.add_log("info", "Processing Main Bot 2...")
                try:
                    if self.main_bot_2:
                        self.main_bot_2.gateway.close()
                except Exception as e:
                    self.add_log("error", f"Error closing Main Bot 2: {e}")
                self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True)
                self.add_log("info", "Main Bot 2 rebooted successfully")
                return True

            elif target_id.startswith('sub_'):
                try:
                    index = int(target_id.split('_')[1])
                    if 0 <= index < len(self.bots):
                        self.add_log("info", f"Processing Sub Bot {index}...")
                        try:
                            if self.bots[index]:
                                self.bots[index].gateway.close()
                        except Exception as e:
                            self.add_log("error", f"Error closing Sub Bot {index}: {e}")
                        
                        if index < len(self.tokens):
                            token_to_reboot = self.tokens[index]
                            self.bots[index] = self.create_bot(token_to_reboot.strip())
                            self.add_log("info", f"Sub Bot {index} rebooted successfully")
                            return True
                    else:
                        self.add_log("error", f"Invalid index: {index}")
                        return False
                except (ValueError, IndexError) as e:
                    self.add_log("error", f"Error processing sub bot target: {e}")
                    return False
            else:
                self.add_log("error", f"Unknown target: {target_id}")
                return False

    def reboot_all_bots(self):
        """Reboot all bots"""
        self.add_log("info", "Rebooting all bots...")
        
        # Reboot main bots
        if self.main_token:
            self.reboot_bot('main_1')
        
        if self.main_token_2:
            self.reboot_bot('main_2')
        
        # Reboot sub bots
        for i in range(len(self.tokens)):
            self.reboot_bot(f'sub_{i}')
        
        self.add_log("info", "All bots rebooted")

    def initialize_all_bots(self):
        """Initialize all bots"""
        self.add_log("info", "Starting bot initialization...")
        
        # Initialize main bots
        if self.main_token:
            self.main_bot = self.create_bot(self.main_token, is_main=True)
            if self.main_bot:
                self.add_log("info", "Main Bot 1 initialized")
            else:
                self.add_log("error", "Failed to initialize Main Bot 1")
        
        if self.main_token_2:
            self.main_bot_2 = self.create_bot(self.main_token_2, is_main_2=True)
            if self.main_bot_2:
                self.add_log("info", "Main Bot 2 initialized")
            else:
                self.add_log("error", "Failed to initialize Main Bot 2")
        
        # Initialize sub bots
        self.bots = []
        for i, token in enumerate(self.tokens):
            if token.strip():
                bot = self.create_bot(token.strip())
                self.bots.append(bot)
                if bot:
                    self.add_log("info", f"Sub Bot {i+1} initialized")
                else:
                    self.add_log("error", f"Failed to initialize Sub Bot {i+1}")
            else:
                self.bots.append(None)
        
        self.add_log("info", f"Bot initialization completed: {len([b for b in self.bots if b])} sub bots initialized")

    def get_html_template(self):
        """Get the HTML template for the web interface"""
        return '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discord Bot Manager - Complete System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }
        
        .card {
            background: #1e293b;
            border: 1px solid #475569;
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1);
        }
        
        .btn {
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            font-size: 0.9rem;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-success { background: #10b981; color: white; }
        .btn-success:hover { background: #059669; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn-warning { background: #f59e0b; color: white; }
        .btn-warning:hover { background: #d97706; }
        .btn-outline { background: transparent; border: 2px solid #475569; color: #e2e8f0; }
        .btn-outline:hover { background: #334155; border-color: #94a3b8; }
        
        .status-online { color: #10b981; }
        .status-offline { color: #ef4444; }
        
        .input-field {
            background: #334155;
            border: 1px solid #475569;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: #e2e8f0;
            font-size: 0.9rem;
            transition: border-color 0.2s ease;
        }
        
        .input-field:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        .logs-container {
            max-height: 300px;
            overflow-y: auto;
            background: #0f172a;
            border: 1px solid #475569;
            border-radius: 8px;
            padding: 1rem;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.8rem;
            line-height: 1.4;
        }
        
        .log-entry {
            margin-bottom: 0.5rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            border-left: 3px solid transparent;
        }
        
        .log-info { border-left-color: #3b82f6; background: rgba(59, 130, 246, 0.05); }
        .log-error { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.05); }
        .log-warning { border-left-color: #f59e0b; background: rgba(245, 158, 11, 0.05); }
        
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid #475569;
            border-top: 2px solid #e2e8f0;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        }
        
        .notification.show { transform: translateX(0); }
        .notification-success { background: #10b981; }
        .notification-error { background: #ef4444; }
        .notification-info { background: #3b82f6; }
        .notification-warning { background: #f59e0b; }
        
        .grid-responsive {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
        }
        
        @media (max-width: 768px) {
            .grid-responsive { grid-template-columns: 1fr; }
            .card { padding: 1rem; }
            .btn { padding: 0.5rem 1rem; font-size: 0.8rem; }
        }
    </style>
</head>
<body class="min-h-screen p-4">
    <div class="max-w-7xl mx-auto">
        <header class="text-center mb-8">
            <h1 class="text-4xl font-bold mb-2">🤖 Discord Bot Manager</h1>
            <p class="text-lg text-gray-400">Hệ thống quản lý Discord bot Karuta hoàn chỉnh</p>
            <div class="mt-4 flex justify-center gap-4">
                <div class="px-3 py-1 bg-green-600 text-white rounded-full text-sm" id="connection-status">
                    🟢 Đã kết nối
                </div>
                <div class="px-3 py-1 bg-gray-600 text-white rounded-full text-sm" id="last-update">
                    ⏱️ Cập nhật: <span id="update-time">--:--</span>
                </div>
            </div>
        </header>

        <div class="grid-responsive">
            <!-- Bot Status -->
            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-semibold">🔌 Trạng thái Bot</h2>
                    <button class="btn btn-outline" onclick="refreshBotStatus()">🔄 Làm mới</button>
                </div>
                <div id="bot-status" class="space-y-2">
                    <div class="text-center text-gray-400 py-4">
                        <div class="spinner mx-auto mb-2"></div>
                        <p>Đang tải...</p>
                    </div>
                </div>
            </div>

            <!-- Auto Grab -->
            <div class="card">
                <h2 class="text-xl font-semibold mb-4">🎯 Auto Grab</h2>
                <div class="space-y-3">
                    <div class="border border-gray-600 rounded-lg p-3">
                        <div class="flex items-center justify-between mb-2">
                            <label class="font-medium">Main Bot 1</label>
                            <button class="btn btn-primary" id="auto-grab-main-1" onclick="toggleAutoGrab('main_1')">
                                Bật
                            </button>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-sm text-gray-400">Hearts threshold:</span>
                            <input type="number" id="threshold-main-1" value="50" min="1" max="1000" 
                                   class="input-field w-20 text-center" 
                                   onchange="updateHeartThreshold('main_1', this.value)">
                        </div>
                    </div>
                    
                    <div class="border border-gray-600 rounded-lg p-3">
                        <div class="flex items-center justify-between mb-2">
                            <label class="font-medium">Main Bot 2</label>
                            <button class="btn btn-primary" id="auto-grab-main-2" onclick="toggleAutoGrab('main_2')">
                                Bật
                            </button>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-sm text-gray-400">Hearts threshold:</span>
                            <input type="number" id="threshold-main-2" value="50" min="1" max="1000" 
                                   class="input-field w-20 text-center" 
                                   onchange="updateHeartThreshold('main_2', this.value)">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Auto Work -->
            <div class="card">
                <h2 class="text-xl font-semibold mb-4">⚙️ Auto Work</h2>
                <div class="space-y-3">
                    <button class="btn btn-success w-full" id="work-toggle" onclick="toggleWork()">
                        Bật Auto Work
                    </button>
                    <div id="work-stats" class="text-sm text-gray-400 space-y-1">
                        <div>🔄 Chu kỳ: <span id="work-total-runs">0</span></div>
                        <div>✅ Thành công: <span id="work-success-runs">0</span></div>
                        <div>❌ Thất bại: <span id="work-failed-runs">0</span></div>
                        <div>👤 Account hiện tại: <span id="work-current-account">0</span>/18</div>
                        <div id="work-next-run" class="hidden">⏰ Chu kỳ tiếp theo: <span id="work-next-time">--</span></div>
                    </div>
                </div>
            </div>

            <!-- Spam Control -->
            <div class="card">
                <h2 class="text-xl font-semibold mb-4">📢 Spam Control</h2>
                <div class="space-y-3">
                    <button class="btn btn-success w-full" id="spam-toggle" onclick="toggleSpam()">
                        Bật Spam
                    </button>
                    <input type="text" id="spam-message" placeholder="Tin nhắn spam..." class="input-field w-full">
                    <input type="number" id="spam-delay" value="10" placeholder="Delay (s)" class="input-field w-full">
                </div>
            </div>

            <!-- Quick Actions -->
            <div class="card">
                <h2 class="text-xl font-semibold mb-4">⚡ Thao tác nhanh</h2>
                <div class="space-y-2">
                    <button class="btn btn-primary w-full" onclick="showSendMessageModal()">📤 Gửi tin nhắn</button>
                    <button class="btn btn-warning w-full" onclick="rebootAll()">🔄 Khởi động lại tất cả</button>
                    <button class="btn btn-danger w-full" onclick="clearLogs()">🗑️ Xóa logs</button>
                </div>
            </div>

            <!-- System Logs -->
            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-semibold">📝 System Logs</h2>
                    <button class="btn btn-outline" onclick="refreshLogs()">🔄 Làm mới</button>
                </div>
                <div id="logs-container" class="logs-container">
                    <div class="text-center text-gray-400 py-4">
                        <div class="spinner mx-auto mb-2"></div>
                        <p>Đang tải logs...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Notification -->
    <div id="notification" class="notification">
        <span id="notification-message"></span>
    </div>

    <!-- Send Message Modal -->
    <div id="send-message-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="card max-w-md w-full mx-4">
            <h3 class="text-lg font-semibold mb-4">📤 Gửi tin nhắn</h3>
            <div class="space-y-3">
                <textarea id="message-input" placeholder="Nhập tin nhắn..." 
                          class="input-field w-full h-24 resize-none"></textarea>
                <div class="flex gap-2">
                    <button class="btn btn-primary flex-1" onclick="sendMessage()">Gửi</button>
                    <button class="btn btn-outline" onclick="closeSendMessageModal()">Hủy</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let logs = [];
        let botStatuses = {};
        let workStats = {};
        
        socket.on('connect', () => {
            console.log('Connected to server');
            showNotification('Đã kết nối với server', 'success');
            document.getElementById('connection-status').innerHTML = '🟢 Đã kết nối';
        });
        
        socket.on('disconnect', () => {
            console.log('Disconnected from server');
            showNotification('Mất kết nối với server', 'error');
            document.getElementById('connection-status').innerHTML = '🔴 Mất kết nối';
        });
        
        socket.on('log', (data) => {
            addLog(data);
        });
        
        socket.on('bot-status', (data) => {
            updateBotStatus(data);
        });
        
        socket.on('work-progress', (data) => {
            document.getElementById('work-current-account').textContent = data.current_account;
            showNotification(`Đang chạy account: ${data.account_name}`, 'info');
        });
        
        function updateBotStatus(statuses) {
            const statusDiv = document.getElementById('bot-status');
            if (!statuses || statuses.length === 0) {
                statusDiv.innerHTML = '<div class="text-gray-400 py-4">Chưa có dữ liệu bot</div>';
                return;
            }
            
            statusDiv.innerHTML = statuses.map(bot => `
                <div class="flex justify-between items-center p-3 bg-gray-800 rounded-lg">
                    <div class="flex items-center gap-3">
                        <span class="text-lg">${getBotIcon(bot.type)}</span>
                        <div>
                            <div class="font-medium">${bot.name}</div>
                            <div class="text-xs text-gray-400">
                                ${new Date(bot.lastSeen).toLocaleTimeString('vi-VN')}
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-1 rounded text-xs ${bot.connected ? 'bg-green-600' : 'bg-red-600'}">
                            ${bot.connected ? '🟢 Online' : '🔴 Offline'}
                        </span>
                        <button class="btn btn-outline text-xs" onclick="rebootBot('${bot.id}')">🔄</button>
                    </div>
                </div>
            `).join('');
            
            botStatuses = statuses;
        }
        
        function addLog(log) {
            logs.unshift(log);
            if (logs.length > 50) logs = logs.slice(0, 50);
            
            const logsDiv = document.getElementById('logs-container');
            logsDiv.innerHTML = logs.map(entry => `
                <div class="log-entry log-${entry.level}">
                    <span class="text-gray-400">[${new Date(entry.timestamp).toLocaleTimeString('vi-VN')}]</span>
                    ${entry.bot_id ? `<span class="text-blue-400">[${entry.bot_id}]</span>` : ''}
                    <span class="ml-2">${entry.message}</span>
                </div>
            `).join('');
            
            logsDiv.scrollTop = logsDiv.scrollHeight;
        }
        
        function updateWorkStats() {
            apiCall('GET', '/api/work/stats').then(stats => {
                workStats = stats;
                document.getElementById('work-total-runs').textContent = stats.total_runs || 0;
                document.getElementById('work-success-runs').textContent = stats.successful_runs || 0;
                document.getElementById('work-failed-runs').textContent = stats.failed_runs || 0;
                document.getElementById('work-current-account').textContent = stats.current_account || 0;
                
                const nextRunDiv = document.getElementById('work-next-run');
                const nextTimeSpan = document.getElementById('work-next-time');
                
                if (stats.running && stats.time_until_next_run) {
                    const hours = Math.floor(stats.time_until_next_run / 3600);
                    const minutes = Math.floor((stats.time_until_next_run % 3600) / 60);
                    nextTimeSpan.textContent = `${hours}h ${minutes}m`;
                    nextRunDiv.classList.remove('hidden');
                } else if (stats.running) {
                    nextTimeSpan.textContent = 'Đang chạy...';
                    nextRunDiv.classList.remove('hidden');
                } else {
                    nextRunDiv.classList.add('hidden');
                }
            });
        }
        
        function getBotIcon(type) {
            switch (type) {
                case 'main_1': case 'main_2': return '🤖';
                case 'sub': return '🔧';
                default: return '❓';
            }
        }
        
        function showNotification(message, type = 'info') {
            const notification = document.getElementById('notification');
            const messageElement = document.getElementById('notification-message');
            
            messageElement.textContent = message;
            notification.className = `notification notification-${type}`;
            notification.classList.add('show');
            
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }
        
        async function apiCall(method, endpoint, data = null) {
            try {
                const options = {
                    method: method,
                    headers: { 'Content-Type': 'application/json' }
                };
                
                if (data) {
                    options.body = JSON.stringify(data);
                }
                
                const response = await fetch(endpoint, options);
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error || 'API call failed');
                }
                
                return result;
            } catch (error) {
                console.error('API Error:', error);
                showNotification(error.message || 'Lỗi khi gọi API', 'error');
                throw error;
            }
        }
        
        async function toggleAutoGrab(botType) {
            try {
                const currentSettings = await apiCall('GET', `/api/auto-grab/${botType}`);
                const newEnabled = !currentSettings.enabled;
                const threshold = parseInt(document.getElementById(`threshold-${botType}`).value);
                
                await apiCall('PATCH', '/api/auto-grab', {
                    botType: botType,
                    enabled: newEnabled,
                    heartThreshold: threshold
                });
                
                const btn = document.getElementById(`auto-grab-${botType}`);
                btn.textContent = newEnabled ? 'Tắt' : 'Bật';
                btn.className = `btn ${newEnabled ? 'btn-success' : 'btn-primary'}`;
                
                showNotification(`Auto grab ${botType} ${newEnabled ? 'đã bật' : 'đã tắt'}`, 'success');
            } catch (error) {
                showNotification('Lỗi khi thay đổi auto grab', 'error');
            }
        }
        
        async function updateHeartThreshold(botType, threshold) {
            try {
                const currentSettings = await apiCall('GET', `/api/auto-grab/${botType}`);
                await apiCall('PATCH', '/api/auto-grab', {
                    botType: botType,
                    enabled: currentSettings.enabled,
                    heartThreshold: parseInt(threshold)
                });
                
                showNotification(`Đã cập nhật heart threshold cho ${botType}`, 'success');
            } catch (error) {
                showNotification('Lỗi khi cập nhật heart threshold', 'error');
            }
        }
        
        async function toggleWork() {
            try {
                const currentSettings = await apiCall('GET', '/api/work');
                const newEnabled = !currentSettings.enabled;
                
                await apiCall('PATCH', '/api/work', {
                    enabled: newEnabled
                });
                
                const btn = document.getElementById('work-toggle');
                btn.textContent = newEnabled ? 'Tắt Auto Work' : 'Bật Auto Work';
                btn.className = `btn ${newEnabled ? 'btn-danger' : 'btn-success'} w-full`;
                
                showNotification(`Auto work ${newEnabled ? 'đã bật' : 'đã tắt'}`, 'success');
                
                if (newEnabled) {
                    updateWorkStats();
                }
            } catch (error) {
                showNotification('Lỗi khi thay đổi auto work', 'error');
            }
        }
        
        async function toggleSpam() {
            try {
                const currentSettings = await apiCall('GET', '/api/spam');
                const newEnabled = !currentSettings.enabled;
                const message = document.getElementById('spam-message').value;
                const delay = parseInt(document.getElementById('spam-delay').value);
                
                await apiCall('PATCH', '/api/spam', {
                    enabled: newEnabled,
                    message: message,
                    delay: delay
                });
                
                const btn = document.getElementById('spam-toggle');
                btn.textContent = newEnabled ? 'Tắt Spam' : 'Bật Spam';
                btn.className = `btn ${newEnabled ? 'btn-danger' : 'btn-success'} w-full`;
                
                showNotification(`Spam ${newEnabled ? 'đã bật' : 'đã tắt'}`, 'success');
            } catch (error) {
                showNotification('Lỗi khi thay đổi spam', 'error');
            }
        }
        
        function showSendMessageModal() {
            document.getElementById('send-message-modal').classList.remove('hidden');
            document.getElementById('message-input').focus();
        }
        
        function closeSendMessageModal() {
            document.getElementById('send-message-modal').classList.add('hidden');
            document.getElementById('message-input').value = '';
        }
        
        async function sendMessage() {
            const message = document.getElementById('message-input').value.trim();
            if (!message) {
                showNotification('Vui lòng nhập tin nhắn', 'warning');
                return;
            }
            
            try {
                const result = await apiCall('POST', '/api/bots/message', { message: message });
                showNotification(`Đã gửi tin nhắn qua ${result.sent_count || 0} bots`, 'success');
                closeSendMessageModal();
            } catch (error) {
                showNotification('Lỗi khi gửi tin nhắn', 'error');
            }
        }
        
        async function rebootBot(botId) {
            try {
                await apiCall('POST', '/api/bots/reboot', { botId: botId });
                showNotification(`Đã khởi động lại bot ${botId}`, 'success');
                setTimeout(refreshBotStatus, 3000);
            } catch (error) {
                showNotification('Lỗi khi khởi động lại bot', 'error');
            }
        }
        
        async function rebootAll() {
            if (!confirm('Bạn có chắc muốn khởi động lại tất cả bot?')) {
                return;
            }
            
            try {
                await apiCall('POST', '/api/bots/reboot', { botId: 'all' });
                showNotification('Đã khởi động lại tất cả bot', 'success');
                setTimeout(refreshBotStatus, 5000);
            } catch (error) {
                showNotification('Lỗi khi khởi động lại tất cả bot', 'error');
            }
        }
        
        async function clearLogs() {
            if (!confirm('Bạn có chắc muốn xóa tất cả logs?')) {
                return;
            }
            
            try {
                await apiCall('DELETE', '/api/logs');
                logs = [];
                document.getElementById('logs-container').innerHTML = '<div class="text-gray-400">Logs đã được xóa</div>';
                showNotification('Logs đã được xóa', 'success');
            } catch (error) {
                showNotification('Lỗi khi xóa logs', 'error');
            }
        }
        
        function refreshBotStatus() {
            apiCall('GET', '/api/bots/status').then(updateBotStatus);
        }
        
        function refreshLogs() {
            apiCall('GET', '/api/logs').then(logData => {
                logs = logData;
                document.getElementById('logs-container').innerHTML = logs.map(entry => `
                    <div class="log-entry log-${entry.level}">
                        <span class="text-gray-400">[${new Date(entry.timestamp).toLocaleTimeString('vi-VN')}]</span>
                        ${entry.bot_id ? `<span class="text-blue-400">[${entry.bot_id}]</span>` : ''}
                        <span class="ml-2">${entry.message}</span>
                    </div>
                `).join('');
            });
        }
        
        function updateTime() {
            document.getElementById('update-time').textContent = new Date().toLocaleTimeString('vi-VN');
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            refreshBotStatus();
            refreshLogs();
            updateWorkStats();
            updateTime();
            
            // Auto-refresh every 30 seconds
            setInterval(() => {
                updateWorkStats();
                updateTime();
            }, 30000);
        });
        
        // Close modals when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('fixed') && e.target.classList.contains('inset-0')) {
                closeSendMessageModal();
            }
        });
        
        // Handle escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeSendMessageModal();
            }
        });
    </script>
</body>
</html>
        '''

    def run_web_server(self, host='0.0.0.0', port=3000, debug=False):
        """Run the web server"""
        self.add_log("info", f"Starting Discord Bot Manager on {host}:{port}")
        self.add_log("info", f"Web interface: http://localhost:{port}")
        
        try:
            self.socketio.run(self.app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
        except Exception as e:
            self.add_log("error", f"Error running web server: {e}")

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    logging.info("Received shutdown signal")
    sys.exit(0)

def main():
    """Main function"""
    print("🤖 Discord Bot Manager - Complete System")
    print("=" * 50)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check environment variables
    if not MAIN_TOKEN and not MAIN_TOKEN_2 and not TOKENS:
        print("⚠️ Warning: No Discord tokens found in environment variables")
        print("Please set MAIN_TOKEN, MAIN_TOKEN_2, and/or TOKENS in your .env file")
        print()
    
    # Create bot manager
    bot_manager = CompleteDiscordBotManager()
    
    try:
        # Initialize bots if tokens are available
        if MAIN_TOKEN or MAIN_TOKEN_2 or TOKENS:
            print("🔄 Initializing Discord bots...")
            bot_manager.initialize_all_bots()
            print("✅ Discord bots initialized")
        
        print("🚀 Starting web server...")
        print("📱 Access the dashboard at: http://localhost:3000")
        print("🛑 Press Ctrl+C to stop")
        print()
        
        # Run web server
        bot_manager.run_web_server(debug=False)
        
    except KeyboardInterrupt:
        print("\n📥 Shutting down...")
        bot_manager.add_log("info", "System shutdown requested")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        return 1
    
    print("✅ Discord Bot Manager stopped")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)