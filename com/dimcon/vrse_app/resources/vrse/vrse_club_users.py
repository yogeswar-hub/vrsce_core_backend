from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import insert as pg_insert
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
import traceback
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation

logger = LoggerManager.setup_logger(__name__)

class ClubUser(Base):
    """
    ORM model representing a user/member synced from ClubReady.
    """
    __tablename__ = 'club_users'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ClubReady Identifiers
    user_id            = Column(Integer, nullable=False, unique=True)
    username           = Column(String(100), nullable=True)
    email              = Column(String(255), nullable=True, unique=True)
    first_name         = Column(String(100), nullable=True)
    last_name          = Column(String(100), nullable=True)
    barcode            = Column(String(100), nullable=True)
    referral_type_id   = Column(Integer, nullable=True)

    # Association to a club location
    primary_store_id   = Column(Integer, ForeignKey(f"{ClubLocation.__tablename__}.club_id"))

    # Audit columns
    created_at         = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at         = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    synced_at          = Column(TIMESTAMP(timezone=True), nullable=True)
    created_by         = Column(String(256), nullable=False)
    updated_by         = Column(String(256), nullable=False)

    # Cognito / Auth attributes
    sub                = Column(String(256), nullable=True)
    iss                = Column(String(512), nullable=True)
    auth_time          = Column(String(256), nullable=True)
    aud                = Column(String(256), nullable=True)
    auth_time_human    = Column(String(256), nullable=True)

    # Latest activity tracking
    latest_segment     = Column(String(50), nullable=True)
    latest_activity_date = Column(TIMESTAMP(timezone=True), nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def create_table(cls, engine):
        from sqlalchemy import inspect
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info(f"Created table '{cls.__tablename__}'")
        else:
            logger.info(f"Table '{cls.__tablename__}' already exists")

    @classmethod
    def bulk_upsert_users(cls, session, users: list[dict], audit: dict):
        """
        Bulk upsert users by email: insert new or update existing rows.
        Only updates the columns provided in the INSERT payload.
        """
        # 1) Prepare audit defaults
        audit.setdefault("created_by", "system")
        audit.setdefault("updated_by", "system")

        # 2) Build the list of rows to insert
        values = []
        for u in users:
            raw_ts = u.get("auth_time")
            auth_time_human = None
            if raw_ts:
                try:
                    auth_time_human = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc).isoformat()
                except Exception:
                    logger.warning(f"Invalid auth_time for user {u.get('UserId')}")

            values.append({
                "user_id":           u["UserId"],
                "email":             u["Email"],
                "first_name":        u.get("FirstName"),
                "last_name":         u.get("LastName"),
                "barcode":           u.get("Barcode"),
                "username":          u.get("Username"),
                "referral_type_id":  u.get("ReferralTypeId"),
                "primary_store_id":  u.get("PrimaryStoreId"),
                "created_at":        datetime.now(timezone.utc),
                "updated_at":        datetime.now(timezone.utc),
                "synced_at":         datetime.now(timezone.utc),
                "created_by":        audit["created_by"],
                "updated_by":        audit["updated_by"],
                "sub":               u.get("sub"),
                "iss":               u.get("iss"),
                "auth_time":         raw_ts,
                "aud":               u.get("aud"),
                "auth_time_human":   auth_time_human,
            })

        if not values:
            logger.info("Nothing to upsert")
            return

        # 3) Build the INSERT … ON CONFLICT statement
        stmt = pg_insert(cls).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["email"],   # ← switch UPSERT key back to email
            set_={
                # Update everything else (including user_id!)
                "first_name":          stmt.excluded.first_name,
                "last_name":           stmt.excluded.last_name,
                "barcode":             stmt.excluded.barcode,
                "username":            stmt.excluded.username,
                "referral_type_id":    stmt.excluded.referral_type_id,
                "primary_store_id":    stmt.excluded.primary_store_id,
                "updated_at":          stmt.excluded.updated_at,
                "synced_at":           stmt.excluded.synced_at,
                "updated_by":          stmt.excluded.updated_by,
                "sub":                 stmt.excluded.sub,
                "iss":                 stmt.excluded.iss,
                "auth_time":           stmt.excluded.auth_time,
                "aud":                 stmt.excluded.aud,
                "auth_time_human":     stmt.excluded.auth_time_human,
                
            }
        )

        try:
            session.execute(stmt)
            session.commit()
            logger.info(f"Upserted {len(values)} users (ON CONFLICT email)")
        except Exception as ex:
            logger.exception("❌ bulk_upsert_users failed", exc_info=True)
            logger.debug("Failed upsert statement: %s", stmt)
            logger.debug("Sample payload values: %r", values[:3])
            traceback.print_exc()
            # re-raise so upstream can handle/abort
            raise

    @classmethod
    def bulk_insert_users(cls, session, users: list[dict], audit: dict):
        """
        Bulk insert new users, skipping those with existing user_id.
        """
        audit.setdefault("created_by", "system")
        audit.setdefault("updated_by", "system")
        values = []
        for u in users:
            auth_time_human = None
            raw_ts = u.get("auth_time")
            if raw_ts:
                try:
                    auth_time_human = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc).isoformat()
                except Exception:
                    logger.warning(f"Invalid auth_time for user {u.get('UserId')}")

            values.append({
                "user_id":          u.get("UserId"),
                "email":            u.get("Email"),
                "first_name":       u.get("FirstName"),
                "last_name":        u.get("LastName"),
                "barcode":          u.get("Barcode"),
                "username":         u.get("Username"),
                "referral_type_id": u.get("ReferralTypeId"),
                "primary_store_id": u.get("PrimaryStoreId"),
                "created_at":       datetime.now(timezone.utc),
                "updated_at":       datetime.now(timezone.utc),
                "synced_at":        datetime.now(timezone.utc),
                "created_by":       audit.get("created_by"),
                "updated_by":       audit.get("updated_by"),
                "sub":              u.get("sub"),
                "iss":              u.get("iss"),
                "auth_time":        raw_ts,
                "aud":              u.get("aud"),
                "auth_time_human":  auth_time_human,
            })

        if not values:
            logger.info("No users to insert")
            return

        stmt = pg_insert(cls).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id"])
        session.execute(stmt)
        session.commit()
        logger.info(f"Inserted {len(values)} new users (skipped existing by user_id)")

    @classmethod
    def insert_single_user(cls, session, u: dict, audit: dict = None):
        """
        Insert one user if user_id does not already exist.
        """
        if audit is None:
            audit = {"created_by":"system","updated_by":"system"}

        auth_time_human = None
        raw_ts = u.get("auth_time")
        if raw_ts:
            try:
                auth_time_human = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc).isoformat()
            except Exception:
                logger.warning(f"Invalid auth_time for user {u.get('UserId')}")

        values = {
            "user_id":         u.get("UserId"),
            "email":           u.get("Email"),
            "first_name":      u.get("FirstName"),
            "last_name":       u.get("LastName"),
            "barcode":         u.get("Barcode"),
            "username":        u.get("Username"),
            "referral_type_id":u.get("ReferralTypeId"),
            "primary_store_id":u.get("PrimaryStoreId"),
            "created_at":      datetime.now(timezone.utc),
            "updated_at":      datetime.now(timezone.utc),
            "synced_at":       datetime.now(timezone.utc),
            "created_by":      audit["created_by"],
            "updated_by":      audit["updated_by"],
            "sub":             u.get("sub"),
            "iss":             u.get("iss"),
            "auth_time":       raw_ts,
            "aud":             u.get("aud"),
            "auth_time_human": auth_time_human,
        }
        stmt = pg_insert(cls).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id"])
        session.execute(stmt)
        session.commit()
        logger.info(f"Inserted user_id={values['user_id']} if not existed")

if __name__ == '__main__':
    from com.dimcon.vrse_app.resources.connect_aurora import get_engine
    eng = get_engine()
    ClubUser.create_table(eng)