from datetime import datetime
from sqlalchemy import select, case, and_, func, literal_column, or_, literal, desc
from sqlalchemy.sql import over
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

        # 1) Define segment ranking expression
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
            # 2) Subquery: rank rows per user to pick the highest-priority segment
            user_rows = (
                select(
                    ClubReadyUser.store_id,
                    ClubReadyUser.user_id,
                    ClubReadyUser.username,
                    ClubReadyUser.email,
                    ClubReadyUser.first_name,
                    ClubReadyUser.last_name,
                    ClubReadyUser.member,
                    ClubReadyUser.membership_expires_date,
                    ClubReadyUser.membership_ended_date,
                    seg_rank,
                    over(
                        func.row_number(),
                        partition_by=(ClubReadyUser.store_id, ClubReadyUser.user_id),
                        order_by=seg_rank
                    ).label("rn")
                )
                .where(ClubReadyUser.store_id == location_id)
            ).subquery()

            # 3) CTE: keep only the row with rn == 1 for each user
            first_seg = (
                session.query(
                    ClubReadyUser.user_id,
                    ClubReadyUser.username,
                    ClubReadyUser.first_name,
                    ClubReadyUser.last_name,
                    ClubReadyUser.email,
                    ClubReadyUser.member,
                    ClubReadyUser.membership_expires_date,
                    ClubReadyUser.membership_ended_date,
                    ClubReadyUser.cell_phone,
                    func.row_number().over(
                        partition_by=ClubReadyUser.user_id,
                        order_by=desc(ClubReadyUser.membership_expires_date)
                    ).label("seg_rank")
                )
                .filter(ClubReadyUser.store_id == location_id)
                .subquery()
            )

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
                first_seg.c.cell_phone,
                case(
                    (first_seg.c.seg_rank == 1, "Silver"),
                    (first_seg.c.seg_rank == 2, "Gold"),
                    (first_seg.c.seg_rank == 3, "Platinum"),
                    else_="Unknown"
                ).label("segment")
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
