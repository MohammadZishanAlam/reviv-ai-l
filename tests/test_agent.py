import pytest
from src.agent import heuristic_diagnose

def test_bank_downtime_diagnosis():
    payment = {
        "payment_id": "pay_fail_1",
        "amount": 400000,
        "bank": "HDFC",
        "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "error_description": "Core banking server timeout"
    }
    telemetry = {"status": "DEGRADED", "success_rate": 65.0}
    
    res = heuristic_diagnose(payment, telemetry)
    assert res["failure_class"] == "BANK_DOWNTIME_TRANSIENT"
    assert res["delay_minutes"] > 0
    assert "HDFC" in res["personalized_message"]

def test_limit_exceeded_diagnosis():
    payment = {
        "payment_id": "pay_fail_2",
        "amount": 10000000,
        "bank": "SBIN",
        "error_code": "INSUFFICIENT_FUNDS_OR_LIMIT_EXCEEDED",
        "error_description": "Daily limit exceeded"
    }
    telemetry = {"status": "HEALTHY", "success_rate": 99.2}
    
    res = heuristic_diagnose(payment, telemetry)
    assert res["failure_class"] == "USER_LIMIT_EXCEEDED"
    assert res["fallback_method"] == "CARD"
    assert res["delay_minutes"] == 0

def test_friction_high_cart_discount():
    payment = {
        "payment_id": "pay_fail_3",
        "amount": 850000, # Rs 8,500.00
        "bank": "ICIC",
        "error_code": "BAD_REQUEST_OTP_TIMEOUT",
        "error_description": "OTP input session timed out"
    }
    telemetry = {"status": "HEALTHY", "success_rate": 99.0}
    
    res = heuristic_diagnose(payment, telemetry)
    assert res["failure_class"] == "AUTH_FRICTION_TIMEOUT"
    assert res["incentive_discount_pct"] == 5.0
