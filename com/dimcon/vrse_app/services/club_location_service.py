# club_location_service.py

from datetime import datetime
from sqlalchemy import (
    func, case, and_, select, literal_column
)
from sqlalchemy.sql import over
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_user_data import ClubReadyUser
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubLocationService:
    def __init__(self, engine=None):
        self.engine = engine or get_engine()
        self.db_util = DBSessionUtil(self.engine)

    def fetch_all_locations_with_active_and_inactive_counts(
        self,
        page: int = 1,
        limit: int = 10,
        search: str | None = None
    ) -> dict:
        """
        Paginated club locations, each with DISTINCT counts of:
          1. Active members  (seg_rank=1)
          2. Inactive members(seg_rank=2)
          3. Prospects        (seg_rank=3)

        Uses a CTE + ROW_NUMBER() to pick exactly one “best” row per (store_id, user_id).
        """
        now = datetime.utcnow()

        # 1) Define segment ranking: 1=active, 2=inactive, 3=prospect, 4=else
        seg_rank = case(
            (and_(
                ClubReadyUser.member.is_(True),
                ClubReadyUser.membership_expires_date > now,
                ClubReadyUser.membership_ended_date.is_(None),
            ), 1),
            (and_(
                ClubReadyUser.member.is_(True),
                ClubReadyUser.membership_expires_date < now,
                ClubReadyUser.membership_ended_date < now,
            ), 2),
            (and_(
                ClubReadyUser.member.is_(False),
                ClubReadyUser.prospect.is_(True),
            ), 3),
            else_=4
        ).label("seg_rank")

        with self.db_util.session_scope() as session:
            # 2) CTE: assign row_number partitioned by (store_id, user_id)
            user_seg = (
                session.query(
                    ClubReadyUser.store_id.label("store_id"),
                    ClubReadyUser.user_id.label("user_id"),
                    seg_rank,
                    over(
                        func.row_number(),
                        partition_by=(ClubReadyUser.store_id, ClubReadyUser.user_id),
                        order_by=seg_rank
                    ).label("rn")
                )
            ).subquery()

            # 3) Keep only the top-ranked row per user
            first_seg = (
                select(
                    user_seg.c.store_id,
                    user_seg.c.user_id,
                    user_seg.c.seg_rank
                )
                .where(user_seg.c.rn == 1)
            ).cte("first_seg")

            # 4) Final aggregation: count each segment per location
            query = (
                session.query(
                    ClubLocation.club_id.label("id"),
                    ClubLocation.name.label("name"),
                    func.count(
                        case((first_seg.c.seg_rank == 1, first_seg.c.user_id))
                    ).label("active_users"),
                    func.count(
                        case((first_seg.c.seg_rank == 2, first_seg.c.user_id))
                    ).label("inactive_users"),
                    func.count(
                        case((first_seg.c.seg_rank == 3, first_seg.c.user_id))
                    ).label("prospects_users"),
                )
                .outerjoin(
                    first_seg,
                    first_seg.c.store_id == ClubLocation.club_id
                )
                .group_by(ClubLocation.club_id, ClubLocation.name)
                .order_by(ClubLocation.name.asc())
            )

            # 5) Optional search filter
            if search:
                term = f"%{search.lower()}%"
                query = query.filter(func.lower(ClubLocation.name).like(term))
                logger.debug("Applied search filter for term=%r", search)

            rows = query.all()
            total = len(rows)
            logger.info("Fetched %d locations with user counts", total)

            # 6) In-Python pagination
            start, end = (page - 1) * limit, page * limit
            page_rows = rows[start:end]

            results = [
                {
                    "id":               r.id,
                    "name":             r.name,
                    "active_users":     r.active_users,
                    "inactive_users":   r.inactive_users,
                    "prospects_users":  r.prospects_users,
                }
                for r in page_rows
            ]

            return {
                "results":     results,
                "total_count": total,
                "page":        page,
                "limit":       limit
            }
