from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil
from com.dimcon.synthera.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.synthera.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.synthera.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.synthera.services.club_ready_sync_service import ClubReadySyncService
from com.dimcon.synthera.utilities.log_handler import LoggerManager
from datetime import datetime, timezone

logger = LoggerManager.setup_logger(__name__)

def main():
    # Initialize DB engine and session utility.
    engine = get_engine()
    db_util = DBSessionUtil(engine)
    
    # Verify enabled configuration exists
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
    
    # Run the live sync service using audit details passed from the test script.
    logger.info("Starting live ClubReady sync...")
    sync_service = ClubReadySyncService()
    sync_service.run_sync(audit)
    
    # Query and print records after sync.
    with db_util.session_scope() as session:
        locations = session.query(ClubLocation).all()
        users = session.query(ClubUser).all()
    
        logger.info(f"Live Sync Results: {len(locations)} Club Location(s) stored in DB.")
        for loc in locations:
            print(loc.to_dict())
    
        logger.info(f"Live Sync Results: {len(users)} Club User(s) stored in DB.")
        for user in users:
            print(user.to_dict())

if __name__ == '__main__':
    main()