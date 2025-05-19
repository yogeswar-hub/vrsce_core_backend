# ================================
# Add project root to sys.path
# ================================
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# ================================
# Standard library imports
# ================================
from datetime import datetime

# ================================
# Third-party imports
# ================================
import pytz
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session

# ================================
# Project-specific imports
# ================================
import logging
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil
from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.meeting.meeting import Meeting
from com.dimcon.synthera.resources.meeting.meeting_types import MeetingType
from com.dimcon.synthera.resources.meeting.meeting_priority import MeetingPriority
from com.dimcon.synthera.resources.leads.leads_details import LeadDetail
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee

# ================================
# Model Definition
# ================================
class Calendar(Base):
    __tablename__ = 'calendar'

    calendar_id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey(Meeting.meeting_id, ondelete="CASCADE"), nullable=False)
    meeting_type_id = Column(Integer, ForeignKey(MeetingType.meeting_type_id))
    meeting_priority_id = Column(Integer, ForeignKey(MeetingPriority.meeting_priority_id))
    lead_id = Column(Integer, ForeignKey(LeadDetail.lead_id))
    title = Column(String(255), nullable=False)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True), nullable=False)
    location = Column(String(255))
    description = Column(Text)
    created_by = Column(Integer, ForeignKey(Employee.emp_id))
    updated_by = Column(Integer, ForeignKey(Employee.emp_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'calendar' created.")
        else:
            logger.info("Table 'calendar' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'calendar' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        record = cls(**kwargs)
        session.add(record)
        session.commit()
        logger.info(f"Inserted calendar record with ID: {record.calendar_id}")
        return record

    @classmethod
    def update_table(cls, session: Session, calendar_id: int, **kwargs):
        cal = session.query(cls).filter_by(calendar_id=calendar_id).first()
        if cal:
            for key, value in kwargs.items():
                setattr(cal, key, value)
            session.commit()
            logger.info(f"Updated calendar record with ID: {calendar_id}")
        else:
            logger.warning(f"Calendar record with ID {calendar_id} not found.")
        return cal

    @classmethod
    def get_table(cls, session: Session, **filters):
        entries = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(entries)} calendar record(s) with filters: {filters}")
        return entries

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # # Create table
    # Calendar.create_table(engine)
    # logger.info("Calendar table creation complete.")

    # # Insert record
    new_event = Calendar.insert_table(
        session,
        meeting_id=1,
        meeting_type_id=1,
        meeting_priority_id=1,
        lead_id=1,
        title="Client Kickoff Meeting",
        start_time=datetime(2025, 4, 22, 10, 0, tzinfo=pytz.utc),
        end_time=datetime(2025, 4, 22, 11, 0, tzinfo=pytz.utc),
        location="Zoom",
        description="Kickoff meeting with the client for onboarding",
        created_by=1,
        updated_by=1
    )
    logger.info("Calendar record insertion complete.")

    # # Fetch records
    # events = Calendar.get_table(session, lead_id=1)
    # logger.info(f"Fetched {len(events)} calendar event(s) for lead_id = 1.")

    # # Update record
    # updated_event = Calendar.update_table(
    #     session,
    #     calendar_id=new_event.calendar_id,
    #     location="Google Meet",
    #     updated_by=2
    # )
    # if updated_event:
    #     logger.info(f"Calendar ID {updated_event.calendar_id} updated successfully.")
    # else:
    #     logger.warning("Calendar event not found. Cannot update.")

    # # Drop table
    # Calendar.drop_table(engine)
    # logger.info("Calendar table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. Calendar script completed.")
