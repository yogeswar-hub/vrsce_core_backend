from sqlalchemy import or_, func, case
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.resources.vrse.vrse_club_members_activity import ClubActiveMember
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
            logger.info("Starting fetch_users_by_location_with_segments for location_id: %s", location_id)
            with self.db_util.session_scope() as session:
                loc = session.query(ClubLocation).filter(ClubLocation.club_id == location_id).one_or_none()
                if not loc:
                    logger.error("Location %s not found", location_id)
                    raise ValueError(f"Location {location_id} not found")

                qry = session.query(
                    ClubActiveMember.user_id,
                    ClubActiveMember.username,
                    ClubActiveMember.first_name,
                    ClubActiveMember.last_name,
                    ClubActiveMember.email,
                    ClubActiveMember.mobile_phone,
                    ClubActiveMember.segment
                ).join(
                    ClubUser, ClubActiveMember.user_id == ClubUser.user_id
                ).filter(
                    ClubUser.primary_store_id == location_id
                )

                if search:
                    term = f"%{search.lower()}%"
                    qry = qry.filter(
                        or_(
                            func.lower(ClubActiveMember.first_name).like(term),
                            func.lower(ClubActiveMember.last_name).like(term),
                            func.lower(ClubActiveMember.username).like(term),
                            func.lower(ClubActiveMember.email).like(term)
                        )
                    )

                total_users = qry.count()

                users = qry.order_by(ClubActiveMember.last_name.asc()).limit(limit).offset((page - 1) * limit).all()

                counts = session.query(
                    func.count(case((ClubActiveMember.segment == 'Active', 1))).label("active_users_count"),
                    func.count(case((ClubActiveMember.segment == 'Inactive', 1))).label("inactive_users_count")
                ).join(
                    ClubUser, ClubActiveMember.user_id == ClubUser.user_id
                ).filter(
                    ClubUser.primary_store_id == location_id
                ).one()

                logger.info("fetch_users_by_location_with_segments completed successfully for location_id: %s", location_id)

                return {
                    "location": {
                        "id": loc.club_id,
                        "name": loc.name,
                        "active_users_count": counts.active_users_count,
                        "inactive_users_count": counts.inactive_users_count
                    },
                    "results": [
                        {
                            "user_id": u.user_id,
                            "username": u.username,
                            "first_name": u.first_name,
                            "last_name": u.last_name,
                            "email": u.email,
                            "phone_number": u.mobile_phone,
                            "segment": u.segment
                        } for u in users
                    ],
                    "total_count": total_users,
                    "page": page,
                    "limit": limit
                }
        except Exception as e:
            logger.error("Error in fetch_users_by_location_with_segments for location_id %s", location_id, exc_info=True)
            raise

    @staticmethod
    def get_all_user_ids(session):
        return set(str(uid) for (uid,) in session.query(ClubUser.user_id).all())
