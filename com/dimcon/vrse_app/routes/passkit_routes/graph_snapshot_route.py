import json
from sqlalchemy.orm import sessionmaker
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.services.passkit_services.graph_snapshot import GraphSnapshot
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class GraphSnapshotRoute:
    """
    Route handler class to serve the latest graph snapshot.
    Handles creating DB session and formatting HTTP responses.
    """

    def __init__(self):
        """
        Initialize the DB session maker.
        """
        engine = get_engine()
        self.Session = sessionmaker(bind=engine)
        logger.debug("GraphSnapshotRoute initialized with DB session maker")

    def handle_event(self, event):
        """
        Handle incoming Lambda event, fetch latest graph snapshot,
        and build an appropriate HTTP response.

        Args:
            event (dict): Lambda event object.

        Returns:
            dict: HTTP response compatible with API Gateway.
        """
        session = self.Session()
        try:
            logger.info("Fetching latest graph snapshot")
            snapshot_service = GraphSnapshot(session)
            millis, snapshot = snapshot_service.get_latest_snapshot()

            if millis is None:
                logger.info("No graph snapshot data available")
                return ResponseBuilder.build_response(404, {"message": "No snapshot data available."})

            logger.info(f"Returning snapshot captured at millis: {millis}")
            return ResponseBuilder.build_response(200, {
                "message": "Latest graph snapshot retrieved",
                "captured_at_millis": millis,
                "snapshot": snapshot
            })

        except Exception as e:
            logger.error("Error handling graph snapshot route", exc_info=True)
            return ResponseBuilder.build_response(500, {"error": str(e)})

        finally:
            session.close()
