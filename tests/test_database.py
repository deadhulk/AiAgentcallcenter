import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, CallLog

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_create_call_log(db_session):
    call_log = CallLog(
        session_id="test-session-123",
        customer_id="customer-456",
        start_time=datetime.utcnow()
    )
    db_session.add(call_log)
    db_session.commit()
    
    saved_log = db_session.query(CallLog).filter_by(session_id="test-session-123").first()
    assert saved_log is not None
    assert saved_log.customer_id == "customer-456"
    assert saved_log.end_time is None

def test_update_call_log(db_session):
    # Create initial call log
    call_log = CallLog(
        session_id="test-session-789",
        customer_id="customer-012",
        start_time=datetime.utcnow()
    )
    db_session.add(call_log)
    db_session.commit()
    
    # Update the call log
    call_log.end_time = datetime.utcnow()
    call_log.transcript = "Test conversation transcript"
    db_session.commit()
    
    # Verify updates
    updated_log = db_session.query(CallLog).filter_by(session_id="test-session-789").first()
    assert updated_log.end_time is not None
    assert updated_log.transcript == "Test conversation transcript"