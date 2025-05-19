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
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session

from com.dimcon.synthera.utilities.log_handler import LoggerManager
import logging
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

# Create engine using the centralized connection utility and instantiate session management.
engine = get_engine()
db_util = DBSessionUtil(engine)

# ================================
# Project-specific imports
# ================================

from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.integration.status import Status
from com.dimcon.synthera.resources.integration.integration import Integration
from com.dimcon.synthera.resources.database_and_users.standard_user import StandardUser

# ================================
# Model Definition
# ================================
class ChimeMeetingIntegration(Base):
    __tablename__ = 'chime_meeting_integrations'

    meeting_id = Column(String, primary_key=True)
    audio_host_url = Column(String)
    screen_data_url = Column(String)
    screen_sharing_url = Column(String)
    screen_viewing_url = Column(String)
    signaling_url = Column(String)
    turn_control_url = Column(String)
    attendee_id = Column(String)
    join_token = Column(String)
    status_id = Column(Integer, ForeignKey(Status.status_id))
    integration_id = Column(Integer, ForeignKey(Integration.integration_id))
    created_by = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    updated_by = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))
     
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'chime_meeting_integrations' created.")
        else:
            logger.info("Table 'chime_meeting_integrations' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'chime_meeting_integrations' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_meeting = cls(**kwargs)
        session.add(new_meeting)
        session.commit()
        logger.info(f"Inserted Chime meeting with ID: {new_meeting.meeting_id}")
        return new_meeting

    @classmethod
    def update_table(cls, session: Session, meeting_id: str, **kwargs):
        meeting = session.query(cls).filter_by(meeting_id=meeting_id).first()
        if meeting:
            for key, value in kwargs.items():
                setattr(meeting, key, value)
            session.commit()
            logger.info(f"Updated Chime meeting with ID: {meeting_id}")
        else:
            logger.warning(f"Meeting with ID {meeting_id} not found.")
        return meeting

    @classmethod
    def get_table(cls, session: Session, **filters):
        meetings = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(meetings)} meeting(s) with filters: {filters}")
        return meetings

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    ChimeMeetingIntegration.create_table(engine)
    logger.info("ChimeMeetingIntegration table creation complete.")

    # # # Insert meeting
    # new_meeting = ChimeMeetingIntegration.insert_table(
    #     session,
    #     meeting_id="meeting-xyz-123",
    #     audio_host_url="https://audio.example.com",
    #     screen_data_url="https://data.example.com",
    #     screen_sharing_url="https://share.example.com",
    #     screen_viewing_url="https://view.example.com",
    #     signaling_url="https://signal.example.com",
    #     turn_control_url="https://turn.example.com",
    #     attendee_id="attendee-001",
    #     join_token="token-abc123",
    #     status_id=1,
    #     integration_id=1,
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("ChimeMeetingIntegration record insertion complete.")

    # # Fetch meetings
    # meetings = ChimeMeetingIntegration.get_table(session, status_id=1)
    # logger.info(f"Fetched {len(meetings)} meetings for status_id = 1.")

    # # Update meeting
    # updated_meeting = ChimeMeetingIntegration.update_table(
    #     session,
    #     meeting_id="meeting-xyz-123",
    #     signaling_url="https://signal-updated.example.com"
    # )
    # if updated_meeting:
    #     logger.info(f"Meeting ID {updated_meeting.meeting_id} updated successfully.")
    # else:
    #     logger.warning("Meeting not found. Cannot update.")

    # # Drop table
    # ChimeMeetingIntegration.drop_table(engine)
    # logger.info("ChimeMeetingIntegration table dropped.")

    # Close session
    db_util.close_session()
    logger.info("Session closed. ChimeMeetingIntegration script completed.")
