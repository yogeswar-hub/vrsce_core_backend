# ================================
# Add project root to sys.path
# ================================
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# ================================
# Standard library imports
# ================================
from datetime import datetime, UTC

# ================================
# Third-party imports
# ================================
import pytz
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session

# ================================
# Centralized Logger and Database Utilities
# ================================
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
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee
from com.dimcon.synthera.resources.organization_and_employees.organization import Organization
from com.dimcon.synthera.resources.leads.lead_stages import LeadStage

# ================================
# Model Definition
# ================================
class LeadDetail(Base):
    __tablename__ = 'leads_details'

    lead_id = Column(Integer, primary_key=True, autoincrement=True)
    lead_first_name = Column(String(100), nullable=False)
    lead_last_name = Column(String(100), nullable=False)
    company = Column(String(255))
    email = Column(String(255), nullable=False, unique=True)
    contact_number = Column(String(50))
    job_title = Column(String(100))
    department = Column(String(100))
    industry = Column(String(100))
    website_url = Column(String(255))
    address_line_1 = Column(String(255))
    address_line_2 = Column(String(255))
    city = Column(String(100))
    state_province = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))
    linkedin_profile_url = Column(String(255))
    preferred_contact_method = Column(String(50))
    budget_range = Column(String(50))
    meeting_availability = Column(TIMESTAMP(timezone=True))
    lead_source = Column(String(100))
    lead_stage_id = Column(Integer, ForeignKey(LeadStage.lead_stage_id))
    lead_stage_name = Column(String, ForeignKey(LeadStage.stage_name))
    organization_id = Column(Integer, ForeignKey(Organization.organization_id))
    created_by = Column(Integer, ForeignKey(Employee.emp_id))
    updated_by = Column(Integer, ForeignKey(Employee.emp_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))
    notes = Column(Text)

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'leads_details' created.")
        else:
            logger.info("Table 'leads_details' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'leads_details' dropped.")

    @classmethod
    def insert_table(cls, **kwargs):
        """
        Inserts a new lead record using a managed session.
        """
        new_lead = cls(**kwargs)
        with db_util.session_scope() as session:
            session.add(new_lead)
            session.commit()
            logger.info(f"Inserted lead with ID: {new_lead.lead_id}")
        return new_lead

    @classmethod
    def update_table(cls, lead_id: int, **kwargs):
        """
        Updates an existing lead record using a managed session.
        """
        with db_util.session_scope() as session:
            lead = session.query(cls).filter_by(lead_id=lead_id).first()
            if lead:
                for key, value in kwargs.items():
                    setattr(lead, key, value)
                session.commit()
                logger.info(f"Updated lead with ID: {lead_id}")
            else:
                logger.warning(f"Lead with ID {lead_id} not found.")
            return lead

    @classmethod
    def get_table(cls, **filters):
        """
        Fetches lead records using a managed session.
        """
        with db_util.session_scope() as session:
            leads = session.query(cls).filter_by(**filters).all()
            logger.info(f"Fetched {len(leads)} lead(s) with filters: {filters}")
        return leads

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")
    

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # If value is a datetime, convert it to string
            if hasattr(value, "isoformat"):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result


# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # Create table if not exists
    LeadDetail.create_table(engine)
    logger.info("LeadDetail table creation complete.")

    # Examples of how to use the centralized utilities:
    #
    # Insert lead example:
    # new_lead = LeadDetail.insert_table(
    #     lead_first_name="Mark",
    #     lead_last_name="Roberts",
    #     company="TechNova Inc.",
    #     email="mark.roberts@technova.com",
    #     contact_number="555-153-4567",
    #     job_title="IT Director",
    #     department="Technology",
    #     industry="Software",
    #     website_url="https://www.technova.com",
    #     address_line_1="200 Enterprise Ave",
    #     address_line_2="Suite 600",
    #     city="San Francisco",
    #     state_province="CA",
    #     postal_code="94105",
    #     country="USA",
    #     linkedin_profile_url="https://www.linkedin.com/in/markroberts",
    #     preferred_contact_method="Email",
    #     budget_range="$100,000 - $500,000",
    #     meeting_availability=datetime(2025, 4, 15, 14, 0, tzinfo=pytz.utc),
    #     lead_source="LinkedIn",
    #     lead_stage_id=1,
    #     lead_stage_name="Qualified Lead",
    #     organization_id=1,
    #     created_by=1,
    #     updated_by=1,
    #     notes="Follow up next week with demo."
    # )
    # logger.info("LeadDetail insertion complete.")
    #
    # Fetch leads example:
    # leads = LeadDetail.get_table(country="USA")
    # logger.info(f"Fetched {len(leads)} lead(s) from USA.")
    #
    # Update lead example:
    # updated_lead = LeadDetail.update_table(
    #     lead_id=new_lead.lead_id,
    #     job_title="CTO",
    #     updated_by=2
    # )
    # if updated_lead:
    #     logger.info(f"Lead ID {updated_lead.lead_id} updated successfully.")
    # else:
    #     logger.warning("Lead not found. Cannot update.")
    #
    # Drop table example:
    # LeadDetail.drop_table(engine)
    # logger.info("LeadDetail table dropped.")

    logger.info("LeadDetail script completed.")
