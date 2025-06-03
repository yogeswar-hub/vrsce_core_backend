# clubready_api_client.py

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def fetch_users(self, page: int, limit: int = 100) -> List[dict]:
        """
        Fetches users for a specific page.

        Args:
            page (int): Page number to fetch.
            limit (int): Number of users per page (default is 100).

        Returns:
            List[dict]: List of user records for the page.
        """
        url = f"{self.BASE_URL}/users/find"
        params = self.params.copy()
        params.update({
            "page": page,
            "limit": limit
        })

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json().get("users", [])
            logger.info(f"Fetched {len(data)} users from page {page}")

            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch page {page} of users: {e}")
            raise

    def fetch_all_users_parallel(self, total_pages: int, limit: int = 100) -> List[dict]:
        """
        Fetches all users for the given chain by fetching multiple pages in parallel.

        Args:
            total_pages (int): Total number of pages to fetch.
            limit (int): Number of users per page (default is 100).

        Returns:
            List[dict]: List of all user records.
        """
        users = []
        # Adjust the number of workers as appropriate (e.g. 10)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_page = {
                executor.submit(self.fetch_users, page, limit): page
                for page in range(1, total_pages + 1)
            }
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    page_users = future.result()
                    users.extend(page_users)
                except Exception as err:
                    logger.error(f"Error fetching page {page}: {err}")
        return users

    def fetch_all_users(self) -> List[dict]:
        """
        Fetches all users for the given chain by looping through paginated results.
        Returns:
            List[dict]: List of user/member records.
        """
        url = f"{self.BASE_URL}/users/find"
        all_users = []
        page = 1  # start from page 1
        per_page = 100   # adjust as needed; 100 is the assumed default page size

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

    def fetch_all_users_parallel_dynamic(self, limit: int = 100, batch_size: int = 10) -> List[dict]:
        """
        Fetches all users for the given chain by fetching multiple pages in parallel,
        with a dynamic approach to determine the number of pages to fetch in each batch.

        Args:
            limit (int): Number of users per page (default is 100).
            batch_size (int): Number of pages to fetch in parallel in each batch (default is 10).

        Returns:
            List[dict]: List of all user records.
        """
        all_users = []
        current_page = 1
        while True:
            pages = list(range(current_page, current_page + batch_size))
            batch_results = {}
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                future_to_page = {
                    executor.submit(self.fetch_users, page, limit): page for page in pages
                }
                for future in as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        users = future.result()
                        batch_results[page_num] = users
                    except Exception as err:
                        logger.error(f"Error fetching page {page_num}: {err}")
                        batch_results[page_num] = []

            # Sort pages in order and add their results
            for page in sorted(batch_results.keys()):
                users = batch_results[page]
                if not users or len(users) < limit:
                    # No more data: Append and break out of the loop.
                    all_users.extend(users)
                    return all_users
                else:
                    all_users.extend(users)
            current_page += batch_size

    def fetch_active_users(self, activity_date: str, activity_operator: str, segment: str = "Active", version: int = 2) -> list:
        """
        Fetches active users from ClubReady API using the provided parameters.
        
        Args:
            activity_date (str): The activity date (e.g., "01-01-2023").
            activity_operator (str): The operator for activity filtering (e.g., "GT").
            segment (str): The segment to filter users (default is "Active").
            version (int): API version number (default is 2).
            
        Returns:
            list: A list of user dictionaries.
        """
        url = f"{self.BASE_URL}/users"
        params = self.params.copy()
        params.update({
            "ActivityDate": activity_date,
            "ActivityOperator": activity_operator,
            "Segment": segment,
            "Version": version
        })
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()  # Expected response is a list of user dicts
            logger.info(f"Fetched {len(data)} active users.")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch active users: {e}")
            raise
