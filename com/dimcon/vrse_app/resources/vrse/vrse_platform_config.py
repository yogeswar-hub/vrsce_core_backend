from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class PlatformConfig(Base):
    """
    ORM model representing platform integration configuration.
    Stores platform name, API key, chain id, sync settings, audit info,
    and additional Cognito attributes along with human-readable auth time.
    """
    __tablename__ = 'platform_config'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Platform Identity
    platform_name = Column(String(128), nullable=False)
    auth_key = Column(String(512), nullable=False)

    # Chain ID
    chain_id = Column(Integer, nullable=False)

    # Sync Options
    enable_member_sync = Column(Boolean, nullable=False, default=False)
    sync_interval_minutes = Column(Integer, nullable=False, default=60)
    auto_distribute_passes = Column(Boolean, nullable=False, default=False)

    # Audit Timestamps
    last_synced_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(UTC), nullable=False)

    # Audit User Info
    created_by = Column(String(256), nullable=False)
    updated_by = Column(String(256), nullable=False)

    # Additional Cognito Attributes
    sub = Column(String(256), nullable=True)
    username = Column(String(256), nullable=True)
    iss = Column(String(512), nullable=True)
    auth_time = Column(String(256), nullable=True)  # Unix timestamp as string
    aud = Column(String(256), nullable=True)

    # Human readable auth time
    auth_time_human = Column(String(256), nullable=True)

    def to_dict(self):
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
            "updated_by": self.updated_by,
            "sub": self.sub,
            "username": self.username,
            "iss": self.iss,
            "auth_time": self.auth_time,
            "aud": self.aud,
            "auth_time_human": self.auth_time_human
        }

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
            logger.error(f"Failed to create table '{cls.__tablename__}': {str(e)}")

    @classmethod
    def drop_table(cls, engine):
        from sqlalchemy import inspect
        inspector = inspect(engine)
        try:
            if cls.__tablename__ in inspector.get_table_names():
                cls.__table__.drop(bind=engine)
                logger.info(f"Dropped table '{cls.__tablename__}' successfully.")
            else:
                logger.info(f"Table '{cls.__tablename__}' does not exist. Nothing to drop.")
        except Exception as e:
            logger.error(f"Failed to drop table '{cls.__tablename__}': {e}")
            raise

    @classmethod
    def insert_config(cls, session, config_data: dict):
        """
        Inserts a new platform configuration record.
        If an 'auth_time' value is provided (as a Unix timestamp), converts
        it to a human readable string stored in 'auth_time_human'.
        """
        try:
            if "auth_time" in config_data:
                try:
                    unix_ts = int(config_data["auth_time"])
                    dt = datetime.fromtimestamp(unix_ts, tz=UTC)
                    config_data["auth_time_human"] = dt.isoformat()
                except Exception as conv_err:
                    logger.warning(f"Could not convert auth_time: {conv_err}")
                    config_data["auth_time_human"] = None

            new_row = cls(**config_data)
            session.add(new_row)
            session.commit()
            logger.info(f"Inserted platform config for '{new_row.platform_name}' (ID: {new_row.id})")
            return new_row
        except Exception as e:
            logger.error(f"Error inserting platform config: {e}")
            session.rollback()
            raise

    @classmethod
    def update_last_synced(cls, session, config_id, timestamp=None):
        try:
            timestamp = timestamp or datetime.now(UTC)
            row = session.query(cls).filter_by(id=config_id).first()
            if row:
                row.last_synced_at = timestamp
                row.updated_at = datetime.now(UTC)
                session.commit()
                logger.info(f"Updated last_synced_at for config ID {config_id}")
                return True
            else:
                logger.warning(f"No platform config found for ID {config_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to update last_synced_at for config ID {config_id}: {e}")
            session.rollback()
            raise

if __name__ == "__main__":
    from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
    from com.dimcon.vrse_app.resources.connect_aurora import get_engine

    engine = get_engine()
    db_util = DBSessionUtil(engine)

    # Drop and recreate table for testing.
    #PlatformConfig.drop_table(engine)
    #PlatformConfig.create_table(engine)

    # Example configuration data to insert.
    config_data = {
        "platform_name": "club_ready",
        "auth_key": "85b59f92-615a-4f89-8dbf-39bd62f5344c",
        "chain_id": 658,
        "enable_member_sync": True,
        "sync_interval_minutes": 60,
        "auto_distribute_passes": True,
        "created_by": "admin",
        "updated_by": "admin",
        "auth_time": "1624388245",  # Unix timestamp as string
        "sub": "cognito-user-sub",
        "username": "cognito_username",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXX",
        "aud": "client_id_here"
    }

    with db_util.session_scope() as session:
        new_config = PlatformConfig.insert_config(session, config_data)
        print("Inserted config:", new_config.to_dict())
