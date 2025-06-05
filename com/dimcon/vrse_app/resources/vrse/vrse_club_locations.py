from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, TIMESTAMP
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

# Setup centralized logger
logger = LoggerManager.setup_logger(__name__)

class ClubLocation(Base):
    """
    Represents a ClubReady location (club) entry synced from the external API.
    Stores metadata such as name, address, contact, identifiers, and additional Cognito attributes.
    """
    __tablename__ = 'club_locations'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ClubReady identifiers
    club_id = Column(Integer, nullable=False, unique=True)  # ClubReady "Id"
    name = Column(String(255), nullable=False)
    district_id = Column(Integer, nullable=True)
    division_id = Column(Integer, nullable=True)
    club_type = Column(String(50), nullable=True)
    credit_balance = Column(Integer, nullable=True)
    time_offset = Column(Integer, nullable=True)
    chain_id = Column(Integer, nullable=True)

    # Address info
    street = Column(String(255), nullable=True)
    city = Column(String(128), nullable=True)
    state_prov = Column(String(10), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # Contact info
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    location_name = Column(String(255), nullable=True)

    # Audit fields
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), nullable=False)
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
        Converts ORM object to dictionary format for serialization/logging.
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def create_table(cls, engine):
        """
        Creates the `club_locations` table if it doesn't already exist.
        """
        from sqlalchemy import inspect
        inspector = inspect(engine)
        try:
            if cls.__tablename__ not in inspector.get_table_names():
                cls.__table__.create(bind=engine)
                logger.info(f"Table '{cls.__tablename__}' created.")
            else:
                logger.info(f"Table '{cls.__tablename__}' already exists. Skipping creation.")
        except Exception as e:
            logger.error(f"Failed to create table '{cls.__tablename__}': {e}")
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

    @classmethod
    @classmethod
    def insert_or_update_locations(cls, session, club_data: list[dict], audit: dict):
        """
        Upserts club locations based on club_id uniqueness.
        """
        try:
            count = 0
            for club in club_data:
                existing = session.query(cls).filter_by(club_id=club["Id"]).first()

                if existing:
                    # Update existing record
                    existing.name = club["Name"]
                    existing.district_id = club.get("DistrictId")
                    existing.division_id = club.get("DivisionId")
                    existing.club_type = club.get("ClubType")
                    existing.credit_balance = club.get("CreditBalance")
                    existing.time_offset = club.get("TimeOffset")
                    existing.chain_id = club.get("ChainId")
                    existing.street = club.get("Address", {}).get("Street")
                    existing.city = club.get("Address", {}).get("City")
                    existing.state_prov = club.get("Address", {}).get("StateProv")
                    existing.postal_code = club.get("Address", {}).get("PostalCode")
                    existing.phone = club.get("Phone")
                    existing.email = club.get("Email")
                    existing.location_name = club.get("LocationName")
                    existing.updated_at = datetime.now(UTC)
                    existing.updated_by = audit.get("updated_by", "unknown")
                else:
                    # Insert new record
                    new_loc = cls(
                        club_id=club["Id"],
                        name=club["Name"],
                        district_id=club.get("DistrictId"),
                        division_id=club.get("DivisionId"),
                        club_type=club.get("ClubType"),
                        credit_balance=club.get("CreditBalance"),
                        time_offset=club.get("TimeOffset"),
                        chain_id=club.get("ChainId"),
                        street=club.get("Address", {}).get("Street"),
                        city=club.get("Address", {}).get("City"),
                        state_prov=club.get("Address", {}).get("StateProv"),
                        postal_code=club.get("Address", {}).get("PostalCode"),
                        phone=club.get("Phone"),
                        email=club.get("Email"),
                        location_name=club.get("LocationName"),
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                        created_by=audit.get("created_by", "unknown"),
                        updated_by=audit.get("updated_by", "unknown"),
                        sub=club.get("sub"),
                        iss=club.get("iss"),
                        auth_time=club.get("auth_time"),
                        aud=club.get("aud"),
                        auth_time_human=club.get("auth_time_human")
                    )
                    session.add(new_loc)
                count += 1

            session.commit()
            logger.info(f"✅ Upserted {count} club location(s) into DB.")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Failed to upsert Club locations: {e}", exc_info=True)
            raise

    @classmethod
    def insert_new_locations(cls, session, club_data: list[dict], audit: dict):
        """
        Inserts only new club location records (skips records where club_id already exists).
        """
        count = 0
        for club in club_data:
            new_location = cls(
                club_id=club["Id"],
                name=club["Name"],
                district_id=club.get("DistrictId"),
                division_id=club.get("DivisionId"),
                club_type=club.get("ClubType"),
                credit_balance=club.get("CreditBalance"),
                time_offset=club.get("TimeOffset"),
                chain_id=club.get("ChainId"),
                street=club.get("Address", {}).get("Street"),
                city=club.get("Address", {}).get("City"),
                state_prov=club.get("Address", {}).get("StateProv"),
                postal_code=club.get("Address", {}).get("PostalCode"),
                phone=club.get("Phone"),
                email=club.get("Email"),
                location_name=club.get("LocationName"),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                created_by=audit.get("created_by", "unknown"),
                updated_by=audit.get("updated_by", "unknown"),
                sub=club.get("sub"),
                iss=club.get("iss"),
                auth_time=club.get("auth_time"),
                aud=club.get("aud"),
                auth_time_human=club.get("auth_time_human")
            )
            session.add(new_location)
            count += 1
        session.commit()
        logger.info(f"Inserted {count} new Club location(s) to DB.")

if __name__ == "__main__":
    from com.dimcon.vrse_app.resources.connect_aurora import get_engine
    from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil

    engine = get_engine()
    db_util = DBSessionUtil(engine)
    ClubLocation.create_table(engine)

