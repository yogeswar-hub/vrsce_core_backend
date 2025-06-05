from com.dimcon.vrse_app.handlers.lambda_entry_point import lambda_handler
from datetime import datetime, timezone

# Simulate the AWS EventBridge event
event = {
    "source": "aws.events",
    "detail-type": "Scheduled Event",
    "time": datetime.now(timezone.utc).isoformat(),
    "region": "us-east-1",
    "resources": [],
    "detail": {}
}

# Dummy context object
context = {}

if __name__ == "__main__":
    response = lambda_handler(event, context)
    print("✅ Lambda handler executed successfully!")
    print("Response:", response)
