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
from com.dimcon.synthera.resources.documents.document_type import DocumentType
from com.dimcon.synthera.resources.documents.document_categories import DocumentCategory
from com.dimcon.synthera.resources.leads.leads_details import LeadDetail
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee

# ================================
# Model Definition
# ================================
class Document(Base):
    __tablename__ = 'documents'

    document_id = Column(Integer, primary_key=True, autoincrement=True)
    document_title = Column(String(255), nullable=False)
    document_url = Column(String(500), nullable=False)
    document_type_id = Column(Integer, ForeignKey(DocumentType.type_id))
    document_category_id = Column(Integer, ForeignKey(DocumentCategory.category_id))
    lead_id = Column(Integer, ForeignKey(LeadDetail.lead_id))
    created_by = Column(Integer, ForeignKey(Employee.emp_id))
    updated_by = Column(Integer, ForeignKey(Employee.emp_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'documents' created.")
        else:
            logger.info("Table 'documents' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'documents' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_doc = cls(**kwargs)
        session.add(new_doc)
        session.commit()
        logger.info(f"Inserted document with ID: {new_doc.document_id}")
        return new_doc

    @classmethod
    def update_table(cls, session: Session, document_id: int, **kwargs):
        doc = session.query(cls).filter_by(document_id=document_id).first()
        if doc:
            for key, value in kwargs.items():
                setattr(doc, key, value)
            session.commit()
            logger.info(f"Updated document with ID: {document_id}")
        else:
            logger.warning(f"Document with ID {document_id} not found.")
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
    # Document.create_table(engine)
    # logger.info("Documents table creation complete.")

    # # Insert document
    new_doc = Document.insert_table(
        session,
        document_title="Sales Pitch Deck",
        document_url="https://cdn.synthera.com/docs/sales_pitch.pdf",
        document_type_id=1,
        document_category_id=1,
        lead_id=1,
        created_by=1,
        updated_by=1
    )
    logger.info("Document insertion complete.")

    # # Fetch documents
    # docs = Document.get_table(session, document_title="Sales Pitch Deck")
    # logger.info(f"Fetched {len(docs)} documents with title 'Sales Pitch Deck'.")

    # # Update document
    # updated_doc = Document.update_table(
    #     session,
    #     document_id=new_doc.document_id,
    #     document_title="Updated Sales Pitch Deck",
    #     updated_by=2
    # )
    # if updated_doc:
    #     logger.info(f"Document ID {updated_doc.document_id} updated successfully.")
    # else:
    #     logger.warning("Document not found. Cannot update.")

    # # Drop table
    # Document.drop_table(engine)
    # logger.info("Documents table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. Documents script completed.")
