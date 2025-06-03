from sqlalchemy import func
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.vrse_app.resources.base_dao import BaseDAO
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubLocationService(BaseDAO):
    """
    Data Access Object (DAO) for ClubLocation records.
    Provides standard CRUD operations using BaseDAO methods.
    """
    def __init__(self):
        engine = get_engine()
        super().__init__(engine)
        self.db_util = DBSessionUtil(engine)

    def fetch_locations(self, session, page=1, limit=10, sort_by="id", sort_order="asc", filters=None):
        try:
            # Uses BaseDAO.fetch_all to return paginated records.
            data = self.fetch_all(session, ClubLocation, page, limit, sort_by, sort_order, filters)
            return data
        except Exception as e:
            logger.error("Error fetching club locations", exc_info=True)
            raise

    def fetch_by_id(self, session, location_id):
        return super().fetch_by_id(session, ClubLocation, location_id)

    def insert_location(self, session, location_instance):
        return super().insert(session, location_instance)

    def update_location(self, session, location_id, data):
        return super().update(session, ClubLocation, location_id, data)

    def delete_location(self, session, location_id):
        return super().delete(session, ClubLocation, location_id)

    def fetch_location_overview(self, page=1, limit=100):
        """
        Returns a list of dicts like:
          {
            "id":           <club_id>,
            "name":         <location.name>,
            "users":        <count of users at this club_id>,
            "active_passes": 0,       # placeholder
            "integration":  <platform_name>
          }
        """
        logger.info("Starting fetch_location_overview: page %s, limit %s", page, limit)
        with self.db_util.session_scope() as session:
            logger.debug("Fetching integration config")
            # 1) Load integration name (assuming just one row)
            cfg = session.query(PlatformConfig).first()
            integration_name = cfg.platform_name if cfg else None
            logger.info("Integration config fetched: integration_name set")

            logger.debug("Counting users per location")
            # 2) Count users per location
            user_counts = (
                session
                .query(
                    ClubUser.primary_store_id,
                    func.count(ClubUser.id).label("user_count")
                )
                .group_by(ClubUser.primary_store_id)
                .all()
            )
            counts_map = {loc_id: cnt for loc_id, cnt in user_counts}
            logger.info("User counts aggregated for locations")

            logger.debug("Querying paginated locations")
            # 3) Fetch locations (paginated)
            loc_query = session.query(ClubLocation).order_by(ClubLocation.name.asc())
            total = loc_query.count()
            locs = loc_query.limit(limit).offset((page - 1) * limit).all()
            logger.info("Fetched %s locations out of total %s", len(locs), total)

            logger.debug("Building response object")
            # 4) Build the response
            results = []
            for loc in locs:
                results.append({
                    "id":            loc.club_id,
                    "name":          loc.name,
                    "users":         counts_map.get(loc.club_id, 0),
                    "active_passes": 0,
                    "integration":   integration_name
                })
            logger.info("Response built successfully with descriptive logs")

            return {"results": results, "total_count": total}