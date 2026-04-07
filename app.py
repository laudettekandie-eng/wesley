from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
import base64
from datetime import datetime

app = Flask(__name__)

# ✅ Proper CORS (fixes your error)
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ================== ENV VARIABLES ==================
PAYHERO_API_USERNAME = os.getenv("PAYHERO_API_USERNAME")
PAYHERO_API_PASSWORD = os.getenv("PAYHERO_API_PASSWORD")
PAYHERO_CHANNEL_ID = os.getenv("PAYHERO_CHANNEL_ID")
CALLBACK_URL = os.getenv("CALLBACK_URL")

MKOPO_BASE_URL = os.getenv("MKOPO_BASE_URL", "https://api.mkopohub.com")
MKOPO_PASSKEY = os.getenv("MKOPO_PASSKEY", "YOUR_DEFAULT_PASSKEY")
# ==================================================


# ✅ Fix preflight (VERY IMPORTANT)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "OK", "service": "MKopo Hub Backend"}), 200


# ================== AUTH TOKEN ==================
def get_access_token():
    try:
        url = f"{MKOPO_BASE_URL}/oauth/token"

        response = requests.get(
            url,
            auth=(PAYHERO_API_USERNAME, PAYHERO_API_PASSWORD),
            timeout=30
        )

        data = response.json()
        return data.get("access_token")

    except Exception as e:
        print("TOKEN ERROR:", str(e))
        return None


# ================== PASSWORD ==================
def generate_password():
    shortcode = str(PAYHERO_CHANNEL_ID)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    data_to_encode = shortcode + MKOPO_PASSKEY + timestamp
    password = base64.b64encode(data_to_encode.encode()).decode()

    return password, timestamp


# ================== STK PUSH ==================
@app.route("/api/stk-push", methods=["POST", "OPTIONS"])
def stk_push():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(force=True)

    phone = data.get("phone")
    amount = data.get("amount")
    reference = data.get("reference", f"MK_{int(time.time())}")
    customer_name = data.get("customer_name", "Customer")

    if not phone or not amount:
        return jsonify({"error": "phone and amount are required"}), 400

    # ✅ FIX phone format (254...)
    if phone.startswith("0"):
        phone = "254" + phone[1:]

    access_token = get_access_token()

    if not access_token:
        return jsonify({"error": "Failed to get access token"}), 500

    password, timestamp = generate_password()

    url = f"{MKOPO_BASE_URL}/mpesa/stkpush"

    payload = {
        "BusinessShortCode": str(PAYHERO_CHANNEL_ID),
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": str(PAYHERO_CHANNEL_ID),
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": reference,
        "TransactionDesc": f"Payment by {customer_name}"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )

        print("=== STK PUSH REQUEST ===")
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)

        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        print("REQUEST ERROR:", str(e))
        return jsonify({"error": "Request failed", "details": str(e)}), 500


# ================== CALLBACK ==================
@app.route("/api/payhero/callback", methods=["POST"])
def mkopo_callback():
    data = request.get_json(force=True)

    print("=== CALLBACK RECEIVED ===")
    print(data)

    try:
        callback = data.get("Body", {}).get("stkCallback", {})
        result_code = callback.get("ResultCode")

        if result_code == 0:
            print("✅ Payment Successful")
        else:
            print("❌ Payment Failed")

    except Exception as e:
        print("CALLBACK ERROR:", str(e))

    return jsonify({"status": "received"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
