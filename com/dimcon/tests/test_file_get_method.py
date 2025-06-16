# filepath: com/dimcon/tests/test_file_get_method.py
import os
#  ← must set the real ENV, not just a Python variable
os.environ["CLUBREADY_BASE_URL"] = "https://clubready.com/api/current"

import json
from com.dimcon.vrse_app.handlers.lambda_entry_point import lambda_handler

def test_get_club_locations():
    # Build an event for GET club_locations
    event = {
        "httpMethod": "GET",
        "path": "/club_locations",
        "queryStringParameters": {
            "page": "1",
            "limit": "100"
        },
        "pathParameters": {},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "sai",
                    "email": "user@example.com",
                    "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_fake",
                    "auth_time": "1680000000",
                    "aud": "client_id_here",
                    "username": "sai"
                }
            }
        }
    }
    context = None  # For testing, context is not used.
    response = lambda_handler(event, context)
    print("GET Club Locations Response:")
    print(json.dumps(response, indent=2))

def test_get_club_users():
    # Build an event for GET club_users with query parameters.
    event = {
        "httpMethod": "GET",
        "path": "/club_users",
        "queryStringParameters": {
            "locationid": 2345,
            "page": "1",
            "limit": "20",
            "search": ""
        },
        "pathParameters": {},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "sai",
                    "email": "user@example.com",
                    "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_fake",
                    "auth_time": "1680000000",
                    "aud": "client_id_here",
                    "username": "sai"
                }
            }
        }
    }
    context = None
    response = lambda_handler(event, context)
    print("GET Club Users Response:")
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    test_get_club_locations()
    test_get_club_users()