from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient
from com.dimcon.vrse_app.resources.vrse.vrse_club_user_data import parse_user_payload, ClubReadyUser
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class ClubReadyAllUserSyncService:
    def sync_all_users(self, audit: dict, api_client: ClubReadyAPIClient, session: Session):
        logger.info("Step 6: Fetching all store users using fetch_users_for_store")

        # Step 1: Get all store_ids
        store_ids = [r.club_id for r in session.query(ClubLocation.club_id).distinct().all() if r.club_id]
        logger.info(f"Fetched {len(store_ids)} unique club_ids from locations")

        all_users = []

        # Step 2: Fetch users from each store
        for store_id in store_ids:
            try:
                users = api_client.fetch_all_users_for_store(store_id)
                for user in users:
                    user["StoreId"] = store_id
                all_users.extend(users)
                logger.info(f"Fetched {len(users)} users from store {store_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch users from store {store_id}: {e}")

        logger.info(f"Total raw users fetched: {len(all_users)}")

        # Step 3: Parse and upsert without deduplication
        parsed_payloads = []
        for u in all_users:
            parsed = parse_user_payload(u)
            if parsed.get("user_id") is not None:
                parsed_payloads.append(parsed)

        logger.info(f"Prepared {len(parsed_payloads)} user payloads to upsert.")
        if parsed_payloads:
            logger.debug(f"Sample payload: {parsed_payloads[0]}")

        logger.info("Upserting parsed user payloads into club_ready_users table")
        ClubReadyUser.bulk_upsert_users(session, parsed_payloads)
        logger.info("User sync complete")
