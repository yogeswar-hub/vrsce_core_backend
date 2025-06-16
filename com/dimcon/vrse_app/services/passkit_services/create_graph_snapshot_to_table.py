import json
from collections import Counter, defaultdict
from google.protobuf.json_format import MessageToDict
from passkit_io.member import member_pb2
from passkit_io.common import filter_pb2
from com.dimcon.vrse_app.resources.vrse_passkit.database_scripts.graph_snapshot_json import GraphSnapshotJson
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.grpc_client import GrpcClient
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class CreateGraphSnapshotToTable:
    """Fetch members via gRPC, analyze distributions, and store snapshot in DB."""

    def __init__(self, program_id: str):
        """Initialize with PassKit program ID."""
        self.program_id = program_id
        self.grpc_client = GrpcClient()

    def fetch_all_members(self, limit_per_page=300, max_pages=10):
        """Fetch member pages from PassKit gRPC."""
        logger.info(f"Fetching members for program_id={self.program_id} limit={limit_per_page} max_pages={max_pages}")
        stub = self.grpc_client.get_members_stub()
        all_members = []
        for page in range(max_pages):
            offset = page * limit_per_page
            filters = filter_pb2.Filters(limit=limit_per_page, offset=offset, orderBy="created", orderAsc=True)
            request = member_pb2.ListRequest(programId=self.program_id, filters=filters)
            try:
                stream = stub.listMembers(request)
                count_this_page = 0
                for member in stream:
                    all_members.append({
                        "result": MessageToDict(member, preserving_proto_field_name=True),
                        "error": {"code": 0, "message": "", "details": []}
                    })
                    count_this_page += 1
                logger.debug(f"Fetched {count_this_page} members on page {page}")
            except Exception as e:
                logger.error(f"Error fetching members on page {page}: {e}", exc_info=True)
        logger.info(f"Total members fetched: {len(all_members)}")
        return all_members

    def analyze(self, members):
        """Generate distributions and geo drilldown from member data."""
        logger.info("Starting analysis of members data.")
        result = {
            "access_type_distribution": self._access_type_distribution(members),
            "wallet_type_distribution": self._wallet_type_distribution(members),
            "pass_status_distribution": self._pass_status_distribution(members),
            "tier_distribution": self._tier_distribution(members),
            "geo_location_drilldown": self._geo_location_drilldown(members)
        }
        logger.info("Completed analysis of members data.")
        return result

    def _access_type_distribution(self, members, access_type_filter=None):
        """Count members by access type."""
        counter = Counter()
        total = 0
        for m in members:
            access_type = m.get("result", {}).get("metaData", {}).get("accessType") or "Unknown"
            if not access_type_filter or access_type == access_type_filter:
                counter[access_type] += 1
                total += 1
        return {
            "distribution": dict(counter),
            "summary": {"Total Members with Access Type": total, "Filtered Access Type": access_type_filter or "All"}
        }

    def _wallet_type_distribution(self, members, event_filter=None):
        """Count wallet lifecycle events."""
        counter = Counter()
        unique_members = set()
        all_event_types = set()
        for m in members:
            member_id = m.get("result", {}).get("id")
            events = m.get("result", {}).get("passMetaData", {}).get("lifecycleEvents", [])
            if events:
                unique_members.add(member_id)
            for event in events:
                all_event_types.add(event)
                if not event_filter or event == event_filter:
                    counter[event] += 1
        return {
            "distribution": dict(counter),
            "summary": {
                "Total Members with Wallet Events": len(unique_members),
                "Unique Wallet Event Types": len(all_event_types),
                "Filtered Event Type": event_filter or "All"
            }
        }

    def _pass_status_distribution(self, members, status_filter=None):
        """Count pass statuses."""
        counter = Counter()
        total = 0
        for m in members:
            status = m.get("result", {}).get("passMetaData", {}).get("status")
            if status and (not status_filter or status == status_filter):
                counter[status] += 1
                total += 1
        return {
            "distribution": dict(counter),
            "summary": {"Total Members with Pass Status": total, "Filtered Status": status_filter or "All"}
        }

    def _tier_distribution(self, members, tier_filter=None):
        """Count tiers."""
        counter = Counter()
        total = 0
        for m in members:
            tier = m.get("result", {}).get("tierId")
            if tier and (not tier_filter or tier == tier_filter):
                counter[tier] += 1
                total += 1
        return {
            "distribution": dict(counter),
            "summary": {"Total Members with Tier": total, "Filtered Tier": tier_filter or "All"}
        }

    def _geo_location_drilldown(self, members, country_filter=None, state_filter=None, city_filter=None, min_count=None):
        """Aggregate members by geographic location."""
        geo_counter = defaultdict(int)
        for m in members:
            loc = m.get("result", {}).get("passMetaData", {}).get("renderLocation", {})
            country = loc.get("country", "Unknown")
            state = loc.get("state", "Unknown")
            city = loc.get("city", "Unknown")
            geo_counter[(country, state, city)] += 1

        full_data = [{"country": c, "state": s, "city": ci, "count": ct} for (c, s, ci), ct in geo_counter.items()]
        filtered = [
            loc for loc in full_data
            if (not country_filter or loc["country"] == country_filter)
            and (not state_filter or loc["state"] == state_filter)
            and (not city_filter or loc["city"] == city_filter)
            and (not min_count or loc["count"] >= min_count)
        ]

        total_members = sum(loc["count"] for loc in full_data)
        filtered_members = sum(loc["count"] for loc in filtered)
        return {
            "locations": filtered,
            "summary": {
                "total_members": total_members,
                "filtered_members": filtered_members,
                "filtered_locations": len(filtered),
                "percentage_of_total_members": f"{(filtered_members / total_members * 100):.2f}%" if total_members else "0.00%"
            }
        }

    def run_and_store_snapshot(self):
        """Fetch members, analyze, and save snapshot JSON in database."""
        logger.info("Starting graph snapshot creation...")
        members = self.fetch_all_members()
        logger.info(f"Fetched {len(members)} members, analyzing data...")
        analysis = self.analyze(members)

        engine = get_engine()
        db_util = DBSessionUtil(engine)
        json_bytes = json.dumps(analysis, indent=2)

        try:
            with db_util.session_scope() as session:
                GraphSnapshotJson.create(session, program_id=self.program_id, content_bytes=json_bytes)
                logger.info("Stored graph snapshot to DB successfully.")
        except Exception as e:
            logger.error(f"Failed to store graph snapshot: {e}", exc_info=True)
            raise

        logger.info("Graph snapshot creation finished.")
        return {
            "message": "Graph snapshot successfully created",
            "program_id": self.program_id,
            "member_count": len(members),
            "analytics": analysis
        }

if __name__ == "__main__":
    program_id = "6vdFJZFxQN6jpEMULbbWvs"  # Your actual program ID here
    snapshot_creator = CreateGraphSnapshotToTable(program_id)
    result = snapshot_creator.run_and_store_snapshot()
    print(result)
