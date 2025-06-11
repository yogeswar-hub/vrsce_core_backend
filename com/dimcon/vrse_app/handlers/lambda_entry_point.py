"""
Lambda entrypoint: only does auth, routing and audit logging
"""
import logging, json
from com.dimcon.vrse_app.routes.platform_config_route     import PlatformConfigRoute
from com.dimcon.vrse_app.routes.club_locations_route      import ClubLocationsRoute
from com.dimcon.vrse_app.routes.club_users_route          import ClubUsersRoute
from com.dimcon.vrse_app.routes.audit_log_route           import AuditLogRoute
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
    "audit_log":                 AuditLogRoute
}

def lambda_handler(event, context):
    logger.info("Received event keys: %s", list(event.keys()))

    # 1) HTTP (API-Gateway) calls always include httpMethod
    if "httpMethod" in event:
        http_method = event["httpMethod"]
        raw_path    = event.get("path", "")
        resource    = raw_path.lstrip("/").split("/")[0].lower()
        RouteClass  = ROUTES.get(resource)

        # extract auth claims into a simple user_info dict
        claims     = event["requestContext"]["authorizer"]["claims"]
        user_info  = {
            "user_id":  claims.get("sub"),
            "username": claims.get("username"),
            "email":    claims.get("email")
        }
        path_params  = event.get("pathParameters") or {}
        query_params = event.get("queryStringParameters") or {}
        # invoke the route’s handler
        return RouteClass.handle_request(
            http_method,
            event,
            context,
            user_info,
            path_params,
            query_params
        )

    # 2) EventBridge schedules have source=="aws.events"
    elif event.get("source") == "aws.events":
        logger.info("EventBridge scheduled event detected. Triggering ClubReady sync.")
        audit = event.get("detail", {}) or {}
        audit.setdefault("created_by", "eventbridge")
        audit.setdefault("updated_by", "eventbridge")

        system_user = {"user_id": "system", "username": "eventbridge", "email": ""}
        AuditLogService.log_access(system_user, "club_ready_sync", "SCHEDULE")

        ClubReadySyncService().run_sync(audit=audit)
        return ResponseBuilder.build_response(
            200,
            {"message": "ClubReady sync triggered via EventBridge."}
        )

    # 3) Anything else…
    else:
        return ResponseBuilder.build_response(
            400,
            {"message": "Unknown event type"}
        )
