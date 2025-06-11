from com.dimcon.vrse_app.resources.connect_aurora import get_engine  

import logging, json
from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient, fetch_users_range
from com.dimcon.vrse_app.services.club_ready_members_activity import ClubReadyActivityUsersService
from com.dimcon.vrse_app.services.club_users_service import ClubUsersService
from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.resources.vrse.vrse_club_members_activity import ClubMemberActivity
from com.dimcon.vrse_app.services.club_ready_user_validator_before_upsert import ClubUserValidator

logger = logging.getLogger(__name__)

class ClubReadyAllUserSyncService:
    """
    Handles fetching *all* ClubReady users, deduplication, validation,
    and bulk upsert into the `club_users` table.
    """

    @staticmethod
    def sync_all_users(audit: dict, api_client: ClubReadyAPIClient, session):
        # 1) Fetch raw users (either a page‐range or dynamically all pages)
        try:
            if "start_page" in audit and "end_page" in audit:
                sp, ep = int(audit["start_page"]), int(audit["end_page"])
                logger.info("Fetching only pages %d–%d", sp, ep)
                all_users = fetch_users_range(
                    api_client,
                    start_page=sp,
                    end_page=ep,
                    limit=100,
                    batch_size=2
                )
            else:
                logger.info("No page range; calling fetch_all_users_parallel_dynamic()")
                all_users = api_client.fetch_all_users_parallel_dynamic(
                    limit=100,
                    batch_size=2
                )
            logger.info("Fetched %d raw user records", len(all_users))
            logger.debug("Sample users: %r", all_users[:3])
        except Exception as e:
            logger.exception("Error during fetch_all_users")
            raise

        # 2) Normalize & group by email
        users_by_email = {}
        for user in all_users:
            email = user.get("Email")
            if not email:
                logger.debug("Skipping user with missing Email: %s", user)
                continue
            normalized = email.strip().lower()
            users_by_email.setdefault(normalized, []).append(user)
        logger.debug("Grouped into %d email buckets", len(users_by_email))

        # 3) Deduplicate: pick highest UserId if multiples
        unique_users, duplicate_info = [], {}
        for email, records in users_by_email.items():
            if len(records) == 1:
                unique_users.append(records[0])
            else:
                chosen = max(records, key=lambda r: int(r.get("UserId", 0)))
                duplicate_info[email] = [r.get("UserId") for r in records]
                unique_users.append(chosen)
        logger.info(
            "Deduped users: %d unique, %d duplicate buckets",
            len(unique_users), len(duplicate_info)
        )
        logger.debug("Sample duplicates: %s", dict(list(duplicate_info.items())[:5]))

        # 3b) Validate against existing DB state
        to_upsert, conflicts, skipped = ClubUserValidator.validate_unique_users(
            session, unique_users
        )
        if conflicts:
            logger.warning("Skipped %d due to ID/email conflicts", len(conflicts))
        if skipped:
            logger.info("Skipped %d already up-to-date users", len(skipped))

        # 4) Bulk upsert into club_users
        try:
            logger.info("Upserting %d users into club_users", len(to_upsert))
            logger.debug("Upsert payload sample: %s", json.dumps(to_upsert[:2]))
            ClubUser(get_engine()).bulk_upsert_users(session, to_upsert, audit)
            logger.info("Bulk upsert completed successfully")
        except Exception:
            logger.exception("Bulk upsert failed")
            raise

        logger.debug("sync_all_users() finished without error")