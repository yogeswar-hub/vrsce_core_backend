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
class DocumentType(Base):
    __tablename__ = 'document_type'

    type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String(100), nullable=False, unique=True)
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
            logger.info("Table 'document_type' created.")
        else:
            logger.info("Table 'document_type' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'document_type' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_type = cls(**kwargs)
        session.add(new_type)
        session.commit()
        logger.info(f"Inserted document type with ID: {new_type.type_id}")
        return new_type

    @classmethod
    def update_table(cls, session: Session, type_id: int, **kwargs):
        doc_type = session.query(cls).filter_by(type_id=type_id).first()
        if doc_type:
            for key, value in kwargs.items():
                setattr(doc_type, key, value)
            session.commit()
            logger.info(f"Updated document type with ID: {type_id}")
        else:
            logger.warning(f"Document type with ID {type_id} not found.")
        return doc_type

    @classmethod
    def get_table(cls, session: Session, **filters):
        types = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(types)} document type(s) with filters: {filters}")
        return types

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    DocumentType.create_table(engine)
    logger.info("DocumentType table creation complete.")

    # # # Insert type
    # new_type = DocumentType.insert_table(
    #     session,
    #     type_name="PDF",
    #     description="Portable Document Format",
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("DocumentType insertion complete.")

    # # Fetch types
    # types = DocumentType.get_table(session, type_name="PDF")
    # logger.info(f"Fetched {len(types)} type(s) named 'PDF'.")

    # # Update type
    # updated_type = DocumentType.update_table(
    #     session,
    #     type_id=new_type.type_id,
    #     description="Updated PDF description",
    #     updated_by=2
    # )
    # if updated_type:
    #     logger.info(f"DocumentType ID {updated_type.type_id} updated successfully.")
    # else:
    #     logger.warning("DocumentType not found. Cannot update.")

    # # Drop table
    # DocumentType.drop_table(engine)
    # logger.info("DocumentType table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. DocumentType script completed.")
