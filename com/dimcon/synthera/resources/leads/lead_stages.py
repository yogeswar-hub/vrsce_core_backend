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
import pytz
import logging

# ================================
# Third-party imports
# ================================
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session

# ================================
# Centralized Utilities
# ================================
# Use centralized logger
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

# Use centralized connection and session management utilities
from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

# Create engine and instantiate session management centrally.
engine = get_engine()
db_util = DBSessionUtil(engine)

# ================================
# Project-specific imports
# ================================
from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.database_and_users.management_user import ManagementUser

# ================================
# Model Definition
# ================================
class LeadStage(Base):
    __tablename__ = 'lead_stages'

    lead_stage_id = Column(Integer, primary_key=True, autoincrement=True)
    stage_name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey(ManagementUser.user_id), nullable=False)
    updated_by = Column(Integer, ForeignKey(ManagementUser.user_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'lead_stages' created.")
        else:
            logger.info("Table 'lead_stages' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'lead_stages' dropped.")

    @classmethod
    def insert_table(cls, **kwargs):
        # Inserts a new lead stage using a managed session.
        new_stage = cls(**kwargs)
        with db_util.session_scope() as session:
            session.add(new_stage)
            session.commit()
            logger.info(f"Inserted lead stage with ID: {new_stage.lead_stage_id}")
        return new_stage

    @classmethod
    def update_table(cls, lead_stage_id: int, **kwargs):
        # Updates an existing lead stage using a managed session.
        with db_util.session_scope() as session:
            stage = session.query(cls).filter_by(lead_stage_id=lead_stage_id).first()
            if stage:
                for key, value in kwargs.items():
                    setattr(stage, key, value)
                session.commit()
                logger.info(f"Updated lead stage with ID: {lead_stage_id}")
            else:
                logger.warning(f"Lead stage with ID {lead_stage_id} not found.")
            return stage

    @classmethod
    def get_table(cls, **filters):
        # Fetches lead stages with filters using a managed session.
        with db_util.session_scope() as session:
            stages = session.query(cls).filter_by(**filters).all()
            logger.info(f"Fetched {len(stages)} lead stage(s) with filters: {filters}")
        return stages

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Example main execution section using centralized utilities.
    LeadStage.create_table(engine)
    logger.info("LeadStage table creation complete.")

    # Additional examples (insert, update, fetch, drop) can be added here.
    # For example:
    # new_stage = LeadStage.insert_table(
    #     stage_name="Qualified Lead",
    #     description="The lead has passed initial qualification criteria.",
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("LeadStage insertion complete.")

    # Close any global sessions if needed (typically handled in our session management utility)
    logger.info("LeadStage script completed.")
