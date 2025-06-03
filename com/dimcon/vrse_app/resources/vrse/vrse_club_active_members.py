from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, cast
from sqlalchemy.dialects.postgresql import insert as pg_insert
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.resources.vrse.models import Passkit_Member

logger = LoggerManager.setup_logger(__name__)

class ClubActiveMember(Base):
    """
    ORM model representing an active member from ClubReady.
    """
    __tablename__ = 'club_active_members'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ClubReady Active Member fields
    user_id = Column(Integer, nullable=False, unique=True)  # ClubReady "UserId"
    email = Column(String(255), nullable=True)
    mobile_phone = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    activity_date = Column(TIMESTAMP(timezone=True), nullable=True)
    activity_type = Column(String(100), nullable=True)
    referral_type_id = Column(Integer, nullable=True)
    referral_type_name = Column(String(255), nullable=True)
    not_in_passkit = Column(Boolean, default=False)  # New column

    # Audit timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        """
        Converts ORM object to dictionary format.
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def create_table(cls, engine):
        """
        Creates the table in the database if it doesn't exist.
        """
        from sqlalchemy import inspect
        inspector = inspect(engine)
        try:
            if cls.__tablename__ not in inspector.get_table_names():
                cls.__table__.create(bind=engine)
                logger.info(f"Table '{cls.__tablename__}' created successfully.")
            else:
                logger.info(f"Table '{cls.__tablename__}' already exists. Skipping creation.")
        except Exception as e:
            logger.error(f"Failed to create table '{cls.__tablename__}': {e}")
            raise

    @classmethod
    def bulk_insert_active_members(cls, session, members: list[dict]):
        """
        Bulk inserts new active members. For each member, it checks if its user_id exists in 
        the Passkit_Member's "person" JSON field under "externalId" and sets not_in_passkit accordingly.
        """
        values = []
        for member in members:
            activity_date = None
            if member.get("ActivityDate"):
                try:
                    activity_date = datetime.fromisoformat(member.get("ActivityDate"))
                except Exception as conv_err:
                    logger.warning(f"Could not convert ActivityDate: {conv_err}")
            user_id = member.get("UserId")
            # For PostgreSQL, cast the JSON field "externalId" to a string.
            passkit_record = session.query(Passkit_Member).filter(
                cast(Passkit_Member.person["externalId"], String) == str(user_id)
            ).first()
            exists_in_passkit = passkit_record is not None
            logger.debug(f"For user_id {user_id}: Passkit record: {passkit_record}, exists_in_passkit: {exists_in_passkit}")

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
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "not_in_passkit": False if exists_in_passkit else True
            })
        stmt = pg_insert(cls).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id"])
        session.execute(stmt)
        logger.info(f"Bulk inserted {len(values)} new active member(s).")

if __name__ == "__main__":
    from com.dimcon.vrse_app.resources.connect_aurora import get_engine
    from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil

    engine = get_engine()
    db_util = DBSessionUtil(engine)
    ClubActiveMember.create_table(engine)