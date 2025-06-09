from sqlalchemy import func, case
from com.dimcon.vrse_app.resources.vrse.vrse_club_members_activity import ClubActiveMember
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.resources.base_dao import BaseDAO
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubLocationService(BaseDAO):
    def __init__(self):
        engine = get_engine()
        super().__init__(engine)
        self.db_util = DBSessionUtil(engine)

    def fetch_all_locations_with_active_and_inactive_counts(self, page=1, limit=10, search=None):
        with self.db_util.session_scope() as session:
            try:
                logger.info("📍 Starting location fetch with counts by latest_segment")

                # Query: group by location and latest_segment.
                query = (
                    session.query(
                        ClubLocation.club_id.label("id"),
                        ClubLocation.name.label("name"),
                        func.coalesce(func.lower(ClubUser.latest_segment), 'no status assigned').label("latest_segment"),
                        func.count(ClubUser.user_id).label("user_count")
                    )
                    .join(ClubUser, ClubUser.primary_store_id == ClubLocation.club_id)
                    .group_by(ClubLocation.club_id, ClubLocation.name, func.coalesce(func.lower(ClubUser.latest_segment), 'no status assigned'))
                    .order_by(ClubLocation.name.asc())
                )

                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.filter(func.lower(ClubLocation.name).like(search_term))
                    logger.info(f"🔍 Applied search filter for term: {search}")

                # Get raw results.
                rows = query.all()
                logger.debug(f"📦 Total grouped rows returned: {len(rows)}")

                # Transform grouped rows into a simpler structure per location.
                locations = {}
                for row in rows:
                    loc_id = row.id
                    if loc_id not in locations:
                        locations[loc_id] = {
                            "id":                    loc_id,
                            "name":                  row.name,
                            "active_users":          0,
                            "inactive_users":        0,
                            "all_users":             0,
                            "no_status_assigned":    0,
                            "prospects_users":       0,   # new
                            "past_due_users":        0    # new
                        }
                    seg   = row.latest_segment
                    count = row.user_count

                    if   seg == "active":
                        locations[loc_id]["active_users"] = count
                    elif seg == "inactive":
                        locations[loc_id]["inactive_users"] = count
                    elif seg == "all":
                        locations[loc_id]["all_users"] = count
                    elif seg == "prospects":                      # new
                        locations[loc_id]["prospects_users"] = count
                    elif seg == "pastdue":                        # new (lowercase from DB)
                        locations[loc_id]["past_due_users"] = count
                    elif seg == "no status assigned":
                        locations[loc_id]["no_status_assigned"] = count
                    else:
                        # unexpected segment → lump into no_status_assigned
                        locations[loc_id]["no_status_assigned"] += count

                all_locations = list(locations.values())
                total = len(all_locations)
                logger.info("✅ Successfully grouped simplified location results by segments")

                # Apply pagination manually.
                start = (page - 1) * limit
                end = start + limit
                paginated_locations = all_locations[start:end]

                return {
                    "results": paginated_locations,
                    "total_count": total,
                    "page": page,
                    "limit": limit
                }

            except Exception as e:
                logger.error("❌ Error fetching paginated location counts by latest_segment", exc_info=True)
                raise
