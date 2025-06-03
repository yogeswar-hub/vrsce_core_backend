import json
from com.dimcon.vrse_app.handlers.lambda_entry_point import lambda_handler

def test_post_club_active_members():
    # Build a simulated API Gateway event for POST to /club_ready_active_members
    event = {
        "httpMethod": "POST",
        "resource": "/club_ready_active_members",
        "body": None,
        "pathParameters": {},
        "queryStringParameters": {
            "Date": "01-01-2023",
            "ActivityOperator": "GT"
        },
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "user-123",
                    "email": "user@example.com",
                    "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXX",
                    "auth_time": "1680000000",
                    "aud": "client_id_here",
                    "username": "johndoe"
                }
            }
        }
    }
    # Ensure audit info contains non-null values.
    # For example, if your sync service uses these values for audit in the active members table,
    # they must not be None.
    context = None  # For testing, context can be None.
    response = lambda_handler(event, context)
    print("POST /club_ready_active_members Response:")
    print(json.dumps(response, indent=2))


def test_get_club_active_members():
    # Build a simulated API Gateway event for GET to /club_ready_active_members
    event = {
        "httpMethod": "GET",
        "resource": "/club_ready_active_members",
        "body": None,
        "pathParameters": {},
        "queryStringParameters": {},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "user-123",
                    "email": "user@example.com",
                    "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXX",
                    "auth_time": "1680000000",
                    "aud": "client_id_here",
                    "username": "johndoe"
                }
            }
        }
    }
    context = None
    response = lambda_handler(event, context)
    print("GET /club_ready_active_members Response:")
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    print("Testing POST to sync club ready active members...")
    test_post_club_active_members()
    print("\nTesting GET to retrieve club ready active members...")
    test_get_club_active_members()