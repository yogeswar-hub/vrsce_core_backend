from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, TIMESTAMP
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(256), nullable=False)
    username = Column(String(256), nullable=True)
    resource = Column(String(256), nullable=False)
    method = Column(String(10), nullable=False)
    accessed_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
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
    def drop_table(cls, engine):
        try:
            cls.__table__.drop(bind=engine)
            logger.info(f"Table '{cls.__tablename__}' dropped successfully.")
        except Exception as e:
            logger.error(f"Failed to drop table '{cls.__tablename__}': {e}")
            raise

if __name__ == "__main__":
    from com.dimcon.vrse_app.resources.connect_aurora import get_engine
    engine = get_engine()
    AuditLog.create_table(engine)