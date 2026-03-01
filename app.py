from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json

SCOPE = ["https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"]

google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(google_creds, scopes=SCOPE)
client = gspread.authorize(creds)

sheet = client.open("BarberIncome").sheet1


def add_income(amount, note):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    print("DEBUG: กำลังบันทึกลงชีท", now, note, amount)
    sheet.append_row([now, note, amount])
    print("DEBUG: บันทึกสำเร็จ")

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


app = Flask(__name__)

# ===== ใส่ค่าของคุณ =====
CHANNEL_ACCESS_TOKEN = "eAiPK/EgQ0hkrs9Zzapdq+ZiYyv1Fs7XtHfBw56JEuxBPz9dLKmIG/Q6Uje5WcQsfV5e2VuKop0vnbfZRVVOYWN4I5a+kBAF9dzT4/6lYHLuYXTiMBlyblXWLmsb56zWhPb8ca/SvS5IWQzOmy8klgdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "0afdedf6016247aa48fbec10f62b36eb"
ADMIN_GROUP_ID = "C614f87b3b0ad0c08b5212c371c2233fb"  # groupId ต้องขึ้นต้นด้วย C

BARBERS = 1
AVG_TIME = 40  # นาทีต่อหัว


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

    if "จอง" in user_text:
        queue_count += 1
        save_queue(queue_count)

        add_income(100, "จองคิว")

        wait_time = (queue_count - 1) * AVG_TIME // BARBERS

        reply = (
            f"จองคิวเรียบร้อยแล้วครับ 💈\n"
            f"ตอนนี้มี {queue_count} คิว\n"
            f"คาดว่าจะถึงคิวคุณในประมาณ {wait_time} นาทีครับ 😊"
        )

    elif "กี่คิว" in user_text:
        wait_time = (queue_count * AVG_TIME) // BARBERS

        if queue_count == 0:
            reply = "ตอนนี้ยังไม่มีคิว เข้ามาได้เลยครับ 💈"
        else:
            reply = f"ตอนนี้มี {queue_count} คิว\nรอประมาณ {wait_time} นาทีค่ะ 💈"

    elif "ราคา" in user_text:
        reply = "ตัดผม 100 บาทครับ 💇"
    
    elif "เปิด" in user_text:
        reply = "ร้านเปิด 10:00–20:00 ทุกวันครับ 😊"

    else:
        reply = "สวัสดีค่ะ 😊\nพิมพ์ 'จอง' เพื่อจองคิว หรือ 'กี่คิว' เพื่อตรวจสอบคิวครับ 💈"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

















