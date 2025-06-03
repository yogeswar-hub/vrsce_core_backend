import logging
import json

from com.dimcon.vrse_app.services.platform_config_service_post import PlatformConfigService
from com.dimcon.vrse_app.services.club_location_service import ClubLocationService
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
from com.dimcon.vrse_app.services.audit_log_service import AuditLogService
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Received event with keys: %s", list(event.keys()))
    
    # Check if this is an EventBridge scheduled event.
    # Scheduled events typically include a "source" field with value "aws.events"
    if event.get("source") == "aws.events":
        logger.info("EventBridge scheduled event detected. Triggering Club Ready sync job.")
        from com.dimcon.vrse_app.services.club_ready_sync_service import ClubReadySyncService
        ClubReadySyncService().run_sync(audit={"created_by": "eventbridge", "updated_by": "eventbridge"})
        return ResponseBuilder.build_response(200, {"message": "ClubReady sync triggered via EventBridge."})
    
    # Otherwise, assume API Gateway event and process normally.
    # Determine HTTP method
    http_method = (
        event.get("requestContext", {}).get("http", {}).get("method", "")
        if event.get("version", "").startswith("2.0")
        else event.get("httpMethod", "")
    ).upper()
    logger.info("HTTP method determined: %s", http_method)
    
    # Determine raw path
    if event.get("version", "").startswith("2.0"):
        raw_path = event.get("rawPath", "")
    else:
        raw_path = event.get("resource") or event.get("path", "")
    raw_path = raw_path.lower()
    logger.info("Normalized raw path: %s", raw_path)
    
    # Fail fast if crucial data is missing
    if not http_method:
        logger.error("Missing HTTP method in event")
        return ResponseBuilder.build_response(400, {"error": "Missing 'httpMethod' in event."})
    if not raw_path:
        logger.error("Missing raw path in event")
        return ResponseBuilder.build_response(400, {"error": "Missing request path."})
    
    # Strip off stage name if present (e.g. '/dev/...')
    parts = raw_path.lstrip("/").split("/")
    logger.info("Path parts after splitting: %s", parts)
    if parts and parts[0] == "dev":
        parts.pop(0)
        logger.info("Removed stage name 'dev', remaining parts: %s", parts)
    resource = parts[0] if parts else ""
    logger.info("Resource determined: %s", resource)
    
    # Grab path & query parameters
    path_params  = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    logger.info("Path parameters: %s", list(path_params.keys()))
    logger.info("Query parameters: %s", list(query_params.keys()))
    
    # Extract Cognito claims for auditing
    claims = (event.get("requestContext", {})
                  .get("authorizer", {})
                  .get("claims", {})) or {}
    logger.info("Cognito claims received with keys: %s", list(claims.keys()))
    if claims:
        logger.info("Cognito claims contain %s keys. Minimal details: sub=%s, username=%s, email=%s",
                    len(claims),
                    claims.get("sub", "unknown"),
                    claims.get("cognito:username", claims.get("username", "")),
                    claims.get("email", ""))
    user_info = {
        "user_id":   claims.get("sub", "unknown"),
        "email":     claims.get("email", ""),
        "iss":       claims.get("iss", ""),
        "auth_time": claims.get("auth_time", ""),
        "aud":       claims.get("aud", ""),
        "username":  claims.get("cognito:username", claims.get("username", ""))
    }
    logger.info("User info prepared for auditing (sensitive values are masked)")
    
    # Determine additional logging info (e.g. location_ID for club_users)
    location_id_for_log = None
    if resource == "club_users":
        loc_id_str = query_params.get("locationId") or query_params.get("locationid")
        if loc_id_str:
            location_id_for_log = loc_id_str

    # Log the access event (for all requests except audit_log retrieval)
    if resource != "audit_log":
        try:
            AuditLogService.log_access(user_info, resource, http_method, location_id=location_id_for_log)
            logger.info("Audit log recorded for user %s accessing resource %s", user_info.get("user_id"), resource)
        except Exception as err:
            logger.error("Error logging audit record: %s", err)
    
    # Route the request based on resource and method
    if http_method == "POST" and resource == "platform_config":
        logger.info("Routing to PlatformConfigService.handle_post")
        result = PlatformConfigService.handle_post(event, user_info, path_params)
        return ResponseBuilder.build_response(200, result)
    
    # New Route for club_ready_active_members
    if resource == "club_ready_active_members":
        if http_method == "POST":
            logger.info("Routing POST to ClubReadyActiveUsersService.sync_active_users")
            query_params = event.get("queryStringParameters") or {}
            # Use default values or override with query parameters
            activity_date = query_params.get("Date", "01-01-2023")
            activity_operator = query_params.get("ActivityOperator", "GT")
            try:
                from com.dimcon.vrse_app.services.club_ready_active_mem_service import ClubReadyActiveUsersService
                ClubReadyActiveUsersService.sync_active_users(activity_date, activity_operator, user_info)
                return ResponseBuilder.build_response(200, {"message": "Active members synced successfully."})
            except Exception as e:
                logger.error("Error syncing active members: %s", e)
                return ResponseBuilder.build_response(500, {"error": "Active members sync failed.", "details": str(e)})
        elif http_method == "GET":
            logger.info("Routing GET to fetch stored club_ready active members with pagination and filtration")
            try:
                from com.dimcon.vrse_app.resources.vrse.vrse_club_active_members import ClubActiveMember
                engine = get_engine()
                db_util = DBSessionUtil(engine)
                with db_util.session_scope() as session:
                    page = int(query_params.get("page", 1))
                    limit = int(query_params.get("limit", 100))
                    search_term = query_params.get("search", "")
                    
                    query = session.query(ClubActiveMember)
                    if search_term:
                        # For example, filter by email (adjust or add more fields as needed)
                        query = query.filter(ClubActiveMember.email.ilike(f"%{search_term}%"))
                    
                    total_count = query.count()
                    members = query.order_by(ClubActiveMember.id)\
                                   .offset((page - 1) * limit)\
                                   .limit(limit)\
                                   .all()
                    members_data = [member.to_dict() for member in members]
                return ResponseBuilder.build_response(200, {
                    "total_active_members": total_count,
                    "page": page,
                    "limit": limit,
                    "active_members": members_data
                })
            except Exception as e:
                logger.error("Error retrieving active members: %s", e)
                return ResponseBuilder.build_response(500, {
                    "error": "Failed to retrieve active members", "details": str(e)
                })
    
    # Route GET for club_locations, club_users, and audit_log
    if http_method == "GET":
        if resource == "club_locations":
            logger.info("Routing to ClubLocationService.fetch_location_overview")
            svc = ClubLocationService()
            page = int(query_params.get("page", 1))
            limit = int(query_params.get("limit", 100))
            data = svc.fetch_location_overview(page, limit)
            return ResponseBuilder.build_response(200, data)
        if resource == "club_users":
            logger.info("Routing to ClubUsersService.fetch_users_by_location")
            if not location_id_for_log:
                logger.error("Missing 'locationId' query parameter in club_users/club_ready_members request")
                return ResponseBuilder.build_response(400, {"error": "Missing 'locationId' query parameter."})
            loc_id = int(location_id_for_log)
            page = int(query_params.get("page", 1))
            limit = int(query_params.get("limit", 20))
            search_term = query_params.get("search")
            from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
            svc = ClubUsersService(get_engine())
            payload = svc.fetch_users_by_location(loc_id, search_term, page, limit)
            return ResponseBuilder.build_response(200, payload)
        if resource == "audit_log":
            logger.info("Routing to AuditLogService.get_audit_logs")
            page = int(query_params.get("page", 1))
            limit = int(query_params.get("limit", 20))
            payload = AuditLogService.get_audit_logs(page, limit)
            return ResponseBuilder.build_response(200, payload)
        logger.error("Invalid resource for GET method: %s", resource)
        return ResponseBuilder.build_response(400, {"error": "Invalid resource for GET method."})
    
    logger.error("Unsupported httpMethod or resource combination. Method: %s, Resource: %s", http_method, resource)
    return ResponseBuilder.build_response(400, {"error": "Unsupported httpMethod or resource combination."})
