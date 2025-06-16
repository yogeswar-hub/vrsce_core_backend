"""
ClubLocationsRoute
Handles GET /club_locations
"""
import logging
from sqlalchemy import func
from com.dimcon.vrse_app.services.club_location_service import ClubLocationService
from com.dimcon.vrse_app.services.audit_log_service import AuditLogService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder

class ClubLocationsRoute:
    """
    Handles GET /club_locations and OPTIONS preflight.
    """
    logger = logging.getLogger(__name__)

    @classmethod
    def handle_request(cls, method, event, context, user_info, path_params, query_params):
        if method == "OPTIONS":
            cls.logger.debug("OPTIONS /club_locations")
            return ResponseBuilder.build_response(200, {})

        if method == "GET":
            cls.logger.info("GET /club_locations by %s", user_info["user_id"])
            svc = ClubLocationService()
            page  = int(query_params.get("page", 1))
            limit = int(query_params.get("limit", 10))
            search = query_params.get("search")
            try:
                data = svc.fetch_all_locations_with_active_and_inactive_counts(
                    page=page, limit=limit, search=search
                )
                cls.logger.info("Fetched %d locations", len(data.get("locations", [])))
                # audit success
                AuditLogService.log_access(
                    user_info,
                    resource="club_locations",
                    http_method=method
                )
                return ResponseBuilder.build_response(200, data)
            except Exception:
                cls.logger.exception("Error fetching club_locations")
                # audit failure
                AuditLogService.log_access(
                    user_info,
                    resource="club_locations",
                    http_method=method,
                    error_message="Failed to fetch locations"
                )
                return ResponseBuilder.build_response(500, {"error": "Failed to fetch locations"})

        cls.logger.error("Method %s not allowed on /club_locations", method)
        return ResponseBuilder.build_response(405, {"error": "Method Not Allowed"})