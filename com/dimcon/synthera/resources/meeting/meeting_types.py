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
class MeetingType(Base):
    __tablename__ = 'meeting_types'

    meeting_type_id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_type_name = Column(String(100), nullable=False, unique=True)
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
            logger.info("Table 'meeting_types' created.")
        else:
            logger.info("Table 'meeting_types' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'meeting_types' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        meeting_type = cls(**kwargs)
        session.add(meeting_type)
        session.commit()
        logger.info(f"Inserted meeting type with ID: {meeting_type.meeting_type_id}")
        return meeting_type

    @classmethod
    def update_table(cls, session: Session, meeting_type_id: int, **kwargs):
        mt = session.query(cls).filter_by(meeting_type_id=meeting_type_id).first()
        if mt:
            for key, value in kwargs.items():
                setattr(mt, key, value)
            session.commit()
            logger.info(f"Updated meeting type with ID: {meeting_type_id}")
        else:
            logger.warning(f"Meeting type with ID {meeting_type_id} not found.")
        return mt

    @classmethod
    def get_table(cls, session: Session, **filters):
        types = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(types)} meeting type(s) with filters: {filters}")
        return types

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    MeetingType.create_table(engine)
    logger.info("MeetingTypes table creation complete.")

    # # # Insert meeting type
    # new_type = MeetingType.insert_table(
    #     session,
    #     meeting_type_name="Client Demo",
    #     description="Demonstration for clients",
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("MeetingTypes insertion complete.")

    # # Fetch meeting types
    # types = MeetingType.get_table(session, meeting_type_name="Client Demo")
    # logger.info(f"Fetched {len(types)} meeting type(s) with name 'Client Demo'.")

    # # Update meeting type
    # updated_type = MeetingType.update_table(
    #     session,
    #     meeting_type_id=new_type.meeting_type_id,
    #     description="Updated description for client demo",
    #     updated_by=2
    # )
    # if updated_type:
    #     logger.info(f"Meeting type ID {updated_type.meeting_type_id} updated successfully.")
    # else:
    #     logger.warning("Meeting type not found. Cannot update.")

    # # Drop table
    # MeetingType.drop_table(engine)
    # logger.info("MeetingTypes table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. MeetingTypes script completed.")
