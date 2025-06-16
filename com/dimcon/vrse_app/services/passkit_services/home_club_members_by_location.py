import json
from sqlalchemy import func
from com.dimcon.vrse_app.resources.vrse_passkit.database_scripts.homeclub_snapshot_json import HomeclubSnapshot
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class HomeClubMembersByLocation:
    """
    Provides methods to fetch the latest Homeclub snapshot of active members by location.
    """

    def __init__(self, session):
        """
        Initialize with an active SQLAlchemy session.

        Args:
            session (Session): SQLAlchemy session object.
        """
        self.session = session

    def get_latest_snapshot(self):
        """
        Fetch the latest snapshot record by max captured_at_millis timestamp.

        Returns:
            tuple: (max_millis (int or None), json_obj (dict or None))
        """
        try:
            max_millis = self.session.query(func.max(HomeclubSnapshot.captured_at_millis)).scalar()
            if not max_millis:
                logger.info("No snapshots found in DB.")
                return None, None

            record = (
                self.session.query(HomeclubSnapshot)
                .filter_by(captured_at_millis=max_millis)
                .first()
            )
            if not record:
                logger.warning(f"Snapshot with max millis {max_millis} not found.")
                return max_millis, None

            json_str = record.file_binary.decode("utf-8")
            json_obj = json.loads(json_str)
            logger.info(f"Retrieved latest snapshot with timestamp {max_millis}.")
            return max_millis, json_obj

        except Exception:
            logger.error("Failed to get latest snapshot", exc_info=True)
            return None, None
