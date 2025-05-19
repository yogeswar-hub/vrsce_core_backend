
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
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, inspect
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
from com.dimcon.synthera.resources.database_and_users.standard_user import StandardUser
from com.dimcon.synthera.resources.integration.status import Status

# ================================
# Model Definition
# ================================
class Integration(Base):
    __tablename__ = 'integration'

    integration_id = Column(Integer, primary_key=True, autoincrement=True)
    integration_name = Column(String(255), nullable=False, unique=True)
    status_id = Column(Integer, ForeignKey(Status.status_id, ondelete='CASCADE'), nullable=False)
    created_by = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    updated_by = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'integration' created.")
        else:
            logger.info("Table 'integration' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'integration' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_integration = cls(**kwargs)
        session.add(new_integration)
        session.commit()
        logger.info(f"Inserted integration with ID: {new_integration.integration_id}")
        return new_integration

    @classmethod
    def update_table(cls, session: Session, integration_id: int, **kwargs):
        integration = session.query(cls).filter_by(integration_id=integration_id).first()
        if integration:
            for key, value in kwargs.items():
                setattr(integration, key, value)
            session.commit()
            logger.info(f"Updated integration with ID: {integration_id}")
        else:
            logger.warning(f"Integration with ID {integration_id} not found.")
        return integration

    @classmethod
    def get_table(cls, session: Session, **filters):
        integrations = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(integrations)} integration(s) with filters: {filters}")
        return integrations

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    Integration.create_table(engine)
    logger.info("Integration table creation complete.")

    # # # Insert integration
    # new_integration = Integration.insert_table(
    #     session,
    #     integration_name="Salesforce Sync",
    #     status_id=1,  # Assuming 'Active' is status_id = 1
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("Integration insertion complete.")

    # # Fetch integrations
    # integrations = Integration.get_table(session, status_id=1)
    # logger.info(f"Fetched {len(integrations)} integration(s) with status_id = 1.")

    # # Update integration
    # updated_integration = Integration.update_table(
    #     session,
    #     integration_id=new_integration.integration_id,
    #     integration_name="Salesforce Connector",
    #     updated_by=2
    # )
    # if updated_integration:
    #     logger.info(f"Integration ID {updated_integration.integration_id} updated successfully.")
    # else:
    #     logger.warning("Integration not found. Cannot update.")

    # # Drop table
    # Integration.drop_table(engine)
    # logger.info("Integration table dropped.")

    # Close session
    db_util.close_session()
    logger.info("Session closed. Integration script completed.")
