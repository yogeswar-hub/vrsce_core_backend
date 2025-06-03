from com.dimcon.vrse_app.services.club_ready_api_client import ClubReadyAPIClient
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.resources.vrse.vrse_club_active_members import ClubActiveMember  # updated import
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubReadyActiveUsersService:
    @staticmethod
    def sync_active_users(activity_date: str, activity_operator: str, audit: dict = None):
        """
        Fetch active users from ClubReady API and store them in the database.
        
        Args:
            activity_date (str): The activity date (e.g., "01-01-2023").
            activity_operator (str): Operator (e.g., "GT").
            audit (dict): Audit information with keys 'created_by' and 'updated_by'.
        """
        if audit is None:
            audit = {
                "created_by": "system",
                "updated_by": "system",
                "sub": "system"
            }
        # Initialize API client with your credentials.
        api_client = ClubReadyAPIClient(api_key="85b59f92-615a-4f89-8dbf-39bd62f5344c", chain_id=658)
        # Call the new endpoint to fetch active users.
        users_data = api_client.fetch_active_users(activity_date, activity_operator)
        logger.info(f"Fetched {len(users_data)} active users from API.")
        
        # Insert active users into database using the ClubActiveMember model.
        engine = get_engine()
        db_util = DBSessionUtil(engine)
        with db_util.session_scope() as session:
            ClubActiveMember.bulk_insert_active_members(session, users_data)
            session.commit()
            logger.info(f"Inserted {len(users_data)} active users into the database.")