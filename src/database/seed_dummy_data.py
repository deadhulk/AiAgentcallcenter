"""
Seeder script to populate the database with dummy call logs and user data for functional testing.
Run this script once to add sample data.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.database.models import Base, CallLog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

# Adjust the database URL as per your config
DATABASE_URL = "sqlite:///test_dummy.db"

def seed():
    engine = create_engine(DATABASE_URL)
    # Drop all tables and recreate
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Dummy call logs with more realistic data
    dummy_logs = [
        CallLog(
            session_id="session_001",
            customer_id="CUST001",
            start_time=datetime.datetime.utcnow() - datetime.timedelta(minutes=10),
            end_time=datetime.datetime.utcnow() - datetime.timedelta(minutes=5),
            transcript="Hello, I need help with my order #12345"
        ),
        CallLog(
            session_id="session_002",
            customer_id="CUST002",
            start_time=datetime.datetime.utcnow() - datetime.timedelta(minutes=30),
            end_time=datetime.datetime.utcnow() - datetime.timedelta(minutes=25),
            transcript="What are your working hours?"
        ),
        CallLog(
            session_id="session_003",
            customer_id="VIP001",
            start_time=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            end_time=datetime.datetime.utcnow() - datetime.timedelta(minutes=45),
            transcript="I'd like to upgrade my service plan"
        ),
        CallLog(
            session_id="session_004",
            customer_id="TEST001",
            start_time=datetime.datetime.utcnow() - datetime.timedelta(days=1),
            end_time=datetime.datetime.utcnow() - datetime.timedelta(days=1, minutes=-10),
            transcript="Testing the system functionality"
        ),
    ]

    session.add_all(dummy_logs)
    session.commit()
    print("Dummy call logs added.")

if __name__ == "__main__":
    seed()
