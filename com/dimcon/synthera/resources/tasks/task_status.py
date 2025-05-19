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
class TaskStatus(Base):
    __tablename__ = 'task_status'

    status_id = Column(Integer, primary_key=True, autoincrement=True)
    status_name = Column(String(100), nullable=False, unique=True)
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
            logger.info("Table 'task_status' created.")
        else:
            logger.info("Table 'task_status' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'task_status' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_status = cls(**kwargs)
        session.add(new_status)
        session.commit()
        logger.info(f"Inserted task status with ID: {new_status.status_id}")
        return new_status

    @classmethod
    def update_table(cls, session: Session, status_id: int, **kwargs):
        status = session.query(cls).filter_by(status_id=status_id).first()
        if status:
            for key, value in kwargs.items():
                setattr(status, key, value)
            session.commit()
            logger.info(f"Updated task status with ID: {status_id}")
        else:
            logger.warning(f"Task status with ID {status_id} not found.")
        return status

    @classmethod
    def get_table(cls, session: Session, **filters):
        statuses = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(statuses)} task status record(s) with filters: {filters}")
        return statuses

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    TaskStatus.create_table(engine)
    logger.info("TaskStatus table creation complete.")

    # # # Insert task status
    # new_status = TaskStatus.insert_table(
    #     session,
    #     status_name="In Progress",
    #     description="Task is currently being worked on.",
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("TaskStatus insertion complete.")

    # # Fetch statuses
    # statuses = TaskStatus.get_table(session, status_name="In Progress")
    # logger.info(f"Fetched {len(statuses)} status entries.")

    # # Update task status
    # updated_status = TaskStatus.update_table(
    #     session,
    #     status_id=new_status.status_id,
    #     description="This task is actively being worked on.",
    #     updated_by=2
    # )
    # if updated_status:
    #     logger.info(f"TaskStatus ID {updated_status.status_id} updated successfully.")
    # else:
    #     logger.warning("TaskStatus not found. Cannot update.")

    # # Drop table
    # TaskStatus.drop_table(engine)
    # logger.info("TaskStatus table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. TaskStatus script completed.")
