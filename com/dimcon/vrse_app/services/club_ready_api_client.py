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
        Fetches all users for the given chain by looping through paginated results.
        Returns:
            List[dict]: List of user/member records.
        """
        url = f"{self.BASE_URL}/users/find"
        all_users = []
        page = 1  # start from page 1
        per_page = 100  # adjust as needed; 100 is the assumed default page size

        while True:
            params = self.params.copy()
            params.update({
                "page": page,
                "limit": per_page
            })

            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json().get("users", [])
                logger.info(f"Fetched {len(data)} users from page {page}")

                if not data:
                    break

                all_users.extend(data)

                # If the data returned is less than per_page, we reached the last page.
                if len(data) < per_page:
                    break

                page += 1
            except requests.RequestException as e:
                logger.error(f"Failed to fetch page {page} of users: {e}")
                raise

        return all_users
