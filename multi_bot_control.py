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
heart_threshold = 50
last_drop_msg_id = ""
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
            global auto_grab_enabled, heart_threshold, last_drop_msg_id

            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])

                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled:
                        print("\n[Bot] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                        last_drop_msg_id = msg["id"]  # Lưu lại ID tin nhắn drop

                        def read_karibbit():
                            time.sleep(1)
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg in messages:
                                author_id = msg.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg and len(msg["embeds"]) > 0:
                                    desc = msg["embeds"][0].get("description", "")
                                    print(f"\n[Bot] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot] ===== Kết thúc tin nhắn =====\n")

                                    lines = desc.split('\n')
                                    heart_numbers = []

                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            num = int(matches[1])
                                            heart_numbers.append(num)
                                            print(f"[Bot] Dòng {i+1} số tim: {num}")
                                        else:
                                            heart_numbers.append(0)
                                            print(f"[Bot] Dòng {i+1} không tìm thấy số tim, mặc định 0")

                                    if sum(heart_numbers) == 0:
                                        print("[Bot] Không có số tim nào, bỏ qua.\n")
                                    else:
                                        max_num = max(heart_numbers)
                                        if max_num < heart_threshold:
                                            print(f"[Bot] Số tim lớn nhất {max_num} < {heart_threshold}, không grab!\n")
                                        else:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 0.9, "2️⃣": 1.7, "3️⃣": 2.2}[emoji]
                                            print(f"[Bot] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")

                                            def grab():
                                                try:
                                                    bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                    print("Đã thả emoji grab!")
                                                    bot.sendMessage(ktb_channel_id, "kt b")
                                                    print("Đã nhắn 'kt b'!")
                                                except Exception as e:
                                                    print(f"Lỗi khi grab hoặc nhắn kt b: {e}")

                                            threading.Timer(delay, grab).start()

                                    break

                        threading.Thread(target=read_karibbit).start()

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

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
<h3>Thiết lập mức tim tiêu chuẩn</h3>
<form method="POST">
    <label>Mức tim hiện tại:</label>
    <input type="number" name="heart_threshold" value="{heart_threshold}" min="0">
    <button type="submit">Cập nhật</button>
</form>
<hr>
<h3>Gửi danh sách mã theo acc chọn</h3>
<form method="POST">
    <label>Chọn acc:</label>
    <select name="acc_index">
""" + "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names)) + """
    </select>
    <br><br>
    <input type="text" name="prefix" placeholder="Nội dung mẫu (vd: kt n)" style="width:300px">
    <br><br>
    <textarea name="codes" placeholder="Danh sách mã, cách nhau dấu phẩy" style="width:300px; height:100px"></textarea>
    <br><br>
    <label>Thời gian cách nhau (giây):</label>
    <input type="number" step="0.1" name="delay" placeholder="11" value="11">
    <br><br>
    <button type="submit" name="send_codes" value="1">Gửi</button>
</form>
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
    global auto_grab_enabled, spam_enabled, spam_message, heart_threshold
    msg_status = ""

    if request.method == "POST":
        msg = request.form.get("message")
        quickmsg = request.form.get("quickmsg")
        toggle = request.form.get("toggle")
        send_codes = request.form.get("send_codes")
        spamtoggle = request.form.get("spamtoggle")
        spammsg = request.form.get("spammsg", "")
        heart_threshold_form = request.form.get("heart_threshold")

        if msg:
            for idx, bot in enumerate(bots):
                try:
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, msg)).start()
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn: {e}")
            msg_status = "Đã gửi thủ công thành công!"

        if quickmsg:
            for idx, bot in enumerate(bots):
                try:
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, quickmsg)).start()
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn: {e}")
            msg_status = f"Đã gửi lệnh {quickmsg} thành công!"

        if toggle:
            auto_grab_enabled = toggle == "on"
            msg_status = f"Tự grab {'đã bật' if auto_grab_enabled else 'đã tắt'}"

        if heart_threshold_form:
            try:
                heart_threshold = int(heart_threshold_form)
                msg_status = f"Đã cập nhật mức tim tiêu chuẩn: {heart_threshold}"
            except:
                msg_status = "Mức tim không hợp lệ!"

        if send_codes:
            acc_index = int(request.form.get("acc_index", 0))
            prefix = request.form.get("prefix", "").strip()
            codes_raw = request.form.get("codes", "")
            delay = float(request.form.get("delay", "11"))

            if acc_index < 0 or acc_index >= len(bots):
                return "Acc không hợp lệ!"

            codes = [c.strip() for c in codes_raw.split(",") if c.strip()]
            if not prefix or not codes:
                return "Thiếu nội dung mẫu hoặc danh sách mã!"

            bot = bots[acc_index]
            acc_name = acc_names[acc_index]

            for i, code in enumerate(codes):
                try:
                    threading.Timer(delay * i, bot.sendMessage, args=(other_channel_id, f"{prefix} {code}")).start()
                    print(f"[{acc_name}] → Đã lên lịch gửi sau {delay * i}s: {prefix} {code}")
                except Exception as e:
                    print(f"Lỗi gửi mã: {e}")

            msg_status = "Đã bắt đầu gửi mã!"

        if spamtoggle:
            spam_enabled = spamtoggle == "on"
            spam_message = spammsg.strip()
            msg_status = f"Spam {'đã bật' if spam_enabled else 'đã tắt'}"

    status = "Đang bật" if auto_grab_enabled else "Đang tắt"
    spamstatus = "Đang bật" if spam_enabled else "Đang tắt"
    return HTML.format(status=status, spamstatus=spamstatus, spammsg=spam_message, heart_threshold=heart_threshold) + (f"<p>{msg_status}</p>" if msg_status else "")

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
