import json
from com.dimcon.vrse_app.services.passkit_services.create_count_status_snapshot_to_table import CountStatusHandler
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class CreateCountStatusSnapshot:
    """
    Lambda route handler for counting member statuses and saving a snapshot.

    Expects 'program_id' in the event dictionary or JSON body.
    Calls the CountStatusHandler service to perform counting and saving.
    Returns a response with message, program_id, and the count summary.
    """

    def __init__(self):
        self.handler = CountStatusHandler()

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
            logger.info(f"Counting status snapshot for program_id: {program_id}")
            summary = self.handler.count_by_status(program_id)
            self.handler.save_snapshot(program_id, summary)
            logger.info("Snapshot saved successfully")

            response_payload = {
                "message": "Snapshot successfully created",
                "program_id": program_id,
                "summary": summary
            }
            return ResponseBuilder.build_response(200, response_payload)

        except Exception as e:
            logger.error("Error in CreateCountStatusSnapshot", exc_info=True)
            return ResponseBuilder.build_response(500, {"error": str(e)})
