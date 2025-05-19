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
from com.dimcon.synthera.resources.database_and_users.standard_user import StandardUser

# ================================
# Model Definition
# ================================
class MeetingPriority(Base):
    __tablename__ = 'meeting_priority'

    meeting_priority_id = Column(Integer, primary_key=True, autoincrement=True)
    priority_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    updated_by = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'meeting_priority' created.")
        else:
            logger.info("Table 'meeting_priority' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'meeting_priority' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        priority = cls(**kwargs)
        session.add(priority)
        session.commit()
        logger.info(f"Inserted meeting priority with ID: {priority.meeting_priority_id}")
        return priority

    @classmethod
    def update_table(cls, session: Session, meeting_priority_id: int, **kwargs):
        mp = session.query(cls).filter_by(meeting_priority_id=meeting_priority_id).first()
        if mp:
            for key, value in kwargs.items():
                setattr(mp, key, value)
            session.commit()
            logger.info(f"Updated meeting priority with ID: {meeting_priority_id}")
        else:
            logger.warning(f"Meeting priority with ID {meeting_priority_id} not found.")
        return mp

    @classmethod
    def get_table(cls, session: Session, **filters):
        priorities = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(priorities)} meeting priority record(s) with filters: {filters}")
        return priorities

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # # Create table
    # MeetingPriority.create_table(engine)
    # logger.info("MeetingPriority table creation complete.")

    # # Insert meeting priority
    new_priority = MeetingPriority.insert_table(
        session,
        priority_name="High",
        description="Critical priority for strategic client meetings.",
        created_by=1,
        updated_by=1
    )
    logger.info("MeetingPriority insertion complete.")

    # # Fetch meeting priorities
    # priorities = MeetingPriority.get_table(session, priority_name="High")
    # logger.info(f"Fetched {len(priorities)} priorities with name 'High'.")

    # # Update meeting priority
    # updated_priority = MeetingPriority.update_table(
    #     session,
    #     meeting_priority_id=new_priority.meeting_priority_id,
    #     description="Updated definition for high priority meetings.",
    #     updated_by=2
    # )
    # if updated_priority:
    #     logger.info(f"Meeting priority ID {updated_priority.meeting_priority_id} updated successfully.")
    # else:
    #     logger.warning("Meeting priority not found. Cannot update.")

    # # Drop table
    # MeetingPriority.drop_table(engine)
    # logger.info("MeetingPriority table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. MeetingPriority script completed.")
