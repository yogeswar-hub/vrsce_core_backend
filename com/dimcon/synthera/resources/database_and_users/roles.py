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
class Role(Base):
    __tablename__ = 'roles'

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    position_short_name = Column(String(20), ForeignKey(StandardUser.position_short_name), nullable=False, default='')
    created_by = Column(Integer, ForeignKey(StandardUser.standard_user_id), nullable=False)
    updated_by = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'roles' created.")
        else:
            logger.info("Table 'roles' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'roles' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_role = cls(**kwargs)
        session.add(new_role)
        session.commit()
        logger.info(f"Inserted role with ID: {new_role.role_id}")
        return new_role

    @classmethod
    def update_table(cls, session: Session, role_id: int, **kwargs):
        role = session.query(cls).filter_by(role_id=role_id).first()
        if role:
            for key, value in kwargs.items():
                setattr(role, key, value)
            session.commit()
            logger.info(f"Updated role with ID: {role_id}")
        else:
            logger.warning(f"Role with ID {role_id} not found.")
        return role

    @classmethod
    def get_table(cls, session: Session, **filters):
        roles = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(roles)} role(s) with filters: {filters}")
        return roles

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table
    Role.create_table(engine)
    logger.info("Roles table creation complete.")

    # # # Insert role
    # new_role = Role.insert_table(
    #     session,
    #     role_name="Manager",
    #     description="Manages a team",
    #     position_short_name="ENG",
    #     created_by=1
    # )
    # logger.info("Role insertion complete.")

    # # Fetch roles
    # roles = Role.get_table(session, role_name="Manager")
    # logger.info(f"Fetched {len(roles)} roles named 'Manager'.")

    # # Update role
    # updated_role = Role.update_table(
    #     session,
    #     role_id=new_role.role_id,
    #     description="Updated description"
    # )
    # if updated_role:
    #     logger.info(f"Role ID {updated_role.role_id} updated successfully.")
    # else:
    #     logger.warning("Role not found. Cannot update.")

    # # Drop table
    # Role.drop_table(engine)
    # logger.info("Roles table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. Role script completed.")
