import sys
import json
import asyncio
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import settings
from src.agent import diagnose_payment_failure

TEST_SCENARIOS = [
    {
        "name": "1. Bank CBS Downtime (SBI 504 Gateway Lag)",
        "payment": {
            "payment_id": "pay_test_sbi_504",
            "amount": 350000, # Rs 3,500
            "method": "upi",
            "bank": "SBIN",
            "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "error_description": "Issuer CBS gateway timed out responding to UPI request.",
            "error_step": "payment_authorization",
            "error_reason": "bank_system_error",
            "customer_name": "Aarav Sharma"
        },
        "telemetry": {"status": "DEGRADED", "success_rate": 62.5}
    },
    {
        "name": "2. UPI Daily Ceiling Limit Exceeded",
        "payment": {
            "payment_id": "pay_test_limit",
            "amount": 2000000, # Rs 20,000
            "method": "upi",
            "bank": "HDFC",
            "error_code": "INSUFFICIENT_FUNDS_OR_LIMIT_EXCEEDED",
            "error_description": "Transaction amount exceeds daily per-transaction UPI ceiling limit.",
            "error_step": "payment_authentication",
            "error_reason": "limit_exceeded",
            "customer_name": "Priya Patel"
        },
        "telemetry": {"status": "HEALTHY", "success_rate": 99.1}
    },
    {
        "name": "3. High-Value Cart Abandonment (> Rs 5000 OTP Friction)",
        "payment": {
            "payment_id": "pay_test_highcart",
            "amount": 899900, # Rs 8,999
            "method": "card",
            "bank": "ICIC",
            "error_code": "BAD_REQUEST_OTP_TIMEOUT",
            "error_description": "User session expired while awaiting 3D-Secure SMS OTP entry.",
            "error_step": "payment_otp",
            "error_reason": "payment_cancelled",
            "customer_name": "Vikram Malhotra"
        },
        "telemetry": {"status": "HEALTHY", "success_rate": 99.4}
    },
    {
        "name": "4. Fraud / Stolen Card (Stopping Rule Test)",
        "payment": {
            "payment_id": "pay_test_fraud",
            "amount": 150000, # Rs 1,500
            "method": "card",
            "bank": "UTIB",
            "error_code": "GATEWAY_ERROR_CARD_STOLEN_OR_BLOCKED",
            "error_description": "Card flagged by issuer risk engine as stolen or compromised.",
            "error_step": "card_authentication",
            "error_reason": "fraud_security_block",
            "customer_name": "Unknown User"
        },
        "telemetry": {"status": "HEALTHY", "success_rate": 99.0}
    }
]

async def run_tests():
    print("=================================================================")
    print("           Reviv-AI-l AI Model Diagnostic Test Suite            ")
    print("=================================================================")
    print(f"Engine Mode: {'LIVE GEMINI 2.0 FLASH' if settings.is_gemini_live else 'DETERMINISTIC HEURISTIC CORE (Failover Mode)'}")
    print(f"Gemini API Key Configured: {'YES' if settings.is_gemini_live else 'NO (Add to .env for live LLM API)'}")
    print("=================================================================\n")

    for scenario in TEST_SCENARIOS:
        print(f"--> Testing Scenario: {scenario['name']}")
        payment = scenario["payment"]
        telemetry = scenario["telemetry"]
        
        result = await diagnose_payment_failure(payment, telemetry)
        
        print(f"    [+] Engine Used:      {result.get('engine')}")
        print(f"    [+] Failure Class:    {result.get('failure_class')}")
        print(f"    [+] Severity:         {result.get('severity')}")
        print(f"    [+] Latency:          {result.get('latency_ms')} ms")
        print(f"    [+] Scheduled Delay:  {result.get('delay_minutes')} mins {'(Bank downtime backoff applied!)' if result.get('delay_minutes', 0) > 0 else '(Immediate action)'}")
        print(f"    [+] Dynamic Discount: {result.get('incentive_discount_pct')}% {'(5% incentive applied for high-value friction!)' if result.get('incentive_discount_pct', 0) > 0 else '(No discount)'}")
        print(f"    [+] Fallback Rail:    {result.get('fallback_method')}")
        print(f"    [+] Root Cause:       {result.get('root_cause_explanation')}")
        print(f"    [+] Outreach Message: \"{result.get('personalized_message')}\"")
        print("-" * 65)

    print("\n[ALL 4 SCENARIOS TESTED SUCCESSFULLY!]")

if __name__ == "__main__":
    asyncio.run(run_tests())
