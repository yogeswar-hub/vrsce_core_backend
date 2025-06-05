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
                logger.info("📍 Starting location fetch with active/inactive counts")

                query = (
                    session.query(
                        ClubLocation.club_id.label("id"),
                        ClubLocation.name.label("name"),
                        func.count(case((ClubActiveMember.segment == 'Active', 1))).label("active_users"),
                        func.count(case((ClubActiveMember.segment == 'Inactive', 1))).label("inactive_users")
                    )
                    .join(ClubUser, ClubUser.primary_store_id == ClubLocation.club_id)
                    .join(ClubActiveMember, ClubActiveMember.user_id == ClubUser.user_id)
                    .group_by(ClubLocation.club_id, ClubLocation.name)
                    .order_by(ClubLocation.name.asc())
                )

                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.filter(func.lower(ClubLocation.name).like(search_term))
                    logger.info(f"🔍 Applied search filter for term: {search}")

                total = query.count()
                logger.debug(f"📦 Total matching locations: {total}")

                paginated_query = query.limit(limit).offset((page - 1) * limit)
                results = paginated_query.all()

                logger.info("✅ Successfully fetched paginated results")
                return {
                    "results": [
                        {
                            "id": row.id,
                            "name": row.name,
                            "active_users": row.active_users,
                            "inactive_users": row.inactive_users
                        } for row in results
                    ],
                    "total_count": total,
                    "page": page,
                    "limit": limit
                }

            except Exception as e:
                logger.error("❌ Error fetching paginated location user counts", exc_info=True)
                raise
