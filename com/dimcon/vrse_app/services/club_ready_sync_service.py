from datetime import datetime, timedelta
from sqlalchemy import func
from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient, fetch_users_range
from com.dimcon.vrse_app.services.club_ready_active_mem_service import ClubReadyActiveUsersService
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.resources.vrse.vrse_platform_config import PlatformConfig
from com.dimcon.vrse_app.resources.vrse.vrse_club_locations import ClubLocation
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.resources.vrse.vrse_club_members_activity import ClubActiveMember
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.services.club_ready_user_validator_before_upsert import ClubUserValidator
import json, math

logger = LoggerManager.setup_logger(__name__)

class ClubReadySyncService:
    @staticmethod
    def run_sync(audit: dict = None):
        logger.debug("run_sync() start – audit=%r", audit)
        engine = get_engine()
        db_util = DBSessionUtil(engine)
        # Use a fixed or dynamic date as required
        activity_date = audit.get("activity_date", "01-01-2020")
        logger.info("Activity date = %s", activity_date)

        with db_util.session_scope() as session:
            logger.debug("Opened DB session %r", session)
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
                logger.info("Step 3: Syncing club locations…")
                locations = api_client.fetch_club_locations()
                ClubLocation.insert_or_update_locations(session, locations, audit)
                logger.info("Synced %d club locations", len(locations))
                logger.debug("Sample locations: %r", locations[:2])
            except Exception as e:
                logger.exception("❌ Failed to sync locations")
                return

            # 4. Sync segmented users (existing logic), if needed...
            try:
                logger.info("Step 4: Fetching segmented users for %s", activity_date)
                segmented_users = ClubReadyActiveUsersService.sync_all_user_segments(
                    activity_date=activity_date,
                    activity_operator="GT",
                    api_client=api_client
                )
                logger.info("Fetched %d segmented users", len(segmented_users))
                logger.debug("Sample segmented_users: %r", segmented_users[:2])
            except Exception as e:
                logger.exception("⚠️ Failed to fetch segmented users")
                return

            logger.debug("Segmented Users Raw Data: %s", json.dumps(segmented_users, indent=2))

            # 5. NEW STEP: Sync all users using /users/find API and process duplicates.
            try:
                logger.info("Step 5: Syncing ALL users (dedupe & upsert)…")
                ClubReadySyncService.sync_all_users(audit, api_client, session)
            except Exception:
                logger.exception("❌ sync_all_users failed")
                return

            # 6. Finally, insert segmented users into active members.
            try:
                logger.info("Step 6: Inserting %d segmented users into club_active_members", len(segmented_users))
                ClubActiveMember.bulk_insert_active_members(session, segmented_users)
                logger.info("✅ Inserted segmented users into club_active_members")
            except Exception as e:
                logger.exception("❌ Failed to insert segmented users")
            # 7. Update latest activity info in club_users
        try:
            logger.info("Step 7: Updating latest activity info in club_users")
            club_users_service = ClubUsersService(get_engine())
            club_users_service.update_latest_activity_info(session)
            logger.info("✅ Latest activity info updated")
        except Exception as e:
            logger.exception("❌ Failed to update latest activity info")
            raise


    @staticmethod
    def sync_all_users(audit: dict, api_client: ClubReadyAPIClient, session):
        """
        Sync users from ClubReady into the local database.
        """
        users_per_page = 100
        logger.debug("sync_all_users() start – audit=%r", audit)
        logger.debug("Using api_client chain_id=%s", api_client.chain_id)

        # 1) Fetch raw users
        try:
            if "start_page" in audit and "end_page" in audit:
                sp = int(audit["start_page"]); ep = int(audit["end_page"])
                logger.info("Fetching only pages %d–%d", sp, ep)
                all_users = fetch_users_range(
                    api_client,
                    start_page=sp,
                    end_page=ep,
                    limit=users_per_page,
                    batch_size=2
                )
                logger.info("fetch_users_range pages %d–%d returned %d records", sp, ep, len(all_users))
                logger.debug("Sample all_users: %r", all_users[:3])
            else:
                logger.info("No page range; calling fetch_all_users_parallel_dynamic()")
                all_users = api_client.fetch_all_users_parallel_dynamic(
                    limit=users_per_page,
                    batch_size=10
                )
                logger.info("fetch_all_users_parallel_dynamic returned %d records", len(all_users))
                logger.debug("Sample all_users: %r", all_users[:3])
        except Exception as e:
            logger.exception("❌ sync_all_users: Error during user fetch")
            raise

        logger.info("Fetched %d raw user records", len(all_users))

        # 2) Normalize & group by email
        users_by_email = {}
        for user in all_users:
            email = user.get("Email")
            if not email:
                logger.debug("Skipping user with missing Email: %s", user)
                continue
            normalized = email.strip().lower()
            user["Email"] = normalized
            users_by_email.setdefault(normalized, []).append(user)
        logger.debug("Grouped into %d email buckets", len(users_by_email))

        # 3) Deduplicate
        unique_users = []
        duplicate_info = {}
        for email, records in users_by_email.items():
            if len(records) == 1:
                unique_users.append(records[0])
            else:
                chosen = max(records, key=lambda r: int(r.get("UserId", 0)))
                dup_ids = [r.get("UserId") for r in records]
                duplicate_info[email] = dup_ids
                unique_users.append(chosen)
        logger.info(
            "Deduped users: %d unique, %d duplicates",
            len(unique_users), len(duplicate_info)
        )
        logger.debug(
            "Sample duplicate buckets: %s",
            list(duplicate_info.items())[:5]
        )

        # 3b) New validation step: remove any email/user_id conflicts
        to_upsert, conflicts, skipped = ClubUserValidator.validate_unique_users(
            session, unique_users
        )
        if conflicts:
            logger.warning(
                f"Skipped {len(conflicts)} users due to user_id/email conflicts. "
                "See logs for details."
            )
        if skipped:
            logger.info(
                f"Skipped {len(skipped)} users: already up to date or no changes."
            )

        # 4) Bulk upsert
        try:
            logger.info("Upserting %d users into club_users", len(to_upsert))
            logger.debug("Sample payload for upsert: %s", to_upsert[:2])
            ClubUser.bulk_upsert_users(session, to_upsert, audit)
            logger.info("✅ Bulk upsert completed successfully")
        except Exception:
            logger.exception("❌ Bulk upsert failed")
            raise

        logger.debug("sync_all_users() completed successfully")