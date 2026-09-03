import hmac
import hashlib
import json
import pytest
from src.webhook import verify_webhook_signature, parse_webhook_payload

def test_valid_hmac_signature():
    secret = "test_webhook_secret_123"
    raw_payload = json.dumps({"event": "payment.failed", "id": "evt_123"}).encode("utf-8")
    
    signature = hmac.new(secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()
    
    assert verify_webhook_signature(raw_payload, signature, secret) is True

def test_tampered_hmac_signature():
    secret = "test_webhook_secret_123"
    raw_payload = json.dumps({"event": "payment.failed", "id": "evt_123"}).encode("utf-8")
    fake_signature = "bad_tampered_signature_hex"
    
    assert verify_webhook_signature(raw_payload, fake_signature, secret) is False

def test_parse_webhook_payload():
    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_999",
                    "order_id": "order_test_888",
                    "amount": 250000,
                    "currency": "INR",
                    "method": "upi",
                    "bank": "HDFC",
                    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "error_description": "Bank network connection timed out",
                    "notes": {"customer_name": "Rohan Verma"}
                }
            }
        }
    }
    parsed = parse_webhook_payload(payload)
    assert parsed["payment_id"] == "pay_test_999"
    assert parsed["amount"] == 250000
    assert parsed["bank"] == "HDFC"
    assert parsed["error_code"] == "BAD_REQUEST_PAYMENT_TIMED_OUT"
    assert parsed["customer_name"] == "Rohan Verma"
