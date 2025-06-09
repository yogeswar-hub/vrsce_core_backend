import sys
from pathlib import Path
# ensure the project root (vrsce_core_backend) is on sys.path so “import com…” works
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from com.dimcon.vrse_app.handlers.lambda_entry_point import lambda_handler
from datetime import datetime, timezone


# Example event for processing the first half (pages 1 to 50)
event_first = {
    "source": "aws.events",
    "detail-type": "Scheduled Event",
    "time": datetime.now(timezone.utc).isoformat(),
    "region": "us-east-1",
    "resources": [],
    "detail": {
        "sync_half": "first",   # Indicates processing the first half.
        "start_page": "1161",
        "end_page": "1166"
    }
}

#Example event for processing the second half (pages 51 to 100)
#     event_second = {
#         "source": "aws.events",
#         "detail-type": "Scheduled Event",
#         "time": datetime.now(timezone.utc).isoformat(),
#         "region": "us-east-1",
#         "resources": [],
#         "detail": {
#             "sync_half": "second",  # Indicates processing the second half.
#             "start_page": "51",
#             "end_page": "100"
#         }
#     }

# Dummy context object
context = {}

if __name__ == "__main__":
    # Choose which event to test
    response = lambda_handler(event_first, context)
    # To test the second half, replace event_first with event_second
    print("✅ Lambda handler executed successfully!")
    print("Response:", response)
