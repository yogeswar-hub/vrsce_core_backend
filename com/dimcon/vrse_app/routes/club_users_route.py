"""
ClubUsersRoute
Handles GET /club_users
"""
import logging
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder
from com.dimcon.vrse_app.resources.connect_aurora import get_engine

class ClubUsersRoute:
    """
    Handles GET /club_users and OPTIONS preflight.
    """
    logger = logging.getLogger(__name__)

    @classmethod
    def handle_request(cls, method, event, context, user_info, path_params, query_params):
        if method == "OPTIONS":
            cls.logger.debug("OPTIONS /club_users")
            return ResponseBuilder.build_response(200, {})

        if method == "GET":
            cls.logger.info("GET /club_users by %s", user_info["user_id"])
            loc = query_params.get("locationId") or query_params.get("locationid")
            if not loc:
                cls.logger.warning("Missing locationId for /club_users")
                return ResponseBuilder.build_response(400, {"error": "Missing 'locationId'"})
            page  = int(query_params.get("page", 1))
            limit = int(query_params.get("limit", 20))
            search = query_params.get("search")
            svc = ClubUsersService(get_engine())
            try:
                payload = svc.fetch_users_by_location(int(loc), search, page, limit)
                return ResponseBuilder.build_response(200, payload)
            except Exception:
                cls.logger.exception("Error fetching club_users")
                return ResponseBuilder.build_response(500, {"error": "Failed to fetch users"})

        cls.logger.error("Method %s not allowed on /club_users", method)
        return ResponseBuilder.build_response(405, {"error": "Method Not Allowed"})