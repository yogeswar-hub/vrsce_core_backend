import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from com.dimcon.vrse_app.utilities.grpc_client import GrpcClient
from passkit_io.member import member_pb2
from passkit_io.common import filter_pb2

from com.dimcon.vrse_app.resources.vrse_passkit.database_scripts.homeclub_snapshot_json import HomeclubSnapshot
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from google.protobuf.json_format import MessageToDict
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class CreateActiveMembersByLocationToTable:
    def __init__(self, program_id):
        self.program_id = program_id
        self.grpc_client = GrpcClient()
        self.members_stub = self.grpc_client.get_members_stub()  # get stub once here

    def fetch_page(self, offset, page_size):
        club_counts = defaultdict(int)
        try:
            filters = filter_pb2.Filters(
                limit=page_size,
                offset=offset,
                orderBy="created",
                orderAsc=True
            )
            request = member_pb2.ListRequest(programId=self.program_id, filters=filters)

            page = list(self.members_stub.listMembers(request))  # Use stub here

            for member in page:
                member_dict = MessageToDict(member)
                home_club = member_dict.get("metaData", {}).get("homeClub", "Unknown")
                club_counts[home_club] += 1

        except Exception as e:
            logger.error(f"Error fetching offset {offset}: {e}")
        return club_counts

    def get_member_counts_by_homeclub(self, total_expected=1600, page_size=200, max_workers=5):
        offsets = [i for i in range(0, total_expected, page_size)]
        total_club_counts = defaultdict(int)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.fetch_page, offset, page_size) for offset in offsets]
            for future in as_completed(futures):
                page_counts = future.result()
                for club, count in page_counts.items():
                    total_club_counts[club] += count

        return dict(sorted(total_club_counts.items(), key=lambda x: x[1], reverse=True))

    def run_and_store_snapshot(self, total_expected=1600, page_size=200, max_workers=5):
        counts = self.get_member_counts_by_homeclub(total_expected, page_size, max_workers)
        total_members = sum(counts.values())

        data = {
            "homeclub_counts": counts,
            "total_members": total_members
        }

        json_bytes = json.dumps(data).encode("utf-8")

        engine = get_engine()
        db_util = DBSessionUtil(engine)
        with db_util.session_scope() as session:
            snapshot = HomeclubSnapshot.create(session, self.program_id, json_bytes)
            session.commit()
            snapshot_id = snapshot.id

        logger.info(f"Stored homeclub snapshot with ID: {snapshot_id}")
        return {
            "message": "Homeclub snapshot stored successfully",
            "program_id": self.program_id,
            "total_members": total_members,
            "homeclub_counts": counts,
            "snapshot_id": snapshot_id
        }

if __name__ == "__main__":
    program_id = "6vdFJZFxQN6jpEMULbbWvs"  # Replace with your actual program ID
    runner = CreateActiveMembersByLocationToTable(program_id)
    result = runner.run_and_store_snapshot()
    logger.info(result)
    print(result)
