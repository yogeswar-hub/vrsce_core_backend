import logging
import json
from datetime import datetime

#clubready imports
from com.dimcon.vrse_app.routes.platform_config_route import PlatformConfigRoute
from com.dimcon.vrse_app.routes.club_locations_route import ClubLocationsRoute
from com.dimcon.vrse_app.routes.club_users_route import ClubUsersRoute
from com.dimcon.vrse_app.routes.audit_log_route import AuditLogRoute

# Passkit imports
from com.dimcon.vrse_app.routes.passkit_routes.count_status_snapshot_routes import CountStatusSnapshotRoute
from com.dimcon.vrse_app.routes.passkit_routes.create_and_distribute_member_pass_routes import CreateMemberPassDistribution
from com.dimcon.vrse_app.routes.passkit_routes.create_count_status_snapshot_to_table_routes import CreateCountStatusSnapshot
from com.dimcon.vrse_app.routes.passkit_routes.create_graph_snapshot_to_table_route import CreateGraphSnapshot
from com.dimcon.vrse_app.routes.passkit_routes.create_home_club_members_by_location_to_table_route import CreateHomeClubMembersByLocation
from com.dimcon.vrse_app.routes.passkit_routes.graph_snapshot_route import GraphSnapshotRoute
from com.dimcon.vrse_app.routes.passkit_routes.home_club_members_by_location_route import HomeClubMembersByLocation

# Utility imports
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder
from com.dimcon.vrse_app.services.audit_log_service import AuditLogService
from com.dimcon.vrse_app.services.club_ready_sync_service import ClubReadySyncService

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# VRSE resource mapping
ROUTES = {
    "platform_config": PlatformConfigRoute,
    "club_locations": ClubLocationsRoute,
    "club_users": ClubUsersRoute,
    "audit_log": AuditLogRoute
}


def lambda_handler(event, context):
    """
    Unified Lambda entrypoint:
      - OPTIONS → CORS preflight
      - API-GW HTTP → VRSE or Passkit routing
      - EventBridge scheduled → ClubReady sync
    """
    logger.info("Received event keys: %s", list(event.keys()))

    # CORS preflight
    method = event.get("httpMethod")
    if method == "OPTIONS":
        return ResponseBuilder.build_response(200, "OK")

    # EventBridge scheduled trigger
    if event.get("source") == "aws.events":
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

    # HTTP/API Gateway invocation
    if method:
        raw_path = event.get("path", "")
        resource = raw_path.lstrip("/").split("/")[0].lower()

        auth = event.get("requestContext", {}).get("authorizer", {}) or {}

        # HTTP API v2
        if "jwt" in auth:
            claims = auth["jwt"].get("claims", {}) or {}
        # REST API / custom authorizer
        else:
            claims = auth.get("claims", {}) or {}

        # DEBUG: log the entire authorizer so you can see exactly where your data lives
        logger.debug("Full authorizer object: %s", auth)

        logger.info("Cognito claims received with keys: %s", list(claims.keys()))
        if claims:
            logger.info(
                "Cognito minimal: sub=%s, username=%s, email=%s",
                claims.get("sub"), claims.get("cognito:username"), claims.get("email")
            )

        user_info = {
            "user_id":   claims.get("sub",    "unknown"),
            "username":  claims.get("cognito:username", ""),
            "email":     claims.get("email",  ""),
            "iss":       claims.get("iss",    ""),
            "aud":       claims.get("aud",    ""),
            "auth_time": claims.get("auth_time", "")
        }

        # VRSE-style routes (authenticated)
        RouteClass = ROUTES.get(resource)
        if RouteClass:
            path_params = event.get("pathParameters") or {}
            query_params = event.get("queryStringParameters") or {}
            return RouteClass.handle_request(
                method,
                event,
                context,
                user_info,
                path_params,
                query_params
            )

        # Passkit-style routes
        query_params = event.get("queryStringParameters") or {}
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except Exception:
                body = {}

        # use the authenticated Cognito user_info you already extracted:
        # event["requestContext"]["authorizer"]["jwt"]["claims"]
        

        # Validate program_id for certain endpoints
        if raw_path.endswith((
            "/count-status", "/create-graph-snapshot",
            "/create-status-snapshot", "/active-members",
            "/dynamic-graph", "/list-member-tiers",
            "/chart/signup-weekday"
        )):
            program_id = body.get("program_id") or query_params.get("program_id")
            if not program_id:
                return ResponseBuilder.build_response(
                    400,
                    {"error": "Missing program_id in body or query parameters."}
                )
            event["program_id"] = program_id

        # Validate template_id for get_by_id
        if raw_path.endswith("/template/get_by_id"):
            template_id = body.get("template_id") or query_params.get("template_id")
            if not template_id:
                return ResponseBuilder.build_response(
                    400,
                    {"error": "Missing template_id in body or query parameters."}
                )
            event["template_id"] = template_id

        # Dispatch Passkit routes
        if raw_path.endswith("/member-create-and-distribute"):
            data = CreateMemberPassDistribution().handle_event(event)
            # audit it
            AuditLogService.log_access(
                user_info,
                "member-create-and-distribute",
                method,
                error_message=data.get("error")
            )
            status = 400 if data.get("error") and "Missing" in data["error"] else 500
            if data.get("error"): 
                return ResponseBuilder.build_response(status, data)
            return ResponseBuilder.build_response(200, data)

        if raw_path.endswith("/status-snapshot"):
            data = CountStatusSnapshotRoute().handle_event_raw(event)
            AuditLogService.log_access(
                user_info,
                "status-snapshot",
                method,
                error_message=None
            )
            return ResponseBuilder.build_response(200, data)

        if raw_path.endswith("/create-status-snapshot"):
            result = CreateCountStatusSnapshot().handle_event(event)
            AuditLogService.log_access(
                user_info,
                "create-status-snapshot",
                method,
                error_message=result.get("error")
            )
            return result

        if raw_path.endswith("/create-graph-snapshot"):
            result = CreateGraphSnapshot().handle_event(event)
            AuditLogService.log_access(
                user_info,
                "create-graph-snapshot",
                method,
                error_message=result.get("error")
            )
            return result

        if raw_path.endswith("/graph-snapshot"):
            data = GraphSnapshotRoute().handle_event(event)
            AuditLogService.log_access(
                user_info,
                "graph-snapshot",
                method
            )
            return ResponseBuilder.build_response(200, data)

        if raw_path.endswith("/member-counts-by-homeclub"):
            data = HomeClubMembersByLocation().handle_event(event)
            AuditLogService.log_access(
                user_info,
                "member-counts-by-homeclub",
                method
            )
            return ResponseBuilder.build_response(200, data)

        if raw_path.endswith("/create-member-counts-by-homeclub"):
            data = CreateHomeClubMembersByLocation().handle_event(event)
            AuditLogService.log_access(
                user_info,
                "create-member-counts-by-homeclub",
                method
            )
            return ResponseBuilder.build_response(200, data)

        # No matching route
        return ResponseBuilder.build_response(404, {"error": "Not found"})

    # Unknown event type
    return ResponseBuilder.build_response(
        400,
        {"message": "Unknown event type"}
    )
