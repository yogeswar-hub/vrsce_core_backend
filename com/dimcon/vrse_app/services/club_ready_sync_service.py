from datetime import datetime, timedelta
from sqlalchemy import func
from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient
from com.dimcon.vrse_app.services.club_ready_active_mem_service import ClubReadyActiveUsersService
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.resources.vrse.vrse_club_members_activity import ClubActiveMember
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubReadySyncService:
    @staticmethod
    def run_sync(audit: dict = None):
        engine = get_engine()
        db_util = DBSessionUtil(engine)
        # Use a fixed date or dynamic date as required.
        activity_date = "01-01-2020"

        with db_util.session_scope() as session:
            # 1. Fetch platform configs for club_ready (case-insensitive)
            platform_records = session.query(PlatformConfig).filter(
                func.lower(PlatformConfig.platform_name) == "club_ready"
            ).all()

            # 2. Extract unique (auth_key, chain_id) pairs
            unique_configs = {(p.auth_key.strip(), p.chain_id) for p in platform_records}
            if len(unique_configs) != 1:
                logger.error(
                    f"Found {len(unique_configs)} unique ClubReady configs. Expected exactly 1. Fix your platform_config table."
                )
                logger.warning(f"Configs found: {list(unique_configs)}")
                return

            auth_key, chain_id = list(unique_configs)[0]
            api_client = ClubReadyAPIClient(api_key=auth_key, chain_id=chain_id)

            # 3. Sync Club Locations
            try:
                logger.info("Syncing club locations...")
                locations = api_client.fetch_club_locations()
                ClubLocation.insert_or_update_locations(session, locations, audit)
                logger.info(f"Synced {len(locations)} locations into club_locations table.")
            except Exception as e:
                logger.error("Failed to sync locations", exc_info=True)
                return

            # 4. Sync segmented users (existing logic), if needed...
            try:
                logger.info(f"👥 Fetching segmented users for activity_date={activity_date}")
                segmented_users = ClubReadyActiveUsersService.sync_all_user_segments(
                    activity_date=activity_date,
                    activity_operator="GT",
                    api_client=api_client
                )
                logger.info(f"Fetched {len(segmented_users)} users from /users endpoint")
            except Exception as e:
                logger.error("Failed to fetch segmented users", exc_info=True)
                return

            # 5. NEW STEP: Sync all users using /users/find API and process duplicates.
            ClubReadySyncService.sync_all_users(audit, api_client, session)

            # 6. Finally, insert segmented users into active members.
            try:
                ClubActiveMember.bulk_insert_active_members(session, segmented_users)
                logger.info("Inserted segmented users into club_active_members")
            except Exception as e:
                logger.error("Failed to insert into club_active_members", exc_info=True)

    @staticmethod
    def sync_all_users(audit: dict, api_client: ClubReadyAPIClient, session):
        """
        Fetch all users using the /users/find API in paginated mode,
        group the users by email and process duplicates:
         - For unique emails: Insert only if not exists.
         - For duplicate emails: Use the record with the maximum user_id.
        """
        try:
            logger.info("Fetching all users in paginated batches via /users/find API...")
            # Using existing API Client method that handles parallel dynamic fetch.
            all_users = api_client.fetch_all_users_parallel_dynamic(limit=100, batch_size=10)
            logger.info(f"Fetched total {len(all_users)} users from API.")
        except Exception as ex:
            logger.error(f"Error fetching all users: {ex}", exc_info=True)
            return

        # Group users by email.
        users_by_email = {}
        for user in all_users:
            email = user.get("Email")
            if not email:
                continue
            users_by_email.setdefault(email, []).append(user)

        # Separate into unique and duplicate records.
        unique_users = []
        duplicate_users = {}  # duplicate_users[email] = { "data": record_with_max_user_id, "all_ids": [list of user_ids] }
        for email, records in users_by_email.items():
            if len(records) == 1:
                unique_users.append(records[0])
            else:
                max_record = max(records, key=lambda r: int(r.get("UserId", 0)))
                duplicate_users[email] = {
                    "data": max_record,
                    "all_ids": [r.get("UserId") for r in records]
                }

        import json
        logger.info("Duplicate Users JSON: " + json.dumps(duplicate_users))

        # Process unique users: insert if not present in ClubUser table.
        for user in unique_users:
            email = user.get("Email")
            existing = ClubUser.get_by_email(session, email)  # Assumes this method exists in ClubUser.
            if existing:
                logger.info(f"Unique user already exists in DB for email: {email}")
            else:
                ClubUser.insert_single_user(session, user, audit)
                logger.info(f"Inserted unique user for email: {email}")

        # Process duplicate users: for each email, use the record with the maximum user_id.
        for email, entry in duplicate_users.items():
            record = entry["data"]
            existing = ClubUser.get_by_email(session, email)
            if existing:
                ClubUser.update_user(session, record, audit)
                logger.info(f"Updated duplicate user for email: {email} using record with max user_id.")
            else:
                ClubUser.insert_single_user(session, record, audit)
                logger.info(f"Inserted duplicate user for email: {email} using record with max user_id.")
