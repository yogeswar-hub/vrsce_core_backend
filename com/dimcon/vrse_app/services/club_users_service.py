from sqlalchemy import or_, func, case, update
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.resources.vrse.vrse_club_members_activity import ClubMemberActivity
from com.dimcon.vrse_app.resources.base_dao import BaseDAO
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubUsersService(BaseDAO):
    def __init__(self, engine):
        super().__init__(engine)
        self.db_util = DBSessionUtil(engine)

    def fetch_users(self, session, page=1, limit=10, sort_by="id", sort_order="asc", filters=None):
        try:
            return self.fetch_all(session, ClubUser, page, limit, sort_by, sort_order, filters)
        except Exception as e:
            logger.error("Error fetching club users", exc_info=True)
            raise

    def fetch_by_id(self, session, user_id):
        return super().fetch_by_id(session, ClubUser, user_id)

    def insert_user(self, session, user_instance):
        return super().insert(session, user_instance)

    def update_user(self, session, user_id, data):
        return super().update(session, ClubUser, user_id, data)

    def delete_user(self, session, user_id):
        return super().delete(session, ClubUser, user_id)

    def fetch_users_by_location(self, location_id, search=None, page=1, limit=20):
        try:
            logger.info("Starting fetch_users_by_location for location_id: %s", location_id)
            with self.db_util.session_scope() as session:
                # Look up the location first.
                loc = session.query(ClubLocation).filter(ClubLocation.club_id == location_id).one_or_none()
                if not loc:
                    logger.error("Location %s not found", location_id)
                    raise ValueError(f"Location {location_id} not found")
                
                # Query for user details directly from ClubUser table.
                # Replace null latest_segment with "no status assigned".
                qry = session.query(
                    ClubUser.user_id,
                    ClubUser.username,
                    ClubUser.first_name,
                    ClubUser.last_name,
                    ClubUser.email,
                    func.coalesce(ClubUser.latest_segment, 'no status assigned').label("latest_segment")
                ).filter(
                    ClubUser.primary_store_id == location_id
                )
                
                if search:
                    term = f"%{search.lower()}%"

                    # support “First Last” and “Last First” searches:
                    full_fl = func.lower(func.concat(ClubUser.first_name, ' ', ClubUser.last_name))
                    full_lf = func.lower(func.concat(ClubUser.last_name,  ' ', ClubUser.first_name))

                    qry = qry.filter(
                        or_(
                            # full‐name matches in either order
                            full_fl.like(term),
                            full_lf.like(term),
                            # individual fields as before
                            func.lower(ClubUser.first_name).like(term),
                            func.lower(ClubUser.last_name).like(term),
                            func.lower(ClubUser.username).like(term),
                            func.lower(ClubUser.email).like(term),
                        )
                    )
                
                total_users = qry.count()
                users = qry.order_by(ClubUser.last_name.asc())\
                            .limit(limit)\
                            .offset((page - 1) * limit)\
                            .all()

                # Get counts by segment from ClubUser. Here we count Active, Inactive,
                # and for records with a null latest_segment, we count them as "no status assigned".
                counts = session.query(
                    func.count(case((func.lower(ClubUser.latest_segment) == 'active',    1))).label("active_users_count"),
                    func.count(case((func.lower(ClubUser.latest_segment) == 'inactive',  1))).label("inactive_users_count"),
                    func.count(case((ClubUser.latest_segment == None,                   1))).label("no_status_assigned_count"),
                    func.count(case((func.lower(ClubUser.latest_segment) == 'prospects', 1))).label("prospects_count"),
                    func.count(case((func.lower(ClubUser.latest_segment) == 'pastdue',   1))).label("past_due_count")
                ).filter(
                     ClubUser.primary_store_id == location_id
                 ).one()
                
                logger.info("fetch_users_by_location completed successfully for location_id: %s", location_id)
                
                return {
                    "location": {
                        "id": loc.club_id,
                        "name": loc.name,
                        "active_users_count":          counts.active_users_count,
                        "inactive_users_count":        counts.inactive_users_count,
                        "no_status_assigned_count":    counts.no_status_assigned_count,
                        "prospects_count":             counts.prospects_count,
                        "past_due_count":              counts.past_due_count
                    },
                    "results": [
                        {
                            "user_id": u.user_id,
                            "username": u.username,
                            "first_name": u.first_name,
                            "last_name": u.last_name,
                            "email": u.email,
                            "latest_segment": u.latest_segment
                        } for u in users
                    ],
                    "total_count": total_users,
                    "page": page,
                    "limit": limit
                }
        except Exception as e:
            logger.error("Error in fetch_users_by_location for location_id: %s", location_id, exc_info=True)
            raise
        @staticmethod
        def get_all_user_ids(session):
            return set(str(uid) for (uid,) in session.query(ClubUser.user_id).all())

    def update_latest_activity_info(self, session):
        """
        Update club_users with the latest activity info (latest segment and activity_date)
        from club_members_activity using a SQLAlchemy update that joins via a subquery with a window function.
        
        For each user in club_members_activity, we compute a row_number (ordered by activity_date DESC)
        partitioned by user_id. This subquery then returns the latest activity (where row number is 1).
        The update then uses this subquery to update club_users.latest_segment and 
        club_users.latest_activity_date.
        """
        # Build a subquery that returns one row per user (the latest activity).
        subq = (
            session.query(
                ClubMemberActivity.user_id,
                ClubMemberActivity.segment,
                ClubMemberActivity.activity_date,
                func.row_number().over(
                    partition_by=ClubMemberActivity.user_id,
                    order_by=ClubMemberActivity.activity_date.desc()
                ).label("rn")
            )
            .subquery()
        )

        # Create an update statement: for each ClubUser whose user_id matches and subq.rn == 1,
        # update latest_segment and latest_activity_date.
        stmt = (
            update(ClubUser)
            .values(
                latest_segment=subq.c.segment,
                latest_activity_date=subq.c.activity_date
            )
            .where(ClubUser.user_id == subq.c.user_id)
            .where(subq.c.rn == 1)
        )
        session.execute(stmt)
        session.commit()
        logger.info("Updated ClubUser.latest_segment and latest_activity_date using latest activity info.")
