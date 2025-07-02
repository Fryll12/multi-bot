import discum
import threading
import time
import os
import random
from flask import Flask, request, render_template_string
from dotenv import load_dotenv
import re

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
heart_mode_enabled = False
heart_threshold = 50

acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "UN the Wicker"
]

spam_enabled = False
spam_message = ""
spam_channel_id = "1388802151723302912"

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
            global auto_grab_enabled, heart_mode_enabled, heart_threshold

            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])

                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled:
                        print("Phát hiện tự drop! Đọc tin nhắn Karibbit ngay lập tức...")
                        read_karibbit(bot)

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

def read_karibbit(bot):
    global heart_mode_enabled, heart_threshold
    try:
        messages = bot.getMessages(main_channel_id, num=5).json()
        for msg in messages:
            author_id = msg.get("author", {}).get("id")
            if author_id == karibbit_id:
                desc = msg.get("content", "")
                lines = desc.split('\n')

                print("===== Tin nhắn Karibbit đọc được =====")
                for line in lines:
                    print(line)
                print("===== Kết thúc tin nhắn =====")

                heart_numbers = []
                for i, line in enumerate(lines[:3]):
                    matches = re.findall(r'`(\d+)`', line)
                    if len(matches) >= 2:
                        num = int(matches[1])
                        heart_numbers.append(num)
                        print(f"Dòng {i+1} số tim: {num}")
                    else:
                        heart_numbers.append(0)
                        print(f"Dòng {i+1} không tìm thấy số tim, mặc định 0")

                if sum(heart_numbers) == 0:
                    print("Không có số tim nào, bỏ qua.")
                    return

                max_num = max(heart_numbers)
                max_index = heart_numbers.index(max_num)

                if heart_mode_enabled and max_num < heart_threshold:
                    print(f"Tổng số tim cao nhất {max_num} < {heart_threshold}, bỏ qua.")
                    return

                emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                delay = {"1️⃣": 1.3, "2️⃣": 2.3, "3️⃣": 3}[emoji]
                print(f"Chọn dòng {max_index+1} với {max_num} tim → Emoji {emoji} → Grab sau {delay}s")
                
                def grab():
                    try:
                        bot.addReaction(main_channel_id, msg["id"], emoji)
                        print("Đã thả emoji grab!")
                        bot.sendMessage(ktb_channel_id, "kt b")
                        print("Đã nhắn 'kt b'!")
                    except Exception as e:
                        print(f"Lỗi khi grab hoặc nhắn kt b: {e}")

                threading.Timer(delay, grab).start()
                break
    except Exception as e:
        print(f"Lỗi khi đọc tin nhắn Karibbit: {e}")

main_bot = create_bot(main_token, is_main=True)

for token in tokens:
    bots.append(create_bot(token, is_main=False))

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
    <br><br>
    <label>Tiêu chuẩn số tim:</label>
    <input type="number" name="threshold" value="{threshold}" min="0">
    <button type="submit">Cập nhật</button>
</form>
<p>Chế độ số tim hiện tại: <b>{heartstatus}</b></p>
<hr>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, heart_mode_enabled, heart_threshold
    msg_status = ""

    if request.method == "POST":
        toggle = request.form.get("toggle")
        heartmode = request.form.get("heartmode")
        threshold = request.form.get("threshold")

        if toggle:
            auto_grab_enabled = toggle == "on"
            msg_status = f"Tự grab {'đã bật' if auto_grab_enabled else 'đã tắt'}"

        if heartmode:
            heart_mode_enabled = heartmode == "on"
            msg_status = f"Chế độ số tim {'đã bật' if heart_mode_enabled else 'đã tắt'}"

        if threshold is not None:
            try:
                heart_threshold = int(threshold)
                msg_status = f"Tiêu chuẩn số tim cập nhật: {heart_threshold}"
            except:
                msg_status = "Số tim không hợp lệ!"

    status = "Đang bật" if auto_grab_enabled else "Đang tắt"
    heartstatus = "Đang bật" if heart_mode_enabled else "Đang tắt"
    return HTML.format(status=status, heartstatus=heartstatus, threshold=heart_threshold) + (f"<p>{msg_status}</p>" if msg_status else "")

def keep_alive():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=keep_alive, daemon=True).start()

while True:
    time.sleep(60)
