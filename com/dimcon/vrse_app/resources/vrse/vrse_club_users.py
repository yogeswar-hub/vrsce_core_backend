from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import insert as pg_insert
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation

# Setup centralized logger
logger = LoggerManager.setup_logger(__name__)

class ClubUser(Base):
    """
    ORM model representing a user/member synced from ClubReady.
    Stores profile, referral, and Cognito attributes and links to a primary club location.
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

    # Additional Cognito Attributes
    sub = Column(String(256), nullable=True)
    iss = Column(String(512), nullable=True)
    auth_time = Column(String(256), nullable=True)  # Unix timestamp as string
    aud = Column(String(256), nullable=True)
    auth_time_human = Column(String(256), nullable=True)

    def to_dict(self):
        """
        Converts ORM object to dictionary format.
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def create_table(cls, engine):
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
    def bulk_upsert_users(cls, session, users: list[dict], audit: dict):
        """
        Bulk upsert a list of user dictionaries in a single statement.
        """
        # Prepare a list of dictionaries with necessary fields.
        # Adjust the keys as per your API data and model definitions.
        values = []
        for user in users:
            # Optionally convert auth_time to auth_time_human
            auth_time_human = None
            if "auth_time" in user:
                try:
                    unix_ts = int(user["auth_time"])
                    auth_time_human = datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()
                except Exception as conv_err:
                    logger.warning(f"Could not convert auth_time: {conv_err}")
            values.append({
                "user_id": user.get("UserId"),
                "email": user.get("Email"),
                "first_name": user.get("FirstName"),
                "last_name": user.get("LastName"),
                "barcode": user.get("Barcode"),
                "username": user.get("Username"),
                "referral_type_id": user.get("ReferralTypeId"),
                "primary_store_id": user.get("PrimaryStoreId"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "synced_at": datetime.now(timezone.utc),
                "created_by": audit.get("created_by"),
                "updated_by": audit.get("updated_by"),
                "sub": user.get("sub"),
                "iss": user.get("iss"),
                "auth_time": user.get("auth_time"),
                "aud": user.get("aud"),
                "auth_time_human": auth_time_human,
            })

        stmt = pg_insert(cls).values(values)
        # Exclude primary key and user_id (or whatever unique fields you use) from update.
        update_cols = {c.name: c for c in stmt.excluded if c.name not in ("user_id",)}
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],  # Unique identifier.
            set_=update_cols
        )
        session.execute(stmt)
        logger.info(f"Bulk upserted {len(values)} Club user(s)")

    @classmethod
    def bulk_insert_users(cls, session, users: list[dict], audit: dict):
        """
        Bulk inserts new club users. Existing users (based on unique user_id) are skipped.
        """
        values = []
        for user in users:
            auth_time_human = None
            if "auth_time" in user:
                try:
                    unix_ts = int(user["auth_time"])
                    auth_time_human = datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()
                except Exception as conv_err:
                    logger.warning(f"Could not convert auth_time: {conv_err}")
            values.append({
                "user_id": user.get("UserId"),
                "email": user.get("Email"),
                "first_name": user.get("FirstName"),
                "last_name": user.get("LastName"),
                "barcode": user.get("Barcode"),
                "username": user.get("Username"),
                "referral_type_id": user.get("ReferralTypeId"),
                "primary_store_id": user.get("PrimaryStoreId"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "synced_at": datetime.now(timezone.utc),
                "created_by": audit.get("created_by"),
                "updated_by": audit.get("updated_by"),
                "sub": user.get("sub"),
                "iss": user.get("iss"),
                "auth_time": user.get("auth_time"),
                "aud": user.get("aud"),
                "auth_time_human": auth_time_human,
            })
        stmt = pg_insert(cls).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id"])
        session.execute(stmt)
        logger.info(f"Bulk inserted {len(values)} new Club user(s).")

# Example usage outside the model (for instance, in a service)
if __name__ == "__main__":
    from com.dimcon.vrse_app.resources.connect_aurora import get_engine
    from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil

    engine = get_engine()
    db_util = DBSessionUtil(engine)
    ClubUser.create_table(engine)

    # Example: a batch of users fetched from an external source.
    all_users = [
        {"UserId": 101, "Email": "user1@example.com", "FirstName": "John", "LastName": "Doe", "Barcode": "ABC123",
         "Username": "johndoe", "ReferralTypeId": 1, "PrimaryStoreId": 1001, "auth_time": "1680000000", "sub": "sub1", "iss": "issuer1", "aud": "aud1"},
        # ... more user dictionaries ...
    ]
    audit = {"created_by": "system", "updated_by": "system"}
    
    with db_util.session_scope() as session:
        ClubUser.bulk_upsert_users(session, all_users, audit)
        session.commit()
