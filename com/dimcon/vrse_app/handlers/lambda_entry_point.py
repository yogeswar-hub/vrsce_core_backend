import logging
import json
from com.dimcon.vrse_app.services.platform_config_service_post import PlatformConfigService
from com.dimcon.vrse_app.services.club_location_service import ClubLocationService
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
from com.dimcon.vrse_app.services.audit_log_service import AuditLogService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder
from com.dimcon.vrse_app.resources.connect_aurora import get_engine

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
    
    # Extract path and query parameters (if any)
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    
    # Extract Cognito claims from the event context; these become our audit details.
    cognito_claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_info = {
        "user_id":   cognito_claims.get("sub", "unknown"),
        "email":     cognito_claims.get("email", ""),
        "iss":       cognito_claims.get("iss", ""),
        "auth_time": cognito_claims.get("auth_time", ""),
        "aud":       cognito_claims.get("aud", ""),
        "username":  cognito_claims.get("username", "")
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
            # Use query string parameters for pagination.
            svc    = ClubLocationService()
            page   = int(query_params.get("page", 1))
            limit  = int(query_params.get("limit", 100))
            data   = svc.fetch_location_overview(page, limit)
            return ResponseBuilder.build_response(200, data)
      
        elif resource == "club_users":
            # e.g. GET /users?locationId=123&page=1&limit=20&search=foo
            params      = query_params
            loc_id      = int(params.get("locationId", 0))
            page        = int(params.get("page", 1))
            limit       = int(params.get("limit", 20))
            search_term = params.get("search")
            
            svc = ClubUsersService(get_engine())
            payload = svc.fetch_users_by_location(loc_id, search_term, page, limit)
            return ResponseBuilder.build_response(200, payload)
        else:
            return ResponseBuilder.build_response(400, {"error": "Invalid resource for GET method."})
    
    else:
        return ResponseBuilder.build_response(400, {"error": "Unsupported httpMethod or resource combination."})
