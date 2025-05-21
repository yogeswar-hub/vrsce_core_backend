# clubready_api_client.py

import requests
from typing import List
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)


class ClubReadyAPIClient:
    """
    API Client for interacting with ClubReady endpoints.
    Handles location and user data sync.
    """

    BASE_URL = "https://clubready.com/api/current"

    def __init__(self, api_key: str, chain_id: int):
        self.api_key = api_key
        self.chain_id = chain_id
        self.params = {
            "ApiKey": self.api_key,
            "ChainId": self.chain_id
        }

    def fetch_club_locations(self) -> List[dict]:
        """
        Fetches all club locations for the given chain.

        Returns:
            List[dict]: List of club/location records.
        """
        url = f"{self.BASE_URL}/corp/{self.chain_id}/clubs"

        try:
            response = requests.get(url, params=self.params)
            response.raise_for_status()
            logger.info(" Fetched club locations from ClubReady API")
            return response.json()  # Expected to be a list of clubs
        except requests.RequestException as e:
            logger.error(f" Failed to fetch club locations: {e}")
            raise

    def fetch_all_users(self) -> List[dict]:
        """
        Fetches all users for the given chain.

        Returns:
            List[dict]: List of user/member records.
        """
        url = f"{self.BASE_URL}/users/find"

        try:
            response = requests.get(url, params=self.params)
            response.raise_for_status()
            logger.info(" Fetched users from ClubReady API")
            return response.json().get("users", [])  # Handles nested 'users' key if present
        except requests.RequestException as e:
            logger.error(f" Failed to fetch users: {e}")
            raise
