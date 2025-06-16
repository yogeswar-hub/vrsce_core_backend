from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert as pg_insert
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.resources.vrse.models import Passkit_Member

logger = LoggerManager.setup_logger(__name__)

class ClubMemberActivity(Base):
    __tablename__ = 'club_members_activity'
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_unique'),
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
    segment = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def create_table(cls, engine):
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
    def bulk_insert_members_activity(cls, session, members: list[dict]):
        values = []
        for member in members:
            user_id = member.get("UserId")
            if not user_id:
                logger.warning(f"Skipping record with missing UserId: {member}")
                continue

            segment_value = member.get("Segment") or member.get("segment")
            logger.debug(f"Inserting ClubReady member for user_id {user_id} with segment: {segment_value}")

            activity_date = None
            if member.get("ActivityDate"):
                try:
                    activity_date = datetime.fromisoformat(member["ActivityDate"])
                except Exception as date_err:
                    logger.warning(f"Invalid ActivityDate for user {user_id}: {date_err}")

            now = datetime.now(timezone.utc)

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
                "created_at": now,
                "updated_at": now
            })

        if not values:
            logger.info("No valid ClubReady member data to upsert.")
            return

        try:
            stmt = pg_insert(cls).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "email": stmt.excluded.email,
                    "mobile_phone": stmt.excluded.mobile_phone,
                    "username": stmt.excluded.username,
                    "first_name": stmt.excluded.first_name,
                    "last_name": stmt.excluded.last_name,
                    "activity_date": stmt.excluded.activity_date,
                    "activity_type": stmt.excluded.activity_type,
                    "referral_type_id": stmt.excluded.referral_type_id,
                    "referral_type_name": stmt.excluded.referral_type_name,
                    "segment": stmt.excluded.segment,
                    "updated_at": datetime.now(timezone.utc)
                }
            )
            session.execute(stmt)
            session.commit()
            logger.info(f"Successfully upserted {len(values)} ClubReady member(s) into DB.")
        except Exception as e:
            session.rollback()
            logger.error("Failed to upsert ClubReady members.", exc_info=True)
            raise

    @classmethod
    def drop_table(cls, engine):
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
    ClubMemberActivity.create_table(engine)
