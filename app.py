from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# ===== ใส่ค่าของคุณทีหลัง =====
CHANNEL_ACCESS_TOKEN = "eAiPK/EgQ0hkrs9Zzapdq+ZiYyv1Fs7XtHfBw56JEuxBPz9dLKmIG/Q6Uje5WcQsfV5e2VuKop0vnbfZRVVOYWN4I5a+kBAF9dzT4/6lYHLuYXTiMBlyblXWLmsb56zWhPb8ca/SvS5IWQzOmy8klgdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "0afdedf6016247aa48fbec10f62b36eb"
ADMIN_GROUP_ID = "YOUR_ADMIN_GROUP_ID"

BARBERS = 1
AVG_TIME = 30

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

queue_count = 0

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
    global queue_count

    user_text = event.message.text.lower()
    source_type = event.source.type

    if source_type == "group":
        group_id = event.source.group_id

        if group_id == ADMIN_GROUP_ID:

            if user_text == "/add":
                queue_count += 1
                reply = f"เพิ่มคิวแล้ว ตอนนี้มี {queue_count} คิว"

            elif user_text == "/done":
                if queue_count > 0:
                    queue_count -= 1
                reply = f"เหลือ {queue_count} คิว"

            elif user_text == "/status":
                wait_time = (queue_count * AVG_TIME) // BARBERS
                reply = f"คิวทั้งหมด: {queue_count}\nรอประมาณ: {wait_time} นาที"

            else:
                reply = "คำสั่ง: /add /done /status"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )

        return

    if "กี่คิว" in user_text:
        wait_time = (queue_count * AVG_TIME) // BARBERS

        if queue_count == 0:
            reply = "ตอนนี้ยังไม่มีคิว เข้ามาได้เลยค่ะ 💈"
        else:
            reply = f"ตอนนี้มี {queue_count} คิว รอประมาณ {wait_time} นาทีค่ะ 💈"

    elif "ราคา" in user_text:
        reply = "ตัดผม 150 บาทค่ะ 💇"

    elif "เปิด" in user_text:
        reply = "ร้านเปิด 10:00–20:00 ทุกวันค่ะ 😊"

    else:
        reply = "สวัสดีค่ะ สอบถามคิวพิมพ์ 'กี่คิว' ได้เลยค่ะ 💈"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=10000)
