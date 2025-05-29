import logging
import json

from com.dimcon.vrse_app.services.platform_config_service_post import PlatformConfigService
from com.dimcon.vrse_app.services.club_location_service     import ClubLocationService
from com.dimcon.vrse_app.services.club_users_service        import ClubUsersService
from com.dimcon.vrse_app.services.audit_log_service         import AuditLogService
from com.dimcon.vrse_app.utilities.responses                import ResponseBuilder
from com.dimcon.vrse_app.resources.connect_aurora           import get_engine

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # 1) Quick debug: log what keys we actually got
    logger.info("RAW EVENT KEYS: %s", list(event.keys()))
    
    # 2) Determine HTTP method
    http_method = (
        event.get("requestContext", {})
             .get("http", {})
             .get("method", "")
        if event.get("version", "").startswith("2.0")
        else event.get("httpMethod", "")
    ).upper()
    
    # 3) Determine raw path, preferring the REST proxy resource
    if event.get("version", "").startswith("2.0"):
        raw_path = event.get("rawPath", "")
    else:
        raw_path = event.get("resource") or event.get("path", "")
    
    raw_path = raw_path.lower()
    logger.info("Normalized incoming: %s %s", http_method, raw_path)
    
    # 4) Fail fast if missing
    if not http_method:
        return ResponseBuilder.build_response(400, {"error": "Missing 'httpMethod' in event."})
    if not raw_path:
        return ResponseBuilder.build_response(400, {"error": "Missing request path."})
    
    # 5) Strip off stage name if present (e.g. '/dev/club_locations')
    parts = raw_path.lstrip("/").split("/")
    if parts and parts[0] == "dev":   # change "dev" to match your stage if different
        parts.pop(0)
    resource = parts[0] if parts else ""
    
    # 6) Grab path & query params
    path_params  = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    
    # 7) Extract Cognito claims for auditing
    claims = event.get("requestContext", {}) \
                  .get("authorizer", {})   \
                  .get("claims", {})        or {}
    user_info = {
        "user_id":   claims.get("sub", "unknown"),
        "email":     claims.get("email", ""),
        "iss":       claims.get("iss", ""),
        "auth_time": claims.get("auth_time", ""),
        "aud":       claims.get("aud", ""),
        "username":  claims.get("username", "")
    }
    
    # 8) Log access
    try:
        AuditLogService.log_access(user_info, resource, http_method)
    except Exception as err:
        logger.error("Error logging audit record: %s", err)
    
    # 9) Route!
    # POST /platform_config
    if http_method == "POST" and resource == "platform_config":
        result = PlatformConfigService.handle_post(event, user_info, path_params)
        return ResponseBuilder.build_response(200, result)
    
    # GET routes
    if http_method == "GET":
        if resource == "club_locations":
            svc   = ClubLocationService()
            page  = int(query_params.get("page",  1))
            limit = int(query_params.get("limit", 100))
            data  = svc.fetch_location_overview(page, limit)
            return ResponseBuilder.build_response(200, data)
        
        if resource == "club_users":
            # require a locationId query parameter
            loc_id_str = query_params.get("locationId") or query_params.get("locationid")
            if not loc_id_str:
                return ResponseBuilder.build_response(400, {
                    "error": "Missing 'locationId' query parameter."
                })
            loc_id      = int(loc_id_str)
            page        = int(query_params.get("page",  1))
            limit       = int(query_params.get("limit", 20))
            search_term = query_params.get("search")
            
            svc     = ClubUsersService(get_engine())
            payload = svc.fetch_users_by_location(loc_id, search_term, page, limit)
            return ResponseBuilder.build_response(200, payload)
        
        # unknown GET resource
        return ResponseBuilder.build_response(400, {
            "error": "Invalid resource for GET method."
        })
    
    # fallback for anything else
    return ResponseBuilder.build_response(400, {
        "error": "Unsupported httpMethod or resource combination."
    })
