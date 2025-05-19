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
class TaskPriority(Base):
    __tablename__ = 'task_priority'

    priority_id = Column(Integer, primary_key=True, autoincrement=True)
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
            logger.info("Table 'task_priority' created.")
        else:
            logger.info("Table 'task_priority' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'task_priority' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_priority = cls(**kwargs)
        session.add(new_priority)
        session.commit()
        logger.info(f"Inserted task priority with ID: {new_priority.priority_id}")
        return new_priority

    @classmethod
    def update_table(cls, session: Session, priority_id: int, **kwargs):
        priority = session.query(cls).filter_by(priority_id=priority_id).first()
        if priority:
            for key, value in kwargs.items():
                setattr(priority, key, value)
            session.commit()
            logger.info(f"Updated task priority with ID: {priority_id}")
        else:
            logger.warning(f"Task priority with ID {priority_id} not found.")
        return priority

    @classmethod
    def get_table(cls, session: Session, **filters):
        priorities = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(priorities)} task priority record(s) with filters: {filters}")
        return priorities

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    TaskPriority.create_table(engine)
    logger.info("TaskPriority table creation complete.")

    # # # Insert task priority
    # new_priority = TaskPriority.insert_table(
    #     session,
    #     priority_name="High",
    #     description="Requires immediate attention",
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("TaskPriority insertion complete.")

    # # Fetch priorities
    # priorities = TaskPriority.get_table(session, priority_name="High")
    # logger.info(f"Fetched {len(priorities)} matching task priorities.")

    # # Update priority
    # updated_priority = TaskPriority.update_table(
    #     session,
    #     priority_id=new_priority.priority_id,
    #     description="Top-level urgent priority",
    #     updated_by=2
    # )
    # if updated_priority:
    #     logger.info(f"TaskPriority ID {updated_priority.priority_id} updated successfully.")
    # else:
    #     logger.warning("TaskPriority not found. Cannot update.")

    # # Drop table
    # TaskPriority.drop_table(engine)
    # logger.info("TaskPriority table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. TaskPriority script completed.")
