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
from com.dimcon.synthera.resources.documents.document import Document
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee

# ================================
# Model Definition
# ================================
class DocumentHistory(Base):
    __tablename__ = 'document_history'

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey(Document.document_id, ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)
    performed_by = Column(Integer, ForeignKey(Employee.emp_id))
    performed_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    notes = Column(Text)

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'document_history' created.")
        else:
            logger.info("Table 'document_history' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'document_history' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        history = cls(**kwargs)
        session.add(history)
        session.commit()
        logger.info(f"Inserted document history record with ID: {history.history_id}")
        return history

    @classmethod
    def update_table(cls, session: Session, history_id: int, **kwargs):
        history = session.query(cls).filter_by(history_id=history_id).first()
        if history:
            for key, value in kwargs.items():
                setattr(history, key, value)
            session.commit()
            logger.info(f"Updated document history record with ID: {history_id}")
        else:
            logger.warning(f"Document history with ID {history_id} not found.")
        return history

    @classmethod
    def get_table(cls, session: Session, **filters):
        histories = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(histories)} history record(s) with filters: {filters}")
        return histories

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # # Create table
    # DocumentHistory.create_table(engine)
    # logger.info("DocumentHistory table creation complete.")

    # # Insert history record
    new_history = DocumentHistory.insert_table(
        session,
        document_id=1,
        action="Uploaded",
        performed_by=1,
        notes="Initial document upload."
    )
    logger.info("DocumentHistory record insertion complete.")

    # # Fetch history records
    # histories = DocumentHistory.get_table(session, document_id=1)
    # logger.info(f"Fetched {len(histories)} history record(s) for document_id = 1.")

    # # Update history record
    # updated_history = DocumentHistory.update_table(
    #     session,
    #     history_id=new_history.history_id,
    #     notes="Corrected file format.",
    #     performed_by=2
    # )
    # if updated_history:
    #     logger.info(f"History ID {updated_history.history_id} updated successfully.")
    # else:
    #     logger.warning("History record not found. Cannot update.")

    # # Drop table
    # DocumentHistory.drop_table(engine)
    # logger.info("DocumentHistory table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. DocumentHistory script completed.")
