import json
from sqlalchemy.orm import sessionmaker
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.services.passkit_services.home_club_members_by_location import HomeClubMembersByLocation as HomeClubService
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder  # shared response builder

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class HomeClubMembersByLocation:
    """
    Lambda route handler for fetching the latest Homeclub members snapshot.

    Opens a DB session, fetches the latest snapshot via the service,
    and returns HTTP response with the snapshot data.
    """

    def __init__(self):
        self.engine = get_engine()
        self.Session = sessionmaker(bind=self.engine)

    def handle_event(self, event):
        session = self.Session()
        try:
            logger.info("Fetching latest Homeclub members snapshot")
            snapshot_handler = HomeClubService(session)
            millis, data = snapshot_handler.get_latest_snapshot()
            if millis is None:
                logger.info("No snapshot data found.")
                return {"message": "No snapshot data found."}
            return {
                "captured_at_millis": millis,
                "snapshot": data
            }
        except Exception as e:
            logger.error("Error in HomeClubMembersByLocationRouteHandler", exc_info=True)
            return {"error": str(e)}
        finally:
            session.close()
