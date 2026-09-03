import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(64), primary_key=True, index=True) # e.g. pay_xxxxx
    order_id = Column(String(64), index=True, nullable=True)
    amount = Column(Integer, nullable=False) # In Paise (e.g. 299900 = Rs 2999.00)
    currency = Column(String(8), default="INR")
    status = Column(String(32), default="failed") # failed, in_recovery, recovered, abandoned
    method = Column(String(32), nullable=True) # upi, card, netbanking
    bank = Column(String(32), nullable=True) # HDFC, SBIN, ICIC
    
    # Razorpay Error Fields
    error_code = Column(String(64), nullable=True)
    error_description = Column(Text, nullable=True)
    error_source = Column(String(32), nullable=True)
    error_step = Column(String(32), nullable=True)
    error_reason = Column(String(64), nullable=True)
    
    # Customer Details
    customer_name = Column(String(128), default="Valued Customer")
    customer_email = Column(String(128), nullable=True)
    customer_contact = Column(String(32), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    recovery_attempts = relationship("RecoveryAttempt", back_populates="transaction")

class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String(64), ForeignKey("transactions.id"), index=True)
    
    failure_class = Column(String(64), nullable=False)
    root_cause_explanation = Column(Text, nullable=False)
    recommended_channel = Column(String(32), default="WHATSAPP")
    scheduled_delay_minutes = Column(Integer, default=0)
    discount_pct = Column(Float, default=0.0)
    
    original_amount = Column(Integer, nullable=False)
    final_amount = Column(Integer, nullable=False)
    
    razorpay_payment_link_id = Column(String(64), nullable=True)
    payment_link_url = Column(String(256), nullable=True)
    personalized_message = Column(Text, nullable=True)
    
    status = Column(String(32), default="scheduled") # scheduled, dispatched, completed, expired
    dispatched_at = Column(DateTime, nullable=True)
    recovered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transaction = relationship("Transaction", back_populates="recovery_attempts")

class BankTelemetry(Base):
    __tablename__ = "bank_telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_code = Column(String(16), unique=True, index=True) # HDFC, SBIN, ICIC, AXIS
    bank_name = Column(String(64), nullable=False)
    health_status = Column(String(16), default="HEALTHY") # HEALTHY, DEGRADED, DOWN
    success_rate = Column(Float, default=99.0) # e.g. 98.5%
    avg_latency_ms = Column(Integer, default=450)
    active_incident = Column(String(256), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
