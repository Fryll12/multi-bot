import discum
import threading
import time
import os
import random
import re
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

main_token = os.getenv("MAIN_TOKEN")
tokens = os.getenv("TOKENS").split(",")

main_channel_id = "1386973916563767396"
other_channel_id = "1387406577040101417"
ktb_channel_id = "1376777071279214662"
karibbit_id = "1274445226064220273"
karuta_id = "646937666251915264"

bots = []
main_bot = None
auto_grab_enabled = False
heart_mode_enabled = False
heart_threshold = 50
waiting_karibbit = False
last_drop_msg_id = ""
spam_enabled = False
spam_message = ""
spam_channel_id = "1388802151723302912"
acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker"
]

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
            global auto_grab_enabled, waiting_karibbit, last_drop_msg_id

            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])

                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled and not waiting_karibbit:
                        print("\n[Bot] Phát hiện tự drop! Đọc tin nhắn Karibbit ngay lập tức...\n")
                        last_drop_msg_id = msg["id"]
                        waiting_karibbit = True
                        threading.Thread(target=read_karibbit, args=(bot,)).start()

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

def read_karibbit(bot):
    global waiting_karibbit, heart_mode_enabled, heart_threshold

    try:
        messages = bot.getMessages(main_channel_id, num=5).json()
        for msg in messages:
            if msg.get("author", {}).get("id") == karibbit_id:
                content = msg.get("content", "")
                print("[Bot] ===== Tin nhắn Karibbit đọc được =====")
                print(content)
                print("[Bot] ===== Kết thúc tin nhắn =====")

                lines = content.split('\n')
                heart_numbers = []

                for line in lines[:3]:
                    match = re.findall(r'`(\d+)`', line)
                    if len(match) >= 2:
                        heart_numbers.append(int(match[1]))
                    else:
                        heart_numbers.append(0)

                print(f"[Bot] Số tim: {heart_numbers}")

                if sum(heart_numbers) == 0:
                    print("[Bot] Không có số tim nào, bỏ qua.\n")
                    break

                max_heart = max(heart_numbers)
                max_index = heart_numbers.index(max_heart)
                emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]

                if heart_mode_enabled and max_heart < heart_threshold:
                    print(f"[Bot] Số tim cao nhất {max_heart} < {heart_threshold}, bỏ qua.\n")
                else:
                    delay = {"1️⃣": 1.3, "2️⃣": 2.3, "3️⃣": 3}[emoji]
                    print(f"[Bot] Chọn emoji {emoji} → Grab sau {delay}s")
                    time.sleep(delay)
                    bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                    print("[Bot] Đã thả emoji grab!\n")
                break
    except Exception as e:
        print(f"[Bot] Lỗi đọc Karibbit: {e}")
    waiting_karibbit = False

main_bot = create_bot(main_token, is_main=True)
for token in tokens:
    bots.append(create_bot(token))

app = Flask(__name__)

HTML = """
<h2>Điều khiển bot nhắn tin</h2>
<form method="POST">
    <input type="text" name="message" placeholder="Nhập nội dung..." style="width:300px">
    <button type="submit">Gửi thủ công</button>
</form>
<hr>
<h3>Menu nhanh</h3>
<form method="POST">
    <select name="quickmsg">
        <option value="kc o:w">kc o:w</option>
        <option value="kc o:ef">kc o:ef</option>
        <option value="kc o:p">kc o:p</option>
        <option value="kc e:1">kc e:1</option>
        <option value="kc e:2">kc e:2</option>
        <option value="kc e:3">kc e:3</option>
        <option value="kc e:4">kc e:4</option>
        <option value="kc e:5">kc e:5</option>
        <option value="kc e:6">kc e:6</option>
        <option value="kc e:7">kc e:7</option>
    </select>
    <button type="submit">Gửi</button>
</form>
<hr>
<h3>Auto Grab</h3>
<form method="POST">
    <button name="toggle" value="on" type="submit">Bật</button>
    <button name="toggle" value="off" type="submit">Tắt</button>
</form>
<p>Trạng thái hiện tại: <b>{status}</b></p>
<hr>
<h3>Chế độ tiêu chuẩn số tim</h3>
<form method="POST">
    <button name="heartmode" value="on" type="submit">Bật</button>
    <button name="heartmode" value="off" type="submit">Tắt</button>
    <input type="number" name="heartthreshold" placeholder="Tiêu chuẩn số tim" value="{heart_threshold}" min="0">
    <button type="submit">Cập nhật</button>
</form>
<p>Tiêu chuẩn số tim: <b>{heart_threshold}</b> | Trạng thái: <b>{heart_status}</b></p>
<hr>
<h3>Spam </h3>
<form method="POST">
    <input type="text" name="spammsg" placeholder="Nội dung spam" style="width:300px" value="{spammsg}">
    <button name="spamtoggle" value="on" type="submit">Bật</button>
    <button name="spamtoggle" value="off" type="submit">Tắt</button>
</form>
<p>Spam hiện tại: <b>{spamstatus}</b></p>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, spam_enabled, spam_message, heart_mode_enabled, heart_threshold
    msg_status = ""

    if request.method == "POST":
        toggle = request.form.get("toggle")
        spamtoggle = request.form.get("spamtoggle")
        spammsg = request.form.get("spammsg", "")
        heartmode = request.form.get("heartmode")
        heartthres = request.form.get("heartthreshold")

        if toggle:
            auto_grab_enabled = toggle == "on"
            msg_status = f"Tự grab {'đã bật' if auto_grab_enabled else 'đã tắt'}"

        if spamtoggle:
            spam_enabled = spamtoggle == "on"
            spam_message = spammsg.strip()
            msg_status = f"Spam {'đã bật' if spam_enabled else 'đã tắt'}"

        if heartmode:
            heart_mode_enabled = heartmode == "on"
            msg_status = f"Chế độ tiêu chuẩn số tim {'đã bật' if heart_mode_enabled else 'đã tắt'}"

        if heartthres is not None:
            try:
                heart_threshold = int(heartthres)
                msg_status = f"Đã cập nhật tiêu chuẩn số tim: {heart_threshold}"
            except:
                msg_status = "Lỗi: tiêu chuẩn số tim phải là số nguyên!"

    status = "Đang bật" if auto_grab_enabled else "Đang tắt"
    spamstatus = "Đang bật" if spam_enabled else "Đang tắt"
    heart_status = "Đang bật" if heart_mode_enabled else "Đang tắt"

    return HTML.format(status=status, spamstatus=spamstatus, spammsg=spam_message, heart_status=heart_status, heart_threshold=heart_threshold) + (f"<p>{msg_status}</p>" if msg_status else "")

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
app.run(host="0.0.0.0", port=8080)

while True:
    time.sleep(60)
