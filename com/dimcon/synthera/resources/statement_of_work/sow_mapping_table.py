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
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, UniqueConstraint, ForeignKey, inspect
from sqlalchemy.orm import Session

# ================================
# Centralized Logger and Database Utilities
# ================================
from com.dimcon.synthera.utilities.log_handler import LoggerManager
import logging
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

# Create engine and DB util
engine = get_engine()
db_util = DBSessionUtil(engine)

# ================================
# Project-specific imports
# ================================
from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.leads.leads_details import LeadDetail
from com.dimcon.synthera.resources.integration.chime_meeting_integrations import ChimeMeetingIntegration
from com.dimcon.synthera.resources.meeting.meeting import Meeting
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee
from com.dimcon.synthera.resources.organization_and_employees.organization import Organization

# ================================
# Model Definition
# ================================
class MeetingQAS(Base):
    __tablename__ = 'meeting_qas'
    __table_args__ = (
        UniqueConstraint('meeting_id', 'question_number', name='uq_meeting_question'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String(64), ForeignKey(f"{ChimeMeetingIntegration.__tablename__}.meeting_id"), nullable=False)
    meeting_title = Column(String(255), nullable=False)
    lead_name = Column(String(255), nullable=False)
    lead_id = Column(Integer, ForeignKey(f"{LeadDetail.__tablename__}.lead_id"), nullable=False)
    emp_id = Column(Integer, ForeignKey(f"{Employee.__tablename__}.emp_id"), nullable=False)
    employee_name = Column(String(255), nullable=False)
    organization_id = Column(Integer, ForeignKey(f"{Organization.__tablename__}.organization_id"), nullable=True)
    organization_name = Column(String(255), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), nullable=False)

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info(f"Table '{cls.__tablename__}' created.")
        else:
            logger.info(f"Table '{cls.__tablename__}' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info(f"Table '{cls.__tablename__}' dropped.")

    @classmethod
    def insert_table(cls,
                     meeting_id, meeting_title,
                     lead_id, lead_name,
                     emp_id, emp_name,
                     org_id=None, organization_name=None,
                     question_number=None,
                     question_text=None,
                     answer_text=None):
        new_row = cls(
            meeting_id=meeting_id,
            meeting_title=meeting_title,
            lead_id=lead_id,
            lead_name=lead_name,
            emp_id=emp_id,
            emp_name=emp_name,
            org_id=org_id,
            organization_name=organization_name,
            question_number=question_number,
            question_text=question_text,
            answer_text=answer_text
        )
        with db_util.session_scope() as session:
            session.add(new_row)
            session.commit()
            logger.info(f"Inserted Q&A row ID: {new_row.id} (Meeting: {meeting_id}, Q#: {question_number})")
        return new_row

    @classmethod
    def get_by_meeting(cls, meeting_id):
        with db_util.session_scope() as session:
            rows = session.query(cls) \
                          .filter_by(meeting_id=meeting_id) \
                          .order_by(cls.question_number) \
                          .all()
            logger.info(f"Fetched {len(rows)} Q&A rows for meeting_id={meeting_id}.")
        return rows

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if hasattr(value, "isoformat"):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    MeetingQAS.create_table(engine)
    logger.info("MeetingQAS table creation complete.")
    # Example usage can be added here
    logger.info("MeetingQAS script completed.")
