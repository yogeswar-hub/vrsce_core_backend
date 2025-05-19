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
from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey, inspect
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
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee

# ================================
# Model Definition
# ================================
class MeetingsCompleted(Base):
    __tablename__ = 'meetings_completed'

    completed_id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey(Meeting.meeting_id, ondelete="CASCADE"))
    completed_by = Column(Integer, ForeignKey(Employee.emp_id))
    completed_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    meeting_summary = Column(Text)

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'meetings_completed' created.")
        else:
            logger.info("Table 'meetings_completed' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'meetings_completed' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        completed = cls(**kwargs)
        session.add(completed)
        session.commit()
        logger.info(f"Inserted completed meeting record with ID: {completed.completed_id}")
        return completed

    @classmethod
    def update_table(cls, session: Session, completed_id: int, **kwargs):
        record = session.query(cls).filter_by(completed_id=completed_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()
            logger.info(f"Updated completed meeting record with ID: {completed_id}")
        else:
            logger.warning(f"Completed meeting record with ID {completed_id} not found.")
        return record

    @classmethod
    def get_table(cls, session: Session, **filters):
        records = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(records)} completed meeting record(s) with filters: {filters}")
        return records

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # # Create table
    # MeetingsCompleted.create_table(engine)
    # logger.info("MeetingsCompleted table creation complete.")

    # # Insert completed meeting
    new_meeting = MeetingsCompleted.insert_table(
        session,
        meeting_id=1,
        completed_by=1,
        meeting_summary="Discussed next quarter goals and deliverables."
    )
    logger.info("MeetingsCompleted insertion complete.")

    # # Fetch completed meetings
    # meetings = MeetingsCompleted.get_table(session, meeting_id=1)
    # logger.info(f"Fetched {len(meetings)} completed meeting(s) for meeting ID 1.")

    # # Update meeting summary
    # updated = MeetingsCompleted.update_table(
    #     session,
    #     completed_id=new_meeting.completed_id,
    #     meeting_summary="Added notes on follow-up actions",
    #     completed_by=2
    # )
    # if updated:
    #     logger.info(f"Completed meeting ID {updated.completed_id} updated successfully.")
    # else:
    #     logger.warning("Completed meeting not found. Cannot update.")

    # # Drop table
    # MeetingsCompleted.drop_table(engine)
    # logger.info("MeetingsCompleted table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. MeetingsCompleted script completed.")
