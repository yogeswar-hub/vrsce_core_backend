"""
AuditLogRoute
Handles GET /audit_log
"""
import logging
from com.dimcon.vrse_app.services.audit_log_service import AuditLogService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder

class AuditLogRoute:
    """
    Handles GET /audit_log and OPTIONS preflight.
    """
    logger = logging.getLogger(__name__)

    @classmethod
    def handle_request(cls, method, event, context, user_info, path_params, query_params):
        if method == "OPTIONS":
            cls.logger.debug("OPTIONS /audit_log")
            return ResponseBuilder.build_response(200, {})

        if method == "GET":
            cls.logger.info("GET /audit_log by %s", user_info["user_id"])
            try:
                page       = int(query_params.get("page", 1))
                limit      = int(query_params.get("limit", 20))
                search     = query_params.get("search")
                start_date = query_params.get("start_date")
                end_date   = query_params.get("end_date")
                payload = AuditLogService.get_audit_logs(
                    page=page, limit=limit,
                    search=search,
                    start_date=start_date,
                    end_date=end_date
                )
                cls.logger.info("Retrieved %d audit log entries", len(payload.get("items", [])))
                return ResponseBuilder.build_response(200, payload)
            except ValueError as ve:
                cls.logger.warning("Bad parameters: %s", ve)
                return ResponseBuilder.build_response(400, {"error": str(ve)})
            except Exception:
                cls.logger.exception("Error in get_audit_logs")
                return ResponseBuilder.build_response(500, {"error": "Failed to retrieve audit logs"})

        cls.logger.error("Method %s not allowed on /audit_log", method)
        return ResponseBuilder.build_response(405, {"error": "Method Not Allowed"})