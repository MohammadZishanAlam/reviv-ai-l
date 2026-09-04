import json
import logging
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from src.config import settings
from src.database import init_db, get_db
from src.models import Transaction, RecoveryAttempt, BankTelemetry, AuditLog
from src.telemetry import seed_bank_telemetry, get_all_bank_telemetry, set_bank_status
from src.webhook import verify_webhook_signature, parse_webhook_payload, process_failed_payment_event
from src.orchestrator import execute_recovery_pipeline, mark_recovery_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reviv_ail.main")

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Error broadcasting to socket client: {e}")

ws_manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema on startup
    init_db()
    # Seed default bank telemetry
    from src.database import SessionLocal
    db = SessionLocal()
    seed_bank_telemetry(db)
    db.close()
    logger.info(f"Reviv-AI-l initialized. Razorpay live mode: {settings.is_razorpay_live} | Gemini live mode: {settings.is_gemini_live}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Payment Failure Diagnosis & Adaptive Revenue Recovery Engine for Razorpay",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Webhook Ingress -----------------

@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Razorpay Webhook listener with HMAC SHA256 signature verification.
    """
    signature = request.headers.get("X-Razorpay-Signature", "")
    raw_body = await request.body()
    
    # Verify HMAC signature
    is_valid = verify_webhook_signature(raw_body, signature, settings.RAZORPAY_WEBHOOK_SECRET)
    if not is_valid:
        logger.warning("Rejected webhook with invalid HMAC signature.")
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    payload = json.loads(raw_body.decode("utf-8"))
    event = payload.get("event", "")
    logger.info(f"Processing Razorpay webhook event: {event}")
    
    parsed = parse_webhook_payload(payload)
    
    if event == "payment.failed":
        tx = process_failed_payment_event(db, parsed)
        recovery = await execute_recovery_pipeline(db, tx)
        
        # Broadcast real-time update
        await ws_manager.broadcast({
            "type": "PAYMENT_FAILED_PROCESSED",
            "transaction_id": tx.id,
            "amount": tx.amount,
            "bank": tx.bank,
            "failure_class": recovery.failure_class,
            "link_url": recovery.payment_link_url,
            "message": recovery.personalized_message,
            "status": recovery.status
        })
        return {"status": "processed", "recovery_id": recovery.id}
        
    elif event in ["order.paid", "payment.captured", "payment_link.paid"]:
        payment_id = parsed["payment_id"] or parsed["order_id"]
        # Match by transaction id or order id
        tx = db.query(Transaction).filter(
            (Transaction.id == payment_id) | (Transaction.order_id == parsed["order_id"])
        ).first()
        if tx:
            mark_recovery_completed(db, tx.id)
            await ws_manager.broadcast({
                "type": "REVENUE_RECOVERED",
                "transaction_id": tx.id,
                "amount": tx.amount
            })
            return {"status": "recovered", "transaction_id": tx.id}
            
    return {"status": "ignored", "event": event}

# ----------------- REST Endpoints for Dashboard -----------------

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Computes high-level recovery metrics."""
    total_failed = db.query(Transaction).count()
    recovered_txs = db.query(Transaction).filter(Transaction.status == "recovered").all()
    failed_txs = db.query(Transaction).all()
    
    total_at_risk_paise = sum(tx.amount for tx in failed_txs)
    total_recovered_paise = sum(tx.amount for tx in recovered_txs)
    
    recovery_rate = (len(recovered_txs) / total_failed * 100.0) if total_failed > 0 else 0.0
    active_interventions = db.query(RecoveryAttempt).filter(RecoveryAttempt.status.in_(["scheduled", "dispatched"])).count()
    
    return {
        "total_failed_count": total_failed,
        "total_recovered_count": len(recovered_txs),
        "total_at_risk_inr": round(total_at_risk_paise / 100.0, 2),
        "total_recovered_inr": round(total_recovered_paise / 100.0, 2),
        "recovery_rate_pct": round(recovery_rate, 1),
        "active_interventions": active_interventions,
        "is_razorpay_live": settings.is_razorpay_live,
        "is_gemini_live": settings.is_gemini_live
    }

@app.get("/api/transactions")
def list_transactions(db: Session = Depends(get_db)):
    """Fetches recent transactions and their associated recovery attempts."""
    txs = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(30).all()
    results = []
    for tx in txs:
        attempt = db.query(RecoveryAttempt).filter(RecoveryAttempt.transaction_id == tx.id).first()
        results.append({
            "id": tx.id,
            "order_id": tx.order_id,
            "amount_inr": round(tx.amount / 100.0, 2),
            "currency": tx.currency,
            "status": tx.status,
            "method": tx.method,
            "bank": tx.bank,
            "error_code": tx.error_code,
            "error_description": tx.error_description,
            "customer_name": tx.customer_name,
            "created_at": tx.created_at.strftime("%Y-%m-%d %H:%M:%S") if tx.created_at else "",
            "recovery": {
                "id": attempt.id if attempt else None,
                "failure_class": attempt.failure_class if attempt else None,
                "root_cause": attempt.root_cause_explanation if attempt else None,
                "recommended_channel": attempt.recommended_channel if attempt else None,
                "delay_minutes": attempt.scheduled_delay_minutes if attempt else 0,
                "discount_pct": attempt.discount_pct if attempt else 0.0,
                "payment_link_url": attempt.payment_link_url if attempt else None,
                "message": attempt.personalized_message if attempt else None,
                "status": attempt.status if attempt else None
            } if attempt else None
        })
    return results

@app.get("/api/telemetry")
def list_telemetry(db: Session = Depends(get_db)):
    """Lists issuer bank health telemetry."""
    return get_all_bank_telemetry(db)

# ----------------- Interactive Simulator Endpoints -----------------

@app.post("/api/simulate/failure")
async def simulate_failure(payload: dict, db: Session = Depends(get_db)):
    """
    Triggers an end-to-end simulated transaction failure scenario.
    """
    scenario = payload.get("scenario", "BANK_DOWNTIME")
    import uuid
    sim_id = f"pay_sim_{uuid.uuid4().hex[:8]}"
    order_id = f"order_sim_{uuid.uuid4().hex[:6]}"
    
    if scenario == "BANK_DOWNTIME":
        # Simulate SBI Bank Outage
        set_bank_status(db, "SBIN", "DEGRADED", incident="SBI CBS switch latency elevated", success_rate=64.2)
        parsed = {
            "payment_id": sim_id,
            "order_id": order_id,
            "amount": 425000, # Rs 4250.00
            "currency": "INR",
            "method": "upi",
            "bank": "SBIN",
            "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "error_description": "SBI core banking gateway timed out responding to UPI request.",
            "error_source": "bank",
            "error_step": "payment_authorization",
            "error_reason": "bank_system_error",
            "customer_name": "Aarav Sharma",
            "customer_email": "aarav.sharma@example.com",
            "customer_contact": "+919876543210"
        }
    elif scenario == "USER_LIMIT":
        parsed = {
            "payment_id": sim_id,
            "order_id": order_id,
            "amount": 2500000, # Rs 25,000.00
            "currency": "INR",
            "method": "upi",
            "bank": "HDFC",
            "error_code": "PAYMENT_LIMIT_EXCEEDED",
            "error_description": "Transaction amount exceeds daily per-transaction UPI ceiling limit.",
            "error_source": "customer",
            "error_step": "payment_authentication",
            "error_reason": "limit_exceeded",
            "customer_name": "Priya Patel",
            "customer_email": "priya.patel@example.com",
            "customer_contact": "+919812345678"
        }
    else: # HIGH_CART_FRICTION
        parsed = {
            "payment_id": sim_id,
            "order_id": order_id,
            "amount": 899900, # Rs 8,999.00
            "currency": "INR",
            "method": "card",
            "bank": "ICIC",
            "error_code": "BAD_REQUEST_OTP_TIMEOUT",
            "error_description": "User session expired while awaiting 3D-Secure SMS OTP entry.",
            "error_source": "customer",
            "error_step": "payment_otp",
            "error_reason": "payment_cancelled",
            "customer_name": "Vikram Malhotra",
            "customer_email": "vikram.m@example.com",
            "customer_contact": "+919765432109"
        }

    tx = process_failed_payment_event(db, parsed)
    recovery = await execute_recovery_pipeline(db, tx)
    
    # Notify clients via WebSocket
    await ws_manager.broadcast({
        "type": "PAYMENT_FAILED_PROCESSED",
        "transaction_id": tx.id,
        "amount": tx.amount,
        "bank": tx.bank,
        "failure_class": recovery.failure_class,
        "link_url": recovery.payment_link_url,
        "message": recovery.personalized_message,
        "status": recovery.status
    })
    
    return {
        "status": "success",
        "scenario": scenario,
        "transaction_id": tx.id,
        "recovery": {
            "failure_class": recovery.failure_class,
            "root_cause": recovery.root_cause_explanation,
            "link_url": recovery.payment_link_url,
            "discount_pct": recovery.discount_pct,
            "message": recovery.personalized_message
        }
    }

@app.post("/api/simulate/recover/{transaction_id}")
async def simulate_customer_recovery(transaction_id: str, db: Session = Depends(get_db)):
    """Simulates customer clicking the payment link and successfully completing checkout."""
    success = mark_recovery_completed(db, transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    await ws_manager.broadcast({
        "type": "REVENUE_RECOVERED",
        "transaction_id": tx.id,
        "amount": tx.amount
    })
    return {"status": "recovered", "transaction_id": transaction_id, "amount": tx.amount}

@app.post("/api/simulate/batch")
async def simulate_batch_recovery(payload: dict = None, db: Session = Depends(get_db)):
    """
    Executes a comprehensive batch recovery test across 25 diverse transactions,
    measuring money recovered, compliant escalation, stopping rules, and audit trails.
    """
    import random
    import uuid

    names = ["Aarav Sharma", "Priya Patel", "Vikram Malhotra", "Ananya Iyer", "Rohan Verma", "Sneha Reddy", "Aditya Nair", "Kavita Rao", "Rajesh Gupta", "Meera Joshi"]
    banks = ["HDFC", "SBIN", "ICIC", "UTIB"]
    
    batch_results = []
    total_at_risk = 0
    total_recovered = 0
    stopping_rules = 0
    delayed_interventions = 0
    incentives_attached = 0

    # 25 realistic transaction profiles
    profiles = [
        # 8 Bank Downtime
        *([("BANK_DOWNTIME", "BAD_REQUEST_PAYMENT_TIMED_OUT", "Issuer CBS server timeout during UPI debit", "upi", random.randint(1500, 6000))] * 8),
        # 7 High-Cart Friction (> Rs 3000)
        *([("FRICTION", "BAD_REQUEST_OTP_TIMEOUT", "Customer session timed out during OTP entry", "card", random.randint(4500, 15000))] * 7),
        # 7 Limit Exceeded
        *([("LIMIT", "INSUFFICIENT_FUNDS_OR_LIMIT_EXCEEDED", "UPI daily ceiling limit exceeded for account", "upi", random.randint(2000, 10000))] * 7),
        # 3 Stolen Card / Fraud (Stopping Rules)
        *([("FRAUD", "GATEWAY_ERROR_CARD_STOLEN_OR_BLOCKED", "Card blocked by issuer risk sentinel as compromised", "card", random.randint(1000, 5000))] * 3),
    ]

    for p_type, code, desc, method, amount_inr in profiles:
        sim_id = f"pay_batch_{uuid.uuid4().hex[:8]}"
        order_id = f"order_batch_{uuid.uuid4().hex[:6]}"
        amount_paise = amount_inr * 100
        bank = random.choice(banks)
        cust_name = random.choice(names)

        parsed = {
            "payment_id": sim_id,
            "order_id": order_id,
            "amount": amount_paise,
            "currency": "INR",
            "method": method,
            "bank": bank,
            "error_code": code,
            "error_description": desc,
            "error_source": "bank" if p_type == "BANK_DOWNTIME" else "customer",
            "error_step": "payment_authorization",
            "error_reason": "bank_system_error" if p_type == "BANK_DOWNTIME" else code.lower(),
            "customer_name": cust_name,
            "customer_email": f"{cust_name.lower().replace(' ', '.')}@example.com",
            "customer_contact": "+919876543210"
        }

        tx = process_failed_payment_event(db, parsed)
        recovery = await execute_recovery_pipeline(db, tx)
        total_at_risk += amount_inr

        if recovery.failure_class == "HARD_FAILURE_IRRECOVERABLE":
            stopping_rules += 1
        elif recovery.scheduled_delay_minutes > 0:
            delayed_interventions += 1
            # Simulate 65% recovery rate for delayed backoff
            if random.random() < 0.65:
                mark_recovery_completed(db, tx.id)
                total_recovered += amount_inr
        else:
            if recovery.discount_pct > 0:
                incentives_attached += 1
            # Simulate 75% recovery rate for friction/limit fallback
            if random.random() < 0.75:
                mark_recovery_completed(db, tx.id)
                total_recovered += amount_inr

    # Broadcast updated state
    await ws_manager.broadcast({"type": "BATCH_COMPLETED"})

    return {
        "status": "success",
        "batch_size": len(profiles),
        "total_at_risk_inr": total_at_risk,
        "total_recovered_inr": total_recovered,
        "recovery_rate_pct": round((total_recovered / total_at_risk * 100.0), 1) if total_at_risk > 0 else 0.0,
        "stopping_rules_enforced": stopping_rules,
        "bank_downtime_delays": delayed_interventions,
        "incentives_attached": incentives_attached,
        "audit_trail_entries_created": len(profiles)
    }

# ----------------- WebSocket Live Stream -----------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# ----------------- Mount Frontend -----------------

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_dashboard():
    return FileResponse("static/index.html")
