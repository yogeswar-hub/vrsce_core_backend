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
from com.dimcon.synthera.resources.integration.status import Status
from com.dimcon.synthera.resources.integration.api_workflow_status import APIWorkflowStatus
from com.dimcon.synthera.resources.leads.leads_details import LeadDetail
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee

# ================================
# Model Definition
# ================================
class APIIntegration(Base):
    __tablename__ = 'api_integration'

    api_integration_id = Column(Integer, primary_key=True, autoincrement=True)
    integration_name = Column(String(255), nullable=False, unique=True)
    api_key = Column(Text, nullable=False)
    api_secret = Column(Text, nullable=False)
    base_url = Column(String(255), nullable=False)
    status_id = Column(Integer, ForeignKey(Status.status_id, ondelete="CASCADE"), nullable=False)
    workflow_status_id = Column(Integer, ForeignKey(APIWorkflowStatus.api_workflow_status_id, ondelete="CASCADE"), nullable=False)
    lead_id = Column(Integer, ForeignKey(LeadDetail.lead_id, ondelete="SET NULL"))
    created_by = Column(Integer, ForeignKey(Employee.emp_id, ondelete="SET NULL"))
    updated_by = Column(Integer, ForeignKey(Employee.emp_id, ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'api_integration' created.")
        else:
            logger.info("Table 'api_integration' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'api_integration' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_integration = cls(**kwargs)
        session.add(new_integration)
        session.commit()
        logger.info(f"Inserted API integration with ID: {new_integration.api_integration_id}")
        return new_integration

    @classmethod
    def update_table(cls, session: Session, api_integration_id: int, **kwargs):
        integration = session.query(cls).filter_by(api_integration_id=api_integration_id).first()
        if integration:
            for key, value in kwargs.items():
                setattr(integration, key, value)
            session.commit()
            logger.info(f"Updated API integration with ID: {api_integration_id}")
        else:
            logger.warning(f"API integration with ID {api_integration_id} not found for update.")
        return integration

    @classmethod
    def get_table(cls, session: Session, **filters):
        integrations = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(integrations)} API integration(s) with filters: {filters}")
        return integrations

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    APIIntegration.create_table(engine)
    logger.info("APIIntegration table creation complete.")

    # # # Insert integration
    # new_integration = APIIntegration.insert_table(
    #     session,
    #     integration_name="Zoom Sync",
    #     api_key="zoom-key-abc",
    #     api_secret="zoom-secret-xyz",
    #     base_url="https://api.zoom.us/v2",
    #     status_id=1,
    #     workflow_status_id=1,
    #     lead_id=1,
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("APIIntegration record insertion complete.")

    # # Fetch integrations
    # integrations = APIIntegration.get_table(session, status_id=1)
    # logger.info(f"Fetched {len(integrations)} integrations for status_id = 1.")

    # # Update integration
    # updated_integration = APIIntegration.update_table(
    #     session,
    #     api_integration_id=new_integration.api_integration_id,
    #     base_url="https://new-api.zoom.us/v2",
    #     updated_by=2
    # )
    # if updated_integration:
    #     logger.info(f"Integration ID {updated_integration.api_integration_id} updated successfully.")
    # else:
    #     logger.warning("APIIntegration record not found. Cannot update.")

    # # Drop table
    # APIIntegration.drop_table(engine)
    # logger.info("APIIntegration table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. APIIntegration script completed.")
