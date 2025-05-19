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
from sqlalchemy import Column, Integer, String, TIMESTAMP, inspect
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


# ================================
# Model Definition
# ================================
class StandardUser(Base):
    __tablename__ = 'standard_user'

    standard_user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone_number = Column(String(20))
    position_name = Column(String(100), nullable=False, default='')
    position_short_name = Column(String(20), nullable=False, unique=True, default='')

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'standard_user' created.")
        else:
            logger.info("Table 'standard_user' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'standard_user' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_user = cls(**kwargs)
        session.add(new_user)
        session.commit()
        logger.info(f"Inserted user with ID: {new_user.standard_user_id}")
        return new_user

    @classmethod
    def update_table(cls, session: Session, user_id: int, **kwargs):
        user = session.query(cls).filter_by(standard_user_id=user_id).first()
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)
            session.commit()
            logger.info(f"Updated user with ID: {user_id}")
        else:
            logger.warning(f"User with ID {user_id} not found.")
        return user

    @classmethod
    def get_table(cls, session: Session, **filters):
        users = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(users)} user(s) with filters: {filters}")
        return users

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    StandardUser.create_table(engine)
    logger.info("StandardUser table creation complete.")

    # # # Insert user
    # new_user = StandardUser.insert_table(
    #     session,
    #     name="Jane vDoe",
    #     email="jadfbdne.dowe@exajmple.com",
    #     phone_number="12345s67890",
    #     position_name="Engignceer",
    #     position_short_name="cENG"
    # )
    # logger.info("StandardUser insertion complete.")

    # # Fetch users
    # users = StandardUser.get_table(session, email="jane.doe@example.com")
    # logger.info(f"Fetched {len(users)} user(s) with email 'jane.doe@example.com'.")

    # # Update user
    # updated_user = StandardUser.update_table(
    #     session,
    #     user_id=new_user.standard_user_id,
    #     name="Jane A. Smith"
    # )
    # if updated_user:
    #     logger.info(f"User ID {updated_user.standard_user_id} updated successfully.")
    # else:
    #     logger.warning("User not found. Cannot update.")

    # # Drop table
    # StandardUser.drop_table(engine)
    # logger.info("StandardUser table dropped.")

    # Close session
    db_util.close_session()
    logger.info("Session closed. StandardUser script completed.")
