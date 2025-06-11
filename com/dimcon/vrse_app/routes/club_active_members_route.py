"""
ActiveMembersRoute
Handles POST & GET /club_ready_active_members
"""
import logging
from com.dimcon.vrse_app.services.club_ready_members_activity import ClubReadyActiveUsersService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder

class ClubActiveMembersRoute:
    """
    Handles POST & GET /club_ready_active_members and OPTIONS preflight.
    """
    logger = logging.getLogger(__name__)

    @classmethod
    def handle_request(cls, method, event, context, user_info, path_params, query_params):
        if method == "OPTIONS":
            cls.logger.debug("OPTIONS /club_ready_active_members")
            return ResponseBuilder.build_response(200, {})

        if method == "POST":
            cls.logger.info("POST /club_ready_active_members by %s", user_info["user_id"])
            date = query_params.get("Date")
            op   = query_params.get("ActivityOperator")
            try:
                ClubReadyActiveUsersService.sync_active_users(date, op, user_info)
                cls.logger.info("Active members sync succeeded")
                return ResponseBuilder.build_response(200, {"message": "Synced successfully"})
            except Exception:
                cls.logger.exception("Error syncing active members")
                return ResponseBuilder.build_response(500, {"error": "Sync failed"})

        if method == "GET":
            cls.logger.info("GET /club_ready_active_members by %s", user_info["user_id"])
            try:
                result = ClubReadyActiveUsersService.fetch_active_members(query_params)
                cls.logger.info("Fetched %d active members", result.get("total_active_members",0))
                return ResponseBuilder.build_response(200, result)
            except Exception:
                cls.logger.exception("Error fetching active members")
                return ResponseBuilder.build_response(500, {"error": "Fetch failed"})

        cls.logger.error("Method %s not allowed on /club_ready_active_members", method)
        return ResponseBuilder.build_response(405, {"error": "Method Not Allowed"})