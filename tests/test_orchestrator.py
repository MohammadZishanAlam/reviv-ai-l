import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.models import Transaction, RecoveryAttempt
from src.orchestrator import create_recovery_payment_link, mark_recovery_completed

def test_payment_link_generation():
    link_info = create_recovery_payment_link(
        amount_paise=299900,
        description="Recovery test",
        customer_info={"name": "Test User", "email": "test@example.com"},
        reference_id="tx_123"
    )
    assert link_info["id"] is not None
    assert "rzp.io" in link_info["short_url"]

def test_mark_recovery_completed():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(bind=test_engine)
    db = TestingSession()
    
    tx = Transaction(
        id="pay_complete_test",
        order_id="order_1",
        amount=199900,
        status="failed"
    )
    db.add(tx)
    db.commit()
    
    success = mark_recovery_completed(db, "pay_complete_test")
    assert success is True
    
    updated_tx = db.query(Transaction).filter(Transaction.id == "pay_complete_test").first()
    assert updated_tx.status == "recovered"
    db.close()
