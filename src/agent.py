import json
import time
import logging
from typing import Dict, Any
from src.config import settings

logger = logging.getLogger("reviv_ail.agent")

DIAGNOSTIC_SYSTEM_PROMPT = """
You are Reviv-AI-l, an autonomous fintech diagnostic agent specializing in Indian digital payment failures on Razorpay.
Your goal is to inspect a failed transaction payload and bank health telemetry, then output a structured JSON diagnostic decision.

TAXONOMY CLASSES:
1. BANK_DOWNTIME_TRANSIENT: Issuer bank CBS timeout, switch degradation, or gateway 504/500 errors.
2. USER_LIMIT_EXCEEDED: Exceeded daily/monthly UPI limit or card limit (e.g. INSUFFICIENT_FUNDS or LIMIT_EXCEEDED).
3. AUTH_FRICTION_TIMEOUT: User took too long entering OTP, closed browser tab, wrong PIN entered, or session expired.
4. PAYMENT_METHOD_INELIGIBLE: Card not enabled for online/international transactions, mandate unsupported.
5. HARD_FAILURE_IRRECOVERABLE: Stolen/blocked card, permanent account freeze, or high-risk fraud flag.

OUTPUT SCHEMA (JSON strictly):
{
  "failure_class": "<ONE_OF_THE_5_CLASSES>",
  "root_cause_explanation": "<Concise 1-2 sentence diagnosis of why it failed>",
  "severity": "<LOW | MEDIUM | HIGH | CRITICAL>",
  "recommended_channel": "<WHATSAPP | SMS | EMAIL>",
  "delay_minutes": <Integer: 0 for friction/limit, 15 to 30 if bank is down>,
  "fallback_method": "<UPI_INTENT | CARD | NETBANKING | QR_CODE>",
  "incentive_discount_pct": <Float: 5.0 for cart > Rs 5000 with friction, else 0.0>,
  "personalized_message": "<Polite, context-aware notification for the customer with place-holder {{link}}>"
}
"""

def heuristic_diagnose(payment_data: dict, bank_health: dict) -> dict:
    """
    Deterministic rule-based fallback when LLM is unavailable or for instant local tests.
    Guarantees failure recovery & zero downtime.
    """
    error_code = str(payment_data.get("error_code") or "").upper()
    error_desc = str(payment_data.get("error_description") or "").lower()
    amount_inr = (payment_data.get("amount") or 0) / 100.0
    bank_status = bank_health.get("status", "HEALTHY")
    customer_name = payment_data.get("customer_name") or "there"
    bank = payment_data.get("bank") or "your bank"

    # Rule 1: Irrecoverable Hard Failure (Stopping Rule)
    if "FRAUD" in error_code or "BLOCKED" in error_code or "STOLEN" in error_code or "SECURITY" in error_code:
        return {
            "failure_class": "HARD_FAILURE_IRRECOVERABLE",
            "root_cause_explanation": "Payment was declined due to permanent risk, fraud, or stolen card block by issuer.",
            "severity": "CRITICAL",
            "recommended_channel": "EMAIL",
            "delay_minutes": 0,
            "fallback_method": "NONE",
            "incentive_discount_pct": 0.0,
            "personalized_message": f"Hi {customer_name}, your payment could not be authorized by your bank due to security restrictions. Please use an alternate payment method."
        }

    # Rule 2: Limit Exceeded / Insufficient Funds
    if "INSUFFICIENT" in error_code or "LIMIT" in error_code or "balance" in error_desc:
        return {
            "failure_class": "USER_LIMIT_EXCEEDED",
            "root_cause_explanation": "UPI or account balance transaction limit exceeded for this issuer.",
            "severity": "MEDIUM",
            "recommended_channel": "WHATSAPP",
            "delay_minutes": 0,
            "fallback_method": "CARD",
            "incentive_discount_pct": 0.0,
            "personalized_message": f"Hi {customer_name}, your UPI limit may have been reached for today. You can complete your order using Credit/Debit Card or NetBanking here: {{link}}"
        }

    # Rule 3: Bank Downtime
    if (bank_status in ["DEGRADED", "DOWN"] 
        or "TIMED_OUT" in error_code 
        or "GATEWAY_TIMEOUT" in error_code
        or ("bank" in error_desc and "server" in error_desc)):
        return {
            "failure_class": "BANK_DOWNTIME_TRANSIENT",
            "root_cause_explanation": f"{bank} servers are experiencing transient core banking delays. Immediate retry would fail.",
            "severity": "HIGH",
            "recommended_channel": "WHATSAPP",
            "delay_minutes": 15,
            "fallback_method": "UPI_INTENT",
            "incentive_discount_pct": 0.0,
            "personalized_message": f"Hi {customer_name}, your payment for Rs. {amount_inr:.0f} encountered temporary server lag at {bank}. We've saved your items! Complete your order safely once bank servers stabilize: {{link}}"
        }

    # Rule 4: Friction / OTP Timeout
    discount = 5.0 if amount_inr >= 3000 else 0.0
    discount_text = " Enjoy an extra 5% recovery discount applied automatically!" if discount > 0 else ""
    return {
        "failure_class": "AUTH_FRICTION_TIMEOUT",
        "root_cause_explanation": "Transaction timed out during 2-Factor Authentication or OTP input.",
        "severity": "LOW",
        "recommended_channel": "WHATSAPP",
        "delay_minutes": 0,
        "fallback_method": "QR_CODE",
        "incentive_discount_pct": discount,
        "personalized_message": f"Hi {customer_name}, looks like your checkout session timed out.{discount_text} Click here to complete your payment in 1 click: {{link}}"
    }

async def diagnose_payment_failure(payment_data: dict, bank_health: dict) -> dict:
    """
    Diagnoses failure root-cause using Gemini LLM with structured output,
    with automatic failover to the heuristic rule matrix.
    """
    start_time = time.time()
    
    # If Gemini is live, use the official SDK
    if settings.is_gemini_live:
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            prompt = f"""
            Analyze this failed transaction:
            - Payment ID: {payment_data.get('payment_id')}
            - Amount: INR {payment_data.get('amount', 0) / 100}
            - Method: {payment_data.get('method')}
            - Bank: {payment_data.get('bank')}
            - Error Code: {payment_data.get('error_code')}
            - Error Desc: {payment_data.get('error_description')}
            - Error Step: {payment_data.get('error_step')}
            - Error Reason: {payment_data.get('error_reason')}
            - Bank Health Telemetry: {json.dumps(bank_health)}
            
            Output strictly valid JSON matching the schema.
            """
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[DIAGNOSTIC_SYSTEM_PROMPT, prompt],
                config={"response_mime_type": "application/json"}
            )
            
            result = json.loads(response.text)
            result["latency_ms"] = int((time.time() - start_time) * 1000)
            result["engine"] = "GEMINI_2.0_FLASH"
            return result
        except Exception as e:
            logger.warning(f"Gemini API call encountered error: {e}. Falling back to heuristic matrix.")
            
    # Fallback to deterministic heuristic engine
    result = heuristic_diagnose(payment_data, bank_health)
    result["latency_ms"] = int((time.time() - start_time) * 1000)
    result["engine"] = "REVIV_HEURISTIC_CORE"
    return result
