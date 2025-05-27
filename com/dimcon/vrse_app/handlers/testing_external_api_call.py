from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.services.club_ready_sync_service import ClubReadySyncService
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from datetime import datetime, timezone

logger = LoggerManager.setup_logger(__name__)

def main():
    # Initialize DB engine and session utility.
    engine = get_engine()
    db_util = DBSessionUtil(engine)
    
    # Verify that enabled configuration exists.
    with db_util.session_scope() as session:
        configs = session.query(PlatformConfig).filter_by(platform_name="club_ready", enable_member_sync=True).all()
        if not configs:
            logger.warning("No enabled PlatformConfig record found for 'club_ready'. Please insert a valid record.")
            return
        else:
            logger.info(f"Found {len(configs)} platform configuration record(s) for ClubReady.")
    
    # Simulate Lambda event to extract audit details.
    sample_event = {
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "example_cognito_user_id"
                }
            }
        }
    }
    claims = sample_event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    audit = {
         "created_by": claims.get("sub", "unknown"),
         "updated_by": claims.get("sub", "unknown")
    }
    logger.info(f"Audit details extracted from event: {audit}")
    
    # Run only the user sync function.
    logger.info("Starting live ClubReady user sync only...")
    sync_service = ClubReadySyncService()
    
    # For each configuration, call only the sync_users() function.
    with db_util.session_scope() as session:
        for config in configs:
            try:
                # Re-attach config to the current session.
                config = session.merge(config)
                logger.info(f"Starting user sync for platform: {config.platform_name} (ChainId: {config.chain_id})")
                sync_service.sync_users(config, session, audit)
                # Update sync timestamps.
                config.last_synced_at = datetime.now(timezone.utc)
                config.updated_at = datetime.now(timezone.utc)
                session.commit()
                logger.info(f"User sync completed successfully for platform: {config.platform_name}")
            except Exception as e:
                session.rollback()
                logger.error(f"User sync failed for platform '{config.platform_name}': {e}")
    
    # Query and print ClubUser records after sync.
    with db_util.session_scope() as session:
        users = session.query(ClubUser).all()
        logger.info(f"Live Sync Results: {len(users)} Club User(s) stored in DB.")
        for user in users:
            print(user.to_dict())

if __name__ == '__main__':
    main()