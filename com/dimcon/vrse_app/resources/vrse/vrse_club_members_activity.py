from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import insert as pg_insert
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.resources.vrse.models import Passkit_Member
from sqlalchemy import UniqueConstraint

logger = LoggerManager.setup_logger(__name__)


class ClubActiveMember(Base):
    """
    ORM model representing active members pulled from the ClubReady platform.

    Attributes:
        user_id: Unique identifier from ClubReady (used for cross-check with PassKit).
        segment: The segment type from ClubReady (Active, Inactive, PastDue, Prospects).
        not_in_passkit: True if the user is not found in PassKit members (based on externalId).
        created_at/updated_at: Standard audit timestamps.
    """

    __tablename__ = 'club_members_activity'  # <-- Updated table name
    __table_args__ = (
        UniqueConstraint('user_id', 'segment', name='uq_user_segment'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    email = Column(String(255), nullable=True)
    mobile_phone = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    activity_date = Column(TIMESTAMP(timezone=True), nullable=True)
    activity_type = Column(String(100), nullable=True)
    referral_type_id = Column(Integer, nullable=True)
    referral_type_name = Column(String(255), nullable=True)
    segment = Column(String(50), nullable=True)  # New column to capture segment
    #not_in_passkit = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        """
        Converts the SQLAlchemy object into a dictionary.
        Useful for serialization.
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def create_table(cls, engine):
        """
        Create the `club_active_members` table if it doesn't already exist.
        """
        from sqlalchemy import inspect
        inspector = inspect(engine)
        try:
            if cls.__tablename__ not in inspector.get_table_names():
                cls.__table__.create(bind=engine)
                logger.info(f" Table '{cls.__tablename__}' created successfully.")
            else:
                logger.info(f" Table '{cls.__tablename__}' already exists.")
        except Exception as e:
            logger.error(f" Failed to create table '{cls.__tablename__}': {e}", exc_info=True)
            raise

    @classmethod
    def bulk_insert_active_members(cls, session, members: list[dict]):
        """
        Bulk upserts active members from ClubReady and includes the segment value.
        If a record with the same (user_id, segment) exists, it will be updated.
        Args:
            session: Active DB session.
            members: List of ClubReady user records.
        """
        values = []
        for member in members:
            user_id = member.get("UserId")
            if not user_id:
                logger.warning(f"Skipping record with missing UserId: {member}")
                continue

            # Log the segment value for debugging.
            segment_value = member.get("Segment") or member.get("segment")
            logger.debug(f"Inserting club Ready member for user_id {user_id} with segment: {segment_value}")

            activity_date = None
            if member.get("ActivityDate"):
                try:
                    activity_date = datetime.fromisoformat(member["ActivityDate"])
                except Exception as date_err:
                    logger.warning(f"Invalid ActivityDate for user {user_id}: {date_err}")

            values.append({
                "user_id": user_id,
                "email": member.get("Email"),
                "mobile_phone": member.get("MobilePhone"),
                "username": member.get("Username"),
                "first_name": member.get("FirstName"),
                "last_name": member.get("LastName"),
                "activity_date": activity_date,
                "activity_type": member.get("ActivityType"),
                "referral_type_id": member.get("ReferralTypeId"),
                "referral_type_name": member.get("ReferralTypeName"),
                "segment": segment_value,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })

        if not values:
            logger.info(" No valid ClubReady member data to upsert.")
            return

        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            # Build the insert statement using the PostgreSQL dialect.
            stmt = pg_insert(cls).values(values)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["user_id", "segment"]
            )
            session.execute(stmt)

            session.commit()
            logger.info(f" Successfully upserted {len(values)} ClubReady member(s) into DB.")
        except Exception as e:
            session.rollback()
            logger.error(" Failed to upsert ClubReady members.", exc_info=True)
            raise

    @classmethod
    def drop_table(cls, engine):
        """
        Drops the `club_active_members` table if it exists.
        Useful for schema reset or testing.
        """
        from sqlalchemy import inspect
        inspector = inspect(engine)
        try:
            if cls.__tablename__ in inspector.get_table_names():
                cls.__table__.drop(bind=engine)
                logger.info(f" Dropped table '{cls.__tablename__}' successfully.")
            else:
                logger.info(f" Table '{cls.__tablename__}' does not exist.")
        except Exception as e:
            logger.error(f" Failed to drop table '{cls.__tablename__}': {e}", exc_info=True)
            raise

if __name__ == "__main__":
    from com.dimcon.vrse_app.resources.connect_aurora import get_engine
    from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil

    engine = get_engine()
    db_util = DBSessionUtil(engine)
    ClubActiveMember.create_table(engine)
