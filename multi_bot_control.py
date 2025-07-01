import discum
import threading
import time
import os
import random
import re
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

main_token = os.getenv("MAIN_TOKEN")
tokens = os.getenv("TOKENS").split(",")

main_channel_id = "1386973916563767396"
other_channel_id = "1387406577040101417"
ktb_channel_id = "1376777071279214662"

karuta_id = "646937666251915264"
karibbit_id = "1274445226064220273"

bots = []
main_bot = None
auto_grab_enabled = False
acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker"
]

spam_enabled = False
spam_message = ""
spam_channel_id = "1388802151723302912"

waiting_karibbit = {"status": False, "msg_id": None}

def create_bot(token, is_main=False):
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                print(f"Đã đăng nhập: {user_id} {'(Acc chính)' if is_main else ''}")
            except Exception as e:
                print(f"Lỗi lấy user_id: {e}")

    if is_main:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled, waiting_karibbit

            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])

                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled:
                        print("Phát hiện tự drop → Chờ Karibbit...")
                        waiting_karibbit["status"] = True
                        waiting_karibbit["msg_id"] = msg["id"]

                if author == karibbit_id and channel == main_channel_id and waiting_karibbit["status"]:
                    desc = msg.get("content", "")
                    heart_numbers = re.findall(r"(\d+) ❤️", desc)

                    if len(heart_numbers) >= 3:
                        nums = list(map(int, heart_numbers[:3]))
                        max_index = nums.index(max(nums))
                        emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                        delay = {"1️⃣": 1.3, "2️⃣": 2.3, "3️⃣": 3}[emoji]

                        print(f"Đã đọc số tim: {nums} → Chọn emoji {emoji} → Grab sau {delay}s")

                        def grab():
                            try:
                                bot.addReaction(channel, waiting_karibbit["msg_id"], emoji)
                                print("Đã thả emoji grab!")
                                bot.sendMessage(ktb_channel_id, "kt b")
                                print("Đã nhắn 'kt b'!")
                            except Exception as e:
                                print(f"Lỗi khi grab hoặc nhắn kt b: {e}")

                        threading.Timer(delay, grab).start()
                        waiting_karibbit["status"] = False

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

main_bot = create_bot(main_token, is_main=True)

for token in tokens:
    bots.append(create_bot(token, is_main=False))

# Giữ nguyên phần Flask, spam loop và keep_alive như cũ...
# (Để tiết kiệm, phần Flask form bên dưới cậu giữ nguyên, tớ không dán lại vì không chỉnh vào đó)

app = Flask(__name__)

# Phần HTML và route Flask giữ nguyên code cũ cậu nhé

# Spam loop giữ nguyên

def spam_loop():
    global spam_enabled, spam_message
    while True:
        if spam_enabled and spam_message:
            for idx, bot in enumerate(bots):
                try:
                    bot.sendMessage(spam_channel_id, spam_message)
                    print(f"[{acc_names[idx]}] đã gửi: {spam_message}")
                    time.sleep(2)
                except Exception as e:
                    print(f"Lỗi gửi spam: {e}")
        time.sleep(30)

threading.Thread(target=spam_loop, daemon=True).start()

def keep_alive():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=keep_alive, daemon=True).start()

while True:
    time.sleep(60)
