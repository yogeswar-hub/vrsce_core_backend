#!/usr/bin/env python3
import os
import json

# 1) Inject the required env var before importing your handler
os.environ["CLUBREADY_BASE_URL"] = "https://clubready.example.com/api/current"

# 2) Now import your lambda handler
from com.dimcon.vrse_app.handlers.lambda_entry_point import lambda_handler

class LambdaEntryPointTester:
    def __init__(self):
        # If your handler expects anything on context, set it here
        self.context = {}

    def run_test(self, name, event):
        resp = lambda_handler(event, self.context)
        print(f"\n--- {name} ---")
        print("StatusCode:", resp.get("statusCode"))
        body = resp.get("body", "")
        try:
            parsed = json.loads(body)
            print("Response Body:", json.dumps(parsed, indent=2))
        except Exception:
            print("Response Body:", body)

    def make_api_gateway_event(self, path, method="GET", body=None, qs=None, claims=None):
        return {
            "httpMethod": method,
            "path": path,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body) if body is not None else None,
            "queryStringParameters": qs or {},
            "pathParameters": {},
            "requestContext": {
                "authorizer": {
                    "claims": claims or {
                        "sub": "system",
                        "username": "tester",
                        "email": "tester@example.com"
                    }
                }
            }
        }

    def test_cors_preflight(self):
        evt = {"httpMethod": "OPTIONS"}
        self.run_test("CORS Preflight", evt)

    def test_eventbridge_sync(self):
        evt = {"source": "aws.events", "detail": {}}
        self.run_test("EventBridge Sync", evt)

    def test_platform_config_route(self):
        evt = self.make_api_gateway_event(path="/platform_config", method="GET")
        self.run_test("VRSE: platform_config", evt)

    def test_club_users_route(self):
        evt = self.make_api_gateway_event(path="/club_users", method="GET")
        self.run_test("VRSE: club_users", evt)

    def test_member_create_and_distribute(self):
        evt = self.make_api_gateway_event(
            path="/member-create-and-distribute",
            method="POST",
            body={
                "user_id": "12345",
                "first_name": "John",
                "last_name": "Doe",
                "email": "t@gmail.com",
                "mobile_phone": "+1234567890"
            }
        )
        self.run_test("Passkit: member-create-and-distribute", evt)


    # def test_member_create_and_distribute(self):
    #     event = {
    #         "httpMethod": "POST",
    #         "path": "/member-create-and-distribute",
    #         "headers": {"Content-Type": "application/json"},
    #         "body": json.dumps({
    #             "user_id": "12345",
    #             "first_name": "Jhn",
    #             "last_name": "Doe",
    #             "email": "avirneninikethsai1144@gmail.com",
    #             "mobile_phone": "+1234567890"
    #         }),
    #         "queryStringParameters": None
    #     }
    #     self.run_test(event)

    def test_status_snapshot(self):
        evt = self.make_api_gateway_event(path="/status-snapshot", method="GET")
        self.run_test("Passkit: status-snapshot", evt)

    def test_create_status_snapshot(self):
        evt = self.make_api_gateway_event(
            path="/create-status-snapshot",
            method="POST",
            body={"program_id": "6vdFJZFxQN6jpEMULbbWvs"}
        )
        self.run_test("Passkit: create-status-snapshot", evt)

    def test_create_graph_snapshot(self):
        evt = self.make_api_gateway_event(
            path="/create-graph-snapshot",
            method="POST",
            body={"program_id": "6vdFJZFxQN6jpEMULbbWvs"}
        )
        self.run_test("Passkit: create-graph-snapshot", evt)

    def test_graph_snapshot(self):
        evt = self.make_api_gateway_event(path="/graph-snapshot", method="GET")
        self.run_test("Passkit: graph-snapshot", evt)

    def test_member_counts_by_homeclub(self):
        evt = self.make_api_gateway_event(path="/member-counts-by-homeclub", method="GET")
        self.run_test("Passkit: member-counts-by-homeclub", evt)

    def test_create_member_counts_by_homeclub(self):
        evt = self.make_api_gateway_event(
            path="/create-member-counts-by-homeclub",
            method="POST",
            body={"program_id": "6vdFJZFxQN6jpEMULbbWvs"}
        )
        self.run_test("Passkit: create-member-counts-by-homeclub", evt)


if __name__ == "__main__":
    tester = LambdaEntryPointTester()

    # Uncomment the tests you want to run:
    # tester.test_cors_preflight()
    # tester.test_eventbridge_sync()
    # tester.test_platform_config_route()
    tester.test_club_users_route()
    
    
    
    
    
    # tester.test_member_create_and_distribute()
    # tester.test_status_snapshot()
    # tester.test_create_status_snapshot()
    # tester.test_create_graph_snapshot()
    # tester.test_graph_snapshot()
    # tester.test_member_counts_by_homeclub()
    # tester.test_create_member_counts_by_homeclub()
