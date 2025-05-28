import json
from com.dimcon.vrse_app.handlers.lambda_entry_point import lambda_handler

def test_post_platform_config():
    # Define the config data to be inserted.
    config_data = {
        "platform_name": "club_ready",
        "auth_key": "85b59f92-615a-4f89-8dbf-39bd62f5344c",
        "chain_id": 658,
        "enable_member_sync": True,
        "sync_interval_minutes": 60,
        "auto_distribute_passes": True,
        "created_by": "admin",
        "updated_by": "admin",
        "auth_time": "1624388245",  # Unix timestamp as string
        "sub": "cognito-user-sub",
        "username": "cognito_username",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXX",
        "aud": "client_id_here"
    }

    # Build a simulated API Gateway event for a POST to /platform_config
    event = {
        "httpMethod": "POST",
        "resource": "/platform_config",
        "body": json.dumps(config_data),
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
    context = None  # For testing, context can be None.
    
    # Invoke the lambda handler
    response = lambda_handler(event, context)
    print("Response:", json.dumps(response, indent=2))

if __name__ == "__main__":
    test_post_platform_config()