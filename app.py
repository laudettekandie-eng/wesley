from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time

app = Flask(__name__)

# ✅ Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ================== ENV VARIABLES ==================
PAYHERO_API_USERNAME = os.getenv("PAYHERO_API_USERNAME")
PAYHERO_API_PASSWORD = os.getenv("PAYHERO_API_PASSWORD")
PAYHERO_CHANNEL_ID = os.getenv("PAYHERO_CHANNEL_ID")
CALLBACK_URL = os.getenv("CALLBACK_URL")

PAYHERO_BASE_URL = "https://backend.payhero.co.ke/api/v2"
# ==================================================


# ✅ Fix preflight (important for Vercel frontend)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "OK", "service": "PayHero Backend"}), 200


# ================== AUTH TOKEN ==================
def get_access_token():
    try:
        url = f"{PAYHERO_BASE_URL}/oauth/token"

        response = requests.post(
            url,
            auth=(PAYHERO_API_USERNAME, PAYHERO_API_PASSWORD),
            data={"grant_type": "client_credentials"},
            timeout=30
        )

        response.raise_for_status()

        data = response.json()
        token = data.get("access_token")

        if not token:
            raise Exception("No access token returned")

        return token

    except Exception as e:
        print("❌ TOKEN ERROR:", str(e))
        return None


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

        # ✅ Format phone to 254...
        if phone.startswith("0"):
            phone = "254" + phone[1:]

        # ================= TOKEN =================
        access_token = get_access_token()

        if not access_token:
            return jsonify({"error": "Failed to get access token"}), 500

        # ================= STK PUSH =================
        url = f"{PAYHERO_BASE_URL}/payments"

        payload = {
            "amount": int(amount),
            "phone_number": phone,
            "account_reference": reference,
            "transaction_desc": f"Payment by {customer_name}",
            "callback_url": CALLBACK_URL
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

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
        # PayHero usually sends status + transaction info
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
