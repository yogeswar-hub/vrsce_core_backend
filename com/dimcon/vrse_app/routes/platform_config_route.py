"""
PlatformConfigRoute
Handles POST /platform_config
"""
import logging
from com.dimcon.vrse_app.services.platform_config_service_post import PlatformConfigService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder
from com.dimcon.vrse_app.services.audit_log_service import AuditLogService

class PlatformConfigRoute:
    """
    Handles POST /platform_config and OPTIONS preflight.
    """
    logger = logging.getLogger(__name__)

    @classmethod
    def handle_request(cls, method, event, context, user_info, path_params, query_params):
        # OPTIONS preflight
        if method == "OPTIONS":
            # audit OPTIONS call
            AuditLogService.log_access(
                user_info,
                resource="platform_config",
                http_method="OPTIONS"
            )
            cls.logger.debug("OPTIONS /platform_config")
            return ResponseBuilder.build_response(200, {})

        # Create or update platform_config
        if method == "POST":
            cls.logger.info("POST /platform_config by %s", user_info["user_id"])
            try:
                result = PlatformConfigService.handle_post(event, user_info, path_params)
                # audit success
                AuditLogService.log_access(
                    user_info,
                    resource="platform_config",
                    http_method=method
                )
                cls.logger.info("Platform config saved successfully")
                return ResponseBuilder.build_response(200, result)
            except ValueError as ve:
                # audit validation error
                AuditLogService.log_access(
                    user_info,
                    resource="platform_config",
                    http_method=method,
                    error_message=str(ve)
                )
                cls.logger.warning("Validation error: %s", ve)
                return ResponseBuilder.build_response(400, {"error": str(ve)})
            except Exception:
                # audit unexpected error
                AuditLogService.log_access(
                    user_info,
                    resource="platform_config",
                    http_method=method,
                    error_message="Internal Server Error"
                )
                cls.logger.exception("Unexpected error saving platform config")
                return ResponseBuilder.build_response(500, {"error": "Internal Server Error"})

        # Method not allowed
        # audit unsupported HTTP method
        AuditLogService.log_access(
            user_info,
            resource="platform_config",
            http_method=method,
            error_message="Method Not Allowed"
        )
        cls.logger.error("Method %s not allowed on /platform_config", method)
        return ResponseBuilder.build_response(405, {"error": "Method Not Allowed"})