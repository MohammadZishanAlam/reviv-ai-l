import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.config import settings
from src.models import Transaction, RecoveryAttempt, AuditLog
from src.telemetry import get_bank_health
from src.agent import diagnose_payment_failure

logger = logging.getLogger("reviv_ail.orchestrator")

def get_razorpay_client():
    """Initializes Razorpay client if live credentials are configured."""
    if settings.is_razorpay_live:
        try:
            import razorpay
            return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        except Exception as e:
            logger.error(f"Failed to initialize Razorpay client: {e}")
    return None

def create_recovery_payment_link(amount_paise: int, description: str, customer_info: dict, reference_id: str) -> dict:
    """
    Creates a Razorpay dynamic payment link using the official SDK,
    or generates a realistic mock link in simulation mode.
    """
    client = get_razorpay_client()
    if client:
        try:
            payload = {
                "amount": amount_paise,
                "currency": "INR",
                "accept_partial": False,
                "description": description,
                "customer": {
                    "name": customer_info.get("name", "Valued Customer"),
                    "email": customer_info.get("email") or "buyer@example.com",
                    "contact": customer_info.get("contact") or "+919999999999"
                },
                "notify": {
                    "sms": False, # Handled by our adaptive dunning
                    "email": False
                },
                "reminder_enable": True,
                "notes": {
                    "source": "reviv_ai_l",
                    "original_reference": reference_id
                }
            }
            res = client.payment_link.create(payload)
            return {
                "id": res.get("id"),
                "short_url": res.get("short_url"),
                "status": res.get("status", "created")
            }
        except Exception as e:
            logger.error(f"Razorpay API link creation failed: {e}. Generating simulated recovery link.")

    # Simulation fallback
    sim_id = f"plink_sim_{uuid.uuid4().hex[:8]}"
    return {
        "id": sim_id,
        "short_url": f"https://rzp.io/i/{sim_id}",
        "status": "created"
    }

async def execute_recovery_pipeline(db: Session, transaction: Transaction) -> RecoveryAttempt:
    """
    End-to-end recovery pipeline:
    1. Fetches bank health telemetry
    2. Executes AI diagnostic classification
    3. Provisions dynamic Razorpay payment link
    4. Records state & audit trail
    """
    # 1. Bank Telemetry
    bank_health = get_bank_health(db, transaction.bank)
    
    # 2. AI Diagnosis
    payment_dict = {
        "payment_id": transaction.id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "method": transaction.method,
        "bank": transaction.bank,
        "error_code": transaction.error_code,
        "error_description": transaction.error_description,
        "error_source": transaction.error_source,
        "error_step": transaction.error_step,
        "error_reason": transaction.error_reason,
        "customer_name": transaction.customer_name
    }
    diagnosis = await diagnose_payment_failure(payment_dict, bank_health)
    
    # 3. Handle Hard Failures
    if diagnosis["failure_class"] == "HARD_FAILURE_IRRECOVERABLE":
        transaction.status = "abandoned"
        recovery = RecoveryAttempt(
            transaction_id=transaction.id,
            failure_class=diagnosis["failure_class"],
            root_cause_explanation=diagnosis["root_cause_explanation"],
            recommended_channel="NONE",
            scheduled_delay_minutes=0,
            discount_pct=0.0,
            original_amount=transaction.amount,
            final_amount=transaction.amount,
            status="aborted_unrecoverable",
            personalized_message=diagnosis["personalized_message"]
        )
        db.add(recovery)
        
        # Explicit Audit Trail entry for Stopping Rule Enforcement
        audit = AuditLog(
            transaction_id=transaction.id,
            event_type="STOPPING_RULE_TRIGGERED",
            details=f"Stopping rule enforced: {diagnosis['root_cause_explanation']}. Recovery outreach halted to prevent non-compliant escalation.",
            latency_ms=diagnosis.get("latency_ms", 0)
        )
        db.add(audit)
        db.commit()
        db.refresh(recovery)
        return recovery

    # 4. Calculate Dynamic Discount
    discount_pct = diagnosis.get("incentive_discount_pct", 0.0)
    original_amount = transaction.amount
    final_amount = int(original_amount * (1.0 - (discount_pct / 100.0)))
    
    # 5. Create Razorpay Payment Link
    customer_info = {
        "name": transaction.customer_name,
        "email": transaction.customer_email,
        "contact": transaction.customer_contact
    }
    link_data = create_recovery_payment_link(
        amount_paise=final_amount,
        description=f"Order Recovery #{transaction.order_id or transaction.id}",
        customer_info=customer_info,
        reference_id=transaction.id
    )
    
    # 6. Format Outreach Message
    final_message = diagnosis["personalized_message"].replace("{{link}}", link_data["short_url"])
    
    # 7. Record Recovery State
    recovery = RecoveryAttempt(
        transaction_id=transaction.id,
        failure_class=diagnosis["failure_class"],
        root_cause_explanation=diagnosis["root_cause_explanation"],
        recommended_channel=diagnosis.get("recommended_channel", "WHATSAPP"),
        scheduled_delay_minutes=diagnosis.get("delay_minutes", 0),
        discount_pct=discount_pct,
        original_amount=original_amount,
        final_amount=final_amount,
        razorpay_payment_link_id=link_data["id"],
        payment_link_url=link_data["short_url"],
        personalized_message=final_message,
        status="dispatched" if diagnosis.get("delay_minutes", 0) == 0 else "scheduled",
        dispatched_at=datetime.utcnow() if diagnosis.get("delay_minutes", 0) == 0 else None
    )
    db.add(recovery)
    
    transaction.status = "in_recovery"
    
    # Audit log
    audit = AuditLog(
        transaction_id=transaction.id,
        event_type="RECOVERY_DISPATCHED",
        details=f"Class: {diagnosis['failure_class']} | Link: {link_data['short_url']} | Delay: {diagnosis.get('delay_minutes')}m",
        latency_ms=diagnosis.get("latency_ms", 0)
    )
    db.add(audit)
    db.commit()
    db.refresh(recovery)
    return recovery

def mark_recovery_completed(db: Session, transaction_id: str) -> bool:
    """Marks a transaction and its recovery attempt as completed when payment succeeds."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        return False
        
    tx.status = "recovered"
    attempt = db.query(RecoveryAttempt).filter(RecoveryAttempt.transaction_id == transaction_id).first()
    if attempt:
        attempt.status = "completed"
        attempt.recovered_at = datetime.utcnow()
        
    audit = AuditLog(
        transaction_id=transaction_id,
        event_type="REVENUE_RECOVERED",
        details=f"Recovered Amount: Rs. {tx.amount / 100:.2f}"
    )
    db.add(audit)
    db.commit()
    return True
