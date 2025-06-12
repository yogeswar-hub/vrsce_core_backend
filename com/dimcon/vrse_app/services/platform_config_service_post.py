import json
from datetime import datetime, timezone
from com.dimcon.vrse_app.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.services.club_ready_sync_service import ClubReadySyncService

logger = LoggerManager.setup_logger(__name__)

class PlatformConfigService:
    
    @staticmethod
    def handle_post(event, user_info, path_params):
        """
        Handles POST requests for platform configuration.
        Inserts the new configuration record and triggers a sync.
        """
        try:
            body = event.get("body")
            if not body:
                return {"error": "Missing request body."}
            # Parse JSON configuration data
            config_data = json.loads(body)
            
            # Combine provided config data with audit details from Cognito claims.
            config_data["created_by"] = user_info.get("user_id", "unknown")
            config_data["updated_by"] = user_info.get("user_id", "unknown")
            config_data["sub"] = user_info.get("user_id", "unknown")
            config_data["iss"] = user_info.get("iss", "")
            config_data["auth_time"] = user_info.get("auth_time", "")
            config_data["aud"] = user_info.get("aud", "")
            config_data["auth_time_human"] = ""  # This will be calculated upon insert if auth_time exists
            
            # Setup database session and insert configuration record.
            engine = get_engine()
            db_util = DBSessionUtil(engine)
            with db_util.session_scope() as session:
                new_cfg = PlatformConfig.insert_config(session, config_data)
                new_cfg_data = new_cfg.to_dict()  # materialize all needed attributes
                logger.info(f"Platform configuration inserted: {new_cfg_data}")
                # session.commit() happens automatically at exit

            # Now trigger sync using the dictionary data, not the detached instance.
            # ClubReadySyncService().run_sync({
            #     "created_by": new_cfg_data.get("created_by"),
            #     "updated_by": new_cfg_data.get("updated_by"),
            #     "platform_config_id": new_cfg_data.get("id")  # if needed by the sync service
            # })
            
            # Return the inserted record details.
            return {"message": "Platform configuration inserted successfully.", "config": new_cfg_data}
        except Exception as e:
            logger.error(f"Error handling platform_config POST: {e}")
            return {"error": "Failed to insert platform configuration.", "details": str(e)}