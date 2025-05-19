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
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session

# ================================
# Project-specific imports
# ================================
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

from com.dimcon.synthera.resources.base import Base

from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.database_and_users.standard_user import StandardUser
from com.dimcon.synthera.resources.database_and_users.roles import Role

# ================================
# Model Definition
# ================================
class ManagementUser(Base):
    __tablename__ = 'management_user'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    standard_user_id = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    role_id = Column(Integer, ForeignKey(Role.role_id), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'management_user' created.")
        else:
            logger.info("Table 'management_user' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'management_user' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_user = cls(**kwargs)
        session.add(new_user)
        session.commit()
        logger.info(f"Inserted user with ID: {new_user.user_id}")
        return new_user

    @classmethod
    def update_table(cls, session: Session, user_id: int, **kwargs):
        user = session.query(cls).filter_by(user_id=user_id).first()
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
    # Create engine using the connect_aurora function
    engine = get_engine()

    # Create table
    ManagementUser.create_table(engine)
    logger.info("ManagementUser table creation complete.")

    # Initialize DB session utility and execute within a session_scope
    db_session_util = DBSessionUtil(engine)
    with db_session_util.session_scope() as session:
    

    # # # Insert user
    # new_user = ManagementUser.insert_table(
    #     session,
    #     username="admin_user",
    #     email="admin@example.com",
    #     password_hash="hashed_password_here",
    #     standard_user_id=1,
    #     role_id=1
    # )
    # logger.info("ManagementUser insertion complete.")

    # # Fetch users
    # users = ManagementUser.get_table(session, email="admin@example.com")
    # logger.info(f"Fetched {len(users)} user(s) with email 'admin@example.com'.")

    # # Update user
    # updated_user = ManagementUser.update_table(
    #     session,
    #     user_id=new_user.user_id,
    #     is_active=False
    # )
    # if updated_user:
    #     logger.info(f"User ID {updated_user.user_id} updated successfully.")
    # else:
    #     logger.warning("User not found. Cannot update.")

    # # Drop table
    # ManagementUser.drop_table(engine)
    # logger.info("ManagementUser table dropped.")

    # Close session
      pass
    logger.info("Session closed. ManagementUser script completed.")
