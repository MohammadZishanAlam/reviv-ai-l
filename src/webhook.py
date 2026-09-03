import hmac
import hashlib
import json
import logging
from sqlalchemy.orm import Session
from src.config import settings
from src.models import Transaction, AuditLog

logger = logging.getLogger("reviv_ail.webhook")

def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """
    Verifies Razorpay HMAC SHA256 Webhook Signature.
    Supports simulation bypass when in development/mock mode with placeholder secret.
    """
    if not signature:
        return False
        
    # If in development and using mock signatures, allow bypass for seamless hackathon demos
    if not settings.is_razorpay_live and signature.startswith("sim_signature_"):
        return True
        
    try:
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Error computing webhook signature: {e}")
        return False

def parse_webhook_payload(payload: dict) -> dict:
    """Extract standard payment failure or success properties from Razorpay payload."""
    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    
    if not entity and "payment_link" in payload.get("payload", {}):
        entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        
    payment_id = entity.get("id", "")
    order_id = entity.get("order_id") or entity.get("reference_id", "")
    amount = entity.get("amount", 0)
    currency = entity.get("currency", "INR")
    method = entity.get("method", "upi")
    bank = entity.get("bank") or entity.get("acquirer_data", {}).get("bank", "")
    
    error_code = entity.get("error_code", "")
    error_description = entity.get("error_description", "")
    error_source = entity.get("error_source", "")
    error_step = entity.get("error_step", "")
    error_reason = entity.get("error_reason", "")
    
    customer_contact = entity.get("contact", "")
    customer_email = entity.get("email", "")
    customer_name = entity.get("notes", {}).get("customer_name", "Valued Customer")
    
    return {
        "event": event,
        "payment_id": payment_id,
        "order_id": order_id,
        "amount": amount,
        "currency": currency,
        "method": method,
        "bank": bank,
        "error_code": error_code,
        "error_description": error_description,
        "error_source": error_source,
        "error_step": error_step,
        "error_reason": error_reason,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_contact": customer_contact,
        "raw_entity": entity
    }

def process_failed_payment_event(db: Session, parsed: dict) -> Transaction:
    """Ingests failed payment event, enforces idempotency, and records audit trail."""
    payment_id = parsed["payment_id"]
    
    # Check for duplicate event (Idempotency)
    existing = db.query(Transaction).filter(Transaction.id == payment_id).first()
    if existing:
        logger.info(f"Payment {payment_id} already ingested. Skipping re-ingestion.")
        return existing
        
    transaction = Transaction(
        id=payment_id,
        order_id=parsed["order_id"],
        amount=parsed["amount"],
        currency=parsed["currency"],
        status="failed",
        method=parsed["method"],
        bank=parsed["bank"],
        error_code=parsed["error_code"],
        error_description=parsed["error_description"],
        error_source=parsed["error_source"],
        error_step=parsed["error_step"],
        error_reason=parsed["error_reason"],
        customer_name=parsed["customer_name"],
        customer_email=parsed["customer_email"],
        customer_contact=parsed["customer_contact"]
    )
    db.add(transaction)
    
    # Audit log
    audit = AuditLog(
        transaction_id=payment_id,
        event_type="PAYMENT_FAILED_INGESTED",
        details=json.dumps({
            "error_code": parsed["error_code"],
            "amount": parsed["amount"],
            "bank": parsed["bank"]
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(transaction)
    return transaction
