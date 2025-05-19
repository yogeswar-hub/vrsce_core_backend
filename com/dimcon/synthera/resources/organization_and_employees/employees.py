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
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session

# ================================
# Use centralized utilities
# ================================
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

# Use your centralized Base
from com.dimcon.synthera.resources.base import Base

# ================================
# Project-specific imports
# ================================
from com.dimcon.synthera.resources.organization_and_employees.organization import Organization
from com.dimcon.synthera.resources.database_and_users.management_user import ManagementUser
from com.dimcon.synthera.resources.database_and_users.standard_user import StandardUser

# Create engine and instantiate session management centrally.
engine = get_engine()
db_util = DBSessionUtil(engine)

# ================================
# Model Definition
# ================================
class Employee(Base):
    __tablename__ = 'employees'

    emp_id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey(Organization.organization_id), nullable=False)
    employee_name = Column(String(255), nullable=False)
    emp_org_email = Column(String(255), unique=True)
    emp_contact_number = Column(String(50))
    emp_address = Column(String(255))
    emp_role = Column(Text, default='employee')
    emp_status = Column(Text, default='active')
    standard_user_id = Column(Integer, ForeignKey(StandardUser.standard_user_id))
    created_by = Column(Integer, ForeignKey(ManagementUser.user_id))
    updated_by = Column(Integer, ForeignKey(ManagementUser.user_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'employees' created.")
        else:
            logger.info("Table 'employees' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'employees' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_emp = cls(**kwargs)
        session.add(new_emp)
        session.commit()
        logger.info(f"Inserted employee with ID: {new_emp.emp_id}")
        return new_emp

    @classmethod
    def update_table(cls, session: Session, emp_id: int, **kwargs):
        emp = session.query(cls).filter_by(emp_id=emp_id).first()
        if emp:
            for key, value in kwargs.items():
                setattr(emp, key, value)
            session.commit()
            logger.info(f"Updated employee with ID: {emp_id}")
        else:
            logger.warning(f"Employee with ID {emp_id} not found.")
        return emp

    @classmethod
    def get_table(cls, session: Session, **filters):
        emps = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(emps)} employee(s) with filters: {filters}")
        return emps

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table using centralized engine
    Employee.create_table(engine)
    logger.info("Employee table creation complete.")

    # Optionally include further examples or test operations here.
    logger.info("Employee script completed.")
