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
import logging
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session

# ================================
# Project-specific imports
# ================================
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.database_and_users.management_user import ManagementUser

# ================================
# Model Definition
# ================================
class Organization(Base):
    __tablename__ = 'organization'

    organization_id = Column(Integer, primary_key=True, autoincrement=True)
    organization_name = Column(String(255), nullable=False)
    org_contact_number = Column(String(50))
    org_email = Column(String(255), unique=True)
    org_address = Column(String(255))
    created_by = Column(Integer, ForeignKey(ManagementUser.user_id))
    updated_by = Column(Integer, ForeignKey(ManagementUser.user_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'organization' created.")
        else:
            logger.info("Table 'organization' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'organization' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_org = cls(**kwargs)
        session.add(new_org)
        session.commit()
        logger.info(f"Inserted organization with ID: {new_org.organization_id}")
        return new_org

    @classmethod
    def update_table(cls, session: Session, organization_id: int, **kwargs):
        org = session.query(cls).filter_by(organization_id=organization_id).first()
        if org:
            for key, value in kwargs.items():
                setattr(org, key, value)
            session.commit()
            logger.info(f"Updated organization with ID: {organization_id}")
        else:
            logger.warning(f"Organization with ID {organization_id} not found.")
        return org

    @classmethod
    def get_table(cls, session: Session, **filters):
        orgs = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(orgs)} organization(s) with filters: {filters}")
        return orgs

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create engine using the connect_aurora function
    engine = get_engine()
    
    # Create table
    Organization.create_table(engine)
    logger.info("Organization table creation complete.")

    # Initialize DB session utility and execute within a session_scope
    db_session_util = DBSessionUtil(engine)
    with db_session_util.session_scope() as session:
        # Example usage: Insert organization (currently commented out)
        # new_org = Organization.insert_table(
        #     session,
        #     organization_name="DimCon Inc.",
        #     org_contact_number="123-456-7890",
        #     org_email="contact@dimcon.com",
        #     org_address="123 Synthera Lane",
        #     created_by=1
        # )
        # logger.info("Organization insertion complete.")

        # Example: Fetch organizations (currently commented out)
        # orgs = Organization.get_table(session, organization_name="DimCon Inc.")
        # logger.info(f"Fetched {len(orgs)} organizations named 'DimCon Inc.'.")

        # Example: Update organization (currently commented out)
        # updated_org = Organization.update_table(
        #     session,
        #     organization_id=new_org.organization_id,
        #     org_address="456 Innovation Drive",
        #     updated_by=2
        # )
        # if updated_org:
        #     logger.info(f"Organization ID {updated_org.organization_id} updated successfully.")
        # else:
        #     logger.warning("Organization not found. Cannot update.")
        pass

    logger.info("Session scope completed. Organization script completed.")
