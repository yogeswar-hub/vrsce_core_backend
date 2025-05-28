import logging
import json
from com.dimcon.vrse_app.services.platform_config_service_post import PlatformConfigService
from com.dimcon.vrse_app.services.club_location_service import ClubLocationService
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
from com.dimcon.vrse_app.services.audit_log_service import AuditLogService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Lambda event: {json.dumps(event)}")
    
    # Extract and normalize HTTP method and resource path.
    http_method = event.get("httpMethod", "").upper()
    resource_path = event.get("resource", "").lower()
    if not resource_path:
        return ResponseBuilder.build_response(400, {"error": "Missing 'resource' in event."})
    if not http_method:
        return ResponseBuilder.build_response(400, {"error": "Missing 'httpMethod' in event."})
    
    # Extract path parameters (if any)
    path_params = event.get("pathParameters") or {}
    
    # Extract Cognito claims from the event context; these become our audit details.
    cognito_claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_info = {
        "user_id": cognito_claims.get("sub", "unknown"),
        "email": cognito_claims.get("email", ""),
        "iss": cognito_claims.get("iss", ""),
        "auth_time": cognito_claims.get("auth_time", ""),
        "aud": cognito_claims.get("aud", ""),
        "username": cognito_claims.get("username", "")
    }
    
    # Determine the primary resource (e.g., platform_config, club_locations, club_users)
    resource = resource_path.strip("/").split("/")[0].lower()
    
    # Log every access to the AuditLog table.
    try:
        AuditLogService.log_access(user_info, resource, http_method)
    except Exception as err:
        logger.error(f"Error logging audit record: {err}")
    
    # Routing based on HTTP method and resource.
    if http_method == "POST" and resource == "platform_config":
        # This call stores a new PlatformConfig record and triggers the sync via an SQLAlchemy event listener.
        result = PlatformConfigService.handle_post(event, user_info, path_params)
        return ResponseBuilder.build_response(200, result)
    
    elif http_method == "GET":
        if resource == "club_locations":
            result = ClubLocationService.handle_get(event, user_info, path_params)
            return ResponseBuilder.build_response(200, result)
        elif resource == "club_users":
            result = ClubUsersService.handle_get(event, user_info, path_params)
            return ResponseBuilder.build_response(200, result)
        else:
            return ResponseBuilder.build_response(400, {"error": "Invalid resource for GET method."})
    
    else:
        return ResponseBuilder.build_response(400, {"error": "Unsupported httpMethod or resource combination."})
