from datetime import datetime
from sqlalchemy.orm import Session
from src.models import BankTelemetry

DEFAULT_BANKS = [
    {"code": "HDFC", "name": "HDFC Bank", "status": "HEALTHY", "rate": 99.2, "latency": 320},
    {"code": "SBIN", "name": "State Bank of India", "status": "HEALTHY", "rate": 98.4, "latency": 480},
    {"code": "ICIC", "name": "ICICI Bank", "status": "HEALTHY", "rate": 99.5, "latency": 290},
    {"code": "UTIB", "name": "Axis Bank", "status": "HEALTHY", "rate": 98.9, "latency": 350},
    {"code": "UPI", "name": "NPCI Unified Payments", "status": "HEALTHY", "rate": 99.1, "latency": 210},
]

def seed_bank_telemetry(db: Session):
    """Seed default issuer bank metrics if not already present."""
    for b in DEFAULT_BANKS:
        existing = db.query(BankTelemetry).filter(BankTelemetry.bank_code == b["code"]).first()
        if not existing:
            telemetry = BankTelemetry(
                bank_code=b["code"],
                bank_name=b["name"],
                health_status=b["status"],
                success_rate=b["rate"],
                avg_latency_ms=b["latency"],
                active_incident=None
            )
            db.add(telemetry)
    db.commit()

def get_bank_health(db: Session, bank_code: str) -> dict:
    """Retrieve health status for a specific bank or default to HEALTHY."""
    if not bank_code:
        return {"status": "HEALTHY", "success_rate": 99.0, "active_incident": None}
    
    bank = db.query(BankTelemetry).filter(BankTelemetry.bank_code == bank_code.upper()).first()
    if not bank:
        return {"status": "HEALTHY", "success_rate": 99.0, "active_incident": None}
        
    return {
        "bank_code": bank.bank_code,
        "bank_name": bank.bank_name,
        "status": bank.health_status,
        "success_rate": bank.success_rate,
        "avg_latency_ms": bank.avg_latency_ms,
        "active_incident": bank.active_incident
    }

def set_bank_status(db: Session, bank_code: str, status: str, incident: str = None, success_rate: float = 65.0):
    """Update bank health status for testing or live failure detection."""
    bank = db.query(BankTelemetry).filter(BankTelemetry.bank_code == bank_code.upper()).first()
    if bank:
        bank.health_status = status
        bank.active_incident = incident
        bank.success_rate = success_rate
        bank.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(bank)
    return bank

def get_all_bank_telemetry(db: Session) -> list:
    """Get all telemetry records for the dashboard."""
    seed_bank_telemetry(db)
    return db.query(BankTelemetry).all()
