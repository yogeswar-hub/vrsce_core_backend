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
    """
    Service layer for fetching club locations along with user segment counts.
    Provides paginated results and grouping by 'latest_segment'.
    """
    def __init__(self):
        """
        Initialize the DAO with an Aurora engine and a session manager.
        """
        engine = get_engine()
        super().__init__(engine)
        self.db_util = DBSessionUtil(engine)

    def fetch_all_locations_with_active_and_inactive_counts(self, page=1, limit=10, search=None):
        """
        Retrieve a paginated list of club locations, each annotated with counts of users
        in various segments (active, inactive, prospects, past due, etc.).

        Args:
            page (int): 1-based page number for pagination.
            limit (int): Number of locations to return per page.
            search (str, optional): Case-insensitive substring to filter location names.

        Returns:
            dict: {
                "results": [ { "id": int, "name": str, ..., "past_due_users": int } ],
                "total_count": int,
                "page": int,
                "limit": int
            }

        Raises:
            Exception: Propagates any database or unexpected errors after logging.
        """
        with self.db_util.session_scope() as session:
            # Log inputs for debugging
            logger.debug(
                "fetch_all_locations_with_active_and_inactive_counts called with "
                "page=%s, limit=%s, search=%r", page, limit, search
            )
            try:
                logger.info("Starting location fetch with counts by latest_segment")

                # Build the grouping query
                query = (
                    session.query(
                        ClubLocation.club_id.label("id"),
                        ClubLocation.name.label("name"),
                        func.coalesce(
                            func.lower(ClubUser.latest_segment),
                            'no status assigned'
                        ).label("latest_segment"),
                        func.count(ClubUser.user_id).label("user_count")
                    )
                    .join(ClubUser, ClubUser.primary_store_id == ClubLocation.club_id)
                    .group_by(
                        ClubLocation.club_id,
                        ClubLocation.name,
                        func.coalesce(
                            func.lower(ClubUser.latest_segment),
                            'no status assigned'
                        )
                    )
                    .order_by(ClubLocation.name.asc())
                )

                # Optional search filter
                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.filter(func.lower(ClubLocation.name).like(search_term))
                    logger.info("Applied search filter for term: %s", search)

                # Execute and log row count
                rows = query.all()
                logger.debug("Total grouped rows returned: %d", len(rows))

                # Transform into structured dict per location
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
                            "prospects_users":       0,
                            "past_due_users":        0
                        }
                    seg = row.latest_segment
                    count = row.user_count

                    # Assign counts based on segment
                    if seg == "active":
                        locations[loc_id]["active_users"] = count
                    elif seg == "inactive":
                        locations[loc_id]["inactive_users"] = count
                    elif seg == "all":
                        locations[loc_id]["all_users"] = count
                    elif seg == "prospects":
                        locations[loc_id]["prospects_users"] = count
                    elif seg == "pastdue":
                        locations[loc_id]["past_due_users"] = count
                    elif seg == "no status assigned":
                        locations[loc_id]["no_status_assigned"] = count
                    else:
                        # Unexpected segment: accumulate under no_status_assigned
                        locations[loc_id]["no_status_assigned"] += count

                all_locations = list(locations.values())
                total = len(all_locations)
                logger.info(
                    "Successfully grouped simplified location results; total locations: %d", total
                )

                # Manual pagination
                start = (page - 1) * limit
                end = start + limit
                paginated_locations = all_locations[start:end]
                logger.debug(
                    "Paginated results indexes: start=%d, end=%d, returned=%d",
                    start, end, len(paginated_locations)
                )

                return {
                    "results":     paginated_locations,
                    "total_count": total,
                    "page":        page,
                    "limit":       limit
                }

            except Exception as e:
                # Log full stack trace with context
                logger.error(
                    "Error fetching paginated location counts "
                    "(page=%s, limit=%s, search=%r): %s",
                    page, limit, search, e, exc_info=True
                )
                # Re-raise so callers can handle or propagate
                raise
