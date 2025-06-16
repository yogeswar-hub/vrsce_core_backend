import grpc
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from passkit_io.member import a_rpc_pb2_grpc, member_pb2
from passkit_io.common import filter_pb2
from com.dimcon.vrse_app.utilities.grpc_client import GrpcClient
from com.dimcon.vrse_app.resources.vrse_passkit.database_scripts.status_snapshot_json import StatusSnapshotJson
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")


class CountStatusHandler:
    """Counts members by pass status via gRPC and saves snapshot to DB."""

    def __init__(self):
        """Initialize gRPC client and Members service stub."""
        self.grpc_client = GrpcClient()
        self.stub = self.grpc_client.get_members_stub()

    def count_by_status(self, program_id, statuses=None):
        """
        Concurrently count members for given statuses.

        Args:
            program_id (str): PassKit program ID.
            statuses (list[str], optional): Statuses to count.

        Returns:
            dict: Counts per status and total count.
        """
        logger.info(f"Starting count_by_status for program_id={program_id}")
        if statuses is None:
            statuses = [
                "PASS_INSTALLED",
                "PASS_ISSUED",
                "PASS_UNINSTALLED",
                "PASS_INVALIDATED"
            ]

        def fetch_count(status):
            """Count members for a single status with pagination."""
            try:
                offset, count, page_size = 0, 0, 100
                start_time = time.time()

                while True:
                    field_filter = filter_pb2.FieldFilter(
                        filterField="passStatus",
                        filterValue=status,
                        filterOperator="eq"
                    )
                    filter_group = filter_pb2.FilterGroup(condition="AND", fieldFilters=[field_filter])
                    filters = filter_pb2.Filters(
                        limit=page_size,
                        offset=offset,
                        orderBy="created",
                        orderAsc=True,
                        filterGroups=[filter_group]
                    )
                    request = member_pb2.ListRequest(programId=program_id, filters=filters)

                    page_count = sum(1 for _ in self.stub.listMembers(request))
                    count += page_count

                    if page_count < page_size:
                        break
                    offset += page_size

                elapsed = time.time() - start_time
                logger.info(f"Counted {count} members for '{status}' in {elapsed:.2f}s")
                return status, count

            except Exception as e:
                logger.error(f"Error counting members for '{status}': {e}", exc_info=True)
                return status, 0

        results = {}
        with ThreadPoolExecutor(max_workers=len(statuses)) as executor:
            futures = {executor.submit(fetch_count, s): s for s in statuses}
            for future in as_completed(futures):
                status, count = future.result()
                results[status] = count

        logger.info(f"Completed count_by_status for program_id={program_id}")
        return {"status_summary": results, "total": sum(results.values())}

    def save_snapshot(self, program_id, payload):
        """
        Save count summary JSON to database.

        Args:
            program_id (str): PassKit program ID.
            payload (dict): Snapshot data.
        """
        logger.info(f"Saving snapshot for program_id={program_id}")
        try:
            engine = get_engine()
            db_util = DBSessionUtil(engine)
            json_bytes = json.dumps(payload).encode("utf-8")

            with db_util.session_scope() as session:
                StatusSnapshotJson.insert(session, program_id, json_bytes)
                logger.info("Snapshot saved to database successfully.")
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}", exc_info=True)


if __name__ == "__main__":
    program_id = "6vdFJZFxQN6jpEMULbbWvs"  # Replace with your actual program ID

    handler = CountStatusHandler()
    summary = handler.count_by_status(program_id)
    print("Count Summary:", summary)
    handler.save_snapshot(program_id, summary)
