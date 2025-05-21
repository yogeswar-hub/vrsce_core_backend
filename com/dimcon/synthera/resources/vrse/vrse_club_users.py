from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.utilities.log_handler import LoggerManager
from com.dimcon.synthera.resources.vrse.vrse_club_locations import ClubLocation

# Setup centralized logger
logger = LoggerManager.setup_logger(__name__)

class ClubUser(Base):
    """
    ORM model representing a user/member synced from ClubReady.
    Stores profile and referral data and links to a primary club location.
    """
    __tablename__ = 'club_users'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ClubReady User Identifiers
    user_id = Column(Integer, nullable=False, unique=True)  # ClubReady "UserId"
    username = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    barcode = Column(String(100), nullable=True)
    referral_type_id = Column(Integer, nullable=True)

    # Foreign Key: Club Location
    primary_store_id = Column(Integer, ForeignKey(f"{ClubLocation.__tablename__}.club_id"))
    # Audit timestamps and user info
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    synced_at  = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    created_by = Column(String(256), nullable=False)
    updated_by = Column(String(256), nullable=False)

    def to_dict(self):
        """
        Converts ORM object to dictionary format for JSON serialization or logging.
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def create_table(cls, engine):
        """
        Creates the `clubready_users` table if it doesn't already exist.
        """
        from sqlalchemy import inspect
        inspector = inspect(engine)

        try:
            if cls.__tablename__ not in inspector.get_table_names():
                cls.__table__.create(bind=engine)
                logger.info(f" Table '{cls.__tablename__}' created successfully.")
            else:
                logger.info(f" Table '{cls.__tablename__}' already exists. Skipping creation.")
        except Exception as e:
            logger.error(f" Failed to create table '{cls.__tablename__}': {e}")
            raise

    @classmethod
    def insert_or_update_users(cls, session, users: list[dict], audit: dict):
        """
        Inserts or updates ClubReady users in the DB.

        Args:
            session: SQLAlchemy session object
            users: List of user dicts from ClubReady API response
            audit: Dict with keys 'created_by' and 'updated_by' extracted from the event (Cognito claims)
        """
        try:
            count = 0
            for user in users:
                record = cls(
                    user_id=user["UserId"],
                    email=user.get("Email"),
                    first_name=user.get("FirstName"),
                    last_name=user.get("LastName"),
                    barcode=user.get("Barcode"),
                    username=user.get("Username"),
                    referral_type_id=user.get("ReferralTypeId"),
                    primary_store_id=user.get("PrimaryStoreId"),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    synced_at=datetime.now(timezone.utc),
                    created_by=audit.get("created_by"),
                    updated_by=audit.get("updated_by")
                )
                session.merge(record)  # safely upsert
                count += 1

            session.commit()
            logger.info(f" Synced {count} Club user(s) to DB.")
        except Exception as e:
            logger.error(f" Failed to insert/update Club users: {e}")
            session.rollback()
            raise

    @classmethod
    def drop_table(cls, engine):
        """
        Drops the `club_locations` table if it exists.
        """
        try:
            cls.__table__.drop(bind=engine)
            logger.info(f"Table '{cls.__tablename__}' dropped successfully.")
        except Exception as e:
            logger.error(f"Failed to drop table '{cls.__tablename__}': {e}")
            raise

if __name__ == "__main__":
    from com.dimcon.synthera.resources.connect_aurora import get_engine
    from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

    engine = get_engine()
    db_util = DBSessionUtil(engine)

    # Create the table if not exists
    ClubUser.create_table(engine)

    # Optional: insert test user list here by calling insert_or_update_users
