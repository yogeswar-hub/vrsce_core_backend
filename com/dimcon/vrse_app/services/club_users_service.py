from datetime import datetime
from sqlalchemy import select, case, and_, func, desc, over
from sqlalchemy.sql import literal_column, or_, literal
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_user_data import ClubReadyUser
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubUsersService:
    def __init__(self, engine):
        """
        Initializes the service with a DB engine for session management.
        """
        self.db_util = DBSessionUtil(engine)

    def fetch_users_by_location(
        self,
        location_id: int,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
        segment: str | None = None  # "active", "inactive", "prospect", or None=all
    ) -> dict:
        """
        Returns a paginated, de-duplicated user list for `location_id`, plus a `location`
        object containing four segment counts:
          - active_users_count
          - inactive_users_count
          - prospects_count
          - past_due_count

        Deduplication and segmentation rules:
          1) Active: member=True AND expires_date > now AND ended_date IS NULL
          2) Inactive: member=True AND expires_date < now AND ended_date < now
          3) Prospect: member=False AND prospect=True
          4) Past due: expires_date < now AND ended_date IS NULL
        """
        now = datetime.utcnow()

        # 1) segmentation expression
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
            # 2) CTE: compute seg_rank + row_number per user
            user_rows = (
                select(
                    ClubReadyUser.store_id,
                    ClubReadyUser.user_id,
                    ClubReadyUser.username,
                    ClubReadyUser.email,
                    ClubReadyUser.first_name,
                    ClubReadyUser.last_name,
                    ClubReadyUser.member,
                    ClubReadyUser.prospect,
                    ClubReadyUser.membership_expires_date,
                    ClubReadyUser.membership_ended_date,
                    ClubReadyUser.cell_phone,
                    seg_rank,
                    over(
                        func.row_number(),
                        partition_by=(ClubReadyUser.store_id, ClubReadyUser.user_id),
                        order_by=seg_rank
                    ).label("rn")
                )
                .where(ClubReadyUser.store_id == location_id)
            ).subquery()

            # 3) first_seg: pick only the top‐ranked row per user
            first_seg = (
                select(
                    user_rows.c.store_id,
                    user_rows.c.user_id,
                    user_rows.c.username,
                    user_rows.c.email,
                    user_rows.c.first_name,
                    user_rows.c.last_name,
                    user_rows.c.member,
                    user_rows.c.prospect,
                    user_rows.c.membership_expires_date,
                    user_rows.c.membership_ended_date,
                    user_rows.c.cell_phone,
                    user_rows.c.seg_rank
                )
                .where(user_rows.c.rn == 1)
            ).subquery()

            # 4) Summary counts for each segment
            summary = session.query(
                func.count(case((first_seg.c.seg_rank == 1, 1)))
                    .label("active_users_count"),
                func.count(case((first_seg.c.seg_rank == 2, 1)))
                    .label("inactive_users_count"),
                func.count(case((first_seg.c.seg_rank == 3, 1)))
                    .label("prospects_count"),
                # Past due = expired but not ended
                func.count(case((
                    and_(
                        first_seg.c.membership_expires_date < now,
                        first_seg.c.membership_ended_date.is_(None)
                    ), 1
                ))).label("past_due_count")
            ).filter(first_seg.c.store_id == location_id).one()

            # 5) Build the user query, mapping seg_rank to segment string
            qry = session.query(
                first_seg.c.user_id,
                first_seg.c.username,
                first_seg.c.first_name,
                first_seg.c.last_name,
                first_seg.c.email,
                first_seg.c.member,
                first_seg.c.membership_expires_date,
                case(
                    (first_seg.c.seg_rank == 1, "active"),
                    (first_seg.c.seg_rank == 2, "inactive"),
                    (first_seg.c.seg_rank == 3, "prospect"),
                    else_="unknown"
                ).label("segment"),
                first_seg.c.cell_phone
            )

            # 6) Filter by requested segment
            if segment in ("active", "inactive", "prospect"):
                rank_map = {"active": 1, "inactive": 2, "prospect": 3}
                qry = qry.filter(first_seg.c.seg_rank == rank_map[segment])

            # 7) Exclude any rows not in one of the three segments
            qry = qry.filter(first_seg.c.seg_rank.in_([1, 2, 3]))

            # 8) Optional search
            if search:
                term = f"%{search.lower()}%"
                qry = qry.filter(
                    func.lower(first_seg.c.username).like(term) |
                    func.lower(first_seg.c.email).like(term)    |
                    func.lower(first_seg.c.first_name).like(term) |
                    func.lower(first_seg.c.last_name).like(term)
                )

            # 9) Pagination & execute
            total = qry.count()
            users = (
                qry
                .order_by(first_seg.c.last_name.asc())
                .limit(limit)
                .offset((page - 1) * limit)
                .all()
            )

            # 10) Fetch location name
            loc_name = (
                session.query(ClubLocation.name)
                .filter(ClubLocation.club_id == location_id)
                .scalar()
            )

            # 11) Assemble response
            return {
                "location": {
                    "id": location_id,
                    "name": loc_name,
                    "active_users_count": summary.active_users_count,
                    "inactive_users_count": summary.inactive_users_count,
                    "prospects_count": summary.prospects_count,
                    
                },
                "results": [
                    {
                        "user_id": user.user_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "member": user.member,
                        "membership_expires_date": 
                            user.membership_expires_date.isoformat() 
                            if user.membership_expires_date else None,
                        "segment": user.segment,
                        "cell_phone": user.cell_phone
                    }
                    for user in users
                ],
                "total_count": total,
                "page": page,
                "limit": limit
            }
