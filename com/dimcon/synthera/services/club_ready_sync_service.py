# clubready_sync_service.py

from datetime import datetime, UTC
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil
from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.synthera.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.synthera.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.synthera.services.club_ready_api_client import ClubReadyAPIClient
from com.dimcon.synthera.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)


class ClubReadySyncService:
    """
    Handles syncing of ClubReady data (locations and users) for each enabled platform configuration.
    Expects audit information to be provided from the caller (e.g. from a Lambda event).
    """

    def __init__(self):
        # Initialize DB engine and session utility
        self.engine = get_engine()
        self.db_util = DBSessionUtil(self.engine)

    def run_sync(self, audit):
        """
        Executes the sync job for all enabled ClubReady platform configurations.

        :param audit: Dictionary with audit details, e.g. {"created_by": "cognito_user", "updated_by": "cognito_user"}
                      If not provided, defaults to {"created_by": "club_ready_sync", "updated_by": "club_ready_sync"}.
        """
        if audit is None:
            audit = {"created_by": "club_ready_sync", "updated_by": "club_ready_sync"}

        try:
            with self.db_util.session_scope() as session:
                # Fetch all enabled platform configurations
                configs = session.query(PlatformConfig).filter_by(enable_member_sync=True).all()

                if not configs:
                    logger.warning("No enabled platform configurations found for ClubReady sync.")
                    return

                for config in configs:
                    try:
                        logger.info(f"Starting sync for platform: {config.platform_name} (ChainId: {config.chain_id})")

                        # Instantiate API client using config credentials
                        client = ClubReadyAPIClient(config.auth_key, config.chain_id)

                        # === Sync Club Locations ===
                        locations = client.fetch_club_locations()
                        print(locations)
                        ClubLocation.insert_or_update_locations(session, locations, audit)
                        logger.info(f"Synced {len(locations)} locations for {config.platform_name}")

                        # === Sync Club Users ===
                        users = client.fetch_all_users()
                        ClubUser.insert_or_update_users(session, users, audit)
                        logger.info(f"Synced {len(users)} users for {config.platform_name}")

                        # === Update sync timestamps ===
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
    # For example, you could run:
    # sync_service = ClubReadySyncService()
    # sync_service.run_sync({"created_by": "actual_cognito_user", "updated_by": "actual_cognito_user"})
    sync_service = ClubReadySyncService()
    sync_service.run_sync()
