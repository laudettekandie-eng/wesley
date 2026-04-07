from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
import base64

app = Flask(__name__)

# ✅ Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ================== ENV VARIABLES ==================
PAYHERO_API_USERNAME = os.getenv("PAYHERO_API_USERNAME")
PAYHERO_API_PASSWORD = os.getenv("PAYHERO_API_PASSWORD")
PAYHERO_CHANNEL_ID = os.getenv("PAYHERO_CHANNEL_ID")
CALLBACK_URL = os.getenv("CALLBACK_URL")

PAYHERO_URL = "https://backend.payhero.co.ke/api/v2/payments"
# ==================================================


# ✅ Fix preflight (important for frontend)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "OK", "service": "PayHero Backend"}), 200


# ================== STK PUSH ==================
@app.route("/api/stk-push", methods=["POST", "OPTIONS"])
def stk_push():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json(force=True)

        phone = data.get("phone")
        amount = data.get("amount")
        reference = data.get("reference", f"REF_{int(time.time())}")
        customer_name = data.get("customer_name", "Customer")

        if not phone or not amount:
            return jsonify({"error": "phone and amount are required"}), 400

        # ✅ Format phone to 254XXXXXXXXX
        if phone.startswith("0"):
            phone = "254" + phone[1:]

        # ================= AUTH (Basic) =================
        auth_string = f"{PAYHERO_API_USERNAME}:{PAYHERO_API_PASSWORD}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json"
        }

        # ================= PAYLOAD =================
        payload = {
            "amount": int(amount),
            "phone_number": phone,
            "account_reference": reference,
            "transaction_desc": f"Payment by {customer_name}",
            "channel_id": PAYHERO_CHANNEL_ID,
            "provider": "m-pesa",
            "callback_url": CALLBACK_URL
        }

        # ================= REQUEST =================
        response = requests.post(
            PAYHERO_URL,
            json=payload,
            headers=headers,
            timeout=30
        )

        print("=== STK PUSH REQUEST ===")
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)

        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        print("❌ REQUEST ERROR:", str(e))
        return jsonify({"error": "Request failed", "details": str(e)}), 500

    except Exception as e:
        print("❌ GENERAL ERROR:", str(e))
        return jsonify({"error": "Internal server error"}), 500


# ================== CALLBACK ==================
@app.route("/api/payhero/callback", methods=["POST"])
def payhero_callback():
    data = request.get_json(force=True)

    print("=== CALLBACK RECEIVED ===")
    print(data)

    try:
        status = data.get("status")

        if status == "success":
            print("✅ Payment Successful")
        else:
            print("❌ Payment Failed or Pending")

    except Exception as e:
        print("❌ CALLBACK ERROR:", str(e))

    return jsonify({"status": "received"}), 200


# ================== RUN ==================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
