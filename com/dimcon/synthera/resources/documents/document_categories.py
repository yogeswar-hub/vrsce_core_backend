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
class DocumentCategory(Base):
    __tablename__ = 'document_categories'

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False, unique=True)
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
            logger.info("Table 'document_categories' created.")
        else:
            logger.info("Table 'document_categories' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'document_categories' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_cat = cls(**kwargs)
        session.add(new_cat)
        session.commit()
        logger.info(f"Inserted document category with ID: {new_cat.category_id}")
        return new_cat

    @classmethod
    def update_table(cls, session: Session, category_id: int, **kwargs):
        cat = session.query(cls).filter_by(category_id=category_id).first()
        if cat:
            for key, value in kwargs.items():
                setattr(cat, key, value)
            session.commit()
            logger.info(f"Updated document category with ID: {category_id}")
        else:
            logger.warning(f"Category with ID {category_id} not found.")
        return cat

    @classmethod
    def get_table(cls, session: Session, **filters):
        cats = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(cats)} document category record(s) with filters: {filters}")
        return cats

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    DocumentCategory.create_table(engine)
    logger.info("DocumentCategory table creation complete.")

    # # # Insert category
    # new_cat = DocumentCategory.insert_table(
    #     session,
    #     category_name="User Guides",
    #     description="Documentation for end-users.",
    #     created_by=1,
    #     updated_by=1
    # )
    # logger.info("DocumentCategory record insertion complete.")

    # # Fetch categories
    # cats = DocumentCategory.get_table(session, category_name="User Guides")
    # logger.info(f"Fetched {len(cats)} categories for name = 'User Guides'.")

    # # Update category
    # updated_cat = DocumentCategory.update_table(
    #     session,
    #     category_id=new_cat.category_id,
    #     description="Updated user documentation category",
    #     updated_by=2
    # )
    # if updated_cat:
    #     logger.info(f"Category ID {updated_cat.category_id} updated successfully.")
    # else:
    #     logger.warning("Category not found. Cannot update.")

    # # Drop table
    # DocumentCategory.drop_table(engine)
    # logger.info("DocumentCategory table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. DocumentCategory script completed.")
