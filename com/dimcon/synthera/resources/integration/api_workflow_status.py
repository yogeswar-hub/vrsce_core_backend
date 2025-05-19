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
class APIWorkflowStatus(Base):
    __tablename__ = 'api_workflow_status'

    api_workflow_status_id = Column(Integer, primary_key=True, autoincrement=True)
    status_name = Column(String(50), nullable=False, unique=True)
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
            logger.info("Table 'api_workflow_status' created.")
        else:
            logger.info("Table 'api_workflow_status' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'api_workflow_status' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_status = cls(**kwargs)
        session.add(new_status)
        session.commit()
        logger.info(f"Inserted API workflow status with ID: {new_status.api_workflow_status_id}")
        return new_status

    @classmethod
    def update_table(cls, session: Session, api_workflow_status_id: int, **kwargs):
        status = session.query(cls).filter_by(api_workflow_status_id=api_workflow_status_id).first()
        if status:
            for key, value in kwargs.items():
                setattr(status, key, value)
            session.commit()
            logger.info(f"Updated API workflow status with ID: {api_workflow_status_id}")
        else:
            logger.warning(f"API workflow status with ID {api_workflow_status_id} not found for update.")
        return status

    @classmethod
    def get_table(cls, session: Session, **filters):
        statuses = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(statuses)} API workflow status record(s) with filters: {filters}")
        return statuses

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    APIWorkflowStatus.create_table(engine)
    logger.info("APIWorkflowStatus table creation complete.")

    # # # Insert status
    # new_status = APIWorkflowStatus.insert_table(
    #     session,
    #     status_name="Pending",
    #     description="Workflow is pending execution.",
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("APIWorkflowStatus record insertion complete.")

    # # Fetch statuses
    # statuses = APIWorkflowStatus.get_table(session, status_name="Pending")
    # logger.info(f"Fetched {len(statuses)} status(es) with name = 'Pending'.")

    # # Update status
    # updated_status = APIWorkflowStatus.update_table(
    #     session,
    #     api_workflow_status_id=new_status.api_workflow_status_id,
    #     description="Pending and waiting in queue.",
    #     updated_by=2
    # )
    # if updated_status:
    #     logger.info(f"APIWorkflowStatus ID {updated_status.api_workflow_status_id} updated successfully.")
    # else:
    #     logger.warning("APIWorkflowStatus record not found. Cannot update.")

    # # Drop table
    # APIWorkflowStatus.drop_table(engine)
    # logger.info("APIWorkflowStatus table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. APIWorkflowStatus script completed.")
