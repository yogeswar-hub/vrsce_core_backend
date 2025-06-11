"""
Lambda entrypoint: only does auth, routing and audit logging
"""
import logging, json
from com.dimcon.vrse_app.routes.platform_config_route     import PlatformConfigRoute
from com.dimcon.vrse_app.routes.club_locations_route      import ClubLocationsRoute
from com.dimcon.vrse_app.routes.club_users_route          import ClubUsersRoute
from com.dimcon.vrse_app.routes.audit_log_route           import AuditLogRoute
from com.dimcon.vrse_app.routes.club_active_members_route import ClubActiveMembersRoute
from com.dimcon.vrse_app.utilities.responses              import ResponseBuilder
from com.dimcon.vrse_app.services.audit_log_service       import AuditLogService
from com.dimcon.vrse_app.services.club_ready_sync_service import ClubReadySyncService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Map normalized resource → its Route class
ROUTES = {
    "platform_config":           PlatformConfigRoute,
    "club_locations":            ClubLocationsRoute,
    "club_users":                ClubUsersRoute,
    "audit_log":                 AuditLogRoute,
    "club_ready_active_members": ClubActiveMembersRoute,
}

def lambda_handler(event, context):
    logger.info("Received event with keys: %s", list(event.keys()))

    # 1) Is this an EventBridge‐scheduled invocation?
    if event.get("source") == "aws.events":
        logger.info("EventBridge scheduled event detected. Triggering ClubReady sync.")
        # prepare audit payload
        audit = event.get("detail", {})
        audit.setdefault("created_by", "eventbridge")
        audit.setdefault("updated_by", "eventbridge")
        # log the schedule
        system_user = {"user_id":"system","username":"eventbridge","email":""}
        AuditLogService.log_access(system_user, "club_ready_sync", "SCHEDULE")
        # now run the sync
        ClubReadySyncService().run_sync(audit=audit)
        return ResponseBuilder.build_response(
            200,
            {"message": "ClubReady sync triggered via EventBridge."}
        )

    # 2) Otherwise it’s an API‐Gateway invocation—continue with HTTP logic…
    #    (determine http_method, raw_path, resource, claims, audit‐log, routing, etc.)
    # 1) Extract Cognito claims for auditing
    claims = (
        event.get("requestContext", {})
             .get("authorizer", {})
             .get("claims", {})
    ) or {}
    logger.info(
        "Cognito claims: sub=%s, username=%s, email=%s",
        claims.get("sub",    "unknown"),
        claims.get("cognito:username", claims.get("username","")),
        claims.get("email","")
    )
    user_info = {
        "user_id":   claims.get("sub",    "unknown"),
        "username":  claims.get("cognito:username", claims.get("username","")),
        "email":     claims.get("email",    ""),
        "iss":       claims.get("iss",      ""),
        "aud":       claims.get("aud",      ""),
        "auth_time": claims.get("auth_time","")
    }

    # 2) Determine HTTP method (v1 vs v2 payload)
    http_method = (
        event.get("requestContext", {}).get("http", {}).get("method", "")
        if event.get("version","").startswith("2.0")
        else event.get("httpMethod","")
    ).upper()
    logger.info("HTTP Method: %s", http_method)

    # 3) Normalize raw path and pick resource
    if event.get("version","").startswith("2.0"):
        raw_path = event.get("rawPath","")
    else:
        raw_path = event.get("path","")
    raw_path = raw_path.lower()
    parts = raw_path.lstrip("/").split("/")
    # strip off the stage (e.g. 'dev')
    if parts and parts[0] == "dev":
        parts.pop(0)
    resource = parts[0].replace("-", "_") if parts else ""
    logger.info("Resource: %s", resource)

    # 4) Grab path & query params
    path_params  = event.get("pathParameters")        or {}
    query_params = event.get("queryStringParameters") or {}
    logger.info("Path params: %s, Query params: %s",
                path_params, query_params)

    # 5) Audit‐log (skip the audit‐log endpoint itself)
    if resource != "audit_log":
        try:
            AuditLogService.log_access(user_info, resource, http_method)
            logger.info("Audit logged for %s %s", http_method, resource)
        except Exception as err:
            logger.error("Audit log failed: %s", err)

    # 6) Dispatch to the correct Route class
    route_cls = ROUTES.get(resource)
    if route_cls:
        return route_cls.handle_request(
            http_method, event, context,
            user_info, path_params, query_params
        )

    # 7) Fallback for unknown resource
    logger.error("Unknown resource: %s", resource)
    return ResponseBuilder.build_response(404, {"error": "Not Found"})
