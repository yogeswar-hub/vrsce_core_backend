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
from sqlalchemy import Column, Integer, String, ARRAY, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# ================================
# Project-specific imports
# ================================
import logging
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil
from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.integration.api_integration import APIIntegration
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee

# ================================
# Model Definition
# ================================
class APIFilesForIntegration(Base):
    __tablename__ = 'api_files_for_integration'

    file_id = Column(Integer, primary_key=True, autoincrement=True)
    api_integration_id = Column(Integer, ForeignKey(APIIntegration.api_integration_id, ondelete="CASCADE"))
    file_name = Column(String(255), nullable=False, unique=True)
    file_type = Column(ARRAY(String), nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_by = Column(Integer, ForeignKey(Employee.emp_id))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'api_files_for_integration' created.")
        else:
            logger.info("Table 'api_files_for_integration' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'api_files_for_integration' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_file = cls(**kwargs)
        session.add(new_file)
        try:
            session.commit()
            logger.info(f"Inserted API file with ID: {new_file.file_id}")
        except IntegrityError:
            session.rollback()
            logger.warning("Integrity Error: Duplicate or invalid data.")
            new_file = None
        return new_file

    @classmethod
    def update_table(cls, session: Session, file_id: int, **kwargs):
        file = session.query(cls).filter_by(file_id=file_id).first()
        if file:
            for key, value in kwargs.items():
                setattr(file, key, value)
            session.commit()
            logger.info(f"Updated API file with ID: {file_id}")
        else:
            logger.warning(f"API file with ID {file_id} not found for update.")
        return file

    @classmethod
    def get_table(cls, session: Session, **filters):
        files = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(files)} file(s) with filters: {filters}")
        return files

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Drop and recreate the table to ensure constraints
    APIFilesForIntegration.drop_table(engine)
    APIFilesForIntegration.create_table(engine)

    # Attempt first insert (should succeed)
    file1 = APIFilesForIntegration.insert_table(
        session,
        api_integration_id=1,
        file_name="zoom_config.json",
        file_type=["json", "config"],
        file_path="/uploads/integrations/zoom_config.json",
        updated_by=1
    )

    # Fetch files to confirm
    files = APIFilesForIntegration.get_table(session, api_integration_id=1)
    logger.info(f"Total files fetched after insertion attempts: {len(files)}")

    # Close session
    session.close()
    logger.info("Session closed. APIFilesForIntegration script completed.")
