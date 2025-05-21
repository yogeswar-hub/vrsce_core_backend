from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from com.dimcon.synthera.resources.base import Base

# Logger setup
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__)

class PlatformConfig(Base):
    """
    ORM model representing platform integration configuration for sync automation.
    Stores platform name, auth keys, sync timing, chain id, and audit fields.
    """
    __tablename__ = 'platform_config'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Platform Identity
    platform_name = Column(String(128), nullable=False)  # e.g., 'ClubReady', 'Shopify'
    auth_key = Column(String(512), nullable=False)        # API Key

    # New: Chain ID
    chain_id = Column(Integer, nullable=False)

    # Sync Options
    enable_member_sync = Column(Boolean, nullable=False, default=False)  # toggle sync on/off
    sync_interval_minutes = Column(Integer, nullable=False, default=60)  # sync frequency (e.g., 60 min)
    auto_distribute_passes = Column(Boolean, nullable=False, default=False)  # whether to send passes post-sync

    # Audit Timestamps
    last_synced_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), nullable=False)

    # Audit User Info
    created_by = Column(String(256), nullable=False)
    updated_by = Column(String(256), nullable=False)

    def to_dict(self):
        """
        Converts ORM object to a serializable dictionary format.
        """
        return {
            "id": self.id,
            "platform_name": self.platform_name,
            "auth_key": self.auth_key,
            "chain_id": self.chain_id,
            "enable_member_sync": self.enable_member_sync,
            "sync_interval_minutes": self.sync_interval_minutes,
            "auto_distribute_passes": self.auto_distribute_passes,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by
        }

    @classmethod
    def create_table(cls, engine):
        """
        Creates the table if it doesn't exist.
        """
        from sqlalchemy import inspect
        inspector = inspect(engine)

        try:
            if cls.__tablename__ not in inspector.get_table_names():
                cls.__table__.create(bind=engine)
                logger.info(f"  Table '{cls.__tablename__}' created successfully.")
            else:
                logger.info(f"  Table '{cls.__tablename__}' already exists. Skipping creation.")
        except Exception as e:
            logger.error(f"  Failed to create table '{cls.__tablename__}': {str(e)}")

    @classmethod
    def drop_table(cls, engine):
        """
        Drops the platform_config table if it exists.
        """
        from sqlalchemy import inspect
        inspector = inspect(engine)
        try:
            if cls.__tablename__ in inspector.get_table_names():
                cls.__table__.drop(bind=engine)
                logger.info(f"  Dropped table '{cls.__tablename__}' successfully.")
            else:
                logger.info(f"  Table '{cls.__tablename__}' does not exist. Nothing to drop.")
        except Exception as e:
            logger.error(f"  Failed to drop table '{cls.__tablename__}': {e}")
            raise

    @classmethod
    def insert_config(cls, session, config_data: dict):
        """
        Inserts a new platform configuration record.
        :param session: active DB session
        :param config_data: dict with keys matching column names
        """
        try:
            new_row = cls(**config_data)
            session.add(new_row)
            session.commit()
            logger.info(f"  Inserted platform config for '{new_row.platform_name}' (ID: {new_row.id})")
            return new_row
        except Exception as e:
            logger.error(f" Error inserting platform config: {e}")
            session.rollback()
            raise

    @classmethod
    def update_last_synced(cls, session, config_id, timestamp=None):
        """
        Updates the `last_synced_at` timestamp for a specific config.
        """
        try:
            timestamp = timestamp or datetime.now(UTC)
            row = session.query(cls).filter_by(id=config_id).first()
            if row:
                row.last_synced_at = timestamp
                row.updated_at = datetime.now(UTC)
                session.commit()
                logger.info(f"  Updated last_synced_at for config ID {config_id}")
                return True
            else:
                logger.warning(f" No platform config found for ID {config_id}")
                return False
        except Exception as e:
            logger.error(f" Failed to update last_synced_at for config ID {config_id}: {e}")
            session.rollback()
            raise

if __name__ == "__main__":
    from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil
    from com.dimcon.synthera.resources.connect_aurora import get_engine

    engine = get_engine()
    db_util = DBSessionUtil(engine)

    # Example: Drop table, then insert a new configuration
    PlatformConfig.create_table(engine)

    
    config_data = {
        "platform_name": "club_ready",
        "auth_key": "85b59f92-615a-4f89-8dbf-39bd62f5344c",
        "chain_id": 658,
        "enable_member_sync": True,
        "sync_interval_minutes": 60,
        "auto_distribute_passes": True,
        "created_by": "admin",
        "updated_by": "admin"
    }
    with db_util.session_scope() as session:
        new_config = PlatformConfig.insert_config(session, config_data)
        print("Inserted config:", new_config.to_dict())
