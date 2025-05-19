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
from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, inspect
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
class DocumentsRecentlyViewed(Base):
    __tablename__ = 'documents_recently_viewed'

    view_id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey(Document.document_id, ondelete="CASCADE"), nullable=False)
    viewed_by = Column(Integer, ForeignKey(Employee.emp_id), nullable=False)
    viewed_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'documents_recently_viewed' created.")
        else:
            logger.info("Table 'documents_recently_viewed' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'documents_recently_viewed' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        record = cls(**kwargs)
        session.add(record)
        session.commit()
        logger.info(f"Inserted recently viewed document record with ID: {record.view_id}")
        return record

    @classmethod
    def update_table(cls, session: Session, view_id: int, **kwargs):
        record = session.query(cls).filter_by(view_id=view_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()
            logger.info(f"Updated recently viewed document record with ID: {view_id}")
        else:
            logger.warning(f"Record with ID {view_id} not found.")
        return record

    @classmethod
    def get_table(cls, session: Session, **filters):
        results = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(results)} recently viewed record(s) with filters: {filters}")
        return results

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # # Create table
    # DocumentsRecentlyViewed.create_table(engine)
    # logger.info("DocumentsRecentlyViewed table creation complete.")

    # # Insert recently viewed record
    new_view = DocumentsRecentlyViewed.insert_table(
        session,
        document_id=1,
        viewed_by=1
    )
    logger.info("DocumentsRecentlyViewed record insertion complete.")

    # # Fetch recently viewed records
    # views = DocumentsRecentlyViewed.get_table(session, document_id=1)
    # logger.info(f"Fetched {len(views)} views for document_id = 1.")

    # # Update record
    # updated_view = DocumentsRecentlyViewed.update_table(
    #     session,
    #     view_id=new_view.view_id,
    #     viewed_by=2
    # )
    # if updated_view:
    #     logger.info(f"View ID {updated_view.view_id} updated successfully.")
    # else:
    #     logger.warning("View record not found. Cannot update.")

    # # Drop table
    # DocumentsRecentlyViewed.drop_table(engine)
    # logger.info("DocumentsRecentlyViewed table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. DocumentsRecentlyViewed script completed.")
