# ================================
# MeetingSOWJsonStore: Versioned JSON Storage
# ================================
import os
import sys
import logging
# ================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, ForeignKey, UniqueConstraint, inspect, Boolean
from sqlalchemy.dialects.postgresql import JSONB

from com.dimcon.synthera.utilities.log_handler import LoggerManager
from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.leads.leads_details import LeadDetail
from com.dimcon.synthera.resources.integration.chime_meeting_integrations import ChimeMeetingIntegration
from com.dimcon.synthera.resources.organization_and_employees.organization import Organization
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee

logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)
engine = get_engine()
db_util = DBSessionUtil(engine)

class MeetingSOWJsonStore(Base):
    __tablename__ = 'meeting_sow_json_store'
    __table_args__ = (
        UniqueConstraint('lead_id', 'version_number', name='uq_lead_version'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    sow_template_reference_number = Column(String(128), nullable=False)

    meeting_id = Column(String(64), ForeignKey(f"{ChimeMeetingIntegration.__tablename__}.meeting_id"), nullable=False)
    lead_id = Column(Integer, ForeignKey(f"{LeadDetail.__tablename__}.lead_id"), nullable=False)
    lead_name = Column(String(255), nullable=False)
    organization_id = Column(Integer, ForeignKey(f"{Organization.__tablename__}.organization_id"), nullable=True)
    organization_name = Column(String(255), nullable=False)

    version_number = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, nullable=False, default=True)
    parent_sow_id = Column(Integer, ForeignKey('meeting_sow_json_store.id'), nullable=True)

    raw_payload = Column(JSONB, nullable=False)

    created_by = Column(Integer, ForeignKey(f"{Employee.__tablename__}.emp_id"), nullable=False)
    updated_by = Column(Integer, ForeignKey(f"{Employee.__tablename__}.emp_id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=datetime.now(UTC), nullable=True)

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info(f"Table '{cls.__tablename__}' created.")
        else:
            logger.info(f"Table '{cls.__tablename__}' already exists. Skipping creation.")

    @classmethod
    def insert_version(cls, sow_ref, meeting_id, lead_id, lead_name, org_id, org_name, payload, created_by):
        with db_util.session_scope() as session:
            latest = session.query(cls).filter_by(lead_id=lead_id, is_latest=True).first()
            next_version = 1 if not latest else latest.version_number + 1

            if latest:
                latest.is_latest = False
                session.add(latest)

            new_entry = cls(
                sow_template_reference_number=sow_ref,
                meeting_id=meeting_id,
                lead_id=lead_id,
                lead_name=lead_name,
                organization_id=org_id,
                organization_name=org_name,
                raw_payload=payload,
                version_number=next_version,
                is_latest=True,
                parent_sow_id=latest.id if latest else None,
                created_by=created_by
            )
            session.add(new_entry) # Ensure the ID is generated before commit
            session.commit()
            logger.info(f"Inserted version {next_version} for lead {lead_id} (SOW ref: {sow_ref})")

        return  new_entry

    @classmethod
    def get_latest_by_lead(cls, lead_id):
        try:
            with db_util.session_scope() as session:
                row = (
                    session.query(cls)
                    .filter_by(lead_id=lead_id, is_latest=True)
                    .order_by(cls.version_number.desc())
                    .first()
                )
                if not row:
                    return None

                # ✅ Extract values safely inside session
                return {
                    "version_number": row.version_number,
                    "lead_name": row.lead_name,
                    "meeting_id": row.meeting_id,
                    "created_by": row.created_by,
                    "created_at": row.created_at,
                    "sow_template_reference_number": row.sow_template_reference_number,
                    "raw_payload": row.raw_payload
                }

        except Exception as e:
            logger.error(f"Failed to fetch latest SOW by lead_id={lead_id}: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    MeetingSOWJsonStore.create_table(engine)
    logger.info("MeetingSOWJsonStore table with versioning created successfully.")
