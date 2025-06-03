from sqlalchemy import or_, func
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.resources.base_dao import BaseDAO
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubUsersService(BaseDAO):
    """
    Data Access Object (DAO) for ClubUser records.
    Provides standard CRUD operations using BaseDAO methods.
    """
    def __init__(self, engine):
        super().__init__(engine)
        self.db_util = DBSessionUtil(engine)

    def fetch_users(self, session, page=1, limit=10, sort_by="id", sort_order="asc", filters=None):
        try:
            # Uses BaseDAO.fetch_all to return paginated records.
            data = self.fetch_all(session, ClubUser, page, limit, sort_by, sort_order, filters)
            return data
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
        """
        Returns:
        {
          "location": {
            "id": <location_id>,
            "name": <location.name>,
            "users_count": <total matching users>
          },
          "results": [
            { "id": <user.id>,
              "first_name": "...",
              "last_name":  "...",
              "email":      "..."
            },
            … 
          ]
        }
        """
        try:
            logger.info("Starting fetch_users_by_location for location_id: %s", location_id)
            with self.db_util.session_scope() as session:
                logger.debug("Looking up location with club_id: %s", location_id)
                # 1) Lookup by the club_id column instead of the surrogate PK.
                loc = (
                    session.query(ClubLocation)
                    .filter(ClubLocation.club_id == location_id)
                    .one_or_none()
                )
                if not loc:
                    logger.error("Location %s not found", location_id)
                    raise ValueError(f"Location {location_id} not found")
                logger.info("Location found: %s", loc.name)
                
                logger.debug("Building base query for ClubUser records at location %s", location_id)
                # 2) Build base query.
                qry = session.query(ClubUser).filter(
                    ClubUser.primary_store_id == location_id
                )
                
                # 3) Optional search (by first, last, or email).
                if search:
                    term = f"%{search}%"
                    logger.debug("Applying optional search filter with term: %s", search)
                    qry = qry.filter(
                        or_(
                            ClubUser.first_name.ilike(term),
                            ClubUser.last_name.ilike(term),
                            ClubUser.email.ilike(term)
                        )
                    )
                
                logger.debug("Counting total matching user records for location %s", location_id)
                # 4) Total count before pagination.
                total_users = qry.with_entities(func.count()).scalar()
                logger.info("Total matching users for location %s: %s", location_id, total_users)
                
                logger.debug("Applying sorting and pagination: page %s, limit %s", page, limit)
                # 5) Apply sorting & pagination.
                users = (
                    qry
                    .order_by(ClubUser.last_name.asc(), ClubUser.first_name.asc())
                    .limit(limit)
                    .offset((page - 1) * limit)
                    .all()
                )
                logger.info("Fetched %s user records for the current page", len(users))
                
                logger.debug("Shaping output for response")
                # 6) Shape output.
                results = [
                    {
                        "id":         u.id,
                        "first_name": u.first_name,
                        "last_name":  u.last_name,
                        "email":      u.email,
                    }
                    for u in users
                ]
                
                response = {
                    "location": {
                        "id":          loc.club_id,
                        "name":        loc.name,
                        "users_count": total_users
                    },
                    "results": results
                }
                logger.info("fetch_users_by_location completed successfully for location %s", location_id)
                return response
        except Exception as e:
            logger.error("Error in fetch_users_by_location for location %s: %s", location_id, e, exc_info=True)
            raise