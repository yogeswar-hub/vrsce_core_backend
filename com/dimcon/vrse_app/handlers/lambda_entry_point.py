import json
import logging
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder

# Import the service handlers (adjust the import paths as needed)
from com.dimcon.vrse_app.services.platform_config_service import PlatformConfigService
from com.dimcon.vrse_app.services.club_location_service import ClubLocationService
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Lambda event: {json.dumps(event)}")
    
    # Extract HTTP method
    http_method = event.get("httpMethod")
    if not http_method:
        return ResponseBuilder.build_response(400, {"error": "Missing httpMethod in event"})
    
    # Extract Cognito claims from the event context
    cognito_claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_info = {
        "user_id": cognito_claims.get("sub", "unknown"),
        "email": cognito_claims.get("email", "")
    }
    
    # Determine the 'source' parameter. Assume for GET the source is in queryStringParameters
    # and for POST the source is included in the JSON body.
    source = None
    if http_method.upper() == "GET":
        source = (event.get("queryStringParameters") or {}).get("source")
    elif http_method.upper() == "POST":
        body = event.get("body")
        if body:
            try:
                parsed_body = json.loads(body)
                source = parsed_body.get("source")
            except Exception as e:
                logger.error(f"Failed to parse POST body: {e}")
                return ResponseBuilder.build_response(400, {"error": "Invalid JSON in body"})
    
    if not source:
        return ResponseBuilder.build_response(400, {"error": "Missing source in event"})
    
    # Routing logic based on httpMethod and source
    if http_method.upper() == "POST" and source.lower() == "platform_config":
        result = PlatformConfigService.handle_post(event, user_info)
        return ResponseBuilder.build_response(200, result)
    
    elif http_method.upper() == "GET":
        if source.lower() == "club_locations":
            result = ClubLocationService.handle_get(event, user_info)
            return ResponseBuilder.build_response(200, result)
        elif source.lower() == "club_users":
            result = ClubUsersService.handle_get(event, user_info)
            return ResponseBuilder.build_response(200, result)
        else:
            return ResponseBuilder.build_response(400, {"error": "Invalid source for GET method."})
    
    else:
        return ResponseBuilder.build_response(400, {"error": "Unsupported httpMethod or source combination."})
