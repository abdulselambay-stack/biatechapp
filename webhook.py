from flask import Flask, request
import json
import datetime

app = Flask(__name__)

VERIFY_TOKEN = "technoglobal123"

# ✅ 1. Meta doğrulaması (GET)
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook doğrulandı.")
        return challenge, 200
    else:
        print("❌ Doğrulama hatası.")
        return "Verification failed", 403


# ✅ 2. Gelen mesajları yakalama (POST)
@app.route("/webhook", methods=["POST"])
def receive():
    data = request.get_json()
    print("📩 Yeni webhook isteği geldi:", json.dumps(data, indent=2, ensure_ascii=False))

    try:
        # WhatsApp mesajı geldiyse
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" in value:
            msg = value["messages"][0]
            sender = msg["from"]
            msg_type = msg["type"]

            if msg_type == "text":
                text = msg["text"]["body"]
                print(f"💬 {sender} → {text}")

                # Burada mesajı dosyaya kaydedelim:
                with open("messages.log", "a") as f:
                    f.write(f"[{datetime.datetime.now()}] {sender}: {text}\n")

        elif "statuses" in value:
            status = value["statuses"][0]
            print(f"📦 Mesaj durumu: {status['status']} → {status['id']}")

    except Exception as e:
        print("⚠️ Webhook parsing hatası:", e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
