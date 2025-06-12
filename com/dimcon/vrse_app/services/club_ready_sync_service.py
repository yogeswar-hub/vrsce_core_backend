from datetime import datetime
from sqlalchemy import func
from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient
from com.dimcon.vrse_app.services.club_ready_members_activity import ClubReadyActivityUsersService
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
from com.dimcon.vrse_app.services.club_ready_all_users_sync import ClubReadyAllUserSyncService  # new import
from com.dimcon.vrse_app.services.audit_log_service import AuditLogService
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_members_activity import ClubMemberActivity
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubReadySyncService:
    @staticmethod
    def run_sync(audit: dict = None):
        # establish a “system” user for audit entries
        system_user = {
            "user_id":  audit.get("updated_by", "system"),
            "username": audit.get("updated_by", ""),
            "email":    ""
        }

        logger.debug("run_sync() start – audit=%r", audit)
        engine = get_engine()
        db_util = DBSessionUtil(engine)
        activity_date = audit.get("activity_date", "01-01-2020")
        logger.info("Activity date = %s", activity_date)

        with db_util.session_scope() as session:
            # 1) Fetch platform configs…
            platform_records = session.query(PlatformConfig).filter(
                func.lower(PlatformConfig.platform_name) == "club_ready"
            ).all()

            # 2) Validate exactly one config…
            unique_configs = {(p.auth_key.strip(), p.chain_id) for p in platform_records}
            if len(unique_configs) != 1:
                logger.error("Found %d ClubReady configs; expected 1", len(unique_configs))
                return

            auth_key, chain_id = next(iter(unique_configs))
            api_client = ClubReadyAPIClient(api_key=auth_key, chain_id=chain_id)

            # 3) Sync Club Locations
            try:
                logger.info("Step 3: Syncing club locations…")
                locations = api_client.fetch_club_locations()
                ClubLocation.insert_or_update_locations(session, locations, audit)
                logger.info("Synced %d club locations", len(locations))
                AuditLogService.log_access(system_user, "club_ready_sync", "SYNC_LOCATIONS")
            except Exception as e:
                AuditLogService.log_access(system_user, "club_ready_sync", "SYNC_LOCATIONS", error_message=str(e))
                logger.exception("Failed to sync locations")
                return

            # 4) Fetch segmented users
            try:
                logger.info("Step 4: Fetching segmented users for %s", activity_date)
                segmented_users = ClubReadyActivityUsersService.sync_all_user_segments(
                    activity_date=activity_date,
                    activity_operator="GT",
                    api_client=api_client
                )
                logger.info("Fetched %d segmented users", len(segmented_users))
                AuditLogService.log_access(system_user, "club_ready_sync", "FETCH_SEGMENT_USERS")
            except Exception as e:
                AuditLogService.log_access(system_user, "club_ready_sync", "SYNC_LOCATIONS", error_message=str(e))
                logger.exception("Failed to fetch segmented users")
                return

            # 5) Insert segmented users into club_members_activity
            try:
                logger.info("Step 5: Inserting %d segmented users…", len(segmented_users))
                ClubMemberActivity.bulk_insert_members_activity(session, segmented_users)
                logger.info("Inserted segmented users")
                AuditLogService.log_access(system_user, "club_ready_sync", "INSERT_SEGMENT_USERS")
            except Exception as e:
                AuditLogService.log_access(system_user, "club_ready_sync", "INSERT_SEGMENT_USERS", error_message=str(e))
                logger.exception("Failed to insert segmented users")

            # 6) Sync all users (dedupe & bulk upsert) via new service class
            try:
                logger.info("Step 6: Syncing ALL users…")
                svc = ClubReadyAllUserSyncService()              # no args here
                svc.sync_all_users(audit, api_client, session)   # pass args to this method
                AuditLogService.log_access(system_user, "club_ready_sync", "SYNC_ALL_USERS")
            except Exception as e:
                AuditLogService.log_access(system_user, "club_ready_sync", "SYNC_ALL_USERS", error_message=str(e))
                logger.exception("sync_all_users failed")
                return


        # 7) Update latest activity info in club_users
        try:
            logger.info("Step 7: Updating latest activity info…")
            ClubUsersService(engine).update_latest_activity_info(session)

            logger.info("Latest activity info updated")
            AuditLogService.log_access(system_user, "club_ready_sync", "UPDATE_LATEST_ACTIVITY")
        except Exception as e:
            AuditLogService.log_access(system_user, "club_ready_sync", "UPDATE_LATEST_ACTIVITY", error_message=str(e))
            logger.exception("Failed to update latest activity info")
            raise