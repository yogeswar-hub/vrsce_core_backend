import json
from com.dimcon.vrse_app.services.passkit_services.create_graph_snapshot_to_table import CreateGraphSnapshotToTable
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.utilities.responses import ResponseBuilder  # import shared builder

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class CreateGraphSnapshot:
    """
    Lambda route handler for creating and storing a graph snapshot.

    Expects 'program_id' in event["program_id"] or inside JSON body.
    Calls the CreateGraphSnapshotToTable service to fetch data,
    analyze, and save snapshot to DB.
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
            logger.info(f"Creating graph snapshot for program_id: {program_id}")
            snapshot_creator = CreateGraphSnapshotToTable(program_id)
            result = snapshot_creator.run_and_store_snapshot()
            logger.info("Graph snapshot created and stored successfully")
            return ResponseBuilder.build_response(200, result)
        except Exception as e:
            logger.error("Error in CreateGraphSnapshot handler", exc_info=True)
            return ResponseBuilder.build_response(500, {"error": str(e)})
