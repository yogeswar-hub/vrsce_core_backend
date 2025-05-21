from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, TIMESTAMP
from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.utilities.log_handler import LoggerManager

# Setup centralized logger
logger = LoggerManager.setup_logger(__name__)

class ClubLocation(Base):
    """
    Represents a ClubReady location (club) entry synced from the external API.
    Stores metadata such as name, address, contact, and identifiers.
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
                logger.info(f" Table '{cls.__tablename__}' created.")
            else:
                logger.info(f" Table '{cls.__tablename__}' already exists. Skipping creation.")
        except Exception as e:
            logger.error(f" Failed to create table '{cls.__tablename__}': {e}")
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
    def insert_or_update_locations(cls, session, club_data: list[dict], audit: dict):
        """
        Inserts or updates Club location records into the database.
        
        Args:
            session: Active SQLAlchemy session.
            club_data: List of dicts representing clubs from the ClubReady API.
            audit: Dict with keys 'created_by' and 'updated_by' extracted from the event (e.g. Cognito claims).
        """
        try:
            count = 0
            for club in club_data:
                address = club.get("Address", {})
                location = cls(
                    club_id=club["Id"],
                    name=club["Name"],
                    district_id=club.get("DistrictId"),
                    division_id=club.get("DivisionId"),
                    club_type=club.get("ClubType"),
                    credit_balance=club.get("CreditBalance"),
                    time_offset=club.get("TimeOffset"),
                    chain_id=club.get("ChainId"),
                    street=address.get("Street"),
                    city=address.get("City"),
                    state_prov=address.get("StateProv"),
                    postal_code=address.get("PostalCode"),
                    phone=club.get("Phone"),
                    email=club.get("Email"),
                    location_name=club.get("LocationName"),
                    updated_at=datetime.now(UTC),
                    created_at=datetime.now(UTC),
                    created_by=audit.get("created_by", "unknown"),
                    updated_by=audit.get("updated_by", "unknown")
                )
                session.merge(location)  # merge = insert or update
                count += 1
            session.commit()
            logger.info(f"Synced {count} Club location(s) to DB.")
        except Exception as e:
            logger.error(f"Failed to insert/update Club locations: {e}")
            session.rollback()
            raise
if __name__ == "__main__":
    from com.dimcon.synthera.resources.connect_aurora import get_engine
    from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

    engine = get_engine()
    db_util = DBSessionUtil(engine)

    # Create the table if not exists
    ClubLocation.create_table(engine)

