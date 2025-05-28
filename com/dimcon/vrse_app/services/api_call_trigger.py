from sqlalchemy import event
from com.dimcon.vrse_app.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.vrse_app.services.club_ready_sync_service import ClubReadySyncService
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

@event.listens_for(PlatformConfig, "after_insert")
def trigger_sync_service(mapper, connection, target):
    """
    Triggered after a new PlatformConfig record is inserted.
    Calls the ClubReadySyncService to start the sync process.
    """
    try:
        logger.info(f"New PlatformConfig record inserted (ID: {target.id}). Initiating sync service.")
        # You might want to pass audit info from the newly inserted record.
        audit = {
            "created_by": target.created_by,
            "updated_by": target.updated_by
        }
        sync_service = ClubReadySyncService()
        # Run sync for all enabled configurations.
        # Alternatively, you can tune the service to only sync for this config if needed.
        sync_service.run_sync(audit)
        logger.info("ClubReady sync service triggered successfully.")
    except Exception as e:
        logger.error(f"Error triggering ClubReadySyncService after insert: {e}")