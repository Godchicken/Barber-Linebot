from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import re
from datetime import timedelta


SCOPE = ["https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"]

google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(google_creds, scopes=SCOPE)
client = gspread.authorize(creds)

sheet = client.open_by_key("1FFRK6b1fP1wzr9tqYp7t9PwoDYytIU3GSJIy_SDYpLo").sheet1


def add_income(amount, note):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        sheet.append_row([now, note, amount])
    except Exception as e:
        print("ERROR ตอนเขียนชีท:", e)

# ====== ฟังก์ชันเก็บคิวลงไฟล์ ======
def load_queue():
    try:
        with open("queue.txt", "r") as f:
            return int(f.read())
    except:
        return 0

def save_queue(q):
    with open("queue.txt", "w") as f:
        f.write(str(q))
        
# ====== ระบบเก็บเวลาจอง ======

def load_bookings():
    try:
        with open("bookings.txt", "r") as f:
            return f.read().splitlines()
    except:
        return []

def save_bookings(bookings):
    with open("bookings.txt", "w") as f:
        for b in bookings:
            f.write(b + "\n")


app = Flask(__name__)

# ===== ใส่ค่าของคุณ =====
CHANNEL_ACCESS_TOKEN = "eAiPK/EgQ0hkrs9Zzapdq+ZiYyv1Fs7XtHfBw56JEuxBPz9dLKmIG/Q6Uje5WcQsfV5e2VuKop0vnbfZRVVOYWN4I5a+kBAF9dzT4/6lYHLuYXTiMBlyblXWLmsb56zWhPb8ca/SvS5IWQzOmy8klgdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "0afdedf6016247aa48fbec10f62b36eb"
ADMIN_GROUP_ID = "C614f87b3b0ad0c08b5212c371c2233fb"  # groupId ต้องขึ้นต้นด้วย C

BARBERS = 1
AVG_TIME = 40  # นาทีต่อหัว
BOOKING_BLOCK = 60 # ล็อกจองล่วงหน้า 1 ชั่วโมง
OPEN_HOUR = 9
CLOSE_HOUR = 20


line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.lower().strip()
    source_type = event.source.type

    # ====== ส่วนแอดมิน (ในกลุ่มเท่านั้น) ======
    if source_type == "group":
        group_id = event.source.group_id

        if group_id == ADMIN_GROUP_ID:
            queue_count = load_queue()

            if user_text in ["/add", "add"]:
                queue_count += 1
                save_queue(queue_count)
                reply = f"เพิ่มคิวแล้ว ตอนนี้มี {queue_count} คิว 💈"

            elif user_text == "+1":
                queue_count += 1
                save_queue(queue_count)
                add_income(100, "ลูกค้าเข้าร้าน")
                reply = f"เพิ่มคิวแล้ว 💈\nบันทึกรายรับ 100 บาทแล้ว 💰\nตอนนี้มี {queue_count} คิว"

            elif user_text in ["/done", "-1", "done"]:
                if queue_count > 0:
                    queue_count -= 1
                    save_queue(queue_count)
                reply = f"เหลือ {queue_count} คิว 💈"

            elif user_text in ["/status", "เช็ก", "เหลือ"]:
                wait_time = (queue_count * AVG_TIME) // BARBERS
                reply = f"คิวทั้งหมด: {queue_count}\nรอประมาณ: {wait_time} นาที 💈"

            else:
                reply = "คำสั่งแอดมิน:\n/add\n/done\n/status"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )

        return  # ออกจาก group ไม่ให้ไปตอบลูกค้า


    # ====== ส่วนลูกค้าทักแชท ======
    queue_count = load_queue()

    # ===============================
    # จอง
    # ===============================
    if "จอง" in user_text:
        now = datetime.now()
        current_hour = now.hour

        if current_hour >= CLOSE_HOUR or current_hour < OPEN_HOUR:
            reply = f"ขออภัยครับ 🙏\nตอนนี้ร้านปิดแล้ว\nร้านเปิด {OPEN_HOUR}:00–{CLOSE_HOUR}:00 ครับ 💈"

        else:
            match = re.search(r"\d{1,2}:\d{2}", user_text)

            # ===== จองคิวปกติ =====
            if user_text.strip() == "จอง":

                queue_count += 1
                save_queue(queue_count)

                wait_time = (queue_count - 1) * AVG_TIME // BARBERS
                add_income(100, "จองคิวหน้าร้าน")

                reply = f"จองคิวสำเร็จ 💈\nตอนนี้มี {queue_count} คิว\nรอประมาณ {wait_time} นาที"

                line_bot_api.push_message(
                    ADMIN_GROUP_ID,
                    TextSendMessage(text=f"🔔 มีลูกค้าจองคิวหน้าร้าน\nตอนนี้ {queue_count} คิว")
                )

            # ===== จองเวลา =====
            elif match:

                slot_time_str = match.group()
                new_time = datetime.strptime(slot_time_str, "%H:%M")

                if new_time.hour >= CLOSE_HOUR or new_time.hour < OPEN_HOUR:
                    reply = f"ขออภัยครับ 🙏\nเวลานี้อยู่นอกเวลาทำการ\nร้านเปิด {OPEN_HOUR}:00–{CLOSE_HOUR}:00 ครับ 💈"

                else:
                    bookings = load_bookings()
                    conflict = False

                    for b in bookings:
                        booked_time = datetime.strptime(b, "%H:%M")
                        diff = abs((new_time - booked_time).total_seconds()) / 60

                        if diff < BOOKING_BLOCK:
                            conflict = True
                            break

                    if conflict:
                        reply = "เวลานั้นไม่ว่างแล้วครับ 😅"
                    else:
                        bookings.append(slot_time_str)
                        save_bookings(bookings)

                        add_income(100, f"จองเวลา {slot_time_str}")

                        reply = f"จองเวลา {slot_time_str} สำเร็จแล้วครับ 💈"

                        line_bot_api.push_message(
                            ADMIN_GROUP_ID,
                            TextSendMessage(text=f"🔔 มีลูกค้าจองเวลา {slot_time_str}")
                         )

            else:
                reply = "กรุณาพิมพ์แบบนี้นะครับ 👇\nจอง 16:00"

    elif "เปิด" in user_text or "ปิด" in user_text:
        reply = f"ร้านเปิด {OPEN_HOUR}:00–{CLOSE_HOUR}:00 ครับ 💈"

    elif "กี่คิว" in user_text:

        if queue_count == 0:
            reply = "ตอนนี้ยังไม่มีคิว เข้ามาได้เลยครับ 💈"
        else:
            wait_time = (queue_count * AVG_TIME) // BARBERS
            reply = f"ตอนนี้มี {queue_count} คิว\nรอประมาณ {wait_time} นาที 💈"

    else:
        reply = "พิมพ์ 'จอง' หรือ 'จอง 16:00' ได้เลยครับ 💈"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



































