import json
import os
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, LargeBinary, BigInteger, DateTime, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from com.dimcon.vrse_app.resources.base import Base
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

from sqlalchemy import inspect

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class HomeclubSnapshot(Base):
    """
    ORM model for storing homeclub snapshot data as JSON bytes.
    Provides CRUD and table management methods.
    """
    __tablename__ = "homeclub_snapshot_json"  # Updated table name here

    id = Column(Integer, primary_key=True, autoincrement=True)
    program_id = Column(String(255), nullable=False)
    file_binary = Column(LargeBinary, nullable=False)  # JSON bytes
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    captured_at_millis = Column(BigInteger, nullable=False, default=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))
     
    @classmethod
    def create_table_if_not_exists(cls, engine):
        if not engine.dialect.has_table(engine, cls.__tablename__):
            Base.metadata.create_all(engine, tables=[cls.__table__])
            logger.info(f"Created table {cls.__tablename__} as it did not exist.")
        else:
            logger.info(f"Table {cls.__tablename__} already exists. Skipping creation.")

    @classmethod
    def insert(cls, session: Session, program_id: str, content_bytes: bytes):
        """Insert a new snapshot and commit."""
        snapshot = cls.create(session, program_id, content_bytes)
        session.commit()
        logger.info(f"Inserted snapshot ID {snapshot.id} and committed.")
        return snapshot

    @classmethod
    def read_by_id(cls, session: Session, record_id: int):
        """Retrieve snapshot by ID or None."""
        try:
            record = session.query(cls).filter_by(id=record_id).first()
            if not record:
                logger.warning(f"Snapshot ID {record_id} not found.")
            return record
        except Exception:
            logger.error(f"Read failed for ID {record_id}", exc_info=True)
            raise

    @classmethod
    def update(cls, session: Session, record_id: int, new_content_bytes: bytes):
        """Update snapshot content by ID and commit."""
        try:
            if isinstance(new_content_bytes, str):
                new_content_bytes = new_content_bytes.encode("utf-8")

            record = session.query(cls).filter_by(id=record_id).first()
            if not record:
                logger.warning(f"Snapshot ID {record_id} not found for update.")
                return None

            record.file_binary = new_content_bytes
            record.captured_at = datetime.now(timezone.utc)
            record.captured_at_millis = int(datetime.now(timezone.utc).timestamp() * 1000)
            session.commit()
            logger.info(f"Updated snapshot ID {record_id} and committed.")
            return record
        except Exception:
            session.rollback()
            logger.error(f"Update failed for ID {record_id}", exc_info=True)
            raise

    @classmethod
    def delete(cls, session: Session, record_id: int):
        """Delete snapshot by ID and commit; returns True if deleted."""
        try:
            record = session.query(cls).filter_by(id=record_id).first()
            if record:
                session.delete(record)
                session.commit()
                logger.info(f"Deleted snapshot ID {record_id} and committed.")
                return True
            logger.warning(f"Snapshot ID {record_id} not found for deletion.")
            return False
        except Exception:
            session.rollback()
            logger.error("Delete failed", exc_info=True)
            raise

    @classmethod
    def drop_table(cls, engine):
        """Drop homeclub_snapshot_json table if exists."""
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Dropped homeclub_snapshot_json table.")

    @classmethod
    def fetch_all_by_program(cls, session: Session, program_id: str, page=1, limit=10):
        """Fetch snapshots by program_id with pagination."""
        query = session.query(cls).filter(cls.program_id == program_id)
        total = query.count()
        results = query.order_by(cls.captured_at_millis.desc())\
                       .limit(limit).offset((page - 1) * limit).all()
        return {"results": results, "total_count": total}

    @classmethod
    def alter_table(cls, engine, column_sql: str):
        """Execute raw SQL to alter the table."""
        with engine.connect() as conn:
            conn.execute(text(column_sql))
            logger.info(f"Altered table with SQL: {column_sql}")

    @classmethod
    def create(cls, session: Session, program_id: str, content_bytes: bytes):
        """
        Create a new snapshot record without committing.
        Use insert() to commit.
        """
        try:
            if isinstance(content_bytes, str):
                content_bytes = content_bytes.encode("utf-8")

            snapshot = cls(
                program_id=program_id,
                file_binary=content_bytes,
                captured_at=datetime.now(timezone.utc),
                captured_at_millis=int(datetime.now(timezone.utc).timestamp() * 1000)
            )
            session.add(snapshot)
            logger.info("Inserted homeclub snapshot.")

            # Keep only latest 5 snapshots
            all_ids = (
                session.query(cls.id)
                .order_by(cls.captured_at_millis.desc())
                .offset(5)
                .all()
            )
            if all_ids:
                ids_to_delete = [row.id for row in all_ids]
                session.query(cls).filter(cls.id.in_(ids_to_delete)).delete(synchronize_session=False)
                logger.info(f"Deleted old snapshot IDs: {ids_to_delete}")

            return snapshot

        except SQLAlchemyError:
            session.rollback()
            logger.error("Insert failed", exc_info=True)
            raise

    @classmethod
    def export_to_file(cls, session: Session, record_id: int, export_dir: str = "."):
        """Export snapshot binary to a JSON file."""
        try:
            record = session.query(cls).filter_by(id=record_id).first()
            if not record:
                logger.warning(f"Snapshot ID {record_id} not found.")
                return False

            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, f"homeclub_snapshot_{record_id}.json")
            with open(export_path, "wb") as f:
                f.write(record.file_binary)
            logger.info(f"Exported snapshot to {export_path}")
            return True
        except Exception:
            logger.error("Export failed", exc_info=True)
            raise

if __name__ == "__main__":
    engine = get_engine()
    db_util = DBSessionUtil(engine)

    inspector = inspect(engine)
    if not inspector.has_table(HomeclubSnapshot.__tablename__):
        Base.metadata.create_all(engine, tables=[HomeclubSnapshot.__table__])
        logger.info(f"Created table {HomeclubSnapshot.__tablename__} as it did not exist.")
    else:
        logger.info(f"Table {HomeclubSnapshot.__tablename__} already exists. No action taken.")
