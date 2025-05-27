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
    Handles syncing of ClubReady data (locations and users) for each enabled platform configuration.
    Expects audit information to be provided from the caller (e.g. from a Lambda event).
    """

    def __init__(self):
        # Initialize DB engine and session utility.
        self.engine = get_engine()
        self.db_util = DBSessionUtil(self.engine)

    def sync_locations(self, config, session, audit):
        """
        Sync club locations for a single configuration.

        :param config: The PlatformConfig record.
        :param session: Active SQLAlchemy session.
        :param audit: Audit dictionary with keys 'created_by' and 'updated_by'.
        """
        # Instantiate API client using config credentials.
        client = ClubReadyAPIClient(config.auth_key, config.chain_id)
        # Fetch locations from the external API.
        locations = client.fetch_club_locations()
        logger.info(f"Fetched {len(locations)} locations for platform: {config.platform_name}")
        # Insert or update ClubLocation records using provided audit details.
        ClubLocation.insert_or_update_locations(session, locations, audit)
        logger.info(f"Synced {len(locations)} locations for {config.platform_name}")

    def sync_users(self, config, session, audit):
        """
        Sync club users for a single configuration.

        :param config: The PlatformConfig record.
        :param session: Active SQLAlchemy session.
        :param audit: Audit dictionary with keys 'created_by' and 'updated_by'.
        """
        # Instantiate API client using config credentials.
        client = ClubReadyAPIClient(config.auth_key, config.chain_id)
        # Fetch all users (handling pagination inside the API client).
        users = client.fetch_all_users()
        logger.info(f"Fetched {len(users)} users for platform: {config.platform_name}")
        # Insert or update ClubUser records using provided audit details.
        ClubUser.insert_or_update_users(session, users, audit)
        logger.info(f"Synced {len(users)} users for {config.platform_name}")

    def run_sync(self, audit=None):
        """
        Executes the sync job for all enabled ClubReady platform configurations.

        :param audit: Dictionary with audit details (e.g. {"created_by": "cognito_user", "updated_by": "cognito_user"})
                      If not provided, defaults to {"created_by": "club_ready_sync", "updated_by": "club_ready_sync"}.
        """
        if audit is None:
            audit = {"created_by": "club_ready_sync", "updated_by": "club_ready_sync"}

        try:
            with self.db_util.session_scope() as session:
                # Fetch all enabled platform configurations.
                configs = session.query(PlatformConfig).filter_by(enable_member_sync=True).all()
                if not configs:
                    logger.warning("No enabled platform configurations found for ClubReady sync.")
                    return

                for config in configs:
                    try:
                        logger.info(f"Starting sync for platform: {config.platform_name} (ChainId: {config.chain_id})")
                        # Call separate functions to sync locations and users.
                        self.sync_locations(config, session, audit)
                        self.sync_users(config, session, audit)

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
    # Example: passing audit details from the calling context (e.g., from a Lambda event)
    sync_service = ClubReadySyncService()
    # Replace the dictionary below with actual audit values if available.
    sync_service.run_sync({"created_by": "actual_cognito_user", "updated_by": "actual_cognito_user"})
