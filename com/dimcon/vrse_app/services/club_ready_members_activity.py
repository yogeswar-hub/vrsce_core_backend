from com.dimcon.vrse_app.resources.vrse.vrse_club_members_activity import ClubMemberActivity
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager
from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient

logger = LoggerManager.setup_logger(__name__)

class ClubReadyActivityUsersService:
    @staticmethod
    def sync_all_user_segments(activity_date: str, activity_operator: str, api_client):
        logger.info(f" Filtering users with activity_date {activity_operator} {activity_date}")
        segments = ["Active", "Inactive", "Prospects", "PastDue"]
        all_users = []

        for segment in segments:
            try:
                logger.info(f"📦 Fetching segment: {segment}")
                users = api_client.fetch_users_activity(activity_date, activity_operator,segment)
                logger.info(f"→ {len(users)} users fetched from segment '{segment}'")
                for u in users:
                    u["Segment"] = segment
                all_users.extend(users)
            except Exception as e:
                logger.warning(f"⚠️ Failed fetching segment {segment}: {e}")

        logger.info(f"✅ Total users from all segments: {len(all_users)}")
        return all_users
        
