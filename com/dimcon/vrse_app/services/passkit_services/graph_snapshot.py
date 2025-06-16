# com/dimcon/vrse_app/services/graph_snapshot.py

import json
from sqlalchemy import func
from com.dimcon.vrse_app.resources.vrse_passkit.database_scripts.graph_snapshot_json import GraphSnapshotJson
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class GraphSnapshot:
    """
    Service class to interact with GraphSnapshotJson table.
    Handles fetching the latest graph snapshot from the database.
    """

    def __init__(self, session):
        """
        Initialize with a SQLAlchemy session.

        Args:
            session (Session): SQLAlchemy DB session.
        """
        self.session = session
        logger.debug("GraphSnapshot service initialized with session %s", session)

    def get_latest_snapshot(self):
        """
        Fetch the latest snapshot from the database.

        Returns:
            tuple: (max_millis, json_obj) or (None, None) if no data found.
        """
        try:
            max_millis = self.session.query(func.max(GraphSnapshotJson.captured_at_millis)).scalar()
            logger.debug(f"Max captured_at_millis found: {max_millis}")

            if not max_millis:
                logger.info("No graph snapshots found in database.")
                return None, None

            record = self.session.query(GraphSnapshotJson).filter_by(captured_at_millis=max_millis).first()
            if not record:
                logger.warning(f"No record found for captured_at_millis={max_millis}")
                return max_millis, None

            json_str = record.file_binary.decode("utf-8")
            json_obj = json.loads(json_str)
            logger.debug(f"Successfully decoded JSON snapshot for millis={max_millis}")
            return max_millis, json_obj

        except Exception as e:
            logger.error("Failed to fetch latest graph snapshot", exc_info=True)
            return None, None
