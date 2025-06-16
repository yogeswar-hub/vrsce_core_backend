from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import insert as pg_insert
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
import traceback

logger = LoggerManager.setup_logger(__name__)

def parse_user_payload(user):
    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', ''))
        except ValueError:
            try:
                return datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p")
            except Exception:
                return None

    return {
        "user_id": user.get("UserId"),
        "prospect": user.get("Prospect", False),
        "member": user.get("Member", False),
        "date_added": parse_date(user.get("DateAdded")),
        "email": user.get("Email"),
        "first_name": user.get("FirstName"),
        "last_name": user.get("LastName"),
        "store_id": user.get("StoreId"),
        "username": user.get("Username"),
        "address": user.get("Address"),
        "city": user.get("City"),
        "state": user.get("State"),
        "zip": user.get("Zip"),
        "barcode": user.get("Barcode"),
        "phone": user.get("Phone"),
        "cell_phone": user.get("CellPhone"),
        "external_user_id": user.get("ExternalUserId"),
        "prospect_type_name": user.get("ProspectTypeName"),
        "date_of_birth": parse_date(user.get("DateOfBirth")),
        "member_since_date": parse_date(user.get("MemberSinceDate")),
        "membership_expires_date": parse_date(user.get("MembershipExpiresDate")),
        "membership_ended_date": parse_date(user.get("MembershipEndedDate")),
        "email_opt_out": user.get("EmailOptOut", False),
        "sms_opt_out": user.get("SmsOptOut", False),
        "sms_opt_in": user.get("SmsOptIn", False),
        "referral_type_id": user.get("ReferralTypeId"),
        "referral_type_name": user.get("ReferralTypeName")
    }

class ClubReadyUser(Base):
    __tablename__ = "club_ready_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, index=True)
    prospect = Column(Boolean, nullable=False)
    member = Column(Boolean, nullable=False)
    date_added = Column(TIMESTAMP(timezone=False))
    email = Column(String(255))
    first_name = Column(String(100))
    last_name = Column(String(100))
    store_id = Column(Integer, nullable=False)
    username = Column(String(100))
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(10))
    zip = Column(String(20))
    barcode = Column(String(100))
    phone = Column(String(50))
    cell_phone = Column(String(50))
    external_user_id = Column(String(100))
    prospect_type_name = Column(String(100))
    date_of_birth = Column(TIMESTAMP(timezone=False), nullable=True)
    member_since_date = Column(TIMESTAMP(timezone=False), nullable=True)
    membership_expires_date = Column(TIMESTAMP(timezone=False), nullable=True)
    membership_ended_date = Column(TIMESTAMP(timezone=False), nullable=True)
    email_opt_out = Column(Boolean, nullable=False)
    sms_opt_out = Column(Boolean, nullable=False)
    sms_opt_in = Column(Boolean, nullable=False)
    referral_type_id = Column(Integer)
    referral_type_name = Column(String(100))

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
    def drop_table(cls, engine):
        cls.__table__.drop(engine)
        logger.info(f"Dropped table '{cls.__tablename__}'")

    @classmethod
    def bulk_insert_users(cls, session, users: list[dict]):
        objects = [cls(**user) for user in users]
        session.bulk_save_objects(objects)
        session.commit()
        logger.info(f"Inserted {len(users)} users")

    
    @classmethod
    def bulk_upsert_users(cls, session, users: list[dict]):
        """
        Optimized smart upsert:
        - Prefetches all relevant existing users in one query
        - Compares input with existing data
        - Batches inserts and updates
        """
        try:
            user_id_list = [u.get("user_id") for u in users if u.get("user_id")]
            if not user_id_list:
                logger.warning("No valid user_ids provided.")
                return

            # Step 1: Fetch existing users
            existing_users = session.query(cls).filter(cls.user_id.in_(user_id_list)).all()
            existing_user_map = {user.user_id: user for user in existing_users}

            insert_batch = []
            update_batch = []

            for i, user_data in enumerate(users, start=1):
                user_id = user_data.get("user_id")
                if not user_id:
                    logger.warning(f"[{i}] Skipping record with missing user_id.")
                    continue

                existing = existing_user_map.get(user_id)

                if existing:
                    has_changes = any(
                        getattr(existing, k) != v
                        for k, v in user_data.items()
                        if hasattr(existing, k)
                    )
                    if has_changes:
                        for field, value in user_data.items():
                            setattr(existing, field, value)
                        update_batch.append(existing)
                    else:
                        logger.debug(f"[{i}] Skipped user_id {user_id} (no changes)")
                else:
                    insert_batch.append(cls(**user_data))

            # Step 2: Bulk insert/update
            if insert_batch:
                session.bulk_save_objects(insert_batch)
            session.commit()  # One commit for both insert/update (updates already in session)

            logger.info(f"User upsert complete. Inserted: {len(insert_batch)}, Updated: {len(update_batch)}, Skipped: {len(users) - len(insert_batch) - len(update_batch)}")

        except Exception as e:
            logger.error(f"Upsert operation failed: {e}")
            logger.debug(traceback.format_exc())
            session.rollback()

if __name__ == '__main__':
    from com.dimcon.vrse_app.resources.connect_aurora import get_engine
    engine = get_engine()
    #ClubReadyUser.drop_table(engine)
    ClubReadyUser.create_table(engine)
