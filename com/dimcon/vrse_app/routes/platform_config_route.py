"""
PlatformConfigRoute
Handles POST /platform_config
"""
import logging
from com.dimcon.vrse_app.services.platform_config_service_post import PlatformConfigService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder

class PlatformConfigRoute:
    """
    Handles POST /platform_config and OPTIONS preflight.
    """
    logger = logging.getLogger(__name__)

    @classmethod
    def handle_request(cls, method, event, context, user_info, path_params, query_params):
        # OPTIONS preflight
        if method == "OPTIONS":
            cls.logger.debug("OPTIONS /platform_config")
            return ResponseBuilder.build_response(200, {})

        # Create or update platform_config
        if method == "POST":
            cls.logger.info("POST /platform_config by %s", user_info["user_id"])
            try:
                result = PlatformConfigService.handle_post(event, user_info, path_params)
                cls.logger.info("Platform config saved successfully")
                return ResponseBuilder.build_response(200, result)
            except ValueError as ve:
                cls.logger.warning("Validation error: %s", ve)
                return ResponseBuilder.build_response(400, {"error": str(ve)})
            except Exception:
                cls.logger.exception("Unexpected error saving platform config")
                return ResponseBuilder.build_response(500, {"error": "Internal Server Error"})

        # Method not allowed
        cls.logger.error("Method %s not allowed on /platform_config", method)
        return ResponseBuilder.build_response(405, {"error": "Method Not Allowed"})