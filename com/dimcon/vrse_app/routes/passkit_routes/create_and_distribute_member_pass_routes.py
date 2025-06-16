import json
from com.dimcon.vrse_app.services.passkit_services.create_and_distribute_member_pass import CreateandDistributeMemberPass
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class CreateMemberPassDistribution:
    """
    Lambda route handler for creating or updating a member in PassKit
    and sending a welcome email.

    Expects JSON body with fields:
    - user_id
    - first_name
    - last_name
    - email
    - mobile_phone

    Returns raw dict with operation result or error info.
    """

    def __init__(self):
        self.processor = CreateandDistributeMemberPass()

    def handle_event(self, event):
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except Exception as e:
                logger.error(f"Failed to parse JSON body: {e}", exc_info=True)
                return {"error": "Invalid JSON body"}

        required_fields = ["user_id", "first_name", "last_name", "email", "mobile_phone"]
        missing = [field for field in required_fields if not body.get(field)]
        if missing:
            return {"error": f"Missing required fields: {', '.join(missing)}"}

        try:
            result = self.processor.process_user(body)
            return result
        except Exception as e:
            logger.error("Error processing member", exc_info=True)
            return {"error": str(e)}
