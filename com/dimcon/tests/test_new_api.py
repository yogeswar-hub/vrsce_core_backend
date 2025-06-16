# ✅ Must go before any other import that needs this env var
import os
os.environ.setdefault("CLUBREADY_BASE_URL", "https://clubready.com/api/current")

from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient
from com.dimcon.vrse_app.resources.vrse.vrse_club_user_data import ClubReadyUser, parse_user_payload
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)


logger = LoggerManager.setup_logger(__name__)

def main():
    # Configure environment and DB
    engine = get_engine()
    db_util = DBSessionUtil(engine)

    # Initialize API client
    client = ClubReadyAPIClient(
        api_key="85b59f92-615a-4f89-8dbf-39bd62f5344c",
        chain_id=658
    )

    # Fetch list of stores
    stores = client.fetch_club_locations()

    for store in stores:
        store_id = store.get("Id")
        logger.info(f"Processing store: {store_id}")

        try:
            users_raw = client.fetch_all_users_for_store(store_id)
            parsed_users = [parse_user_payload(u) for u in users_raw if u.get("UserId")]

            with db_util.session_scope() as session:
                ClubReadyUser.bulk_upsert_users(session, parsed_users)
                logger.info(f"[Store {store_id}] Upserted {len(parsed_users)} users")

        except Exception as e:
            logger.exception(f"Failed to sync users for store {store_id}: {e}")

if __name__ == "__main__":
    main()
