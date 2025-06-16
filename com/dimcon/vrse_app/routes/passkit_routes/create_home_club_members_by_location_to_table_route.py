import json
from com.dimcon.vrse_app.services.passkit_services.create_home_club_members_by_location_to_table import CreateActiveMembersByLocationToTable
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder  # shared response builder

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class CreateHomeClubMembersByLocation:
    """
    Lambda route handler for creating and storing Homeclub members by location snapshot.

    Expects 'program_id' in event["program_id"] or in JSON body.
    Calls CreateActiveMembersByLocationToTable service to fetch and store snapshot.
    """

    def __init__(self):
        pass  # program_id comes from event

    def handle_event(self, event):
        program_id = event.get("program_id")

        if not program_id:
            body = {}
            if event.get("body"):
                try:
                    body = json.loads(event["body"])
                except Exception:
                    pass
            program_id = body.get("program_id")

        if not program_id:
            logger.warning("Missing required parameter: program_id")
            return ResponseBuilder.build_response(400, {"error": "Missing required parameter: program_id"})

        try:
            logger.info(f"Running Homeclub members snapshot for program_id: {program_id}")
            runner = CreateActiveMembersByLocationToTable(program_id)
            result = runner.run_and_store_snapshot()
            logger.info("Homeclub members snapshot stored successfully")
            return result  # Return raw data instead of a wrapped response
        except Exception as e:
            logger.error("Error in CreateHomeClubMembersByLocation handler", exc_info=True)
            return {"error": str(e)}
