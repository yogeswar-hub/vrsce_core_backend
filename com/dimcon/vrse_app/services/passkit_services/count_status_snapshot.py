import json
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.resources.vrse_passkit.database_scripts.status_snapshot_json import StatusSnapshotJson
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class CountStatusSnapshot:
    """
    Service to fetch the latest count status snapshot from the database.

    Manages its own database session internally.
    """

    def __init__(self):
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def get_latest_snapshot(self):
        """
        Retrieves the latest snapshot record by timestamp.

        Returns:
            tuple: (captured_at_millis (int or None), snapshot JSON dict or None)
        """
        try:
            max_millis = self.session.query(func.max(StatusSnapshotJson.captured_at_millis)).scalar()
            logger.debug(f"Max captured_at_millis: {max_millis}")

            if not max_millis:
                logger.info("No snapshots found in the database.")
                return None, None

            record = self.session.query(StatusSnapshotJson).filter_by(captured_at_millis=max_millis).first()

            if not record:
                logger.warning(f"No record found for millis={max_millis}")
                return max_millis, None

            try:
                json_str = record.file_binary.decode("utf-8")
                json_obj = json.loads(json_str)
                logger.debug(f"Decoded JSON snapshot for millis={max_millis}")
                return max_millis, json_obj
            except Exception as e:
                logger.error(f"Failed to decode JSON snapshot for millis={max_millis}", exc_info=True)
                return max_millis, None

        except Exception as e:
            logger.error("Database query failed while fetching latest snapshot.", exc_info=True)
            return None, None

        finally:
            self.session.close()
