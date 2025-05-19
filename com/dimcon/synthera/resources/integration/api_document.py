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
class APIDocument(Base):
    __tablename__ = 'api_documents'

    doc_id = Column(Integer, primary_key=True, autoincrement=True)
    api_integration_id = Column(Integer, ForeignKey(APIIntegration.api_integration_id, ondelete="CASCADE"))
    doc_title = Column(String(255), nullable=False)
    doc_url = Column(String(500), nullable=False)
    uploaded_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_by = Column(Integer, ForeignKey(Employee.emp_id))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'api_documents' created.")
        else:
            logger.info("Table 'api_documents' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'api_documents' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_doc = cls(**kwargs)
        session.add(new_doc)
        session.commit()
        logger.info(f"Inserted API document with ID: {new_doc.doc_id}")
        return new_doc

    @classmethod
    def update_table(cls, session: Session, doc_id: int, **kwargs):
        doc = session.query(cls).filter_by(doc_id=doc_id).first()
        if doc:
            for key, value in kwargs.items():
                setattr(doc, key, value)
            session.commit()
            logger.info(f"Updated API document with ID: {doc_id}")
        else:
            logger.warning(f"API document with ID {doc_id} not found for update.")
        return doc

    @classmethod
    def get_table(cls, session: Session, **filters):
        docs = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(docs)} document(s) with filters: {filters}")
        return docs

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # # Create table
    # APIDocument.create_table(engine)
    # logger.info("APIDocument table creation complete.")

    # # Insert document
    new_doc = APIDocument.insert_table(
        session,
        api_integration_id=1,
        doc_title="Zoom OAuth Setup Guide",
        doc_url="https://docs.synthera.com/integrations/zoom_oauth.pdf",
        updated_by=1
    )
    logger.info("APIDocument record insertion complete.")

    # # Fetch documents
    # docs = APIDocument.get_table(session, api_integration_id=1)
    # logger.info(f"Fetched {len(docs)} documents for api_integration_id = 1.")

    # # Update document
    # updated_doc = APIDocument.update_table(
    #     session,
    #     doc_id=new_doc.doc_id,
    #     doc_title="Zoom OAuth Setup Guide v2",
    #     updated_by=2
    # )
    # if updated_doc:
    #     logger.info(f"Document ID {updated_doc.doc_id} updated successfully.")
    # else:
    #     logger.warning("Document not found. Cannot update.")

    # # Drop table
    # APIDocument.drop_table(engine)
    # logger.info("APIDocument table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. APIDocument script completed.")
