from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
import base64

app = Flask(__name__)
CORS(app)

# ================== ENV VARIABLES ==================
PAYHERO_API_USERNAME = os.getenv("PAYHERO_API_USERNAME")
PAYHERO_API_PASSWORD = os.getenv("PAYHERO_API_PASSWORD")
PAYHERO_CHANNEL_ID = os.getenv("PAYHERO_CHANNEL_ID")  # OPTIONAL
CALLBACK_URL = os.getenv("CALLBACK_URL")

PAYHERO_URL = "https://backend.payhero.co.ke/api/v2/payments"
# ===================================================


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "OK", "service": "PAYHERO BACKEND LIVE"}), 200


# ================== STK PUSH ==================
@app.route("/api/stk-push", methods=["POST"])
def stk_push():
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

        # 🔐 Build Basic Auth
        auth_string = f"{PAYHERO_API_USERNAME}:{PAYHERO_API_PASSWORD}"
        auth_token = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # ================= PAYLOAD =================
        payload = {
            "amount": int(amount),
            "phone_number": phone,
            "external_reference": reference,
            "customer_name": customer_name,
            "provider": "mpesa",  # ✅ FIXED (no hyphen)
            "callback_url": CALLBACK_URL
        }

        # ✅ ONLY include channel_id if provided
        #if PAYHERO_CHANNEL_ID:
            #payload["channel_id"] = int(PAYHERO_CHANNEL_ID)

        # ================= REQUEST =================
        response = requests.post(
            PAYHERO_URL,
            json=payload,
            headers=headers,
            timeout=30
        )

        print("=== STK PUSH REQUEST ===")
        print("PAYLOAD:", payload)
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)

        try:
            return jsonify(response.json()), response.status_code
        except:
            return jsonify({"raw_response": response.text}), response.status_code

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


# ================== CALLBACK ==================
@app.route("/api/payhero/callback", methods=["POST"])
def payhero_callback():
    try:
        data = request.get_json(force=True)

        print("=== PAYHERO CALLBACK RECEIVED ===")
        print(data)

        status = data.get("status")

        if status == "success":
            print("✅ Payment Successful")
        else:
            print("⚠️ Payment Failed / Pending")

        return jsonify({"status": "received"}), 200

    except Exception as e:
        print("❌ CALLBACK ERROR:", str(e))
        return jsonify({"error": "callback failed"}), 500


# ================== RUN ==================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
