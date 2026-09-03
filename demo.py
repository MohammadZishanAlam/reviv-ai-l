import sys
import hmac
import hashlib
import json
import time
import httpx
from src.config import settings

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

WEBHOOK_URL = "http://127.0.0.1:8000/api/webhooks/razorpay"
SECRET = settings.RAZORPAY_WEBHOOK_SECRET

def send_simulated_webhook():
    print(">> Reviv-AI-l CLI Demo Runner")
    print("--------------------------------------------------")
    
    # 1. Bank Server Downtime Payload
    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_cli_{int(time.time())}",
                    "order_id": f"order_cli_{int(time.time())}",
                    "amount": 499900,
                    "currency": "INR",
                    "method": "upi",
                    "bank": "HDFC",
                    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "error_description": "Issuer CBS gateway timed out responding to UPI debit.",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": "bank_system_error",
                    "contact": "+919876543210",
                    "email": "demo.user@example.com",
                    "notes": {
                        "customer_name": "Kavita Rao"
                    }
                }
            }
        }
    }
    
    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature
    }
    
    print("[*] Dispatching simulated Razorpay payment.failed webhook...")
    try:
        with httpx.Client() as client:
            resp = client.post(WEBHOOK_URL, content=raw_body, headers=headers)
            print(f"[+] Response Code: {resp.status_code}")
            print(f"[+] Response Body: {resp.text}")
            if resp.status_code == 200:
                print("\n[SUCCESS] Webhook successfully ingested and processed by Reviv-AI-l!")
                print(">> Open your dashboard at http://127.0.0.1:8000 to see the live AI diagnosis.")
    except Exception as e:
        print(f"[!] Could not reach {WEBHOOK_URL}: {e}")

if __name__ == "__main__":
    send_simulated_webhook()
