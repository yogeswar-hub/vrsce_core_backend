from com.dimcon.vrse_app.services.passkit_services.count_status_snapshot import CountStatusSnapshot
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class CountStatusSnapshotRoute:
    """
    Route handler returning only the raw JSON data dictionary
    without HTTP response wrapping.
    """

    def __init__(self):
        self.service = CountStatusSnapshot()

    def handle_event_raw(self, event):
        try:
            millis, snapshot = self.service.get_latest_snapshot()
            if millis is None:
                logger.info("No snapshot data available.")
                return {"message": "No snapshot data available."}

            return {
                "captured_at_millis": millis,
                "parsed_json": snapshot,
            }

        except Exception as e:
            logger.error("Error occurred in handle_event_raw", exc_info=True)
            return {"message": "Internal server error"}


