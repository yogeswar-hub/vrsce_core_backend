# clubready_sync_service.py

from datetime import datetime, UTC
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)


class ClubReadySyncService:
    """
    Syncs ClubReady data (locations and users) for each enabled platform.
    Only records not already in the database will be inserted.
    """

    def __init__(self):
        self.engine = get_engine()
        self.db_util = DBSessionUtil(self.engine)

    def sync_locations(self, config, session, audit):
        """
        Sync club locations for a single configuration – only insert new locations.
        """
        client = ClubReadyAPIClient(config.auth_key, config.chain_id)
        fetched_locations = client.fetch_club_locations()
        logger.info(f"Fetched {len(fetched_locations)} locations for platform: {config.platform_name}")

        # Get existing club IDs in the DB.
        existing_ids = {loc for (loc,) in session.query(ClubLocation.club_id).all()}
        new_locations = [loc for loc in fetched_locations if loc.get("Id") not in existing_ids]
        logger.info(f"Found {len(new_locations)} new locations for platform: {config.platform_name}")

        if new_locations:
            ClubLocation.insert_new_locations(session, new_locations, audit)
            logger.info(f"Inserted {len(new_locations)} new location(s) for {config.platform_name}")
        else:
            logger.info("No new locations to sync.")

    def sync_users(self, config, audit):
        """
        Sync club users for a single configuration – only insert new users.
        """
        client = ClubReadyAPIClient(config.auth_key, config.chain_id)
        all_users = client.fetch_all_users_parallel_dynamic(limit=100, batch_size=1)
        logger.info(f"Fetched a total of {len(all_users)} users from ClubReady API using dynamic parallel tasks.")

        # Open a session to filter out new users.
        with self.db_util.session_scope() as session:
            existing_user_ids = {uid for (uid,) in session.query(ClubUser.user_id).all()}
            new_users = [user for user in all_users if user.get("UserId") not in existing_user_ids]
            logger.info(f"Found {len(new_users)} new users for platform: {config.platform_name}")
            
            if new_users:
                ClubUser.bulk_insert_users(session, new_users, audit)
                logger.info(f"Inserted {len(new_users)} new club user(s) for {config.platform_name}")
            else:
                logger.info("No new users to sync.")

    def run_sync(self, audit=None):
        """
        Runs the sync job for all enabled ClubReady platform configurations.
        Deduplicates configurations by auth_key to avoid multiple fetches.
        """
        if audit is None:
            audit = {"created_by": "club_ready_sync", "updated_by": "club_ready_sync"}

        try:
            with self.db_util.session_scope() as session:
                configs = session.query(PlatformConfig).filter_by(enable_member_sync=True).all()
                if not configs:
                    logger.warning("No enabled platform configurations found for ClubReady sync.")
                    return

                unique_configs = {}
                for config in configs:
                    # Use the auth_key as the deduplication key; adjust if needed.
                    if config.auth_key not in unique_configs:
                        unique_configs[config.auth_key] = config

                for config in unique_configs.values():
                    try:
                        logger.info(f"Starting sync for platform: {config.platform_name} (ChainId: {config.chain_id})")
                        self.sync_locations(config, session, audit)
                        self.sync_users(config, audit)

                        # Update sync timestamps in the configuration record.
                        config.last_synced_at = datetime.now(UTC)
                        config.updated_at = datetime.now(UTC)
                        session.commit()
                        logger.info(f"Sync completed successfully for platform: {config.platform_name}")
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Sync failed for platform '{config.platform_name}': {e}")
        except Exception as global_error:
            logger.critical(f"Critical failure in ClubReady sync service: {global_error}", exc_info=True)

if __name__ == "__main__":
    sync_service = ClubReadySyncService()
    sync_service.run_sync({"created_by": "actual_cognito_user", "updated_by": "actual_cognito_user"})
